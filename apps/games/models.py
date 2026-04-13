# -*- coding: utf-8 -*-
"""
games/models.py - 游戏模型
存储游戏数据、词语库、发言记录、投票记录等
"""

import random
from django.db import models
from apps.users.models import User
from apps.rooms.models import Room


class WordSet(models.Model):
    """
    词库模型
    管理词语集合，支持自定义词库
    """
    
    # 词库分类
    CATEGORY_GENERAL = 'general'      # 通用
    CATEGORY_MOVIE = 'movie'           # 影视
    CATEGORY_FOOD = 'food'             # 美食
    CATEGORY_TRAVEL = 'travel'         # 旅游
    CATEGORY_WORK = 'work'             # 职场
    CATEGORY_DAILY = 'daily'           # 日常生活
    CATEGORY_ADULT = 'adult'           # 成人（需验证）
    
    # 状态
    STATUS_PENDING = 0    # 待审核
    STATUS_APPROVED = 1   # 已通过
    STATUS_REJECTED = 2   # 已拒绝
    
    name = models.CharField(
        max_length=100,
        verbose_name='词库名称'
    )
    category = models.CharField(
        max_length=50,
        default=CATEGORY_GENERAL,
        verbose_name='分类',
        choices=(
            (CATEGORY_GENERAL, '通用'),
            (CATEGORY_MOVIE, '影视'),
            (CATEGORY_FOOD, '美食'),
            (CATEGORY_TRAVEL, '旅行'),
            (CATEGORY_WORK, '职场'),
            (CATEGORY_DAILY, '日常生活'),
            (CATEGORY_ADULT, '成人'),
        )
    )
    description = models.CharField(
        max_length=255,
        default='',
        verbose_name='描述'
    )
    
    # 权限
    is_official = models.BooleanField(
        default=False,
        verbose_name='是否官方词库'
    )
    is_public = models.BooleanField(
        default=True,
        verbose_name='是否公开'
    )
    
    # 创建者
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='word_sets',
        verbose_name='创建者'
    )
    
    # 统计
    word_count = models.IntegerField(
        default=0,
        verbose_name='词组数量'
    )
    use_count = models.IntegerField(
        default=0,
        verbose_name='使用次数'
    )
    
    # 状态
    status = models.SmallIntegerField(
        default=STATUS_APPROVED,
        verbose_name='状态',
        choices=(
            (STATUS_PENDING, '待审核'),
            (STATUS_APPROVED, '已通过'),
            (STATUS_REJECTED, '已拒绝'),
        )
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    
    class Meta:
        db_table = 'word_set'
        verbose_name = '词库'
        verbose_name_plural = '词库列表'
    
    def __str__(self):
        return self.name


class Word(models.Model):
    """
    词语模型
    存储平民词和卧底词
    """
    
    # 难度
    DIFFICULTY_EASY = 1
    DIFFICULTY_NORMAL = 2
    DIFFICULTY_HARD = 3
    
    word_set = models.ForeignKey(
        WordSet,
        on_delete=models.CASCADE,
        related_name='words',
        verbose_name='所属词库'
    )
    
    civilian_word = models.CharField(
        max_length=50,
        verbose_name='平民词语',
        help_text='普通玩家看到的词语'
    )
    joker_word = models.CharField(
        max_length=50,
        verbose_name='卧底词语',
        help_text='卧底玩家看到的词语（与平民词语相似但不同）'
    )
    
    difficulty = models.SmallIntegerField(
        default=DIFFICULTY_NORMAL,
        verbose_name='难度',
        choices=(
            (DIFFICULTY_EASY, '简单'),
            (DIFFICULTY_NORMAL, '普通'),
            (DIFFICULTY_HARD, '困难'),
        )
    )
    
    play_count = models.IntegerField(
        default=0,
        verbose_name='使用次数'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    
    class Meta:
        db_table = 'word'
        verbose_name = '词语'
        verbose_name_plural = '词语列表'
    
    def __str__(self):
        return f'{self.civilian_word} / {self.joker_word}'


class Game(models.Model):
    """
    游戏模型
    存储游戏状态、玩家角色、词语分配等
    """
    
    # 游戏状态
    STATUS_PREPARING = 0     # 准备阶段
    STATUS_DISTRIBUTING = 1  # 发词阶段
    STATUS_SPEAKING = 2      # 发言阶段
    STATUS_VOTING = 3        # 投票阶段
    STATUS_REVEALING = 4     # 揭示阶段
    STATUS_FINISHED = 5      # 已结束
    
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name='games',
        verbose_name='房间'
    )
    word_set = models.ForeignKey(
        WordSet,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='词库'
    )
    
    # 词语分配
    civilian_word = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name='平民词语'
    )
    joker_word = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name='卧底词语'
    )
    
    # 轮次
    round = models.SmallIntegerField(
        default=1,
        verbose_name='当前轮次'
    )
    max_rounds = models.SmallIntegerField(
        default=6,
        verbose_name='最大轮次'
    )
    
    # 发言顺序
    speaker_order = models.JSONField(
        default=list,
        verbose_name='发言顺序',
        help_text='玩家openid列表'
    )
    current_speaker_index = models.SmallIntegerField(
        default=0,
        verbose_name='当前发言者索引'
    )
    current_speaker = models.CharField(
        max_length=64,
        blank=True,
        default='',
        verbose_name='当前发言者openid'
    )
    
    # 发言时间
    speak_time = models.SmallIntegerField(
        default=60,
        verbose_name='发言时间（秒）'
    )
    vote_time = models.SmallIntegerField(
        default=30,
        verbose_name='投票时间（秒）'
    )
    
    # 状态
    status = models.SmallIntegerField(
        default=STATUS_PREPARING,
        verbose_name='游戏状态',
        choices=(
            (STATUS_PREPARING, '准备中'),
            (STATUS_DISTRIBUTING, '发词中'),
            (STATUS_SPEAKING, '发言中'),
            (STATUS_VOTING, '投票中'),
            (STATUS_REVEALING, '揭示中'),
            (STATUS_FINISHED, '已结束'),
        )
    )
    
    # 投票记录
    votes = models.JSONField(
        default=dict,
        verbose_name='投票记录',
        help_text='{voter_openid: target_openid}'
    )
    
    # 游戏结果
    winner = models.SmallIntegerField(
        null=True,
        blank=True,
        verbose_name='胜利方',
        choices=(
            (0, '平民胜利'),
            (1, '卧底胜利'),
        )
    )
    revealed_player = models.CharField(
        max_length=64,
        blank=True,
        default='',
        verbose_name='被揭示玩家openid'
    )
    is_joker_revealed = models.BooleanField(
        default=False,
        verbose_name='被揭示者是否为卧底'
    )
    
    # 玩家角色分配
    player_roles = models.JSONField(
        default=dict,
        verbose_name='玩家角色',
        help_text='{openid: role} role: 0=平民, 1=卧底'
    )
    
    # 时间戳
    started_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='开始时间'
    )
    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='结束时间'
    )
    
    class Meta:
        db_table = 'game'
        verbose_name = '游戏'
        verbose_name_plural = '游戏列表'
    
    def __str__(self):
        return f'房间{self.room.code} 第{self.round}轮'
    
    def get_player_word(self, openid):
        """获取指定玩家的词语"""
        role = self.player_roles.get(openid, 0)
        if role == 1:  # 卧底
            return self.joker_word
        return self.civilian_word
    
    def is_player_joker(self, openid):
        """判断是否为卧底"""
        return self.player_roles.get(openid, 0) == 1
    
    def get_next_speaker(self):
        """获取下一个发言者"""
        if self.current_speaker_index < len(self.speaker_order) - 1:
            self.current_speaker_index += 1
            self.current_speaker = self.speaker_order[self.current_speaker_index]
            self.save(update_fields=['current_speaker_index', 'current_speaker'])
            return self.current_speaker
        return None  # 所有人已发言完毕
    
    def add_vote(self, voter_openid, target_openid):
        """添加投票"""
        self.votes[voter_openid] = target_openid
        self.save(update_fields=['votes'])
        
        # 检查是否所有人都投完票
        player_count = len(self.speaker_order)
        if len(self.votes) >= player_count:
            return self.count_votes()
        return None
    
    def count_votes(self):
        """统计票数"""
        vote_count = {}
        for target in self.votes.values():
            vote_count[target] = vote_count.get(target, 0) + 1
        
        # 找出票数最多的玩家
        max_votes = max(vote_count.values()) if vote_count else 0
        eliminated = [openid for openid, count in vote_count.items() if count == max_votes]
        
        if len(eliminated) == 1:
            # 唯一的最高票
            return {
                'eliminated': eliminated[0],
                'is_joker': self.is_player_joker(eliminated[0]),
                'vote_count': vote_count
            }
        else:
            # 平票
            return {
                'eliminated': None,
                'is_joker': None,
                'vote_count': vote_count,
                'tie': True,
                'tied_players': eliminated
            }
    
    def assign_roles_and_words(self):
        """分配角色和词语"""
        players = self.room.players
        player_count = len(players)
        
        # 确定卧底数量
        joker_count = 1
        if player_count >= 6:
            joker_count = 2
        
        # 随机选择卧底
        openids = [p['openid'] for p in players]
        joker_indices = random.sample(range(player_count), joker_count)
        
        self.player_roles = {}
        for i, openid in enumerate(openids):
            self.player_roles[openid] = 1 if i in joker_indices else 0
        
        # 随机选择词语
        if self.word_set:
            words = list(Word.objects.filter(word_set=self.word_set))
            if words:
                selected = random.choice(words)
                self.civilian_word = selected.civilian_word
                self.joker_word = selected.joker_word
                selected.play_count += 1
                selected.save(update_fields=['play_count'])
        
        # 随机发言顺序
        self.speaker_order = random.sample(openids, player_count)
        self.current_speaker = self.speaker_order[0]
        
        self.save()
        return self.player_roles


class SpeakRecord(models.Model):
    """
    发言记录模型
    存储玩家每轮的发言内容
    """
    
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name='speak_records',
        verbose_name='游戏'
    )
    player_openid = models.CharField(
        max_length=64,
        verbose_name='玩家openid'
    )
    player_nickname = models.CharField(
        max_length=50,
        default='',
        verbose_name='玩家昵称'
    )
    
    round = models.SmallIntegerField(
        verbose_name='轮次'
    )
    
    # 发言内容
    content = models.TextField(
        blank=True,
        default='',
        verbose_name='文字内容'
    )
    audio_url = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='语音URL'
    )
    duration = models.IntegerField(
        default=0,
        verbose_name='录音时长（秒）'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='发言时间'
    )
    
    class Meta:
        db_table = 'speak_record'
        verbose_name = '发言记录'
        verbose_name_plural = '发言记录列表'
        ordering = ['round', 'created_at']
    
    def __str__(self):
        return f'{self.player_nickname} 第{self.round}轮发言'


class GameResult(models.Model):
    """
    游戏结果记录
    存储每局游戏的最终结果和玩家得分
    """
    
    game = models.OneToOneField(
        Game,
        on_delete=models.CASCADE,
        related_name='result',
        verbose_name='游戏'
    )
    
    winner = models.SmallIntegerField(
        verbose_name='胜利方',
        choices=(
            (0, '平民胜利'),
            (1, '卧底胜利'),
        )
    )
    
    civilian_word = models.CharField(
        max_length=50,
        verbose_name='平民词语'
    )
    joker_word = models.CharField(
        max_length=50,
        verbose_name='卧底词语'
    )
    
    total_rounds = models.SmallIntegerField(
        verbose_name='总轮数'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='结算时间'
    )
    
    class Meta:
        db_table = 'game_result'
        verbose_name = '游戏结果'
        verbose_name_plural = '游戏结果列表'
    
    def __str__(self):
        return f'游戏结果: {"平民" if self.winner == 0 else "卧底"}胜利'
