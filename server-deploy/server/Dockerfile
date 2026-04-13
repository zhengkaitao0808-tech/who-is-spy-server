# -*- coding: utf-8 -*-
"""
Dockerfile for WhoIsSpy Django project.
微信云托管 Docker 部署配置
"""

FROM python:3.11-slim

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=config.settings

# 设置工作目录
WORKDIR /app

# 安装系统依赖（MySQL客户端）
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . /app/

# 收集静态文件
RUN python manage.py collectstatic --noinput || true

# 创建数据库迁移（如果需要）
RUN python manage.py makemigrations --noinput || true

# 暴露端口
EXPOSE 8000

# 启动命令 - 使用 Daphne ASGI 服务器
# Daphne 是性能和兼容性最佳的 ASGI 服务器，支持 HTTP 和 WebSocket
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
