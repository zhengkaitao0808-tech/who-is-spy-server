# -*- coding: utf-8 -*-
"""
games/serializers.py - 游戏序列化器
"""

from rest_framework import serializers
from .models import Game, WordSet, Word, SpeakRecord, GameResult


class WordSerializer(serializers.ModelSerializer):
    """词语序列化器"""
    
    class Meta:
        model = Word
        fields = ['id', 'civilian_word', 'joker_word', 'difficulty']


class WordSetSerializer(serializers.ModelSerializer):
    """词库序列化器"""
    
    word_count = serializers.ReadOnlyField()
    
    class Meta:
        model = WordSet
        fields = ['id', 'name', 'category', 'description', 'word_count', 'use_count']


class SpeakRecordSerializer(serializers.ModelSerializer):
    """发言记录序列化器"""
    
    class Meta:
        model = SpeakRecord
        fields = ['id', 'player_openid', 'player_nickname', 'round', 'content', 'audio_url', 'duration', 'created_at']


class PlayerGameInfoSerializer(serializers.Serializer):
    """玩家游戏信息序列化器"""
    
    openid = serializers.CharField()
    nickname = serializers.CharField()
    avatar = serializers.CharField(allow_blank=True)
    role = serializers.IntegerField(help_text='0=平民, 1=卧底')
    word = serializers.CharField(required=False, help_text='玩家词语（仅在揭示阶段或结束后可见）')
    is_revealed = serializers.BooleanField(default=False)
    vote_count = serializers.IntegerField(default=0)
    score = serializers.IntegerField(default=0)


class GameSerializer(serializers.ModelSerializer):
    """游戏信息序列化器"""
    
    player_count = serializers.SerializerMethodField()
    civilian_word = serializers.SerializerMethodField()
    joker_word = serializers.SerializerMethodField()
    
    class Meta:
        model = Game
        fields = [
            'id', 'room', 'round', 'max_rounds',
            'status', 'speak_time', 'vote_time',
            'current_speaker', 'speaker_order',
            'civilian_word', 'joker_word',
            'started_at', 'ended_at'
        ]
    
    def get_player_count(self, obj):
        return len(obj.speaker_order)
    
    def get_civilian_word(self, obj):
        # 根据请求者身份决定是否返回平民词
        request = self.context.get('request')
        if request and hasattr(obj, '_reveal_words'):
            return obj.civilian_word
        return ''
    
    def get_joker_word(self, obj):
        request = self.context.get('request')
        if request and hasattr(obj, '_reveal_words'):
            return obj.joker_word
        return ''


class GameDetailSerializer(GameSerializer):
    """游戏详情序列化器（包含玩家信息）"""
    
    players = serializers.SerializerMethodField()
    votes = serializers.SerializerMethodField()
    
    class Meta(GameSerializer.Meta):
        fields = GameSerializer.Meta.fields + ['players', 'votes']
    
    def get_players(self, obj):
        """获取玩家信息"""
        request = self.context.get('request')
        reveal = hasattr(obj, '_reveal_words') and obj._reveal_words
        result = []
        
        for openid in obj.speaker_order:
            player = obj.room.get_player(openid)
            if player:
                info = {
                    'openid': openid,
                    'nickname': player.get('nickname', ''),
                    'avatar': player.get('avatar', ''),
                    'role': obj.player_roles.get(openid, 0),
                    'vote_count': 0,
                }
                
                # 计算投票数
                info['vote_count'] = list(obj.votes.values()).count(openid)
                
                # 是否揭示身份
                if reveal or obj.status == Game.STATUS_FINISHED:
                    info['word'] = obj.get_player_word(openid) if openid == request.GET.get('openid') else ''
                
                result.append(info)
        
        return result
    
    def get_votes(self, obj):
        """获取投票信息"""
        return obj.votes


class GameResultSerializer(serializers.ModelSerializer):
    """游戏结果序列化器"""
    
    player_results = serializers.SerializerMethodField()
    
    class Meta:
        model = GameResult
        fields = ['id', 'winner', 'civilian_word', 'joker_word', 'total_rounds', 'player_results', 'created_at']
    
    def get_player_results(self, obj):
        """获取玩家结果"""
        game = obj.game
        result = []
        
        for openid in game.speaker_order:
            player = game.room.get_player(openid)
            if player:
                is_joker = game.player_roles.get(openid, 0) == 1
                result.append({
                    'openid': openid,
                    'nickname': player.get('nickname', ''),
                    'avatar': player.get('avatar', ''),
                    'role': '卧底' if is_joker else '平民',
                    'is_winner': (obj.winner == 1 and is_joker) or (obj.winner == 0 and not is_joker),
                    'score': player.get('score', 0),
                })
        
        return result
