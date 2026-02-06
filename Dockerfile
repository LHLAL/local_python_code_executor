# 假设基础镜像已预装 Python 3.10
# 示例：FROM your-custom-python310-base-image:latest
FROM registry.access.redhat.com/ubi8/ubi:latest

LABEL maintainer="Manus Sandbox Team"

WORKDIR /app

USER root

# 由于 Python 3.10 已预装，我们仅需安装：
# 1. 编译工具 (gcc/make) 用于部分 Python 库的编译安装
# 2. 进程管理工具 (procps-ng) 用于 entrypoint.sh 中的进程检查
# 3. Node.js 运行时
RUN dnf install -y \
    gcc \
    gcc-c++ \
    make \
    procps-ng \
    && dnf module install -y nodejs:18 \
    && dnf clean all

# 确保 python3 指向 3.10 (根据您基础镜像的实际路径调整)
# RUN ln -sf /usr/bin/python3.10 /usr/bin/python3

# 复制依赖并安装
COPY requirements.txt .
# 使用预装的 pip 运行
RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY . .

# 安全配置
RUN useradd -m sandboxuser && \
    chown -R sandboxuser:sandboxuser /app && \
    chmod +x /app/entrypoint.sh

EXPOSE 8000

USER sandboxuser

ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
