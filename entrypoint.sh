#!/bin/bash

# 加载配置中的参数，如果不存在则使用默认值
PORT=$(python3 -c "import yaml; print(yaml.safe_load(open('config.yaml'))['server']['port'])" 2>/dev/null || echo 8000)
WORKERS=$(python3 -c "import yaml; print(yaml.safe_load(open('config.yaml'))['server']['workers'])" 2>/dev/null || echo 4)

echo "Starting server on port $PORT with $WORKERS workers..."

exec gunicorn -w "$WORKERS" -k uvicorn.workers.UvicornWorker -b "0.0.0.0:$PORT" app.main:app
