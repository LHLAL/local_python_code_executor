# Dify-Compatible Sandbox Executor (High Performance Edition)

一个极高性能、安全、可扩展的多语言代码执行沙箱，完全对齐 **dify-sandbox** API 标准。

## 核心特性升级

- **高性能架构**:
  - **Granian**: 引入基于 Rust 的高性能 HTTP 服务器，提供比传统 Uvicorn 更高的吞吐量。
  - **Gunicorn + Uvicorn**: 支持经典的工业级进程管理方案，确保 Worker 常驻且稳定。
- **Dify 接口对齐**: 深度适配 `v1/sandbox/run` 接口，仅需 `language` 和 `code` 参数。
- **多语言执行**: 支持 Python 3.9/3.10+ 和 Node.js 18+。
- **生产级日志**: 记录请求耗时、状态，支持 `docker logs` 实时审计。
- **安全隔离**: CPU/内存配额限制，AST 级包导入白名单拦截。

---

## 快速开始

### 1. 配置引擎 (`config.yaml`)
您可以在配置文件中自由切换执行引擎：
```yaml
server:
  engine: "granian" # 可选: granian (推荐生产环境), uvicorn
  workers: 4
  max_concurrent_requests: 20
```

### 2. 启动服务
```bash
chmod +x entrypoint.sh
./entrypoint.sh
```

---

## 接口示例

### 代码执行
- **URL**: `POST /v1/sandbox/run`
- **Body**:
```json
{
  "language": "python3",
  "code": "import json\nfrom base64 import b64decode\ndef main(obj): return f'Result: {obj.get(\"x\") + obj.get(\"y\")}'\ninputs_obj=json.loads(b64decode('eyInIjogMTAsICJ5IjogMjB9').decode('utf-8'))\nprint(main(inputs_obj))"
}
```

---

## 自动化测试
运行全场景验证：
```bash
python3 test_sandbox.py
```
