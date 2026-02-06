# Dify-Compatible Sandbox Executor (Enterprise Edition)

一个高性能、安全、可扩展的多语言代码执行沙箱，完全对齐 **dify-sandbox** API 标准，专为生产环境和国产化（麒麟 V10/红帽）环境优化。

## 核心特性

- **Dify 接口对齐**: 深度适配 `v1/sandbox/run` 接口，支持 `language`, `code`, `obj` (Base64) 等核心参数。
- **多语言执行引擎**: 
  - **Python**: 支持 `main(obj)` 结构化调用，适配 Python 3.9/3.10+。
  - **Node.js**: 支持 `async/await` 异步执行，适配 Node.js 18/20+。
- **生产级安全隔离**:
  - **资源配额**: 严格限制 CPU 时间、内存使用量、文件写入大小。
  - **依赖审计**: 基于静态分析（AST）的 `import/require` 包白名单拦截机制。
  - **非 Root 运行**: 容器内采用普通用户权限执行，防止逃逸。
- **高可用保障**:
  - **并发控制**: 集成 Gunicorn 多进程管理，API 层支持信号量并发限制。
  - **过载保护**: 内置请求队列，超载时自动返回 `429 Too Many Requests`。
- **全面可观测性**: 提供 `/metrics` 接口，原生对接 Prometheus 监控。

---

## 接口指南

### 1. 代码执行接口
- **URL**: `POST /v1/sandbox/run`
- **Body**:
```json
{
  "language": "python3",
  "code": "def main(obj): return f'Result: {obj.get(\"x\") + obj.get(\"y\")}'",
  "obj": "eyJ4IjogMTAsICJ5IjogMjB9"
}
```
- **Response**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "stdout": "Result: 30\n",
    "error": ""
  }
}
```

### 2. 复杂 Python 场景示例
通过 `obj` 传入复杂嵌套字典，代码内部处理逻辑并返回 JSON 字符串作为多出参：
```python
# code 内容
import json
def main(obj):
    params = obj.get('params', {})
    result = params.get('a') * params.get('b')
    return json.dumps({"calc_result": result, "status": "ok"})
```

---

## 自动化测试

项目内置了 `test_sandbox.py`，涵盖以下 7 大核心场景：
1. **健康检查**: 验证系统存活状态。
2. **基础执行**: 验证简单的代码输出。
3. **复杂 I/O**: 验证多参数传入、Base64 解码及结构化数据返回。
4. **Node.js 异步**: 验证 Node.js 异步函数执行。
5. **安全拦截**: 验证非法包（如 `os`）导入拦截。
6. **资源限制**: 验证执行超时自动终止。
7. **压力测试**: 验证高并发下的队列保护机制。

**执行测试**:
```bash
python3 test_sandbox.py
```

---

## 部署说明

### 1. 配置文件 (`config.yaml`)
支持通过挂载外部配置文件动态调整：
- `server.max_concurrent_requests`: 最大并行执行数。
- `runtimes.python3.allowed_packages`: 允许导入的包列表。

### 2. Docker 部署 (红帽/麒麟适配)
```bash
docker build -t py-sandbox-executor .
docker run -d -p 8000:8000 \
  -v $(pwd)/config.yaml:/app/config.yaml \
  py-sandbox-executor
```
