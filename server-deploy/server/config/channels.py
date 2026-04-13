# -*- coding: utf-8 -*-
"""
Channels routing configuration.
定义 WebSocket 的路由规则
"""

from django.urls import re_path
from apps.games import consumers

websocket_urlpatterns = [
    # 房间 WebSocket 连接
    re_path(r'ws/room/(?P<room_code>\w+)/$', consumers.RoomConsumer.as_asgi()),
]
