import unittest
import requests
import base64
import json
import time
import threading

class TestSandboxExecutor(unittest.TestCase):
    BASE_URL = "http://localhost:8000"

    def test_01_health_check(self):
        """测试健康检查接口"""
        response = requests.get(f"{self.BASE_URL}/v1/sandbox/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")

    def test_02_python_basic(self):
        """测试 Python 基础执行"""
        payload = {"runtime": "python3", "code": "print('Hello World')"}
        response = requests.post(f"{self.BASE_URL}/v1/sandbox/run", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["stdout"].strip(), "Hello World")

    def test_03_python_main_obj(self):
        """测试 Python main(obj) 和 Base64 输入"""
        obj = {"name": "Manus"}
        obj_b64 = base64.b64encode(json.dumps(obj).encode()).decode()
        payload = {
            "runtime": "python3",
            "code": "def main(obj): return f'Hello {obj[\"name\"]}'",
            "obj": obj_b64
        }
        response = requests.post(f"{self.BASE_URL}/v1/sandbox/run", json=payload)
        self.assertEqual(response.json()["data"]["stdout"].strip(), "Hello Manus")

    def test_04_nodejs_basic(self):
        """测试 Node.js 基础执行"""
        payload = {"runtime": "nodejs", "code": "console.log('NodeJS Works')"}
        response = requests.post(f"{self.BASE_URL}/v1/sandbox/run", json=payload)
        self.assertEqual(response.json()["data"]["stdout"].strip(), "NodeJS Works")

    def test_05_python_whitelist_block(self):
        """测试 Python 包白名单拦截 (os 不在白名单)"""
        payload = {"runtime": "python3", "code": "import os\nprint(os.name)"}
        response = requests.post(f"{self.BASE_URL}/v1/sandbox/run", json=payload)
        self.assertEqual(response.json()["data"]["error"], "Unsupported package: os")

    def test_06_nodejs_whitelist_block(self):
        """测试 Node.js 包白名单拦截 (http 不在白名单)"""
        payload = {"runtime": "nodejs", "code": "const http = require('http');"}
        response = requests.post(f"{self.BASE_URL}/v1/sandbox/run", json=payload)
        self.assertEqual(response.json()["data"]["error"], "Unsupported package: http")

    def test_07_timeout(self):
        """测试执行超时"""
        payload = {"runtime": "python3", "code": "import time\ntime.sleep(15)"}
        response = requests.post(f"{self.BASE_URL}/v1/sandbox/run", json=payload)
        self.assertIn("Timeout", response.json()["data"]["error"])

    def test_08_concurrent_limit(self):
        """测试并发压力下的 429 拒绝"""
        def send_request():
            return requests.post(f"{self.BASE_URL}/v1/sandbox/run", json={"code": "import time; time.sleep(1)"})
        
        results = []
        threads = [threading.Thread(target=lambda: results.append(send_request())) for _ in range(100)]
        for t in threads: t.start()
        for t in threads: t.join()
        
        status_codes = [r.status_code for r in results]
        self.assertIn(429, status_codes)

if __name__ == "__main__":
    unittest.main()
