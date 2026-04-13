# -*- coding: utf-8 -*-
"""
URL configuration for WhoIsSpy project.
根路由配置
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Django admin
    path('admin/', admin.site.urls),
    
    # API routes
    path('api/user/', include('apps.users.urls')),
    path('api/room/', include('apps.rooms.urls')),
    path('api/game/', include('apps.games.urls')),
    
    # Health check endpoint
    path('health/', lambda request: __import__('django.http', fromlist=['JsonResponse']).JsonResponse({'status': 'ok'})),
]

# 开发环境静态文件服务
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
