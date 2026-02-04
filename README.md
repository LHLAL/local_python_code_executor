# Multi-Runtime Sandbox Executor (V4 Final)

一个高性能、安全、可扩展的多语言代码执行器，支持 Python 和 Node.js，专为生产环境和国产化系统（麒麟 V10）设计。

## 核心特性

- **多语言支持**: 插件化架构，支持 Python3、Python3.11 及 Node.js。
- **`main(obj)` 模式**: 支持通过函数入口调用，自动处理 Base64 解码的 JSON 输入。
- **生产级安全隔离**: 
  - 使用 `ulimit` (resource) 限制 CPU、内存、文件和进程数。
  - 针对 Node.js 22 优化了虚拟内存预留限制。
- **高并发保障**: 基于信号量和请求队列的流量控制，超出负载自动返回 `429`。
- **可观测性**: 集成 Prometheus 指标接口 (`/metrics`)。
- **动态配置**: 支持外部 `config.yaml` 挂载。

---

## 接口文档

### 1. 健康检查
- **URL**: `/v1/sandbox/health`
- **Method**: `GET`
- **Response**: 返回当前支持的运行时及配置状态。

### 2. 代码执行
- **URL**: `/v1/sandbox/run`
- **Method**: `POST`
- **Request Body**:
| 参数 | 类型 | 必选 | 说明 |
| :--- | :--- | :--- | :--- |
| `code` | string | 是 | 用户代码内容 |
| `runtime` | string | 否 | 运行时环境，默认 `python3`。可选: `python3`, `python311`, `nodejs` |
| `obj` | string | 否 | Base64 编码的 JSON 字符串，将作为参数传递给 `main(obj)` |

- **Response Body**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "stdout": "执行输出内容",
    "error": "错误详情（如果有）"
  }
}
```

### 3. 监控指标
- **URL**: `/metrics`
- **Method**: `GET`
- **Metrics**:
  - `sandbox_concurrent_requests`: 当前并发执行数。
  - `sandbox_queue_size`: 当前队列积压数。
  - `sandbox_requests_total`: 累计请求计数。

---

## 测试用例

### Python `main(obj)` 示例
**Request**:
```json
{
  "runtime": "python3",
  "code": "def main(obj):\n    return f'Hello {obj[\"name\"]}'",
  "obj": "eyJuYW1lIjogIk1hbnVzIn0="
}
```
**Output**: `Hello Manus`

### Node.js `main(obj)` 示例
**Request**:
```json
{
  "runtime": "nodejs",
  "code": "async function main(obj) { return 'NodeJS: ' + obj.id; }",
  "obj": "eyJpZCI6IDEyM30="
}
```
**Output**: `NodeJS: 123`

---

## 自动化测试

项目根目录下提供了 `test_sandbox.py`，包含完整的单元测试：
1. **基础功能测试**: 验证 Python/NodeJS 正常输出。
2. **Base64 参数测试**: 验证 `main(obj)` 参数传递。
3. **资源限制测试**: 验证超时 (Timeout) 和内存溢出 (OOM) 拦截。
4. **并发压力测试**: 验证 429 队列拒绝机制。

**运行测试**:
```bash
python3 test_sandbox.py
```

---

## 部署说明

### Docker 部署
```bash
docker build -t sandbox-v4 .
docker run -d -p 8000:8000 -v $(pwd)/config.yaml:/app/config.yaml sandbox-v4
```

### 4. 包白名单安全机制 (Security Whitelist)
服务会通过静态分析（Python 使用 `ast`，Node.js 使用正则）检查代码中的依赖。
- **拦截逻辑**: 只有在 `config.yaml` 的 `allowed_packages` 列表中定义的包才允许被 `import` 或 `require`。
- **错误提示**: 若使用未授权的包，返回 `{"data": {"error": "Unsupported package: xxx"}}`。
