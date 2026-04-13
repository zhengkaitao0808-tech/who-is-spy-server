# -*- coding: utf-8 -*-
"""
games/consumers.py - WebSocket 消费者
处理房间实时通信，包括玩家加入/离开、发言、投票等事件
"""

import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


class RoomConsumer(AsyncWebsocketConsumer):
    """
    房间 WebSocket 消费者
    处理房间内的实时消息和事件广播
    """
    
    async def connect(self):
        """WebSocket 连接建立"""
        self.room_code = self.scope['url_route']['kwargs']['room_code']
        self.room_group_name = f'room_{self.room_code}'
        self.user_openid = None
        self.is_connected = False
        
        # 将连接加入房间组
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        self.is_connected = True
        
        logger.info(f'WebSocket connected to room {self.room_code}')
        
        # 发送连接成功消息
        await self.send(text_data=json.dumps({
            'type': 'connection',
            'action': 'connected',
            'data': {'room_code': self.room_code}
        }))
    
    async def disconnect(self, close_code):
        """WebSocket 连接断开"""
        if self.is_connected and self.user_openid:
            # 通知其他玩家该玩家离线
            await self.broadcast_event({
                'type': 'room',
                'action': 'player_offline',
                'data': {'openid': self.user_openid}
            })
            
            # 更新房间玩家在线状态
            await self.update_player_online_status(self.room_code, self.user_openid, False)
        
        # 从房间组移除
        if self.is_connected:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        
        logger.info(f'WebSocket disconnected from room {self.room_code}')
    
    async def receive(self, text_data):
        """
        接收 WebSocket 消息
        处理客户端发送的各种事件
        """
        try:
            data = json.loads(text_data)
            msg_type = data.get('type', 'unknown')
            action = data.get('action', '')
            payload = data.get('data', {})
            
            logger.debug(f'Received message: type={msg_type}, action={action}')
            
            # 根据消息类型处理
            if msg_type == 'auth':
                # 用户认证
                await self.handle_auth(payload)
            
            elif msg_type == 'room':
                # 房间事件
                await self.handle_room_event(action, payload)
            
            elif msg_type == 'game':
                # 游戏事件
                await self.handle_game_event(action, payload)
            
            elif msg_type == 'chat':
                # 聊天消息
                await self.handle_chat(payload)
            
            elif msg_type == 'heartbeat':
                # 心跳
                await self.send(text_data=json.dumps({
                    'type': 'heartbeat',
                    'data': {'timestamp': payload.get('timestamp')}
                }))
            
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'data': {'message': 'Invalid JSON format'}
            }))
        except Exception as e:
            logger.error(f'Error handling message: {str(e)}')
            await self.send(text_data=json.dumps({
                'type': 'error',
                'data': {'message': str(e)}
            }))
    
    async def handle_auth(self, payload):
        """处理用户认证"""
        openid = payload.get('openid')
        if openid:
            self.user_openid = openid
            
            # 更新房间玩家在线状态
            await self.update_player_online_status(self.room_code, openid, True)
            
            # 广播玩家上线
            await self.broadcast_event({
                'type': 'room',
                'action': 'player_online',
                'data': {'openid': openid}
            })
            
            await self.send(text_data=json.dumps({
                'type': 'auth',
                'action': 'success',
                'data': {'openid': openid}
            }))
    
    async def handle_room_event(self, action, payload):
        """处理房间事件"""
        if action == 'ready':
            # 玩家准备
            is_ready = payload.get('is_ready', True)
            room = await self.update_player_ready(self.room_code, self.user_openid, is_ready)
            
            await self.broadcast_event({
                'type': 'room',
                'action': 'player_ready_changed',
                'data': {
                    'openid': self.user_openid,
                    'is_ready': is_ready,
                    'can_start_game': room.can_start_game if room else False
                }
            })
        
        elif action == 'leave':
            # 玩家离开
            await self.broadcast_event({
                'type': 'room',
                'action': 'player_left',
                'data': {'openid': self.user_openid}
            })
    
    async def handle_game_event(self, action, payload):
        """处理游戏事件"""
        if action == 'start':
            # 开始游戏
            game = await self.start_game(self.room_code)
            if game:
                await self.broadcast_event({
                    'type': 'game',
                    'action': 'started',
                    'data': {
                        'game_id': game.id,
                        'round': game.round,
                        'speaker_order': game.speaker_order
                    }
                })
        
        elif action == 'speak':
            # 发言完成
            content = payload.get('content', '')
            await self.record_speak(self.room_code, self.user_openid, content)
            
            await self.broadcast_event({
                'type': 'game',
                'action': 'player_spoke',
                'data': {
                    'openid': self.user_openid,
                    'content': content
                }
            })
            
            # 检查是否所有人都发言完毕
            game = await self.get_current_game(self.room_code)
            if game:
                # 获取下一个发言者
                next_speaker = await self.get_next_speaker(game.id)
                if next_speaker:
                    await self.broadcast_event({
                        'type': 'game',
                        'action': 'next_speaker',
                        'data': {'next_speaker': next_speaker}
                    })
                else:
                    # 进入投票阶段
                    await self.start_voting(game.id)
                    await self.broadcast_event({
                        'type': 'game',
                        'action': 'voting_started',
                        'data': {}
                    })
        
        elif action == 'vote':
            # 投票
            target_openid = payload.get('target_openid')
            if target_openid:
                result = await self.record_vote(self.room_code, self.user_openid, target_openid)
                
                await self.broadcast_event({
                    'type': 'game',
                    'action': 'vote_recorded',
                    'data': {
                        'voter': self.user_openid,
                        'target': target_openid
                    }
                })
                
                # 检查投票是否完成
                if result and result.get('completed'):
                    await self.broadcast_event({
                        'type': 'game',
                        'action': 'voting_completed',
                        'data': result
                    })
        
        elif action == 'next_round':
            # 下一轮
            game = await self.next_round(self.room_code)
            if game:
                await self.broadcast_event({
                    'type': 'game',
                    'action': 'round_started',
                    'data': {
                        'round': game.round,
                        'current_speaker': game.current_speaker
                    }
                })
    
    async def handle_chat(self, payload):
        """处理聊天消息"""
        from apps.users.models import User
        from apps.rooms.models import Room
        
        try:
            room = await database_sync_to_async(Room.objects.get)(code=self.room_code)
            player = room.get_player(self.user_openid)
            
            if player:
                await self.broadcast_event({
                    'type': 'chat',
                    'action': 'message',
                    'data': {
                        'openid': self.user_openid,
                        'nickname': player.get('nickname', ''),
                        'avatar': player.get('avatar', ''),
                        'content': payload.get('content', ''),
                        'timestamp': payload.get('timestamp')
                    }
                })
        except Exception as e:
            logger.error(f'Error handling chat: {str(e)}')
    
    # ==================== 广播方法 ====================
    
    async def broadcast_event(self, event):
        """向房间内所有玩家广播事件"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'room_message',
                'message': event
            }
        )
    
    async def room_message(self, event):
        """发送消息到 WebSocket"""
        await self.send(text_data=json.dumps(event['message']))
    
    # ==================== 数据库操作 ====================
    
    @database_sync_to_async
    def update_player_online_status(self, room_code, openid, is_online):
        """更新玩家在线状态"""
        from apps.rooms.models import Room
        
        try:
            room = Room.objects.get(code=room_code)
            room.set_online_status(openid, is_online)
            return True
        except Room.DoesNotExist:
            return False
    
    @database_sync_to_async
    def update_player_ready(self, room_code, openid, is_ready):
        """更新玩家准备状态"""
        from apps.rooms.models import Room
        
        try:
            room = Room.objects.get(code=room_code)
            room.set_player_ready(openid, is_ready)
            return room
        except Room.DoesNotExist:
            return None
    
    @database_sync_to_async
    def start_game(self, room_code):
        """开始游戏"""
        from apps.rooms.models import Room
        from apps.games.models import Game, WordSet
        
        try:
            room = Room.objects.get(code=room_code)
            
            # 检查是否可以开始游戏
            if not room.can_start_game:
                return None
            
            # 获取官方词库
            word_set = WordSet.objects.filter(is_official=True, status=WordSet.STATUS_APPROVED).first()
            
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
            game.assign_roles_and_words()
            
            # 更新房间状态
            room.status = Room.STATUS_PLAYING
            room.current_game = game
            room.save(update_fields=['status', 'current_game', 'updated_at'])
            
            # 更新游戏状态为发言阶段
            game.status = Game.STATUS_SPEAKING
            game.save(update_fields=['status'])
            
            return game
        except Exception as e:
            logger.error(f'Error starting game: {str(e)}')
            return None
    
    @database_sync_to_async
    def get_current_game(self, room_code):
        """获取当前房间的游戏"""
        from apps.rooms.models import Room
        
        try:
            room = Room.objects.get(code=room_code)
            return room.current_game
        except Room.DoesNotExist:
            return None
    
    @database_sync_to_async
    def record_speak(self, room_code, openid, content):
        """记录发言"""
        from apps.rooms.models import Room
        from apps.games.models import Game, SpeakRecord
        
        try:
            room = Room.objects.get(code=room_code)
            game = room.current_game
            
            if not game:
                return None
            
            player = room.get_player(openid)
            
            record = SpeakRecord.objects.create(
                game=game,
                player_openid=openid,
                player_nickname=player.get('nickname', '') if player else '',
                round=game.round,
                content=content
            )
            
            return record
        except Exception as e:
            logger.error(f'Error recording speak: {str(e)}')
            return None
    
    @database_sync_to_async
    def get_next_speaker(self, game_id):
        """获取下一个发言者"""
        from apps.games.models import Game
        
        try:
            game = Game.objects.get(id=game_id)
            next_openid = game.get_next_speaker()
            return next_openid
        except Game.DoesNotExist:
            return None
    
    @database_sync_to_async
    def start_voting(self, game_id):
        """开始投票阶段"""
        from apps.games.models import Game
        
        try:
            game = Game.objects.get(id=game_id)
            game.status = Game.STATUS_VOTING
            game.votes = {}
            game.save(update_fields=['status', 'votes'])
            return game
        except Game.DoesNotExist:
            return None
    
    @database_sync_to_async
    def record_vote(self, room_code, voter_openid, target_openid):
        """记录投票"""
        from apps.rooms.models import Room
        from apps.games.models import Game
        
        try:
            room = Room.objects.get(code=room_code)
            game = room.current_game
            
            if not game or game.status != Game.STATUS_VOTING:
                return None
            
            # 记录投票
            result = game.add_vote(voter_openid, target_openid)
            
            if result:
                # 检查投票结果
                player_count = len(game.speaker_order)
                if len(game.votes) >= player_count:
                    return self.process_vote_result(game, result)
            
            return {'completed': False}
        except Exception as e:
            logger.error(f'Error recording vote: {str(e)}')
            return None
    
    def process_vote_result(self, game, result):
        """处理投票结果"""
        from apps.games.models import Game, GameResult
        from apps.users.models import User
        from django.utils import timezone
        
        eliminated = result.get('eliminated')
        
        if eliminated:
            # 有人被投出
            game.revealed_player = eliminated
            game.is_joker_revealed = result.get('is_joker', False)
            
            if game.is_joker_revealed:
                # 卧底被投出，平民胜利
                game.status = Game.STATUS_FINISHED
                game.winner = 0
                game.ended_at = timezone.now()
            else:
                # 平民被投出
                # 检查是否还有卧底存活
                remaining_jokers = 0
                for openid in game.speaker_order:
                    if openid != eliminated and game.is_player_joker(openid):
                        remaining_jokers += 1
                
                if remaining_jokers == 0:
                    # 没有卧底了，平民胜利
                    game.status = Game.STATUS_FINISHED
                    game.winner = 0
                    game.ended_at = timezone.now()
                elif game.round >= game.max_rounds:
                    # 达到最大轮数，卧底胜利
                    game.status = Game.STATUS_FINISHED
                    game.winner = 1
                    game.ended_at = timezone.now()
                else:
                    # 游戏继续，进入下一轮
                    game.status = Game.STATUS_REVEALING
            
            game.save()
            
            # 保存游戏结果
            if game.status == Game.STATUS_FINISHED:
                self.save_game_result(game)
                self.calculate_scores(game)
        
        return {
            'completed': True,
            'result': result
        }
    
    @database_sync_to_async
    def save_game_result(self, game):
        """保存游戏结果"""
        from apps.games.models import GameResult
        
        GameResult.objects.create(
            game=game,
            winner=game.winner,
            civilian_word=game.civilian_word,
            joker_word=game.joker_word,
            total_rounds=game.round
        )
    
    @database_sync_to_async
    def calculate_scores(self, game):
        """计算并更新玩家积分"""
        from apps.games.models import GameResult
        from apps.users.models import User
        from django.conf import settings
        
        score_rules = settings.GAME_CONFIG.get('SCORE_RULES', {})
        civilian_win_score = score_rules.get('civilian_win', 10)
        civilian_lose_score = score_rules.get('civilian_lose', 3)
        joker_win_score = score_rules.get('joker_win', 15)
        joker_lose_score = score_rules.get('joker_lose', 5)
        
        for openid in game.speaker_order:
            try:
                user = User.objects.get(openid=openid)
                is_joker = game.is_player_joker(openid)
                
                # 计算积分
                if is_joker:
                    if game.winner == 1:  # 卧底胜利
                        score = joker_win_score
                    else:
                        score = joker_lose_score
                else:
                    if game.winner == 0:  # 平民胜利
                        score = civilian_win_score
                    else:
                        score = civilian_lose_score
                
                # 更新积分
                user.add_score(score, 'joker_win' if (is_joker and game.winner == 1) else 'game_win')
                
                # 更新房间玩家积分
                room = game.room
                for player in room.players:
                    if player['openid'] == openid:
                        player['score'] = score
                        break
                room.save(update_fields=['players'])
                
                # 更新用户游戏统计
                user.update_game_stats(
                    won=(game.winner == 0 and not is_joker) or (game.winner == 1 and is_joker),
                    as_joker=is_joker,
                    joker_won=(is_joker and game.winner == 1)
                )
                
            except User.DoesNotExist:
                continue
    
    @database_sync_to_async
    def next_round(self, room_code):
        """进入下一轮"""
        from apps.rooms.models import Room
        from apps.games.models import Game
        
        try:
            room = Room.objects.get(code=room_code)
            game = room.current_game
            
            if not game:
                return None
            
            # 重置投票
            game.votes = {}
            
            # 轮数加1
            game.round += 1
            
            # 重新随机发言顺序
            game.speaker_order = game.speaker_order  # 保持当前顺序
            game.current_speaker_index = 0
            game.current_speaker = game.speaker_order[0] if game.speaker_order else ''
            
            # 更新状态
            game.status = Game.STATUS_SPEAKING
            
            # 重置房间玩家准备状态
            room.reset_ready_status()
            
            game.save()
            room.save()
            
            return game
        except Exception as e:
            logger.error(f'Error starting next round: {str(e)}')
            return None
