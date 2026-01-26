"""
游戏中心命令模块
"""
import discord
from discord import app_commands
from discord.ext import commands
from typing import TYPE_CHECKING, Optional

from ui.base_views import BaseView
from ui.menus import MenuButton, BackButton
from utils.constants import Emoji, Colors
from utils.helpers import format_chips
from config import Config

if TYPE_CHECKING:
    from bot import GameCenterBot


class GameCenterView(BaseView):
    """游戏中心主面板View"""
    
    def __init__(self, cog: 'GameCenterCog', user_id: int, balance: int):
        super().__init__(user_id)
        self.cog = cog
        self.balance = balance
        self._setup_buttons()
    
    def _setup_buttons(self):
        """设置按钮"""
        # 恶魔轮盘赌按钮
        self.add_item(MenuButton(
            label="恶魔轮盘赌",
            emoji=Emoji.BUCKSHOT,
            callback=self.on_buckshot_roulette,
            style=discord.ButtonStyle.primary
        ))
        
        # 个人统计按钮
        self.add_item(MenuButton(
            label="个人统计",
            emoji=Emoji.STATS,
            callback=self.on_stats,
            style=discord.ButtonStyle.secondary
        ))
        
        # 排行榜按钮
        self.add_item(MenuButton(
            label="排行榜",
            emoji=Emoji.TROPHY,
            callback=self.on_leaderboard,
            style=discord.ButtonStyle.secondary
        ))
        
        # 签到按钮
        self.add_item(MenuButton(
            label="签到",
            emoji=Emoji.GIFT,
            callback=self.on_daily,
            style=discord.ButtonStyle.success
        ))
        
        # 转账按钮
        self.add_item(MenuButton(
            label="转账",
            emoji=Emoji.TRANSFER,
            callback=self.on_transfer,
            style=discord.ButtonStyle.secondary
        ))
    
    async def on_buckshot_roulette(self, interaction: discord.Interaction):
        """恶魔轮盘赌子面板"""
        embed = self._create_buckshot_embed()
        view = BuckshotRouletteView(self.cog, self.user_id, self.balance)
        view.message = self.message
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def on_stats(self, interaction: discord.Interaction):
        """个人统计面板"""
        stats = await self.cog.bot.player_data.get_stats(self.user_id)
        
        embed = discord.Embed(
            title=f"{Emoji.STATS} 个人统计",
            color=Colors.PRIMARY
        )
        embed.add_field(
            name="📊 总体数据",
            value=f"游戏场次: {stats.games_played}\n"
                  f"胜利场次: {stats.games_won}\n"
                  f"胜率: {stats.win_rate:.1f}%",
            inline=True
        )
        embed.add_field(
            name="🤖 PvE数据",
            value=f"最佳阶段: 第{stats.pve_best_stage}阶段\n"
                  f"总收益: {format_chips(stats.pve_total_earnings)}",
            inline=True
        )
        embed.add_field(
            name="⚔️ PvP数据",
            value=f"胜/负: {stats.pvp_wins}/{stats.pvp_losses}\n"
                  f"胜率: {stats.pvp_win_rate:.1f}%\n"
                  f"总收益: {format_chips(stats.pvp_total_earnings)}",
            inline=True
        )
        embed.add_field(
            name="💰 经济数据",
            value=f"总获得: {format_chips(stats.total_chips_earned)}\n"
                  f"总消费: {format_chips(stats.total_chips_spent)}",
            inline=False
        )
        
        view = BackOnlyView(self.cog, self.user_id, self.balance)
        view.message = self.message
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def on_leaderboard(self, interaction: discord.Interaction):
        """排行榜面板"""
        # 先延迟响应，因为获取用户信息可能耗时较长
        await interaction.response.defer()
        
        # 获取筹码排行榜
        chips_lb = await self.cog.bot.database.get_chips_leaderboard(10)
        
        embed = discord.Embed(
            title=f"{Emoji.TROPHY} 排行榜",
            color=Colors.GOLD
        )
        
        # 筹码排行
        chips_text = ""
        for i, (user_id, chips) in enumerate(chips_lb, 1):
            medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
            try:
                user = await self.cog.bot.fetch_user(user_id)
                name = user.display_name
            except:
                name = f"用户{user_id}"
            chips_text += f"{medal} {name}: {format_chips(chips)}\n"
        
        if not chips_text:
            chips_text = "暂无数据"
        
        embed.add_field(
            name="💰 筹码排行",
            value=chips_text,
            inline=False
        )
        
        view = BackOnlyView(self.cog, self.user_id, self.balance)
        view.message = self.message
        await interaction.edit_original_response(embed=embed, view=view)
    
    async def on_daily(self, interaction: discord.Interaction):
        """签到"""
        success, reward, message = await self.cog.bot.daily.claim_daily(self.user_id)
        
        if success:
            self.balance += reward
            embed = self._create_main_embed()
            embed.add_field(
                name=f"{Emoji.GIFT} 签到成功！",
                value=f"获得 {format_chips(reward)}\n当前余额: {format_chips(self.balance)}",
                inline=False
            )
        else:
            embed = self._create_main_embed()
            embed.add_field(
                name=f"{Emoji.INFO} 签到",
                value=message,
                inline=False
            )
        
        # 刷新View以更新余额显示
        view = GameCenterView(self.cog, self.user_id, self.balance)
        view.message = self.message
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def on_transfer(self, interaction: discord.Interaction):
        """转账面板"""
        embed = discord.Embed(
            title=f"{Emoji.TRANSFER} 转账",
            description=f"当前余额: {format_chips(self.balance)}\n\n"
                        f"最低转账金额: {Config.MIN_TRANSFER} 🎰\n"
                        f"转账无手续费，即时到账",
            color=Colors.PRIMARY
        )
        
        view = TransferView(self.cog, self.user_id, self.balance)
        view.message = self.message
        await interaction.response.edit_message(embed=embed, view=view)
    
    def _create_main_embed(self) -> discord.Embed:
        """创建主面板Embed"""
        embed = discord.Embed(
            title=f"{Emoji.GAME} 游戏中心",
            description=f"{Emoji.CHIPS} 余额: {self.balance:,}",
            color=Colors.PRIMARY
        )
        embed.add_field(
            name="欢迎来到游戏中心！",
            value="选择一个游戏开始：\n\n"
                  f"{Emoji.BUCKSHOT} **恶魔轮盘赌** - 与恶魔进行致命的轮盘赌\n"
                  f"🎲 更多游戏即将推出...",
            inline=False
        )
        return embed
    
    def _create_buckshot_embed(self) -> discord.Embed:
        """创建恶魔轮盘赌子面板Embed"""
        embed = discord.Embed(
            title=f"{Emoji.BUCKSHOT} 恶魔轮盘赌",
            description=f"{Emoji.CHIPS} 余额: {self.balance:,}",
            color=Colors.DANGER
        )
        embed.add_field(
            name="选择游戏模式：",
            value=f"{Emoji.ROBOT} **单人挑战** (入场费: {Config.PVE_ENTRY_FEE}🎰)\n"
                  f"渐进难度，每3轮可选择撤离或翻倍\n\n"
                  f"{Emoji.PVP} **PvP对战** (押注: 自定义)\n"
                  f"3轮2胜制，挑战其他玩家，赢家通吃\n\n"
                  f"{Emoji.QUICK} **快速模式** (入场费: 5-50🎰)\n"
                  f"单轮快速游戏，可选难度",
            inline=False
        )
        return embed


class BuckshotRouletteView(BaseView):
    """恶魔轮盘赌子面板View"""
    
    def __init__(self, cog: 'GameCenterCog', user_id: int, balance: int):
        super().__init__(user_id)
        self.cog = cog
        self.balance = balance
        self._setup_buttons()
    
    def _setup_buttons(self):
        """设置按钮"""
        # 单人挑战
        can_pve = self.balance >= Config.PVE_ENTRY_FEE
        self.add_item(MenuButton(
            label="单人挑战",
            emoji=Emoji.ROBOT,
            callback=self.on_pve,
            style=discord.ButtonStyle.primary,
            disabled=not can_pve
        ))
        
        # PvP对战
        can_pvp = self.balance >= Config.MIN_BET
        self.add_item(MenuButton(
            label="PvP对战",
            emoji=Emoji.PVP,
            callback=self.on_pvp,
            style=discord.ButtonStyle.danger,
            disabled=not can_pvp
        ))
        
        # 快速模式（使用最低入场费判断）
        min_quick_fee = min(c["entry_fee"] for c in Config.QUICK_DIFFICULTY_CONFIG.values())
        can_quick = self.balance >= min_quick_fee
        self.add_item(MenuButton(
            label="快速",
            emoji=Emoji.QUICK,
            callback=self.on_quick,
            style=discord.ButtonStyle.success,
            disabled=not can_quick
        ))
        
        # 规则
        self.add_item(MenuButton(
            label="规则",
            emoji=Emoji.RULES,
            callback=self.on_rules,
            style=discord.ButtonStyle.secondary
        ))
        
        # 返回
        self.add_item(BackButton(callback=self.on_back))
    
    async def on_pve(self, interaction: discord.Interaction):
        """开始PvE游戏"""
        await self.cog.bot.buckshot_roulette.start_pve_game(interaction)
    
    async def on_pvp(self, interaction: discord.Interaction):
        """开始PvP游戏"""
        # 显示PvP设置面板
        embed = discord.Embed(
            title="⚔️ 发起PvP挑战",
            description=f"🎰 你的余额: {format_chips(self.balance)}",
            color=Colors.DANGER
        )
        embed.add_field(
            name="设置押注金额",
            value="选择押注金额，然后选择对手",
            inline=False
        )
        
        view = PvPSetupView(self.cog, self.user_id, self.balance)
        view.message = self.message
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def on_quick(self, interaction: discord.Interaction):
        """显示快速模式难度选择"""
        embed = self._create_quick_difficulty_embed()
        view = QuickDifficultyView(self.cog, self.user_id, self.balance)
        view.message = self.message
        await interaction.response.edit_message(embed=embed, view=view)
    
    def _create_quick_difficulty_embed(self) -> discord.Embed:
        """创建快速模式难度选择Embed"""
        embed = discord.Embed(
            title=f"{Emoji.QUICK} 快速模式 - 选择难度",
            description=f"{Emoji.CHIPS} 余额: {self.balance:,}",
            color=Colors.DANGER
        )
        
        difficulty_text = ""
        for diff_key, diff_config in Config.QUICK_DIFFICULTY_CONFIG.items():
            difficulty_text += (
                f"{diff_config['emoji']} **{diff_config['name']}** "
                f"| 入场费: {diff_config['entry_fee']}🎰 "
                f"| 奖励: {diff_config['reward']}🎰\n"
            )
        
        embed.add_field(
            name="选择AI难度",
            value=difficulty_text,
            inline=False
        )
        embed.add_field(
            name="💡 提示",
            value="难度越高，AI越聪明，奖励也越丰厚！",
            inline=False
        )
        return embed
    
    async def on_rules(self, interaction: discord.Interaction):
        """显示规则"""
        embed = discord.Embed(
            title=f"{Emoji.RULES} 恶魔轮盘赌 - 游戏规则",
            color=Colors.PRIMARY
        )
        embed.add_field(
            name="🔫 基础规则",
            value="• 游戏使用一把霰弹枪，装填混合的**实弹**和**空包弹**\n"
                  "• 玩家和对手各有一定的**生命值**\n"
                  "• 轮流行动，可以射击对手、射击自己或使用道具\n"
                  "• 射击自己时，空包弹可保留行动权\n"
                  "• 生命值归零者**失败**",
            inline=False
        )
        embed.add_field(
            name="🎯 PvE模式",
            value="• 渐进式难度，每3轮为一个阶段\n"
                  "• 阶段结束可选择撤离领取奖励或翻倍继续\n"
                  "• 中途死亡将失去所有奖励",
            inline=False
        )
        embed.add_field(
            name="⚔️ PvP模式",
            value="• 双方押注，赢家通吃\n"
                  "• **3轮2胜制**：先赢得2轮的玩家获胜\n"
                  "• 每轮结束后生命值重置，重新发放道具",
            inline=False
        )
        
        view = BackOnlyView(self.cog, self.user_id, self.balance, back_to="buckshot")
        view.message = self.message
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def on_back(self, interaction: discord.Interaction):
        """返回主面板"""
        embed = self._create_main_embed()
        view = GameCenterView(self.cog, self.user_id, self.balance)
        view.message = self.message
        await interaction.response.edit_message(embed=embed, view=view)
    
    def _create_main_embed(self) -> discord.Embed:
        """创建主面板Embed"""
        embed = discord.Embed(
            title=f"{Emoji.GAME} 游戏中心",
            description=f"{Emoji.CHIPS} 余额: {self.balance:,}",
            color=Colors.PRIMARY
        )
        embed.add_field(
            name="欢迎来到游戏中心！",
            value="选择一个游戏开始：\n\n"
                  f"{Emoji.BUCKSHOT} **恶魔轮盘赌** - 与恶魔进行致命的轮盘赌\n"
                  f"🎲 更多游戏即将推出...",
            inline=False
        )
        return embed


class BackOnlyView(BaseView):
    """只有返回按钮的View"""
    
    def __init__(self, cog: 'GameCenterCog', user_id: int, balance: int, back_to: str = "main"):
        super().__init__(user_id)
        self.cog = cog
        self.balance = balance
        self.back_to = back_to
        self.add_item(BackButton(callback=self.on_back))
    
    async def on_back(self, interaction: discord.Interaction):
        """返回"""
        if self.back_to == "buckshot":
            embed = self._create_buckshot_embed()
            view = BuckshotRouletteView(self.cog, self.user_id, self.balance)
        else:
            embed = self._create_main_embed()
            view = GameCenterView(self.cog, self.user_id, self.balance)
        
        view.message = self.message
        await interaction.response.edit_message(embed=embed, view=view)
    
    def _create_main_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"{Emoji.GAME} 游戏中心",
            description=f"{Emoji.CHIPS} 余额: {self.balance:,}",
            color=Colors.PRIMARY
        )
        embed.add_field(
            name="欢迎来到游戏中心！",
            value="选择一个游戏开始：\n\n"
                  f"{Emoji.BUCKSHOT} **恶魔轮盘赌** - 与恶魔进行致命的轮盘赌\n"
                  f"🎲 更多游戏即将推出...",
            inline=False
        )
        return embed
    
    def _create_buckshot_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"{Emoji.BUCKSHOT} 恶魔轮盘赌",
            description=f"{Emoji.CHIPS} 余额: {self.balance:,}",
            color=Colors.DANGER
        )
        embed.add_field(
            name="选择游戏模式：",
            value=f"{Emoji.ROBOT} **单人挑战** (入场费: {Config.PVE_ENTRY_FEE}🎰)\n"
                  f"渐进难度，每3轮可选择撤离或翻倍\n\n"
                  f"{Emoji.PVP} **PvP对战** (押注: 自定义)\n"
                  f"3轮2胜制，挑战其他玩家，赢家通吃\n\n"
                  f"{Emoji.QUICK} **快速模式** (入场费: 5-50🎰)\n"
                  f"单轮快速游戏，可选难度",
            inline=False
        )
        return embed


class QuickDifficultyView(BaseView):
    """快速模式难度选择View"""
    
    def __init__(self, cog: 'GameCenterCog', user_id: int, balance: int):
        super().__init__(user_id)
        self.cog = cog
        self.balance = balance
        self._setup_buttons()
    
    def _setup_buttons(self):
        """设置难度按钮"""
        for diff_key, diff_config in Config.QUICK_DIFFICULTY_CONFIG.items():
            can_play = self.balance >= diff_config["entry_fee"]
            self.add_item(MenuButton(
                label=f"{diff_config['name']} ({diff_config['entry_fee']}🎰)",
                emoji=diff_config["emoji"],
                callback=lambda inter, d=diff_key: self.on_difficulty_select(inter, d),
                style=discord.ButtonStyle.primary if can_play else discord.ButtonStyle.secondary,
                disabled=not can_play,
                row=0 if diff_key in ["easy", "normal", "hard"] else 1
            ))
        
        # 返回按钮
        self.add_item(BackButton(callback=self.on_back, row=2))
    
    async def on_difficulty_select(self, interaction: discord.Interaction, difficulty: str):
        """选择难度并开始游戏"""
        await self.cog.bot.buckshot_roulette.start_quick_game(interaction, difficulty)
    
    async def on_back(self, interaction: discord.Interaction):
        """返回恶魔轮盘赌面板"""
        embed = self._create_buckshot_embed()
        view = BuckshotRouletteView(self.cog, self.user_id, self.balance)
        view.message = self.message
        await interaction.response.edit_message(embed=embed, view=view)
    
    def _create_buckshot_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"{Emoji.BUCKSHOT} 恶魔轮盘赌",
            description=f"{Emoji.CHIPS} 余额: {self.balance:,}",
            color=Colors.DANGER
        )
        embed.add_field(
            name="选择游戏模式：",
            value=f"{Emoji.ROBOT} **单人挑战** (入场费: {Config.PVE_ENTRY_FEE}🎰)\n"
                  f"渐进难度，每3轮可选择撤离或翻倍\n\n"
                  f"{Emoji.PVP} **PvP对战** (押注: 自定义)\n"
                  f"3轮2胜制，挑战其他玩家，赢家通吃\n\n"
                  f"{Emoji.QUICK} **快速模式** (入场费: 5-50🎰)\n"
                  f"单轮快速游戏，可选难度",
            inline=False
        )
        return embed


class TransferView(BaseView):
    """转账面板View"""
    
    def __init__(self, cog: 'GameCenterCog', user_id: int, balance: int):
        super().__init__(user_id)
        self.cog = cog
        self.balance = balance
        self.selected_user: Optional[discord.User] = None
        self.transfer_amount: int = Config.MIN_TRANSFER
        self._setup_components()
    
    def _setup_components(self):
        """设置组件"""
        # 用户选择菜单
        from ui.menus import UserSelectMenu
        self.add_item(UserSelectMenu(
            placeholder="📋 选择转账对象",
            callback=self.on_user_select,
            row=0
        ))
        
        # 金额按钮
        amounts = [10, 50, 100, 500]
        for i, amount in enumerate(amounts):
            self.add_item(MenuButton(
                label=str(amount),
                emoji="🎰",
                callback=lambda inter, amt=amount: self.on_amount_select(inter, amt),
                style=discord.ButtonStyle.secondary,
                row=1
            ))
        
        # 确认转账按钮
        self.add_item(MenuButton(
            label="确认转账",
            emoji=Emoji.TRANSFER,
            callback=self.on_confirm_transfer,
            style=discord.ButtonStyle.success,
            row=2
        ))
        
        # 返回按钮
        self.add_item(BackButton(callback=self.on_back, row=2))
    
    async def on_user_select(self, interaction: discord.Interaction, users: list):
        """选择用户"""
        if users:
            self.selected_user = users[0]
            embed = self._create_transfer_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    async def on_amount_select(self, interaction: discord.Interaction, amount: int):
        """选择金额"""
        self.transfer_amount = amount
        embed = self._create_transfer_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def on_confirm_transfer(self, interaction: discord.Interaction):
        """确认转账"""
        if self.selected_user is None:
            await interaction.response.send_message(
                f"{Emoji.WARNING} 请先选择转账对象！",
                ephemeral=True
            )
            return
        
        if self.transfer_amount > self.balance:
            await interaction.response.send_message(
                f"{Emoji.WARNING} 余额不足！当前余额: {format_chips(self.balance)}",
                ephemeral=True
            )
            return
        
        # 执行转账
        success, message = await self.cog.bot.economy.transfer(
            self.user_id,
            self.selected_user.id,
            self.transfer_amount
        )
        
        if success:
            self.balance -= self.transfer_amount
            embed = discord.Embed(
                title=f"{Emoji.TRANSFER} 转账成功！",
                description=f"已向 **{self.selected_user.display_name}** 转账 {format_chips(self.transfer_amount)}",
                color=Colors.SUCCESS
            )
            embed.add_field(
                name="当前余额",
                value=format_chips(self.balance),
                inline=False
            )
            # 重置选择
            self.selected_user = None
            self.transfer_amount = Config.MIN_TRANSFER
            view = TransferView(self.cog, self.user_id, self.balance)
            view.message = self.message
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.send_message(
                f"{Emoji.WARNING} {message}",
                ephemeral=True
            )
    
    async def on_back(self, interaction: discord.Interaction):
        """返回主面板"""
        embed = self._create_main_embed()
        view = GameCenterView(self.cog, self.user_id, self.balance)
        view.message = self.message
        await interaction.response.edit_message(embed=embed, view=view)
    
    def _create_transfer_embed(self) -> discord.Embed:
        """创建转账面板Embed"""
        embed = discord.Embed(
            title=f"{Emoji.TRANSFER} 转账",
            color=Colors.PRIMARY
        )
        embed.add_field(
            name="💰 当前余额",
            value=format_chips(self.balance),
            inline=True
        )
        embed.add_field(
            name="📋 转账对象",
            value=self.selected_user.display_name if self.selected_user else "未选择",
            inline=True
        )
        embed.add_field(
            name="🎰 转账金额",
            value=format_chips(self.transfer_amount),
            inline=True
        )
        embed.add_field(
            name="💡 提示",
            value=f"• 最低转账金额: {Config.MIN_TRANSFER} 🎰\n"
                  f"• 转账无手续费，即时到账\n"
                  f"• 点击金额按钮选择转账金额",
            inline=False
        )
        return embed
    
    def _create_main_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"{Emoji.GAME} 游戏中心",
            description=f"{Emoji.CHIPS} 余额: {self.balance:,}",
            color=Colors.PRIMARY
        )
        embed.add_field(
            name="欢迎来到游戏中心！",
            value="选择一个游戏开始：\n\n"
                  f"{Emoji.BUCKSHOT} **恶魔轮盘赌** - 与恶魔进行致命的轮盘赌\n"
                  f"🎲 更多游戏即将推出...",
            inline=False
        )
        return embed


class PvPSetupView(BaseView):
    """PvP设置面板View"""
    
    def __init__(self, cog: 'GameCenterCog', user_id: int, balance: int):
        super().__init__(user_id)
        self.cog = cog
        self.balance = balance
        self.bet_amount: int = Config.MIN_BET
        self.target_user: Optional[discord.User] = None
        self._setup_components()
    
    def _setup_components(self):
        """设置组件"""
        # 用户选择菜单
        from ui.menus import UserSelectMenu
        self.add_item(UserSelectMenu(
            placeholder="📋 选择对手",
            callback=self.on_user_select,
            row=0
        ))
        
        # 金额按钮
        amounts = [10, 50, 100, 500]
        for amount in amounts:
            disabled = amount > self.balance
            self.add_item(MenuButton(
                label=str(amount),
                emoji="🎰",
                callback=lambda inter, amt=amount: self.on_amount_select(inter, amt),
                style=discord.ButtonStyle.secondary,
                disabled=disabled,
                row=1
            ))
        
        # 发起挑战按钮
        self.add_item(MenuButton(
            label="发起挑战",
            emoji="⚔️",
            callback=self.on_challenge,
            style=discord.ButtonStyle.danger,
            row=2
        ))
        
        # 返回按钮
        self.add_item(BackButton(callback=self.on_back, row=2))
    
    async def on_user_select(self, interaction: discord.Interaction, users: list):
        """选择对手"""
        if users:
            self.target_user = users[0]
            embed = self._create_setup_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    async def on_amount_select(self, interaction: discord.Interaction, amount: int):
        """选择金额"""
        self.bet_amount = min(amount, self.balance)
        embed = self._create_setup_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def on_challenge(self, interaction: discord.Interaction):
        """发起挑战"""
        if self.target_user is None:
            await interaction.response.send_message(
                f"{Emoji.WARNING} 请先选择对手！",
                ephemeral=True
            )
            return
        
        if self.target_user.id == self.user_id:
            await interaction.response.send_message(
                f"{Emoji.WARNING} 不能挑战自己！",
                ephemeral=True
            )
            return
        
        if self.target_user.bot:
            await interaction.response.send_message(
                f"{Emoji.WARNING} 不能挑战机器人！",
                ephemeral=True
            )
            return
        
        # 检查对手余额
        target_balance = await self.cog.bot.economy.get_balance(self.target_user.id)
        if target_balance < self.bet_amount:
            await interaction.response.send_message(
                f"{Emoji.WARNING} 对手余额不足！需要 {format_chips(self.bet_amount)}",
                ephemeral=True
            )
            return
        
        # 发送挑战
        from games.buckshot_roulette.views import PvPChallengeView
        
        embed = discord.Embed(
            title="⚔️ 收到挑战！",
            color=Colors.DANGER
        )
        embed.add_field(
            name="🎯 挑战者",
            value=f"<@{self.user_id}>",
            inline=True
        )
        embed.add_field(
            name="🎰 押注金额",
            value=format_chips(self.bet_amount),
            inline=True
        )
        embed.add_field(
            name="",
            value=f"接受挑战需要: {format_chips(self.bet_amount)}\n"
                  f"你的余额: {format_chips(target_balance)} ✅",
            inline=False
        )
        embed.add_field(
            name="⏰ 请在60秒内做出选择",
            value="",
            inline=False
        )
        
        view = PvPChallengeView(
            self.cog.bot.buckshot_roulette,
            self.user_id,
            self.target_user.id,
            self.bet_amount
        )
        
        await interaction.response.send_message(
            content=f"<@{self.target_user.id}>",
            embed=embed,
            view=view
        )
        view.message = await interaction.original_response()
    
    async def on_back(self, interaction: discord.Interaction):
        """返回"""
        embed = self._create_buckshot_embed()
        view = BuckshotRouletteView(self.cog, self.user_id, self.balance)
        view.message = self.message
        await interaction.response.edit_message(embed=embed, view=view)
    
    def _create_setup_embed(self) -> discord.Embed:
        """创建设置面板Embed"""
        embed = discord.Embed(
            title="⚔️ 发起PvP挑战",
            color=Colors.DANGER
        )
        embed.add_field(
            name="💰 你的余额",
            value=format_chips(self.balance),
            inline=True
        )
        embed.add_field(
            name="🎯 对手",
            value=self.target_user.display_name if self.target_user else "未选择",
            inline=True
        )
        embed.add_field(
            name="🎰 押注金额",
            value=format_chips(self.bet_amount),
            inline=True
        )
        embed.add_field(
            name="💡 规则",
            value="• 3轮2胜制\n"
                  "• 赢家获得双方押注总额\n"
                  "• 平局各自返还押注",
            inline=False
        )
        return embed
    
    def _create_buckshot_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"{Emoji.BUCKSHOT} 恶魔轮盘赌",
            description=f"{Emoji.CHIPS} 余额: {self.balance:,}",
            color=Colors.DANGER
        )
        embed.add_field(
            name="选择游戏模式：",
            value=f"{Emoji.ROBOT} **单人挑战** (入场费: {Config.PVE_ENTRY_FEE}🎰)\n"
                  f"渐进难度，每3轮可选择撤离或翻倍\n\n"
                  f"{Emoji.PVP} **PvP对战** (押注: 自定义)\n"
                  f"3轮2胜制，挑战其他玩家，赢家通吃\n\n"
                  f"{Emoji.QUICK} **快速模式** (入场费: 5-50🎰)\n"
                  f"单轮快速游戏，可选难度",
            inline=False
        )
        return embed


class GameCenterCog(commands.Cog):
    """游戏中心Cog"""
    
    def __init__(self, bot: 'GameCenterBot'):
        self.bot = bot
    
    @app_commands.command(name="game", description="打开游戏中心")
    async def game_command(self, interaction: discord.Interaction):
        """游戏中心主命令"""
        user_id = interaction.user.id
        
        # 确保玩家存在（新玩家发放礼包）
        is_new = await self.bot.economy.ensure_player_exists(user_id)
        
        # 获取余额
        balance = await self.bot.economy.get_balance(user_id)
        
        # 创建主面板
        embed = discord.Embed(
            title=f"{Emoji.GAME} 游戏中心",
            description=f"{Emoji.CHIPS} 余额: {balance:,}",
            color=Colors.PRIMARY
        )
        
        # 新玩家提示
        if is_new:
            embed.add_field(
                name=f"{Emoji.GIFT} 欢迎新玩家！",
                value=f"你获得了 {format_chips(Config.NEW_PLAYER_BONUS)} 新手礼包！",
                inline=False
            )
        
        embed.add_field(
            name="欢迎来到游戏中心！",
            value="选择一个游戏开始：\n\n"
                  f"{Emoji.BUCKSHOT} **恶魔轮盘赌** - 与恶魔进行致命的轮盘赌\n"
                  f"🎲 更多游戏即将推出...",
            inline=False
        )
        
        view = GameCenterView(self, user_id, balance)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()


async def setup(bot: 'GameCenterBot'):
    """加载Cog"""
    await bot.add_cog(GameCenterCog(bot))