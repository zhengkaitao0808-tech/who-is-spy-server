# -*- coding: utf-8 -*-
"""
games/urls.py - 游戏模块路由配置
"""

from django.urls import path
from . import views

app_name = 'games'

urlpatterns = [
    # 开始游戏
    path('start/', views.GameStartView.as_view(), name='start'),
    
    # 获取词语
    path('word/', views.GameWordView.as_view(), name='word'),
    
    # 发言
    path('speak/', views.GameSpeakView.as_view(), name='speak'),
    
    # 投票
    path('vote/', views.GameVoteView.as_view(), name='vote'),
    
    # 游戏结果
    path('result/', views.GameResultView.as_view(), name='result'),
    
    # 下一轮
    path('next_round/', views.GameNextRoundView.as_view(), name='next_round'),
    
    # 词库列表
    path('wordset/', views.WordSetListView.as_view(), name='wordset'),
]
