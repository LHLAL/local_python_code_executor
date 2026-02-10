#!/bin/bash

# 加载配置中的参数
PORT=$(python3 -c "import yaml; print(yaml.safe_load(open('config.yaml'))['server']['port'])" 2>/dev/null || echo 8000)
WORKERS=$(python3 -c "import yaml; print(yaml.safe_load(open('config.yaml'))['server']['workers'])" 2>/dev/null || echo 4)
ENGINE=$(python3 -c "import yaml; print(yaml.safe_load(open('config.yaml'))['server'].get('engine', 'uvicorn'))" 2>/dev/null || echo uvicorn)

echo "Starting Sandbox Executor with $ENGINE engine on port $PORT with $WORKERS workers..."

if [ "$ENGINE" == "granian" ]; then
    # 使用 Granian 启动 (高性能 Rust 基础的 HTTP 服务器)
    # 修正参数: ASGI/RSGI 下 --blocking-threads 必须为 1
    exec granian --interface asgi --port $PORT --host 0.0.0.0 --workers $WORKERS --blocking-threads 1 app.main:app
else
    # 使用 Gunicorn + Uvicorn 启动
    exec gunicorn app.main:app \
        --workers "$WORKERS" \
        --worker-class uvicorn.workers.UvicornWorker \
        --bind "0.0.0.0:$PORT" \
        --access-log-file - \
        --error-log-file -
fi
