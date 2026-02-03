# 使用麒麟 V10 基础镜像 (基于 RedHat/CentOS)
FROM centos:7

# 设置工作目录
WORKDIR /app

# 安装 Python 3, Node.js 和必要工具
# 注意：在 CentOS 7 上安装较新版本可能需要额外的 repo
RUN yum install -y epel-release && \
    yum install -y python3 python3-pip nodejs && \
    yum clean all

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# 复制应用代码和默认配置
COPY app/ ./app/
COPY config.yaml .
COPY entrypoint.sh .

# 赋予执行权限并创建非 root 用户
RUN chmod +x entrypoint.sh && useradd -m sandboxuser
USER sandboxuser

# 暴露端口
EXPOSE 8000

# 启动脚本
ENTRYPOINT ["./entrypoint.sh"]
