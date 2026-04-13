# -*- coding: utf-8 -*-
"""
rooms/models.py - 房间模型
存储房间信息，包括房间号、房主、玩家列表、状态等
"""

import random
import string
from django.db import models
from apps.users.models import User


class Room(models.Model):
    """
    房间模型
    玩家可以创建房间、加入房间进行游戏
    """
    
    # 房间状态常量
    STATUS_WAITING = 0      # 等待中
    STATUS_PLAYING = 1      # 游戏中
    STATUS_FINISHED = 2      # 已结束
    
    # 生成6位房间号
    @staticmethod
    def generate_code():
        """生成唯一的6位房间号"""
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if not Room.objects.filter(code=code).exists():
                return code
    
    code = models.CharField(
        max_length=6,
        unique=True,
        db_index=True,
        verbose_name='房间号',
        help_text='6位唯一房间码'
    )
    name = models.CharField(
        max_length=50,
        default='游戏房间',
        verbose_name='房间名称',
        help_text='房间显示名称'
    )
    
    # 房主
    host = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='hosted_rooms',
        verbose_name='房主',
        help_text='房间创建者'
    )
    
    # 玩家列表（JSON格式存储玩家ID）
    players = models.JSONField(
        default=list,
        verbose_name='玩家列表',
        help_text='存储玩家ID和状态 [{openid, nickname, avatar, is_ready}]'
    )
    
    # 房间设置
    settings = models.JSONField(
        default=dict,
        verbose_name='房间设置',
        help_text='游戏设置 {max_players, speak_time, vote_time, max_rounds}'
    )
    
    # 人数限制
    max_players = models.SmallIntegerField(
        default=8,
        verbose_name='最大人数',
        help_text='房间最大玩家数'
    )
    min_players = models.SmallIntegerField(
        default=4,
        verbose_name='最小人数',
        help_text='开始游戏所需最小人数'
    )
    
    # 状态
    status = models.SmallIntegerField(
        default=STATUS_WAITING,
        verbose_name='房间状态',
        choices=(
            (STATUS_WAITING, '等待中'),
            (STATUS_PLAYING, '游戏中'),
            (STATUS_FINISHED, '已结束'),
        )
    )
    
    # 当前游戏ID
    current_game = models.ForeignKey(
        'games.Game',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='current_room',
        verbose_name='当前游戏'
    )
    
    # 时间戳
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间'
    )
    expire_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='过期时间',
        help_text='房间过期自动删除时间'
    )
    
    class Meta:
        db_table = 'room'
        verbose_name = '房间'
        verbose_name_plural = '房间列表'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.name}({self.code})'
    
    @property
    def player_count(self):
        """获取当前玩家数量"""
        return len(self.players)
    
    @property
    def is_full(self):
        """判断房间是否已满"""
        return self.player_count >= self.max_players
    
    @property
    def can_start_game(self):
        """判断是否可以开始游戏"""
        return (self.player_count >= self.min_players and 
                self.status == self.STATUS_WAITING and
                all(p.get('is_ready', False) for p in self.players))
    
    def add_player(self, user):
        """添加玩家到房间"""
        if self.is_full:
            return False, '房间已满'
        
        # 检查玩家是否已在房间中
        for player in self.players:
            if player['openid'] == user.openid:
                return False, '已在房间中'
        
        # 添加玩家
        self.players.append({
            'openid': user.openid,
            'nickname': user.nickname,
            'avatar': user.avatar,
            'is_ready': False,
            'score': 0,
            'is_online': True,
            'joined_at': models.functions.Now(),  # 后面会序列化
        })
        self.save(update_fields=['players', 'updated_at'])
        return True, '加入成功'
    
    def remove_player(self, openid):
        """移除玩家"""
        self.players = [p for p in self.players if p['openid'] != openid]
        
        # 如果房主离开，转移给下一个玩家
        if self.host.openid == openid and self.players:
            self.host = User.objects.get(openid=self.players[0]['openid'])
        
        self.save(update_fields=['players', 'host', 'updated_at'])
        return True, '离开成功'
    
    def set_player_ready(self, openid, is_ready=True):
        """设置玩家准备状态"""
        for player in self.players:
            if player['openid'] == openid:
                player['is_ready'] = is_ready
                self.save(update_fields=['players', 'updated_at'])
                return True
        return False
    
    def reset_ready_status(self):
        """重置所有玩家准备状态"""
        for player in self.players:
            player['is_ready'] = False
        self.save(update_fields=['players', 'updated_at'])
    
    def get_player(self, openid):
        """获取指定玩家信息"""
        for player in self.players:
            if player['openid'] == openid:
                return player
        return None
    
    def set_online_status(self, openid, is_online):
        """设置玩家在线状态"""
        for player in self.players:
            if player['openid'] == openid:
                player['is_online'] = is_online
                self.save(update_fields=['players', 'updated_at'])
                return True
        return False
