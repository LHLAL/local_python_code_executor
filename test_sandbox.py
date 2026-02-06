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

    def test_03_python_complex_io(self):
        """场景3: 复杂 Python 场景 - 多入参、多出参、结构化 JSON 输出"""
        # 模拟多个输入参数
        obj = {
            "user_info": {"id": 1, "name": "Manus"},
            "params": {"a": 10, "b": 20},
            "action": "multiply"
        }
        obj_b64 = base64.b64encode(json.dumps(obj).encode()).decode()
        
        # 模拟复杂逻辑和结构化输出
        code = """
import json
def main(obj):
    user = obj.get('user_info', {})
    params = obj.get('params', {})
    action = obj.get('action')
    
    # 模拟计算
    result_val = 0
    if action == 'multiply':
        result_val = params.get('a', 0) * params.get('b', 0)
    
    # 模拟多个输出结果（通过 JSON 字符串）
    output = {
        "status": "processed",
        "greeting": f"Hello {user.get('name')}",
        "result": result_val,
        "meta": {"timestamp": 123456789}
    }
    return json.dumps(output)
"""
        payload = {
            "language": "python3",
            "code": code,
            "obj": obj_b64
        }
        response = requests.post(f"{self.BASE_URL}/v1/sandbox/run", json=payload)
        res_json = response.json()
        self.assertEqual(res_json["code"], 0)
        
        # 解析 stdout 中的 JSON 输出
        output_data = json.loads(res_json["data"]["stdout"].strip())
        self.assertEqual(output_data["result"], 200)
        self.assertEqual(output_data["greeting"], "Hello Manus")

    def test_04_nodejs_complex(self):
        """场景4: Node.js 复杂场景 - Async/Await 与结构化输出"""
        obj = {"x": 5, "y": 10}
        obj_b64 = base64.b64encode(json.dumps(obj).encode()).decode()
        
        code = """
async function main(obj) {
    const sum = obj.x + obj.y;
    return JSON.stringify({
        sum: sum,
        success: true,
        runtime: "nodejs"
    });
}
"""
        payload = {
            "language": "nodejs",
            "code": code,
            "obj": obj_b64
        }
        response = requests.post(f"{self.BASE_URL}/v1/sandbox/run", json=payload)
        res_json = response.json()
        output_data = json.loads(res_json["data"]["stdout"].strip())
        self.assertEqual(output_data["sum"], 15)

    def test_05_security_whitelist(self):
        """场景5: 安全性测试 - 包白名单拦截"""
        # os 模块默认不被允许
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
            return requests.post(f"{self.BASE_URL}/v1/sandbox/run", json={"code": "import time; time.sleep(1)"})
        
        results = []
        threads = [threading.Thread(target=lambda: results.append(send_req())) for _ in range(150)]
        for t in threads: t.start()
        for t in threads: t.join()
        
        status_codes = [r.status_code for r in results]
        # 应该存在 429 请求被拒绝的情况（根据默认配置并发10+队列20）
        self.assertIn(429, status_codes)

if __name__ == "__main__":
    unittest.main()
