# -*- coding: utf-8 -*-
"""
rooms app 配置
"""

from django.apps import AppConfig


class RoomsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.rooms'
    verbose_name = '房间管理'
