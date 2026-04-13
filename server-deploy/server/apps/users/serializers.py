# -*- coding: utf-8 -*-
"""
users/serializers.py - 用户序列化器
将用户模型转换为 JSON 格式供 API 使用
"""

from rest_framework import serializers
from .models import User, ScoreRecord


class UserSerializer(serializers.ModelSerializer):
    """用户基本信息序列化器"""
    
    win_rate = serializers.ReadOnlyField()
    is_admin = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = [
            'id', 'openid', 'nickname', 'avatar', 'phone',
            'total_score', 'current_score',
            'games_played', 'games_won', 'win_rate',
            'as_joker_count', 'joker_win_count',
            'role', 'status', 'created_at'
        ]
        read_only_fields = [
            'id', 'openid', 'total_score', 'games_played', 
            'games_won', 'as_joker_count', 'joker_win_count',
            'role', 'status', 'created_at'
        ]


class UserLoginSerializer(serializers.Serializer):
    """微信登录序列化器"""
    
    code = serializers.CharField(
        max_length=128,
        required=True,
        help_text='微信登录code'
    )
    nickname = serializers.CharField(
        max_length=50,
        required=False,
        default='',
        help_text='用户昵称（可选）'
    )
    avatar = serializers.CharField(
        max_length=255,
        required=False,
        default='',
        help_text='用户头像URL（可选）'
    )


class UserProfileUpdateSerializer(serializers.Serializer):
    """用户信息更新序列化器"""
    
    nickname = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        help_text='昵称'
    )
    avatar = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text='头像URL'
    )
    phone = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        help_text='手机号'
    )


class ScoreRecordSerializer(serializers.ModelSerializer):
    """积分记录序列化器"""
    
    username = serializers.CharField(source='user.nickname', read_only=True)
    
    class Meta:
        model = ScoreRecord
        fields = ['id', 'user', 'username', 'change', 'reason', 'balance', 'extra', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']
