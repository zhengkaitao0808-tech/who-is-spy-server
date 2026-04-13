# -*- coding: utf-8 -*-
"""
users/views.py - 用户视图
处理用户登录、个人信息等 API 请求
"""

import requests
import logging
from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import User
from .serializers import (
    UserSerializer, 
    UserLoginSerializer,
    UserProfileUpdateSerializer
)

logger = logging.getLogger(__name__)


class WeChatLoginView(APIView):
    """
    微信登录接口
    POST /api/user/login/
    
    小程序调用 wx.login() 获取 code，提交到后端换取 openid
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """处理微信登录"""
        serializer = UserLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'code': 400, 'msg': '参数错误', 'data': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        code = serializer.validated_data['code']
        nickname = serializer.validated_data.get('nickname', '')
        avatar = serializer.validated_data.get('avatar', '')
        
        try:
            # 调用微信接口获取 openid
            openid = self.get_wechat_openid(code)
            
            if not openid:
                return Response(
                    {'code': 401, 'msg': '微信登录失败', 'data': None},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # 获取或创建用户
            user, created = User.objects.get_or_create(
                openid=openid,
                defaults={
                    'nickname': nickname or f'用户{openid[-6:]}',
                    'avatar': avatar,
                }
            )
            
            # 更新用户信息（如果提供了新的昵称或头像）
            if not created and (nickname or avatar):
                if nickname:
                    user.nickname = nickname
                if avatar:
                    user.avatar = avatar
                user.save(update_fields=['nickname', 'avatar', 'updated_at'])
            
            # 生成简单的登录凭证（实际生产应使用 JWT）
            token = self.generate_token(user)
            
            return Response({
                'code': 0,
                'msg': '登录成功',
                'data': {
                    'token': token,
                    'user': UserSerializer(user).data
                }
            })
            
        except Exception as e:
            logger.error(f'微信登录异常: {str(e)}')
            return Response(
                {'code': 500, 'msg': '服务器错误', 'data': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get_wechat_openid(self, code):
        """
        调用微信接口获取 openid
        
        Args:
            code: wx.login() 返回的 code
            
        Returns:
            openid: 微信用户唯一标识
        """
        url = 'https://api.weixin.qq.com/sns/jscode2session'
        params = {
            'appid': settings.WECHAT_APPID,
            'secret': settings.WECHAT_SECRET,
            'js_code': code,
            'grant_type': 'authorization_code'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if 'openid' in data:
                return data['openid']
            else:
                logger.error(f'微信接口返回错误: {data}')
                return None
                
        except requests.RequestException as e:
            logger.error(f'请求微信接口失败: {str(e)}')
            return None
    
    def generate_token(self, user):
        """
        生成简单的登录凭证
        实际生产环境应使用 JWT 或其他安全方案
        """
        import hashlib
        import time
        
        # 使用 openid 和时间戳生成简单 token
        raw = f'{user.openid}:{int(time.time())}:{settings.SECRET_KEY}'
        token = hashlib.sha256(raw.encode()).hexdigest()
        
        # 更新用户最后登录时间
        from django.utils import timezone
        user.last_login_at = timezone.now()
        user.save(update_fields=['last_login_at'])
        
        return token


class UserProfileView(APIView):
    """
    用户信息接口
    GET /api/user/profile/ - 获取当前用户信息
    PUT /api/user/profile/ - 更新用户信息
    """
    permission_classes = [AllowAny]  # 实际生产应使用 IsAuthenticated
    
    def get_user_from_request(self, request):
        """
        从请求中获取用户
        实际生产应通过 Token/JWT 验证
        """
        # 从 header 获取 token（简化实现）
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            # 从 query string 获取
            token = request.GET.get('token', '')
        
        if not token:
            return None
        
        # 简化实现：通过 openid 查找用户
        # 实际生产应解析 token 获取用户
        import hashlib
        import time
        
        # 遍历查找（实际生产不应这样做，应该解析 token）
        # 这里简化处理，从请求中获取 openid
        openid = request.GET.get('openid')
        if openid:
            try:
                return User.objects.get(openid=openid, status=User.STATUS_NORMAL)
            except User.DoesNotExist:
                return None
        
        return None
    
    def get(self, request):
        """获取用户信息"""
        user = self.get_user_from_request(request)
        
        if not user:
            return Response(
                {'code': 401, 'msg': '未登录', 'data': None},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        return Response({
            'code': 0,
            'msg': 'success',
            'data': UserSerializer(user).data
        })
    
    def put(self, request):
        """更新用户信息"""
        user = self.get_user_from_request(request)
        
        if not user:
            return Response(
                {'code': 401, 'msg': '未登录', 'data': None},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        serializer = UserProfileUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'code': 400, 'msg': '参数错误', 'data': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 更新用户信息
        if 'nickname' in serializer.validated_data:
            user.nickname = serializer.validated_data['nickname']
        if 'avatar' in serializer.validated_data:
            user.avatar = serializer.validated_data['avatar']
        if 'phone' in serializer.validated_data:
            user.phone = serializer.validated_data['phone']
        
        user.save()
        
        return Response({
            'code': 0,
            'msg': '更新成功',
            'data': UserSerializer(user).data
        })


class UserDetailView(APIView):
    """
    用户详情接口
    GET /api/user/<openid>/ - 获取指定用户信息
    """
    permission_classes = [AllowAny]
    
    def get(self, request, openid):
        """获取指定用户信息"""
        try:
            user = User.objects.get(openid=openid, status=User.STATUS_NORMAL)
            return Response({
                'code': 0,
                'msg': 'success',
                'data': UserSerializer(user).data
            })
        except User.DoesNotExist:
            return Response(
                {'code': 404, 'msg': '用户不存在', 'data': None},
                status=status.HTTP_404_NOT_FOUND
            )
