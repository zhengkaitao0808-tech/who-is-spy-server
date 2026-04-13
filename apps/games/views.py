# -*- coding: utf-8 -*-
"""
games/views.py - 游戏视图
处理游戏开始、词语获取、投票等 API 请求
"""

import logging
from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from apps.users.models import User
from apps.rooms.models import Room
from apps.games.models import Game, WordSet, Word, GameResult
from .serializers import (
    GameSerializer, GameDetailSerializer, GameResultSerializer,
    WordSetSerializer
)

logger = logging.getLogger(__name__)


def get_user_from_request(request):
    """从请求中获取用户"""
    openid = (
        request.GET.get('openid') or 
        request.data.get('openid')
    )
    
    if not openid:
        return None
    
    try:
        return User.objects.get(openid=openid, status=User.STATUS_NORMAL)
    except User.DoesNotExist:
        return None


def get_room_from_code(room_code):
    """根据房间号获取房间"""
    try:
        return Room.objects.get(code=room_code.upper())
    except Room.DoesNotExist:
        return None


class GameStartView(APIView):
    """
    开始游戏接口
    POST /api/game/start/ - 房主开始游戏
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """开始游戏"""
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
        
        room = get_room_from_code(room_code)
        if not room:
            return Response(
                {'code': 404, 'msg': '房间不存在', 'data': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 检查是否为房主
        if room.host.openid != user.openid:
            return Response(
                {'code': 403, 'msg': '只有房主可以开始游戏', 'data': None},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 检查是否可以开始
        if not room.can_start_game:
            player_count = room.player_count
            ready_count = sum(1 for p in room.players if p.get('is_ready', False))
            return Response(
                {'code': 400, 'msg': f'玩家准备人数不足 ({ready_count}/{room.min_players})', 'data': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 获取词库
        word_set = WordSet.objects.filter(
            is_official=True, 
            status=WordSet.STATUS_APPROVED
        ).first()
        
        if not word_set or word_set.words.count() == 0:
            return Response(
                {'code': 400, 'msg': '词库为空，请先添加词语', 'data': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 创建游戏
        game = Game.objects.create(
            room=room,
            word_set=word_set,
            max_rounds=room.settings.get('max_rounds', 6),
            speak_time=room.settings.get('speak_time', 60),
            vote_time=room.settings.get('vote_time', 30),
            status=Game.STATUS_DISTRIBUTING
        )
        
        # 分配角色和词语
        player_roles = game.assign_roles_and_words()
        
        # 更新房间状态
        room.status = Room.STATUS_PLAYING
        room.current_game = game
        room.save(update_fields=['status', 'current_game', 'updated_at'])
        
        # 更新游戏状态
        game.status = Game.STATUS_SPEAKING
        game.save(update_fields=['status'])
        
        logger.info(f'游戏开始: 房间 {room.code}, 游戏ID {game.id}')
        
        return Response({
            'code': 0,
            'msg': '游戏开始',
            'data': {
                'game_id': game.id,
                'round': game.round,
                'speaker_order': game.speaker_order,
                'current_speaker': game.current_speaker,
                'speak_time': game.speak_time,
                'vote_time': game.vote_time
            }
        })


class GameWordView(APIView):
    """
    获取词语接口
    GET /api/game/word/ - 获取当前玩家的词语
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """获取词语"""
        user = get_user_from_request(request)
        if not user:
            return Response(
                {'code': 401, 'msg': '请先登录', 'data': None},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        room_code = request.GET.get('room_code')
        if not room_code:
            return Response(
                {'code': 400, 'msg': '缺少房间号', 'data': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        room = get_room_from_code(room_code)
        if not room:
            return Response(
                {'code': 404, 'msg': '房间不存在', 'data': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        game = room.current_game
        if not game:
            return Response(
                {'code': 400, 'msg': '房间暂无进行中的游戏', 'data': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 获取玩家词语
        word = game.get_player_word(user.openid)
        role = game.player_roles.get(user.openid, 0)
        
        # 设置揭示标记
        game._reveal_words = True
        
        return Response({
            'code': 0,
            'msg': 'success',
            'data': {
                'word': word,
                'role': role,  # 0=平民, 1=卧底
                'role_name': '卧底' if role == 1 else '平民',
                'is_joker': role == 1
            }
        })


class GameSpeakView(APIView):
    """
    发言接口
    POST /api/game/speak/ - 提交发言内容
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """发言"""
        user = get_user_from_request(request)
        if not user:
            return Response(
                {'code': 401, 'msg': '请先登录', 'data': None},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        room_code = request.data.get('room_code')
        content = request.data.get('content', '')
        
        if not room_code:
            return Response(
                {'code': 400, 'msg': '缺少房间号', 'data': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        room = get_room_from_code(room_code)
        if not room:
            return Response(
                {'code': 404, 'msg': '房间不存在', 'data': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        game = room.current_game
        if not game:
            return Response(
                {'code': 400, 'msg': '房间暂无进行中的游戏', 'data': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 检查是否在发言阶段
        if game.status != Game.STATUS_SPEAKING:
            return Response(
                {'code': 400, 'msg': '当前不是发言阶段', 'data': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 检查是否为当前发言者
        if game.current_speaker != user.openid:
            return Response(
                {'code': 400, 'msg': '当前不是你的发言时间', 'data': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 记录发言
        from apps.games.models import SpeakRecord
        SpeakRecord.objects.create(
            game=game,
            player_openid=user.openid,
            player_nickname=user.nickname,
            round=game.round,
            content=content
        )
        
        # 获取下一个发言者
        next_openid = game.get_next_speaker()
        
        if next_openid:
            game.save()
            return Response({
                'code': 0,
                'msg': '发言成功',
                'data': {
                    'next_speaker': next_openid,
                    'current_round': game.round
                }
            })
        else:
            # 所有人发言完毕，进入投票阶段
            game.status = Game.STATUS_VOTING
            game.votes = {}
            game.save(update_fields=['status', 'votes'])
            
            return Response({
                'code': 0,
                'msg': '发言结束，进入投票阶段',
                'data': {
                    'status': 'voting',
                    'vote_time': game.vote_time
                }
            })


class GameVoteView(APIView):
    """
    投票接口
    POST /api/game/vote/ - 投票给指定玩家
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """投票"""
        user = get_user_from_request(request)
        if not user:
            return Response(
                {'code': 401, 'msg': '请先登录', 'data': None},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        room_code = request.data.get('room_code')
        target_openid = request.data.get('target_openid')
        
        if not room_code or not target_openid:
            return Response(
                {'code': 400, 'msg': '缺少参数', 'data': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        room = get_room_from_code(room_code)
        if not room:
            return Response(
                {'code': 404, 'msg': '房间不存在', 'data': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        game = room.current_game
        if not game:
            return Response(
                {'code': 400, 'msg': '房间暂无进行中的游戏', 'data': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 检查是否在投票阶段
        if game.status != Game.STATUS_VOTING:
            return Response(
                {'code': 400, 'msg': '当前不是投票阶段', 'data': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 检查是否已投票
        if user.openid in game.votes:
            return Response(
                {'code': 400, 'msg': '你已经投过票了', 'data': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 检查目标玩家是否在游戏中
        if target_openid not in game.speaker_order:
            return Response(
                {'code': 400, 'msg': '目标玩家不在游戏中', 'data': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 记录投票
        result = game.add_vote(user.openid, target_openid)
        
        player_count = len(game.speaker_order)
        voted_count = len(game.votes)
        
        if result:
            # 投票结束，处理结果
            return self.process_vote_result(game, result, room)
        
        return Response({
            'code': 0,
            'msg': '投票成功',
            'data': {
                'voted_count': voted_count,
                'total_count': player_count,
                'completed': False
            }
        })
    
    def process_vote_result(self, game, result, room):
        """处理投票结果"""
        from django.utils import timezone
        
        eliminated = result.get('eliminated')
        
        if eliminated:
            game.revealed_player = eliminated
            game.is_joker_revealed = result.get('is_joker', False)
            
            if game.is_joker_revealed:
                # 卧底被投出
                game.status = Game.STATUS_FINISHED
                game.winner = 0
                game.ended_at = timezone.now()
                room.status = Room.STATUS_FINISHED
                room.save(update_fields=['status'])
            else:
                # 平民被投出，检查是否还有卧底
                remaining_jokers = sum(
                    1 for openid in game.speaker_order 
                    if openid != eliminated and game.is_player_joker(openid)
                )
                
                if remaining_jokers == 0:
                    game.status = Game.STATUS_FINISHED
                    game.winner = 0
                    game.ended_at = timezone.now()
                    room.status = Room.STATUS_FINISHED
                    room.save(update_fields=['status'])
                elif game.round >= game.max_rounds:
                    game.status = Game.STATUS_FINISHED
                    game.winner = 1
                    game.ended_at = timezone.now()
                    room.status = Room.STATUS_FINISHED
                    room.save(update_fields=['status'])
                else:
                    game.status = Game.STATUS_REVEALING
            
            game.save()
            
            # 保存游戏结果
            GameResult.objects.create(
                game=game,
                winner=game.winner,
                civilian_word=game.civilian_word,
                joker_word=game.joker_word,
                total_rounds=game.round
            )
            
            # 计算积分
            self.calculate_scores(game)
        
        return Response({
            'code': 0,
            'msg': '投票结束',
            'data': {
                'completed': True,
                'eliminated': eliminated,
                'is_joker': game.is_joker_revealed,
                'winner': game.winner,
                'status': game.status,
                'result': result
            }
        })
    
    def calculate_scores(self, game):
        """计算玩家积分"""
        score_rules = settings.GAME_CONFIG.get('SCORE_RULES', {})
        
        for openid in game.speaker_order:
            try:
                user = User.objects.get(openid=openid)
                is_joker = game.is_player_joker(openid)
                
                # 计算积分
                if is_joker:
                    score = score_rules.get('joker_win' if game.winner == 1 else 'joker_lose', 5)
                else:
                    score = score_rules.get('civilian_win' if game.winner == 0 else 'civilian_lose', 3)
                
                user.add_score(score, 'joker_win' if (is_joker and game.winner == 1) else 'game_win')
                
                # 更新用户游戏统计
                user.update_game_stats(
                    won=(game.winner == 0 and not is_joker) or (game.winner == 1 and is_joker),
                    as_joker=is_joker,
                    joker_won=(is_joker and game.winner == 1)
                )
                
                # 更新房间玩家积分
                for player in game.room.players:
                    if player['openid'] == openid:
                        player['score'] = score
                        break
                game.room.save(update_fields=['players'])
                
            except User.DoesNotExist:
                continue


class GameResultView(APIView):
    """
    游戏结果接口
    GET /api/game/result/ - 获取游戏结果
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """获取游戏结果"""
        room_code = request.GET.get('room_code')
        
        if not room_code:
            return Response(
                {'code': 400, 'msg': '缺少房间号', 'data': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        room = get_room_from_code(room_code)
        if not room:
            return Response(
                {'code': 404, 'msg': '房间不存在', 'data': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        game = room.current_game
        if not game:
            return Response(
                {'code': 400, 'msg': '房间暂无游戏记录', 'data': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 获取游戏结果
        try:
            result = GameResult.objects.get(game=game)
            return Response({
                'code': 0,
                'msg': 'success',
                'data': GameResultSerializer(result).data
            })
        except GameResult.DoesNotExist:
            return Response({
                'code': 0,
                'msg': 'success',
                'data': {
                    'winner': game.winner,
                    'civilian_word': game.civilian_word,
                    'joker_word': game.joker_word,
                    'total_rounds': game.round,
                    'status': game.status
                }
            })


class GameNextRoundView(APIView):
    """
    下一轮接口
    POST /api/game/next_round/ - 进入下一轮
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """进入下一轮"""
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
        
        room = get_room_from_code(room_code)
        if not room:
            return Response(
                {'code': 404, 'msg': '房间不存在', 'data': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        game = room.current_game
        if not game:
            return Response(
                {'code': 400, 'msg': '房间暂无进行中的游戏', 'data': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 检查是否在揭示阶段
        if game.status != Game.STATUS_REVEALING:
            return Response(
                {'code': 400, 'msg': '当前不能进入下一轮', 'data': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 重置投票
        game.votes = {}
        
        # 轮数加1
        game.round += 1
        
        # 重新随机发言顺序
        import random
        remaining_players = [openid for openid in game.speaker_order if openid != game.revealed_player]
        game.speaker_order = random.sample(remaining_players, len(remaining_players))
        game.current_speaker_index = 0
        game.current_speaker = game.speaker_order[0] if game.speaker_order else ''
        
        # 更新状态
        game.status = Game.STATUS_SPEAKING
        
        # 重置房间玩家准备状态
        room.reset_ready_status()
        
        game.save()
        room.save()
        
        return Response({
            'code': 0,
            'msg': '进入第{}轮'.format(game.round),
            'data': {
                'round': game.round,
                'speaker_order': game.speaker_order,
                'current_speaker': game.current_speaker,
                'speak_time': game.speak_time
            }
        })


class WordSetListView(APIView):
    """
    词库列表接口
    GET /api/game/wordset/ - 获取词库列表
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """获取词库列表"""
        category = request.GET.get('category')
        
        queryset = WordSet.objects.filter(
            status=WordSet.STATUS_APPROVED
        )
        
        if category:
            queryset = queryset.filter(category=category)
        
        return Response({
            'code': 0,
            'msg': 'success',
            'data': WordSetSerializer(queryset, many=True).data
        })
