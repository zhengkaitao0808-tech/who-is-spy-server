# -*- coding: utf-8 -*-
"""
users/urls.py - 用户模块路由配置
"""

from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # 微信登录
    path('login/', views.WeChatLoginView.as_view(), name='login'),
    
    # 用户信息
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    
    # 用户详情
    path('<str:openid>/', views.UserDetailView.as_view(), name='detail'),
]
