import time
import asyncio
from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from .executor import ExecutorFactory
from .config import config
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

app = FastAPI(title="Multi-Runtime Sandbox")

# 并发控制
semaphore = asyncio.Semaphore(config["server"]["max_concurrent_requests"])
current_waiting = 0

# 指标
REQUEST_COUNT = Counter("sandbox_requests_total", "Total requests", ["method", "endpoint", "status", "runtime"])
REQUEST_LATENCY = Histogram("sandbox_request_duration_seconds", "Latency", ["endpoint", "runtime"])
CONCURRENT_GAUGE = Gauge("sandbox_concurrent_requests", "Current concurrent requests")
QUEUE_GAUGE = Gauge("sandbox_queue_size", "Current requests in queue")

class RunRequest(BaseModel):
    code: str
    runtime: str = "python3"
    obj: Optional[str] = None # Base64 encoded string

class RunResponseData(BaseModel):
    stdout: str
    error: str

class RunResponse(BaseModel):
    code: int
    message: str
    data: RunResponseData

@app.get("/v1/sandbox/health")
async def health_check():
    return {"status": "healthy", "runtimes": config["runtimes"]}

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/v1/sandbox/run", response_model=RunResponse)
async def run_code(request: RunRequest):
    global current_waiting
    
    runtime = request.runtime
    if runtime not in config["runtimes"] or not config["runtimes"][runtime].get("enabled", False):
        raise HTTPException(status_code=400, detail=f"Runtime {runtime} is not supported or enabled")

    if current_waiting >= config["server"]["max_queue_size"]:
        REQUEST_COUNT.labels(method="POST", endpoint="/run", status="rejected_queue_full", runtime=runtime).inc()
        raise HTTPException(status_code=429, detail="Server busy: queue full")

    current_waiting += 1
    QUEUE_GAUGE.set(current_waiting)
    
    try:
        async with semaphore:
            current_waiting -= 1
            QUEUE_GAUGE.set(current_waiting)
            CONCURRENT_GAUGE.inc()
            
            REQUEST_COUNT.labels(method="POST", endpoint="/run", status="received", runtime=runtime).inc()
            
            start_time = time.time()
            
            # 获取对应的执行器
            runner = ExecutorFactory.get_runner(runtime)
            
            # 在线程池中执行同步的 runner.run
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, runner.run, request.code, request.obj, runtime)
            
            latency = time.time() - start_time
            REQUEST_LATENCY.labels(endpoint="/run", runtime=runtime).observe(latency)
            
            CONCURRENT_GAUGE.dec()
            status = "success" if result["success"] else "error"
            REQUEST_COUNT.labels(method="POST", endpoint="/run", status=status, runtime=runtime).inc()
            
            return RunResponse(
                code=0,
                message="success",
                data=RunResponseData(stdout=result["stdout"], error=result["error"])
            )
    except Exception as e:
        if current_waiting > 0: current_waiting -= 1
        CONCURRENT_GAUGE.set(0)
        REQUEST_COUNT.labels(method="POST", endpoint="/run", status="internal_error", runtime=runtime).inc()
        return RunResponse(
            code=500,
            message="internal_error",
            data=RunResponseData(stdout="", error=str(e))
        )
