# Python Sandbox Executor (Production Ready v3)

一个支持动态配置、高并发控制和资源隔离的生产级 Python 代码执行器。

## 新增特性

- **动态配置支持**: 支持通过 `config.yaml` 配置服务参数。
- **并发与队列控制**:
  - `max_concurrent_requests`: 限制同时执行代码的最大请求数。
  - `max_queue_size`: 当并发达到上限时，允许进入队列等待的最大请求数。
  - **自动拒绝**: 超过队列长度的请求将直接返回 `429 Too Many Requests`。
- **配置驱动的资源限制**: 动态调整 CPU、内存、文件大小和超时时间。
- **Docker 挂载生效**: 配置文件和端口可由外部挂载动态决定。

## 配置文件说明 (config.yaml)

```yaml
server:
  port: 8000
  workers: 4                # Gunicorn Worker 数量
  max_concurrent_requests: 10 # API 层最大并发执行数
  max_queue_size: 20        # 队列等待上限

resource_limits:
  cpu_time_limit: 10        # CPU 时间限制 (秒)
  memory_limit_mb: 256      # 内存限制 (MB)
  file_size_limit_kb: 1024   # 文件大小限制 (KB)
  timeout: 10               # 进程强制杀掉的超时时间
```

## 部署与挂载

### Docker 启动并挂载配置
```bash
docker run -d \
  --name sandbox \
  -p 8080:8000 \
  -v $(pwd)/config.yaml:/app/config.yaml \
  py-sandbox-prod
```

## 可观测性
- `/metrics`: 提供 Prometheus 监控数据，包含 `sandbox_concurrent_requests` (并发执行中) 和 `sandbox_queue_size` (队列中等待)。
- `/v1/sandbox/health`: 查看当前生效的配置和健康状态。
