# -*- coding: utf-8 -*-
"""
games app 配置
"""

from django.apps import AppConfig


class GamesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.games'
    verbose_name = '游戏管理'
