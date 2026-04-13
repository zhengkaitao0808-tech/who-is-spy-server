# -*- coding: utf-8 -*-
"""
games/routing.py - WebSocket 路由配置
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # 房间 WebSocket 连接
    re_path(r'ws/room/(?P<room_code>\w+)/$', consumers.RoomConsumer.as_asgi()),
]
