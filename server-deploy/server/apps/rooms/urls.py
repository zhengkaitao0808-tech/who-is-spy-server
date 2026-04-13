# -*- coding: utf-8 -*-
"""
rooms/urls.py - 房间模块路由配置
"""

from django.urls import path
from . import views

app_name = 'rooms'

urlpatterns = [
    # 房间列表
    path('list/', views.RoomListView.as_view(), name='list'),
    
    # 创建房间
    path('create/', views.RoomCreateView.as_view(), name='create'),
    
    # 加入房间
    path('join/', views.RoomJoinView.as_view(), name='join'),
    
    # 离开房间
    path('leave/', views.RoomLeaveView.as_view(), name='leave'),
    
    # 房间详情
    path('<str:room_code>/', views.RoomDetailView.as_view(), name='detail'),
    
    # 准备状态
    path('<str:room_code>/ready/', views.RoomReadyView.as_view(), name='ready'),
    
    # 在线状态
    path('<str:room_code>/online/', views.RoomOnlineView.as_view(), name='online'),
]
