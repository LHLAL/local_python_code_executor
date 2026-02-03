import asyncio
import httpx
import time

async def send_request(client, i):
    code = "import time; time.sleep(0.5); print('Task done')"
    try:
        response = await client.post("http://localhost:8000/v1/sandbox/run", json={"code": code}, timeout=15)
        print(f"Request {i}: Status {response.status_code}")
    except Exception as e:
        print(f"Request {i}: Failed {str(e)}")

async def main():
    async with httpx.AsyncClient() as client:
        # 快速发送 100 个请求
        tasks = [send_request(client, i) for i in range(100)]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
