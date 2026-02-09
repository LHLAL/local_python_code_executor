import unittest
import requests
import base64
import json
import time
import threading

class TestSandboxExecutor(unittest.TestCase):
    BASE_URL = "http://localhost:8000"

    def test_01_health_check(self):
        """场景1: 健康检查接口验证"""
        response = requests.get(f"{self.BASE_URL}/v1/sandbox/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")

    def test_02_python_basic(self):
        """场景2: Python 基础代码执行"""
        payload = {"language": "python3", "code": "print('Hello World')"}
        response = requests.post(f"{self.BASE_URL}/v1/sandbox/run", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["stdout"].strip(), "Hello World")

    def test_03_python_complex_dify_style(self):
        """场景3: 复杂 Python 场景 - 对齐 Dify 逻辑（所有内容都在 code 中）"""
        obj_b64 = base64.b64encode(json.dumps({"x": 10, "y": 20}).encode()).decode()
        
        # 模拟用户提供的 code 逻辑
        code = f"""
import json
from base64 import b64decode

def main(obj):
    return f'Result: {{obj.get("x") + obj.get("y")}}'

inputs_obj = json.loads(b64decode('{obj_b64}').decode('utf-8'))
output_obj = main(inputs_obj)
print(output_obj)
"""
        payload = {
            "language": "python3",
            "code": code
        }
        response = requests.post(f"{self.BASE_URL}/v1/sandbox/run", json=payload)
        res_json = response.json()
        self.assertEqual(res_json["code"], 0)
        self.assertEqual(res_json["data"]["stdout"].strip(), "Result: 30")

    def test_04_nodejs_complex_dify_style(self):
        """场景4: Node.js 复杂场景 - 逻辑整合进 code"""
        obj_b64 = base64.b64encode(json.dumps({"name": "Manus"}).encode()).decode()
        
        # Node.js 代码
        code = f"""
const obj = JSON.parse(Buffer.from('{obj_b64}', 'base64').toString('utf-8'));
function main(o) {{
    return "Hello " + o.name;
}}
console.log(main(obj));
"""
        payload = {
            "language": "nodejs",
            "code": code
        }
        response = requests.post(f"{self.BASE_URL}/v1/sandbox/run", json=payload)
        res_json = response.json()
        # 如果 Node.js 未安装，可能返回错误，这里做个兼容判断
        if "Unsupported language" not in res_json["data"]["error"]:
            self.assertEqual(res_json["data"]["stdout"].strip(), "Hello Manus")

    def test_05_security_whitelist(self):
        """场景5: 安全性测试 - 包白名单拦截"""
        payload = {"language": "python3", "code": "import os\nprint(os.name)"}
        response = requests.post(f"{self.BASE_URL}/v1/sandbox/run", json=payload)
        self.assertIn("Unsupported package", response.json()["data"]["error"])

    def test_06_resource_limit_timeout(self):
        """场景6: 资源限制测试 - 执行超时"""
        payload = {"language": "python3", "code": "import time\ntime.sleep(15)"}
        response = requests.post(f"{self.BASE_URL}/v1/sandbox/run", json=payload)
        self.assertIn("Timeout", response.json()["data"]["error"])

    def test_07_concurrent_pressure(self):
        """场景7: 高并发压力测试 - 队列与拒绝"""
        def send_req():
            try:
                return requests.post(f"{self.BASE_URL}/v1/sandbox/run", json={"language": "python3", "code": "import time; time.sleep(1)"}, timeout=10)
            except:
                return None
        
        results = []
        threads = [threading.Thread(target=lambda: results.append(send_req())) for _ in range(100)]
        for t in threads: t.start()
        for t in threads: t.join()
        
        status_codes = [r.status_code for r in results if r is not None]
        self.assertIn(429, status_codes)

if __name__ == "__main__":
    unittest.main()
