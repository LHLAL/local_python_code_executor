from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

from .executor import ExecutorFactory
from .config import config

app = FastAPI(title="Dify-Standard Sandbox Executor")

# Prometheus Metrics
REQUESTS_TOTAL = Counter("sandbox_requests_total", "Total sandbox requests", ["language", "endpoint"])
REQUEST_DURATION = Histogram("sandbox_request_duration_seconds", "Sandbox request duration", ["language"])
CONCURRENT_REQUESTS = Gauge("sandbox_concurrent_requests", "Current concurrent requests")
QUEUE_SIZE = Gauge("sandbox_queue_size", "Current queue size")

# 线程池和信号量控制并发
executor_pool = ThreadPoolExecutor(max_workers=config["server"]["workers"])
semaphore = asyncio.Semaphore(config["server"]["max_concurrent_requests"])
current_waiting = 0

class RunRequest(BaseModel):
    language: str = "python3"
    code: str
    preload: Optional[str] = ""

class RunResponseData(BaseModel):
    stdout: str
    error: str

class RunResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: RunResponseData

@app.get("/v1/sandbox/health")
async def health():
    return {
        "status": "healthy",
        "runtimes": config["runtimes"]
    }

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/v1/sandbox/run", response_model=RunResponse)
async def run_code(request: RunRequest):
    global current_waiting
    
    if request.language not in config["runtimes"]:
        if request.language == "python" and "python3" in config["runtimes"]:
            request.language = "python3"
        else:
            return RunResponse(
                code=400, 
                message=f"Unsupported language: {request.language}", 
                data=RunResponseData(stdout="", error=f"Unsupported language: {request.language}")
            )

    if current_waiting >= config["server"]["max_queue_size"]:
        raise HTTPException(status_code=429, detail="Too Many Requests: Queue Full")

    current_waiting += 1
    QUEUE_SIZE.set(current_waiting)
    
    REQUESTS_TOTAL.labels(language=request.language, endpoint="/run").inc()
    
    try:
        async with semaphore:
            current_waiting -= 1
            QUEUE_SIZE.set(current_waiting)
            CONCURRENT_REQUESTS.inc()
            
            start_time = time.time()
            
            loop = asyncio.get_event_loop()
            runner = ExecutorFactory.get_runner(request.language)
            
            # 执行代码，不再传递 obj 参数
            result = await loop.run_in_executor(
                executor_pool, 
                runner.run, 
                request.code, 
                request.language
            )
            
            duration = time.time() - start_time
            REQUEST_DURATION.labels(language=request.language).observe(duration)
            
            CONCURRENT_REQUESTS.dec()
            
            return RunResponse(
                code=0,
                message="success",
                data=RunResponseData(
                    stdout=result.get("stdout", ""),
                    error=result.get("error", "")
                )
            )
    except Exception as e:
        if current_waiting > 0:
            current_waiting -= 1
            QUEUE_SIZE.set(current_waiting)
        CONCURRENT_REQUESTS.set(0)
        return RunResponse(
            code=500, 
            message="Internal Server Error", 
            data=RunResponseData(stdout="", error=str(e))
        )
