# -*- coding: utf-8 -*-
"""
users/models.py - 用户模型
存储用户信息，包括微信openid、昵称、头像、积分等
"""

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager


class UserManager(BaseUserManager):
    """自定义用户管理器"""
    
    def create_user(self, openid, nickname='', avatar='', **extra_fields):
        """创建普通用户"""
        if not openid:
            raise ValueError('openid不能为空')
        
        user = self.model(
            openid=openid,
            nickname=nickname,
            avatar=avatar,
            **extra_fields
        )
        user.save(using=self._db)
        return user
    
    def create_superuser(self, openid, nickname='', **extra_fields):
        """创建超级用户"""
        extra_fields.setdefault('is_admin', True)
        return self.create_user(openid, nickname, **extra_fields)


class User(AbstractBaseUser):
    """
    用户模型
    使用 openid 作为唯一标识符（微信用户唯一ID）
    """
    
    # 用户状态常量
    STATUS_NORMAL = 1
    STATUS_BANNED = 0
    
    # 身份常量
    ROLE_NORMAL = 0
    ROLE_VIP = 1
    ROLE_ADMIN = 2
    
    openid = models.CharField(
        max_length=64, 
        unique=True, 
        db_index=True,
        verbose_name='微信OpenID',
        help_text='微信用户唯一标识'
    )
    nickname = models.CharField(
        max_length=50, 
        default='', 
        verbose_name='昵称',
        help_text='用户显示昵称'
    )
    avatar = models.CharField(
        max_length=255, 
        default='', 
        verbose_name='头像URL',
        help_text='用户头像地址'
    )
    phone = models.CharField(
        max_length=20, 
        blank=True, 
        default='',
        verbose_name='手机号'
    )
    
    # 积分相关
    total_score = models.IntegerField(
        default=0, 
        verbose_name='累计积分',
        help_text='用户累计获得的积分'
    )
    current_score = models.IntegerField(
        default=0, 
        verbose_name='当前积分',
        help_text='用户当前可用积分'
    )
    
    # 游戏统计
    games_played = models.IntegerField(
        default=0, 
        verbose_name='游戏场次',
        help_text='参与的游戏总场次'
    )
    games_won = models.IntegerField(
        default=0, 
        verbose_name='胜利次数',
        help_text='获胜的游戏场次'
    )
    as_joker_count = models.IntegerField(
        default=0, 
        verbose_name='卧底次数',
        help_text='作为卧底参与的游戏次数'
    )
    joker_win_count = models.IntegerField(
        default=0, 
        verbose_name='卧底胜利次数',
        help_text='作为卧底获胜的次数'
    )
    
    # 身份和状态
    role = models.SmallIntegerField(
        default=ROLE_NORMAL,
        verbose_name='用户角色',
        choices=(
            (ROLE_NORMAL, '普通用户'),
            (ROLE_VIP, 'VIP用户'),
            (ROLE_ADMIN, '管理员'),
        )
    )
    status = models.SmallIntegerField(
        default=STATUS_NORMAL,
        verbose_name='账号状态',
        choices=(
            (STATUS_NORMAL, '正常'),
            (STATUS_BANNED, '已封禁'),
        )
    )
    
    # 时间戳
    last_login_at = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name='最后登录时间'
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='创建时间'
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name='更新时间'
    )
    
    # 自定义用户管理器
    objects = UserManager()
    
    # 使用 openid 作为用户名
    USERNAME_FIELD = 'openid'
    
    class Meta:
        db_table = 'user'
        verbose_name = '用户'
        verbose_name_plural = '用户列表'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.nickname or "用户"}({self.openid[:8]}...)'
    
    @property
    def is_active(self):
        """判断用户是否激活"""
        return self.status == self.STATUS_NORMAL
    
    @property
    def is_admin(self):
        """判断用户是否为管理员"""
        return self.role == self.ROLE_ADMIN
    
    @property
    def win_rate(self):
        """计算胜率"""
        if self.games_played == 0:
            return 0
        return round(self.games_won / self.games_played * 100, 1)
    
    def add_score(self, amount, reason=''):
        """增加积分"""
        self.current_score += amount
        self.total_score += amount
        self.save(update_fields=['current_score', 'total_score', 'updated_at'])
        
        # 创建积分记录
        ScoreRecord.objects.create(
            user=self,
            change=amount,
            reason=reason,
            balance=self.current_score
        )
        return self.current_score
    
    def update_game_stats(self, won=False, as_joker=False, joker_won=False):
        """更新游戏统计"""
        self.games_played += 1
        if won:
            self.games_won += 1
        if as_joker:
            self.as_joker_count += 1
            if joker_won:
                self.joker_win_count += 1
        self.save(update_fields=[
            'games_played', 'games_won', 
            'as_joker_count', 'joker_win_count',
            'updated_at'
        ])


class ScoreRecord(models.Model):
    """
    积分记录表
    记录用户积分的每次变化
    """
    
    # 变化原因常量
    REASON_GAME_WIN = 'game_win'
    REASON_GAME_LOSE = 'game_lose'
    REASON_JOKER_WIN = 'joker_win'
    REASON_MVP_BONUS = 'mvp_bonus'
    REASON_DAILY_BONUS = 'daily_bonus'
    REASON_ADMIN_ADJUST = 'admin_adjust'
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='score_records',
        verbose_name='用户'
    )
    change = models.IntegerField(
        verbose_name='积分变化',
        help_text='正数增加，负数减少'
    )
    reason = models.CharField(
        max_length=50,
        default='',
        verbose_name='变化原因',
        choices=(
            (REASON_GAME_WIN, '游戏胜利'),
            (REASON_GAME_LOSE, '游戏失败'),
            (REASON_JOKER_WIN, '卧底胜利'),
            (REASON_MVP_BONUS, 'MVP加成'),
            (REASON_DAILY_BONUS, '每日奖励'),
            (REASON_ADMIN_ADJUST, '管理员调整'),
        )
    )
    balance = models.IntegerField(
        default=0,
        verbose_name='变化后余额'
    )
    extra = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='附加信息',
        help_text='存储游戏ID等额外信息'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    
    class Meta:
        db_table = 'score_record'
        verbose_name = '积分记录'
        verbose_name_plural = '积分记录列表'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.user.nickname}: {self.change:+d}'
