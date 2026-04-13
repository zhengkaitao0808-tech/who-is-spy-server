# -*- coding: utf-8 -*-
"""
rooms/serializers.py - 房间序列化器
"""

from rest_framework import serializers
from .models import Room


class PlayerSerializer(serializers.Serializer):
    """玩家信息序列化器"""
    
    openid = serializers.CharField()
    nickname = serializers.CharField()
    avatar = serializers.CharField(allow_blank=True)
    is_ready = serializers.BooleanField(default=False)
    score = serializers.IntegerField(default=0)
    is_online = serializers.BooleanField(default=True)


class RoomSerializer(serializers.ModelSerializer):
    """房间信息序列化器"""
    
    player_count = serializers.ReadOnlyField()
    is_full = serializers.ReadOnlyField()
    can_start_game = serializers.ReadOnlyField()
    players = PlayerSerializer(many=True, read_only=True)
    host_nickname = serializers.CharField(source='host.nickname', read_only=True)
    host_avatar = serializers.CharField(source='host.avatar', read_only=True)
    
    class Meta:
        model = Room
        fields = [
            'id', 'code', 'name',
            'host', 'host_nickname', 'host_avatar',
            'players', 'player_count', 'max_players', 'min_players',
            'settings', 'status',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'code', 'host', 'created_at', 'updated_at']


class RoomCreateSerializer(serializers.Serializer):
    """创建房间序列化器"""
    
    room_name = serializers.CharField(
        max_length=50,
        required=False,
        default='游戏房间',
        help_text='房间名称'
    )
    max_players = serializers.IntegerField(
        required=False,
        default=8,
        min_value=4,
        max_value=8,
        help_text='最大玩家数'
    )
    min_players = serializers.IntegerField(
        required=False,
        default=4,
        min_value=4,
        max_value=8,
        help_text='最小玩家数'
    )
    speak_time = serializers.IntegerField(
        required=False,
        default=60,
        min_value=30,
        max_value=120,
        help_text='发言时间（秒）'
    )
    vote_time = serializers.IntegerField(
        required=False,
        default=30,
        min_value=15,
        max_value=60,
        help_text='投票时间（秒）'
    )


class RoomJoinSerializer(serializers.Serializer):
    """加入房间序列化器"""
    
    room_code = serializers.CharField(
        max_length=6,
        required=True,
        help_text='房间号'
    )


class RoomReadySerializer(serializers.Serializer):
    """准备游戏序列化器"""
    
    is_ready = serializers.BooleanField(
        required=False,
        default=True,
        help_text='是否准备'
    )
