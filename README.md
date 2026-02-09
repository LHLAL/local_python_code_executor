# Dify-Compatible Sandbox Executor (Enterprise Edition)

一个高性能、安全、可扩展的多语言代码执行沙箱，完全对齐 **dify-sandbox** API 标准，专为生产环境和国产化（麒麟 V10/红帽）环境优化。

## 核心特性

- **Dify 接口对齐**: 深度适配 `v1/sandbox/run` 接口，支持 `language`, `code` 等核心参数。
- **多语言执行引擎**: 
  - **Python**: 支持 `main(obj)` 结构化调用，适配 Python 3.9/3.10+。
  - **Node.js**: 支持 `async/await` 异步执行，适配 Node.js 18/20+。
- **生产级日志系统**:
  - **请求审计**: 自动记录每次请求的语言、耗时、执行结果及错误详情。
  - **Docker 友好**: 日志同步输出到标准输出（Stdout）和本地文件，支持 `docker logs` 实时查看。
- **安全与隔离**: 资源配额限制（CPU/内存/文件）及基于 AST 的包导入白名单拦截。
- **高性能**: 集成 Gunicorn 并发管理，支持请求队列与过载保护。
- **可观测性**: 原生提供 Prometheus `/metrics` 接口。

---

## 接口指南

### 代码执行接口
- **URL**: `POST /v1/sandbox/run`
- **Body**:
```json
{
  "language": "python3",
  "code": "import json\nfrom base64 import b64decode\ndef main(obj): return f'Result: {obj.get(\"x\") + obj.get(\"y\")}'\ninputs_obj=json.loads(b64decode('eyInIjogMTAsICJ5IjogMjB9').decode('utf-8'))\nprint(main(inputs_obj))"
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

---

## 日志与监控

### 1. 查看日志
日志默认输出到控制台，可通过 Docker 查看：
```bash
docker logs -f <container_id>
```
日志文件默认路径：`/home/ubuntu/py-sandbox-executor/sandbox.log`（可在 `config.yaml` 中配置）。

### 2. Prometheus 指标
访问 `http://localhost:8000/metrics` 获取实时执行指标。

---

## 自动化测试

项目内置了 `test_sandbox.py`，涵盖以下核心场景：
- **健康检查**
- **Dify 风格代码执行 (Python & Node.js)**
- **包白名单安全拦截**
- **资源超时限制**
- **高并发队列拒绝 (429)**

**执行测试**:
```bash
python3 test_sandbox.py
```
