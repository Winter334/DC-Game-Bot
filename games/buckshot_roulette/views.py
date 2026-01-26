"""
Discord Views - 恶魔轮盘赌
"""
import discord
from discord import ui
from typing import TYPE_CHECKING, Optional, Dict
import asyncio

from ui.base_views import BaseView
from config import Config
from ui.menus import MenuButton, BackButton
from utils.constants import Emoji, Colors, GameState
from utils.helpers import format_chips
from config import Config

from .embeds import (
    create_game_embed, create_stage_complete_embed, 
    create_game_over_embed, create_item_select_embed,
    create_adrenaline_select_embed
)
from .items import ItemType

if TYPE_CHECKING:
    from .session import GameSession
    from .game import BuckshotRouletteGame


class GameView(BaseView):
    """游戏主界面View"""
    
    def __init__(self, game: 'BuckshotRouletteGame', session: 'GameSession', user_id: int):
        super().__init__(user_id, timeout=Config.TURN_TIMEOUT)
        self.game = game
        self.session = session
        self._setup_buttons()
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """PVP模式下允许两个玩家都能交互（但只有当前玩家能操作按钮）"""
        from utils.constants import GameMode
        
        if self.session.mode == GameMode.PVP:
            # PVP模式：检查是否是游戏中的玩家
            player_ids = [p.user_id for p in self.session.players]
            if interaction.user.id in player_ids:
                # 重置超时
                self.reset_timeout()
                # 只有当前玩家能操作
                if interaction.user.id == self.session.current_player.user_id:
                    return True
                else:
                    await interaction.response.send_message(
                        "⏳ 还没轮到你行动！",
                        ephemeral=True
                    )
                    return False
            else:
                await interaction.response.send_message(
                    "❌ 这不是你的游戏！",
                    ephemeral=True
                )
                return False
        else:
            # 其他模式使用默认检查
            return await super().interaction_check(interaction)
    
    def _setup_buttons(self):
        """设置按钮"""
        # 只有当前玩家可以操作
        is_current = self.session.current_player.user_id == self.user_id
        is_ai_turn = self.session.current_player.is_ai
        
        # 射击对手
        self.add_item(MenuButton(
            label="射击对手",
            emoji=Emoji.SHOOT,
            callback=self.on_shoot_opponent,
            style=discord.ButtonStyle.danger,
            disabled=not is_current or is_ai_turn,
            row=0
        ))
        
        # 射击自己
        self.add_item(MenuButton(
            label="射击自己",
            emoji=Emoji.TARGET,
            callback=self.on_shoot_self,
            style=discord.ButtonStyle.primary,
            disabled=not is_current or is_ai_turn,
            row=0
        ))
        
        # 使用道具
        has_items = len(self.session.current_player.items) > 0 if is_current else False
        self.add_item(MenuButton(
            label="使用道具",
            emoji=Emoji.ITEM,
            callback=self.on_use_item,
            style=discord.ButtonStyle.secondary,
            disabled=not is_current or is_ai_turn or not has_items,
            row=0
        ))
    
    async def on_shoot_opponent(self, interaction: discord.Interaction):
        """射击对手"""
        await interaction.response.defer()
        await self.game.handle_shoot_opponent(self.session, interaction)
    
    async def on_shoot_self(self, interaction: discord.Interaction):
        """射击自己"""
        await interaction.response.defer()
        await self.game.handle_shoot_self(self.session, interaction)
    
    async def on_use_item(self, interaction: discord.Interaction):
        """使用道具"""
        embed = create_item_select_embed(self.session)
        view = ItemSelectView(self.game, self.session, self.user_id)
        self.session.set_current_view(view)  # 注册当前视图
        view.message = self.message
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def on_timeout(self):
        """超时处理"""
        if self.session.state == GameState.PLAYING:
            # 超时自动射击对手
            await self.game.handle_timeout(self.session)


class ItemSelectView(BaseView):
    """道具选择View"""
    
    def __init__(self, game: 'BuckshotRouletteGame', session: 'GameSession', user_id: int):
        super().__init__(user_id, timeout=Config.ITEM_SELECT_TIMEOUT)
        self.game = game
        self.session = session
        self._setup_buttons()
    
    def _setup_buttons(self):
        """设置道具按钮"""
        player = self.session.current_player
        
        for i, item in enumerate(player.items[:8]):  # 最多显示8个
            row = i // 4
            self.add_item(MenuButton(
                label=item.name,
                emoji=item.emoji,
                callback=lambda inter, idx=i: self.on_item_select(inter, idx),
                style=discord.ButtonStyle.secondary,
                row=row
            ))
        
        # 返回按钮
        self.add_item(BackButton(callback=self.on_back, row=2))
    
    async def on_item_select(self, interaction: discord.Interaction, index: int):
        """选择道具"""
        player = self.session.current_player
        if index < len(player.items):
            item = player.items[index]
            
            # 检查是否需要选择目标（肾上腺素）
            if item.item_type == ItemType.ADRENALINE:
                stealable = [i for i in self.session.opponent.items if i.can_be_stolen]
                if stealable:
                    embed = create_adrenaline_select_embed(self.session)
                    view = AdrenalineTargetView(self.game, self.session, self.user_id, item)
                    self.session.set_current_view(view)  # 注册当前视图
                    view.message = self.message
                    await interaction.response.edit_message(embed=embed, view=view)
                    return
            
            await interaction.response.defer()
            await self.game.handle_use_item(self.session, interaction, item)
    
    async def on_back(self, interaction: discord.Interaction):
        """返回游戏界面"""
        embed = create_game_embed(self.session)
        view = GameView(self.game, self.session, self.user_id)
        self.session.set_current_view(view)  # 注册当前视图
        view.message = self.message
        await interaction.response.edit_message(embed=embed, view=view)


class AdrenalineTargetView(BaseView):
    """肾上腺素目标选择View"""
    
    def __init__(self, game: 'BuckshotRouletteGame', session: 'GameSession',
                 user_id: int, adrenaline_item):
        super().__init__(user_id, timeout=Config.ITEM_SELECT_TIMEOUT)
        self.game = game
        self.session = session
        self.adrenaline_item = adrenaline_item
        self._setup_buttons()
    
    def _setup_buttons(self):
        """设置目标按钮"""
        opponent = self.session.opponent
        stealable = [item for item in opponent.items if item.can_be_stolen]
        
        for i, item in enumerate(stealable[:8]):
            row = i // 4
            self.add_item(MenuButton(
                label=item.name,
                emoji=item.emoji,
                callback=lambda inter, idx=i: self.on_target_select(inter, idx),
                style=discord.ButtonStyle.secondary,
                row=row
            ))
        
        # 返回按钮
        self.add_item(BackButton(callback=self.on_back, row=2))
    
    async def on_target_select(self, interaction: discord.Interaction, index: int):
        """选择目标"""
        await interaction.response.defer()
        await self.game.handle_use_item(self.session, interaction, self.adrenaline_item, index)
    
    async def on_back(self, interaction: discord.Interaction):
        """返回道具选择"""
        embed = create_item_select_embed(self.session)
        view = ItemSelectView(self.game, self.session, self.user_id)
        self.session.set_current_view(view)  # 注册当前视图
        view.message = self.message
        await interaction.response.edit_message(embed=embed, view=view)


class StageCompleteView(BaseView):
    """阶段完成View"""
    
    def __init__(self, game: 'BuckshotRouletteGame', session: 'GameSession', user_id: int):
        super().__init__(user_id, timeout=Config.STAGE_COMPLETE_TIMEOUT)
        self.game = game
        self.session = session
        self._setup_buttons()
    
    def _setup_buttons(self):
        """设置按钮"""
        reward = self.session.stage_manager.get_current_reward()
        
        # 撤离按钮
        self.add_item(MenuButton(
            label=f"领取 {reward}🎰 撤离",
            emoji=Emoji.RUN,
            callback=self.on_retreat,
            style=discord.ButtonStyle.success,
            row=0
        ))
        
        # 继续按钮
        self.add_item(MenuButton(
            label="翻倍继续挑战",
            emoji=Emoji.CONTINUE,
            callback=self.on_continue,
            style=discord.ButtonStyle.danger,
            row=0
        ))
    
    async def on_retreat(self, interaction: discord.Interaction):
        """撤离"""
        await interaction.response.defer()
        await self.game.handle_retreat(self.session, interaction)
    
    async def on_continue(self, interaction: discord.Interaction):
        """继续挑战"""
        await interaction.response.defer()
        await self.game.handle_continue(self.session, interaction)


class GameOverView(BaseView):
    """游戏结束View"""
    
    def __init__(self, game: 'BuckshotRouletteGame', session: 'GameSession', user_id: int):
        super().__init__(user_id, timeout=Config.GAME_OVER_TIMEOUT)
        self.game = game
        self.session = session
        self._setup_buttons()
    
    def _setup_buttons(self):
        """设置按钮"""
        # 再来一局
        self.add_item(MenuButton(
            label="再来一局",
            emoji=Emoji.RELOAD,
            callback=self.on_play_again,
            style=discord.ButtonStyle.primary,
            row=0
        ))
        
        # 返回主菜单
        self.add_item(MenuButton(
            label="返回主菜单",
            emoji="🏠",
            callback=self.on_main_menu,
            style=discord.ButtonStyle.secondary,
            row=0
        ))
    
    async def on_play_again(self, interaction: discord.Interaction):
        """再来一局"""
        await self.game.start_new_game(interaction, self.session.mode)
    
    async def on_main_menu(self, interaction: discord.Interaction):
        """返回主菜单"""
        # 获取游戏中心cog和用户余额
        cog = self.game.bot.get_cog('GameCenterCog')
        balance = await self.game.bot.economy.get_balance(self.user_id)
        
        # 导入必要的类（避免循环导入）
        from cogs.game_center import GameCenterView
        
        # 创建主菜单embed
        embed = discord.Embed(
            title=f"{Emoji.GAME} 游戏中心",
            description=f"{Emoji.CHIPS} 余额: {balance:,}",
            color=Colors.PRIMARY
        )
        embed.add_field(
            name="欢迎来到游戏中心！",
            value="选择一个游戏开始：\n\n"
                  f"{Emoji.BUCKSHOT} **恶魔轮盘赌** - 与恶魔进行致命的轮盘赌\n"
                  f"🎲 更多游戏即将推出...",
            inline=False
        )
        
        # 创建主菜单视图
        view = GameCenterView(cog, self.user_id, balance)
        view.message = self.message
        await interaction.response.edit_message(embed=embed, view=view)


class PvPChallengeView(BaseView):
    """PvP挑战View"""
    
    def __init__(self, game: 'BuckshotRouletteGame', challenger_id: int, 
                 target_id: int, bet_amount: int):
        super().__init__(target_id, timeout=Config.CHALLENGE_TIMEOUT)
        self.game = game
        self.challenger_id = challenger_id
        self.target_id = target_id
        self.bet_amount = bet_amount
        self._setup_buttons()
    
    def _setup_buttons(self):
        """设置按钮"""
        self.add_item(MenuButton(
            label="接受挑战",
            emoji="✅",
            callback=self.on_accept,
            style=discord.ButtonStyle.success,
            row=0
        ))
        
        self.add_item(MenuButton(
            label="拒绝",
            emoji="❌",
            callback=self.on_decline,
            style=discord.ButtonStyle.danger,
            row=0
        ))
    
    async def on_accept(self, interaction: discord.Interaction):
        """接受挑战"""
        await interaction.response.defer()
        
        # 删除挑战消息（游戏开始后不需要了）
        if Config.AUTO_DELETE_MESSAGES and self.message:
            try:
                await self.message.delete()
            except:
                pass
        
        await self.game.start_pvp_game(
            interaction,
            self.challenger_id,
            self.target_id,
            self.bet_amount
        )
    
    async def on_decline(self, interaction: discord.Interaction):
        """拒绝挑战"""
        embed = discord.Embed(
            title="❌ 挑战被拒绝",
            description=f"<@{self.target_id}> 拒绝了挑战",
            color=Colors.DANGER
        )
        await interaction.response.edit_message(embed=embed, view=None)
        
        # 计划删除消息
        if Config.AUTO_DELETE_MESSAGES:
            asyncio.create_task(self.schedule_delete(Config.CHALLENGE_DELETE_DELAY))
    
    async def on_timeout(self):
        """超时处理"""
        if self.message:
            embed = discord.Embed(
                title="⏰ 挑战超时",
                description="对方没有在规定时间内响应",
                color=Colors.SECONDARY
            )
            try:
                await self.message.edit(embed=embed, view=None)
                
                # 计划删除消息
                if Config.AUTO_DELETE_MESSAGES:
                    asyncio.create_task(self.schedule_delete(Config.CHALLENGE_DELETE_DELAY))
            except:
                pass