# -*- coding: utf-8 -*-
"""
rooms/views.py - 房间视图
处理房间创建、加入、离开等 API 请求
"""

import logging
from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from apps.users.models import User
from .models import Room
from .serializers import (
    RoomSerializer,
    RoomCreateSerializer,
    RoomJoinSerializer,
    RoomReadySerializer
)

logger = logging.getLogger(__name__)


def get_user_from_request(request):
    """从请求中获取用户"""
    # 从 query string 或 body 获取 openid
    openid = (
        request.GET.get('openid') or 
        request.data.get('openid') or
        request.headers.get('X-OpenId')
    )
    
    if not openid:
        return None
    
    try:
        return User.objects.get(openid=openid, status=User.STATUS_NORMAL)
    except User.DoesNotExist:
        return None


class RoomListView(APIView):
    """
    房间列表接口
    GET /api/room/list/ - 获取可加入的房间列表
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """获取房间列表"""
        # 获取等待中的房间
        rooms = Room.objects.filter(
            status=Room.STATUS_WAITING
        ).exclude(
            players__len=0
        ).order_by('-created_at')[:20]  # 限制返回数量
        
        return Response({
            'code': 0,
            'msg': 'success',
            'data': RoomSerializer(rooms, many=True).data
        })


class RoomCreateView(APIView):
    """
    创建房间接口
    POST /api/room/create/ - 创建新房间
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """创建房间"""
        # 获取用户
        user = get_user_from_request(request)
        if not user:
            return Response(
                {'code': 401, 'msg': '请先登录', 'data': None},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # 验证参数
        serializer = RoomCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'code': 400, 'msg': '参数错误', 'data': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = serializer.validated_data
        
        # 创建房间
        room = Room.objects.create(
            code=Room.generate_code(),
            name=data.get('room_name', '游戏房间'),
            host=user,
            max_players=data.get('max_players', 8),
            min_players=data.get('min_players', 4),
            settings={
                'speak_time': data.get('speak_time', 60),
                'vote_time': data.get('vote_time', 30),
                'max_rounds': settings.GAME_CONFIG.get('MAX_ROUNDS', 6),
            },
            players=[{
                'openid': user.openid,
                'nickname': user.nickname,
                'avatar': user.avatar,
                'is_ready': False,
                'score': 0,
                'is_online': True,
            }]
        )
        
        logger.info(f'用户 {user.openid} 创建了房间 {room.code}')
        
        return Response({
            'code': 0,
            'msg': '创建成功',
            'data': RoomSerializer(room).data
        })


class RoomJoinView(APIView):
    """
    加入房间接口
    POST /api/room/join/ - 加入指定房间
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """加入房间"""
        # 获取用户
        user = get_user_from_request(request)
        if not user:
            return Response(
                {'code': 401, 'msg': '请先登录', 'data': None},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # 验证参数
        serializer = RoomJoinSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'code': 400, 'msg': '参数错误', 'data': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        room_code = serializer.validated_data['room_code'].upper()
        
        # 查找房间
        try:
            room = Room.objects.get(code=room_code)
        except Room.DoesNotExist:
            return Response(
                {'code': 404, 'msg': '房间不存在', 'data': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 检查房间状态
        if room.status != Room.STATUS_WAITING:
            return Response(
                {'code': 400, 'msg': '房间已开始或已结束', 'data': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 加入房间
        success, message = room.add_player(user)
        if not success:
            return Response(
                {'code': 400, 'msg': message, 'data': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logger.info(f'用户 {user.openid} 加入了房间 {room.code}')
        
        return Response({
            'code': 0,
            'msg': '加入成功',
            'data': RoomSerializer(room).data
        })


class RoomLeaveView(APIView):
    """
    离开房间接口
    POST /api/room/leave/ - 离开当前房间
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """离开房间"""
        # 获取用户
        user = get_user_from_request(request)
        if not user:
            return Response(
                {'code': 401, 'msg': '请先登录', 'data': None},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        room_code = request.data.get('room_code')
        if not room_code:
            return Response(
                {'code': 400, 'msg': '缺少房间号', 'data': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 查找房间
        try:
            room = Room.objects.get(code=room_code.upper())
        except Room.DoesNotExist:
            return Response(
                {'code': 404, 'msg': '房间不存在', 'data': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 检查是否在房间中
        player = room.get_player(user.openid)
        if not player:
            return Response(
                {'code': 400, 'msg': '不在此房间中', 'data': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 离开房间
        room.remove_player(user.openid)
        
        logger.info(f'用户 {user.openid} 离开了房间 {room.code}')
        
        return Response({
            'code': 0,
            'msg': '离开成功',
            'data': {'room_code': room.code}
        })


class RoomDetailView(APIView):
    """
    房间详情接口
    GET /api/room/<room_code>/ - 获取房间详情
    """
    permission_classes = [AllowAny]
    
    def get(self, request, room_code):
        """获取房间详情"""
        try:
            room = Room.objects.get(code=room_code.upper())
            return Response({
                'code': 0,
                'msg': 'success',
                'data': RoomSerializer(room).data
            })
        except Room.DoesNotExist:
            return Response(
                {'code': 404, 'msg': '房间不存在', 'data': None},
                status=status.HTTP_404_NOT_FOUND
            )


class RoomReadyView(APIView):
    """
    准备接口
    POST /api/room/<room_code>/ready/ - 设置准备状态
    """
    permission_classes = [AllowAny]
    
    def post(self, request, room_code):
        """设置准备状态"""
        user = get_user_from_request(request)
        if not user:
            return Response(
                {'code': 401, 'msg': '请先登录', 'data': None},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        serializer = RoomReadySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'code': 400, 'msg': '参数错误', 'data': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            room = Room.objects.get(code=room_code.upper())
        except Room.DoesNotExist:
            return Response(
                {'code': 404, 'msg': '房间不存在', 'data': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 检查是否在房间中
        if not room.get_player(user.openid):
            return Response(
                {'code': 400, 'msg': '不在此房间中', 'data': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 设置准备状态
        is_ready = serializer.validated_data.get('is_ready', True)
        room.set_player_ready(user.openid, is_ready)
        
        return Response({
            'code': 0,
            'msg': '设置成功',
            'data': {
                'is_ready': is_ready,
                'can_start_game': room.can_start_game
            }
        })


class RoomOnlineView(APIView):
    """
    在线状态接口
    POST /api/room/<room_code>/online/ - 更新在线状态
    """
    permission_classes = [AllowAny]
    
    def post(self, request, room_code):
        """更新在线状态"""
        user = get_user_from_request(request)
        if not user:
            return Response(
                {'code': 401, 'msg': '请先登录', 'data': None},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        is_online = request.data.get('is_online', True)
        
        try:
            room = Room.objects.get(code=room_code.upper())
            room.set_online_status(user.openid, is_online)
            return Response({
                'code': 0,
                'msg': '更新成功',
                'data': {'is_online': is_online}
            })
        except Room.DoesNotExist:
            return Response(
                {'code': 404, 'msg': '房间不存在', 'data': None},
                status=status.HTTP_404_NOT_FOUND
            )
