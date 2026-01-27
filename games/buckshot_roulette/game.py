"""
游戏主逻辑 - 恶魔轮盘赌
"""
import discord
import asyncio
from typing import Dict, Optional, TYPE_CHECKING

from .session import GameSession, ActionResult
from .player import Player
from .items import Item
from .embeds import create_game_embed, create_stage_complete_embed, create_game_over_embed
from .views import GameView, StageCompleteView, GameOverView
from utils.constants import GameMode, GameState
from config import Config

if TYPE_CHECKING:
    from bot import GameCenterBot


class BuckshotRouletteGame:
    """恶魔轮盘赌游戏管理器"""
    
    def __init__(self, bot: 'GameCenterBot'):
        self.bot = bot
        self.sessions: Dict[str, GameSession] = {}  # session_id -> session
        self.user_sessions: Dict[int, str] = {}     # user_id -> session_id
    
    def get_session_by_user(self, user_id: int) -> Optional[GameSession]:
        """通过用户ID获取会话"""
        session_id = self.user_sessions.get(user_id)
        if session_id:
            return self.sessions.get(session_id)
        return None
    
    def create_session(self, mode: str) -> GameSession:
        """创建新会话"""
        session = GameSession(mode=mode)
        self.sessions[session.id] = session
        return session
    
    def remove_session(self, session: GameSession) -> None:
        """移除会话"""
        if session.id in self.sessions:
            del self.sessions[session.id]
        
        for player in session.players:
            if player.user_id in self.user_sessions:
                del self.user_sessions[player.user_id]
    
    async def start_pve_game(self, interaction: discord.Interaction) -> None:
        """开始PvE游戏"""
        user_id = interaction.user.id
        
        # 检查是否已在游戏中
        existing = self.get_session_by_user(user_id)
        if existing:
            await interaction.response.send_message(
                "你已经在一局游戏中了！",
                ephemeral=True
            )
            return
        
        # 检查并扣除入场费
        success = await self.bot.economy.deduct_chips(user_id, Config.PVE_ENTRY_FEE, "PvE入场费")
        if not success:
            await interaction.response.send_message(
                f"余额不足！需要 {Config.PVE_ENTRY_FEE} 🎰 入场费",
                ephemeral=True
            )
            return
        
        # 创建会话
        session = self.create_session(GameMode.PVE)
        session.initialize_pve(user_id, interaction.user.display_name)
        session.channel_id = interaction.channel_id
        
        # 记录用户会话
        self.user_sessions[user_id] = session.id
        
        # 开始第一轮
        session.start_round()
        
        # 发送游戏界面
        embed = create_game_embed(session)
        view = GameView(self, session, user_id)
        session.set_current_view(view)  # 注册当前视图
        
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()
        session.message_id = view.message.id
    
    async def start_quick_game(self, interaction: discord.Interaction, difficulty: str = "normal") -> None:
        """开始快速游戏
        
        Args:
            interaction: Discord交互
            difficulty: AI难度 (easy/normal/hard/hard_plus/demon)
        """
        user_id = interaction.user.id
        
        # 检查是否已在游戏中
        existing = self.get_session_by_user(user_id)
        if existing:
            await interaction.response.send_message(
                "你已经在一局游戏中了！",
                ephemeral=True
            )
            return
        
        # 获取难度配置
        diff_config = Config.QUICK_DIFFICULTY_CONFIG.get(difficulty, Config.QUICK_DIFFICULTY_CONFIG["normal"])
        entry_fee = diff_config["entry_fee"]
        
        # 检查并扣除入场费
        success = await self.bot.economy.deduct_chips(user_id, entry_fee, f"快速模式入场费({diff_config['name']})")
        if not success:
            await interaction.response.send_message(
                f"余额不足！需要 {entry_fee} 🎰 入场费",
                ephemeral=True
            )
            return
        
        # 创建会话
        session = self.create_session(GameMode.QUICK)
        session.initialize_quick(user_id, interaction.user.display_name, difficulty)
        session.channel_id = interaction.channel_id
        
        # 记录用户会话
        self.user_sessions[user_id] = session.id
        
        # 开始游戏
        session.start_round()
        
        # 发送游戏界面
        embed = create_game_embed(session)
        view = GameView(self, session, user_id)
        session.set_current_view(view)  # 注册当前视图
        
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()
        session.message_id = view.message.id
    
    async def start_pvp_game(self, interaction: discord.Interaction,
                             player1_id: int, player2_id: int, bet: int) -> None:
        """开始PvP游戏"""
        # 扣除双方押注
        success1 = await self.bot.economy.deduct_chips(player1_id, bet, "PvP押注")
        success2 = await self.bot.economy.deduct_chips(player2_id, bet, "PvP押注")
        
        if not success1 or not success2:
            # 退还已扣除的
            if success1:
                await self.bot.economy.add_chips(player1_id, bet, "PvP押注退还")
            if success2:
                await self.bot.economy.add_chips(player2_id, bet, "PvP押注退还")
            
            await interaction.followup.send(
                "押注失败，余额不足！",
                ephemeral=True
            )
            return
        
        # 获取玩家名称
        try:
            user1 = await self.bot.fetch_user(player1_id)
            user2 = await self.bot.fetch_user(player2_id)
            name1 = user1.display_name
            name2 = user2.display_name
        except:
            name1 = f"玩家{player1_id}"
            name2 = f"玩家{player2_id}"
        
        # 创建会话
        session = self.create_session(GameMode.PVP)
        session.initialize_pvp(player1_id, name1, player2_id, name2, bet)
        session.channel_id = interaction.channel_id
        
        # 记录用户会话
        self.user_sessions[player1_id] = session.id
        self.user_sessions[player2_id] = session.id
        
        # 开始第一轮
        session.start_round()
        
        # 发送游戏界面
        embed = create_game_embed(session)
        current_user_id = session.current_player.user_id
        view = GameView(self, session, current_user_id)
        session.set_current_view(view)  # 注册当前视图
        
        message = await interaction.followup.send(embed=embed, view=view)
        view.message = message
        session.message_id = message.id
    
    async def start_new_game(self, interaction: discord.Interaction, mode: str) -> None:
        """开始新游戏（再来一局）"""
        if mode == GameMode.PVE:
            await self.start_pve_game(interaction)
        elif mode == GameMode.QUICK:
            await self.start_quick_game(interaction)
        else:
            await interaction.response.send_message(
                "请使用游戏中心发起新的PvP挑战",
                ephemeral=True
            )
    
    async def handle_shoot_opponent(self, session: GameSession, 
                                    interaction: discord.Interaction) -> None:
        """处理射击对手"""
        result = session.shoot_opponent()
        
        await self._process_action_result(session, interaction, result)
    
    async def handle_shoot_self(self, session: GameSession,
                                interaction: discord.Interaction) -> None:
        """处理射击自己"""
        result = session.shoot_self()
        
        await self._process_action_result(session, interaction, result)
    
    async def handle_use_item(self, session: GameSession,
                              interaction: discord.Interaction,
                              item: Item, target_index: Optional[int] = None) -> None:
        """处理使用道具"""
        result = session.use_item(item, target_index)
        
        # 如果有私密信息，通过 ephemeral 消息发送给使用者
        if result.private_info:
            try:
                await interaction.followup.send(
                    f"🔒 **私密信息**\n{result.private_info}",
                    ephemeral=True
                )
            except:
                pass
        
        await self._process_action_result(session, interaction, result)
    
    async def _process_action_result(self, session: GameSession,
                                     interaction: discord.Interaction,
                                     result: ActionResult) -> None:
        """处理动作结果"""
        if result.game_over:
            await self._handle_game_over(session, interaction)
            return
        
        if result.round_over:
            # 先更新一次界面，显示最后的动作结果（弹夹打空前的状态）
            await self._update_game_view(session, interaction)
            
            # 等待一段时间让玩家看到结果，再进行装填
            await asyncio.sleep(Config.RELOAD_DELAY)
            
            stage_complete = session.handle_round_end()
            
            if session.state == GameState.STAGE_COMPLETE:
                await self._show_stage_complete(session, interaction)
                return
            elif session.state == GameState.ENDED:
                await self._handle_game_over(session, interaction)
                return
            
            # 发送装填通知消息（30秒后删除）
            await self._send_reload_notification(session, interaction)
            
            # 新一轮已经开始，直接更新界面
            await self._update_game_view(session, interaction)
            
            # 如果是AI回合，先等待让玩家看到装填信息，再执行AI动作
            if session.current_player.is_ai:
                await asyncio.sleep(Config.RELOAD_DELAY)  # 额外等待让玩家看到装填信息
                await self._execute_ai_turn(session, interaction)
            return
        
        # 切换回合（除非获得额外回合）
        if not result.extra_turn:
            session.next_turn()
        
        # 更新界面
        await self._update_game_view(session, interaction)
        
        # 如果是AI回合，执行AI动作
        if session.current_player.is_ai:
            await self._execute_ai_turn(session, interaction)
    
    async def _update_game_view(self, session: GameSession,
                                interaction: discord.Interaction) -> None:
        """更新游戏界面"""
        embed = create_game_embed(session)
        current_user_id = session.current_player.user_id
        if session.current_player.is_ai:
            current_user_id = session.human_player.user_id
        
        view = GameView(self, session, current_user_id)
        session.set_current_view(view)  # 注册当前视图，停止旧视图
        
        try:
            await interaction.edit_original_response(embed=embed, view=view)
            view.message = await interaction.original_response()
            
            # PVP模式：提醒当前玩家轮到他了
            if session.mode == GameMode.PVP and not session.current_player.is_ai:
                current_player = session.current_player
                # 发送一条提醒消息，@玩家
                try:
                    channel = interaction.channel
                    if channel:
                        mention_msg = await channel.send(
                            f"🔔 <@{current_player.user_id}> 轮到你行动了！"
                        )
                        # 5秒后自动删除提醒消息
                        asyncio.create_task(self._delete_after(mention_msg, 5))
                except:
                    pass
        except:
            pass
    
    async def _delete_after(self, message: discord.Message, delay: int) -> None:
        """延迟删除消息"""
        await asyncio.sleep(delay)
        try:
            await message.delete()
        except:
            pass
    
    async def _send_reload_notification(self, session: GameSession,
                                        interaction: discord.Interaction) -> None:
        """发送装填通知消息（30秒后删除）"""
        try:
            channel = interaction.channel
            if channel:
                live = session.shotgun.live_count
                blank = session.shotgun.blank_count
                total = live + blank
                
                # 创建装填通知嵌入消息
                embed = discord.Embed(
                    title="🔫 弹夹装填完成",
                    description=f"**实弹**: {live} 发 🔴\n**空包弹**: {blank} 发 ⚪\n**总计**: {total} 发",
                    color=discord.Color.orange()
                )
                embed.set_footer(text="此消息将在30秒后自动删除")
                
                reload_msg = await channel.send(embed=embed)
                # 30秒后自动删除
                asyncio.create_task(self._delete_after(reload_msg, 30))
        except:
            pass
    
    async def _show_stage_complete(self, session: GameSession,
                                   interaction: discord.Interaction) -> None:
        """显示阶段完成界面"""
        embed = create_stage_complete_embed(session)
        view = StageCompleteView(self, session, session.human_player.user_id)
        session.set_current_view(view)  # 注册当前视图
        
        try:
            await interaction.edit_original_response(embed=embed, view=view)
            view.message = await interaction.original_response()
        except:
            pass
    
    async def _handle_game_over(self, session: GameSession,
                                interaction: discord.Interaction) -> None:
        """处理游戏结束"""
        session.state = GameState.ENDED
        
        winner = session.get_winner()
        human = session.human_player
        
        # 计算奖励
        if session.mode == GameMode.PVE:
            won = winner and not winner.is_ai
            if won and session.accumulated_reward > 0:
                await self.bot.economy.add_chips(
                    human.user_id, 
                    session.accumulated_reward,
                    "PvE奖励"
                )
        elif session.mode == GameMode.PVP:
            if winner:
                total_pot = session.bet_amount * 2
                await self.bot.economy.add_chips(
                    winner.user_id,
                    total_pot,
                    "PvP胜利奖励"
                )
        else:  # QUICK
            won = winner and not winner.is_ai
            if won:
                # 获取难度配置确定奖励
                difficulty = session.ai_difficulty or "normal"
                diff_config = Config.QUICK_DIFFICULTY_CONFIG.get(difficulty, Config.QUICK_DIFFICULTY_CONFIG["normal"])
                reward = diff_config["reward"]
                await self.bot.economy.add_chips(
                    human.user_id,
                    reward,
                    f"快速模式奖励({diff_config['name']})"
                )
        
        # 更新统计
        await self._update_stats(session)
        
        # 显示结束界面
        # 对于PvE和快速模式，检查人类玩家是否获胜
        # 对于PvP模式，won参数用于显示胜利者信息，这里传True让embed显示胜利者
        if session.mode == GameMode.PVP:
            won = winner is not None  # PvP模式只要有胜利者就显示胜利界面
            # PvP模式：只有挑战发起者可以操作结束界面
            view_owner_id = session.challenger_id
        else:
            won = winner is not None and winner.user_id == human.user_id
            view_owner_id = human.user_id
        embed = create_game_over_embed(session, won)
        view = GameOverView(self, session, view_owner_id)
        session.set_current_view(view)  # 注册当前视图
        
        try:
            await interaction.edit_original_response(embed=embed, view=view)
            view.message = await interaction.original_response()
            
            # 计划自动删除消息
            if Config.AUTO_DELETE_MESSAGES:
                asyncio.create_task(view.schedule_delete(Config.GAME_OVER_DELETE_DELAY))
        except:
            pass
        
        # 清理会话
        self.remove_session(session)
    
    async def _update_stats(self, session: GameSession) -> None:
        """更新玩家统计"""
        winner = session.get_winner()
        
        for player in session.players:
            if player.is_ai:
                continue
            
            stats = await self.bot.database.get_player_stats(player.user_id)
            stats.games_played += 1
            
            if winner and winner.user_id == player.user_id:
                stats.games_won += 1
            
            if session.mode == GameMode.PVE:
                stage = session.stage_manager.current_stage
                if stage > stats.pve_best_stage:
                    stats.pve_best_stage = stage
                if session.accumulated_reward > 0:
                    stats.pve_total_earnings += session.accumulated_reward
            elif session.mode == GameMode.PVP:
                if winner and winner.user_id == player.user_id:
                    stats.pvp_wins += 1
                    stats.pvp_total_earnings += session.bet_amount * 2
                else:
                    stats.pvp_losses += 1
            
            await self.bot.database.update_player_stats(stats)
    
    async def handle_retreat(self, session: GameSession,
                            interaction: discord.Interaction) -> None:
        """处理撤离"""
        reward = session.handle_retreat()
        
        # 发放奖励
        await self.bot.economy.add_chips(
            session.human_player.user_id,
            reward,
            "PvE撤离奖励"
        )
        
        # 更新统计
        await self._update_stats(session)
        
        # 显示结束界面
        embed = create_game_over_embed(session, True)
        view = GameOverView(self, session, session.human_player.user_id)
        session.set_current_view(view)  # 注册当前视图
        
        try:
            await interaction.edit_original_response(embed=embed, view=view)
            view.message = await interaction.original_response()
            
            # 计划自动删除消息
            if Config.AUTO_DELETE_MESSAGES:
                asyncio.create_task(view.schedule_delete(Config.GAME_OVER_DELETE_DELAY))
        except:
            pass
        
        # 清理会话
        self.remove_session(session)
    
    async def handle_continue(self, session: GameSession,
                             interaction: discord.Interaction) -> None:
        """处理继续挑战"""
        session.handle_continue()
        
        # 更新界面
        await self._update_game_view(session, interaction)
        
        # 如果是AI回合，执行AI动作
        if session.current_player.is_ai:
            await self._execute_ai_turn(session, interaction)
    
    async def handle_timeout(self, session: GameSession) -> None:
        """处理超时"""
        if session.state != GameState.PLAYING:
            return
        
        # 超时自动射击对手
        result = session.shoot_opponent()
        
        # 由于没有interaction，需要直接编辑消息
        # 这里简化处理，直接结束游戏
        if result.game_over or result.round_over:
            session.state = GameState.ENDED
            self.remove_session(session)
    
    async def _execute_ai_turn(self, session: GameSession,
                               interaction: discord.Interaction) -> None:
        """执行AI回合"""
        # 延迟模拟思考
        await asyncio.sleep(Config.AI_THINK_DELAY)
        
        # 导入AI模块
        from .ai import AIPlayer
        
        # 快速模式使用指定难度，其他模式使用阶段难度
        if session.mode == GameMode.QUICK and session.ai_difficulty:
            ai_level = session.ai_difficulty
        else:
            ai_level = session.stage_manager.get_ai_level()
        
        ai = AIPlayer(ai_level)
        action = ai.decide_action(session)
        
        if action["type"] == "shoot_opponent":
            result = session.shoot_opponent()
        elif action["type"] == "shoot_self":
            result = session.shoot_self()
        elif action["type"] == "use_item":
            item = action["item"]
            target = action.get("target")
            result = session.use_item(item, target)
        else:
            # 默认射击对手
            result = session.shoot_opponent()
        
        await self._process_action_result(session, interaction, result)