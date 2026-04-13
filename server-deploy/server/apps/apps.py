# -*- coding: utf-8 -*-
"""
apps/apps.py
Apps 配置
"""

from django.apps import AppConfig


class AppsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps'
    verbose_name = '应用集合'
