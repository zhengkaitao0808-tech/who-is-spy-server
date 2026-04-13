# -*- coding: utf-8 -*-
"""
ASGI config for WhoIsSpy project.
Django Channels ASGI 配置，支持 WebSocket
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# 获取 Django ASGI 应用
django_asgi_app = get_asgi_application()

# 导入各 app 的 websocket 路由
from apps.games.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    # HTTP 请求（普通 Django 请求）
    'http': django_asgi_app,
    
    # WebSocket 请求
    'websocket': AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
