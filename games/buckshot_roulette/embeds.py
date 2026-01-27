"""
Embed生成 - 恶魔轮盘赌
ASCII 艺术风格界面
"""
import discord
from typing import TYPE_CHECKING, Optional

from utils.constants import Emoji, Colors, GameState, GameMode
from utils.helpers import format_chips, format_duration
from config import Config

if TYPE_CHECKING:
    from .session import GameSession


def create_shotgun_ascii(is_sawed: bool = False) -> str:
    """创建霰弹枪 ASCII 艺术
    
    Args:
        is_sawed: 是否被锯短
        
    Returns:
        霰弹枪 ASCII 艺术字符串
    """
    if is_sawed:
        # 锯短形态
        return (
            "```\n"
            "         ╔═══════════════╗\n"
            "         ║▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄║══╗\n"
            "         ╚═══════════════╝  ║\n"
            "                           ═╝\n"
            "```"
        )
    else:
        # 正常形态
        return (
            "```\n"
            "      ╔═══════════════════════╗\n"
            "      ║▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄║══╗\n"
            "      ╚═══════════════════════╝  ║\n"
            "                                ═╝\n"
            "```"
        )


def create_game_embed(session: 'GameSession') -> discord.Embed:
    """创建游戏主界面Embed"""
    
    if session.mode == GameMode.PVE:
        return create_pve_embed(session)
    elif session.mode == GameMode.PVP:
        return create_pvp_embed(session)
    else:
        return create_quick_embed(session)


def create_pve_embed(session: 'GameSession') -> discord.Embed:
    """创建PvE游戏Embed - ASCII艺术风格"""
    stage_info = session.stage_manager.get_stage_info()
    
    embed = discord.Embed(
        title=f"🎰 恶魔轮盘赌 - {session.stage_manager.format_progress()}",
        color=Colors.DANGER
    )
    
    # 玩家状态 - 使用 inline 字段实现左右布局
    player = session.human_player
    ai = session.ai_player
    
    # 恶魔状态 (左侧)
    ai_status = f"{ai.format_health()}\n{ai.format_items()}"
    embed.add_field(
        name=f"💀 {ai.name}",
        value=ai_status,
        inline=True
    )
    
    # 玩家状态 (右侧)
    player_status = f"{player.format_health()}\n{player.format_items()}"
    embed.add_field(
        name=f"👤 {player.name}",
        value=player_status,
        inline=True
    )
    
    # 霰弹枪 - 使用代码块保持 ASCII 艺术对齐
    shotgun = session.shotgun
    shotgun_title = "🔫 霰弹枪"
    if shotgun.is_sawed:
        shotgun_title += " ⚠️ 已锯短(x2)"
    
    embed.add_field(
        name=shotgun_title,
        value=create_shotgun_ascii(shotgun.is_sawed),
        inline=False
    )
    
    # 弹夹 - 普通文本
    magazine_display = shotgun.format_magazine()
    bullet_count = len(shotgun.magazine)
    embed.add_field(
        name="💎 弹夹",
        value=f"{magazine_display}  ({bullet_count}发)",
        inline=False
    )
    
    # 奖励
    embed.add_field(
        name="🎰 奖励",
        value=f"当前: {stage_info['reward']} 🪙 | 翻倍后: {stage_info['next_reward']} 🪙",
        inline=False
    )
    
    # 动态日志
    logs = session.get_recent_logs()
    if logs:
        log_text = "\n".join(f"└ {log}" for log in logs[-3:])
        embed.add_field(
            name="📜 动态",
            value=log_text,
            inline=False
        )
    
    # 当前回合提示
    current = session.current_player
    if current.is_ai:
        embed.set_footer(text="💀 恶魔正在思考...")
    else:
        embed.set_footer(text=f"轮到 {current.name} 行动")
    
    return embed


def create_pvp_embed(session: 'GameSession') -> discord.Embed:
    """创建PvP游戏Embed - ASCII艺术风格"""
    embed = discord.Embed(
        title=f"⚔️ PvP对战 - 第{session.pvp_current_round}轮 | 比分: {session.pvp_scores[0]}-{session.pvp_scores[1]}",
        color=Colors.DANGER
    )
    
    # 玩家状态 - 使用 inline 字段实现左右布局
    p1 = session.players[0]
    p2 = session.players[1]
    
    # 玩家1状态 (左侧)
    p1_status = f"{p1.format_health()}\n{p1.format_items()}"
    embed.add_field(
        name=f"👤 {p1.name} ({session.pvp_scores[0]}胜)",
        value=p1_status,
        inline=True
    )
    
    # 玩家2状态 (右侧)
    p2_status = f"{p2.format_health()}\n{p2.format_items()}"
    embed.add_field(
        name=f"👤 {p2.name} ({session.pvp_scores[1]}胜)",
        value=p2_status,
        inline=True
    )
    
    # 霰弹枪 - 使用代码块保持 ASCII 艺术对齐
    shotgun = session.shotgun
    shotgun_title = "🔫 霰弹枪"
    if shotgun.is_sawed:
        shotgun_title += " ⚠️ 已锯短(x2)"
    
    embed.add_field(
        name=shotgun_title,
        value=create_shotgun_ascii(shotgun.is_sawed),
        inline=False
    )
    
    # 弹夹 - 普通文本
    magazine_display = shotgun.format_magazine()
    bullet_count = len(shotgun.magazine)
    embed.add_field(
        name="💎 弹夹",
        value=f"{magazine_display}  ({bullet_count}发)",
        inline=False
    )
    
    # 押注池
    embed.add_field(
        name="🎰 押注池",
        value=f"{session.bet_amount * 2} 🪙",
        inline=False
    )
    
    # 动态日志
    logs = session.get_recent_logs()
    if logs:
        log_text = "\n".join(f"└ {log}" for log in logs[-3:])
        embed.add_field(
            name="📜 动态",
            value=log_text,
            inline=False
        )
    
    # 当前回合提示
    current = session.current_player
    embed.set_footer(text=f"轮到 {current.name} 行动")
    
    return embed


def create_quick_embed(session: 'GameSession') -> discord.Embed:
    """创建快速模式Embed - ASCII艺术风格"""
    # 获取难度信息
    difficulty = session.ai_difficulty or "normal"
    diff_config = Config.QUICK_DIFFICULTY_CONFIG.get(difficulty, Config.QUICK_DIFFICULTY_CONFIG["normal"])
    
    embed = discord.Embed(
        title=f"⚡ 快速模式 - {diff_config['emoji']} {diff_config['name']}",
        color=Colors.WARNING
    )
    
    # 玩家状态 - 使用 inline 字段实现左右布局
    player = session.human_player
    ai = session.ai_player
    
    # 恶魔状态 (左侧)
    ai_status = f"{ai.format_health()}\n{ai.format_items()}"
    embed.add_field(
        name=f"💀 {ai.name}",
        value=ai_status,
        inline=True
    )
    
    # 玩家状态 (右侧)
    player_status = f"{player.format_health()}\n{player.format_items()}"
    embed.add_field(
        name=f"👤 {player.name}",
        value=player_status,
        inline=True
    )
    
    # 霰弹枪 - 使用代码块保持 ASCII 艺术对齐
    shotgun = session.shotgun
    shotgun_title = "🔫 霰弹枪"
    if shotgun.is_sawed:
        shotgun_title += " ⚠️ 已锯短(x2)"
    
    embed.add_field(
        name=shotgun_title,
        value=create_shotgun_ascii(shotgun.is_sawed),
        inline=False
    )
    
    # 弹夹 - 普通文本
    magazine_display = shotgun.format_magazine()
    bullet_count = len(shotgun.magazine)
    embed.add_field(
        name="💎 弹夹",
        value=f"{magazine_display}  ({bullet_count}发)",
        inline=False
    )
    
    # 胜利奖励（基于难度）
    embed.add_field(
        name="🎰 胜利奖励",
        value=f"{diff_config['reward']} 🪙",
        inline=False
    )
    
    # 动态日志
    logs = session.get_recent_logs()
    if logs:
        log_text = "\n".join(f"└ {log}" for log in logs[-3:])
        embed.add_field(
            name="📜 动态",
            value=log_text,
            inline=False
        )
    
    # 当前回合提示
    current = session.current_player
    if current.is_ai:
        embed.set_footer(text="💀 恶魔正在思考...")
    else:
        embed.set_footer(text=f"轮到 {current.name} 行动")
    
    return embed


def create_stage_complete_embed(session: 'GameSession') -> discord.Embed:
    """创建阶段完成Embed"""
    stage_info = session.stage_manager.get_stage_info()
    next_info = session.stage_manager.get_next_stage_preview()
    
    embed = discord.Embed(
        title=f"🎰 第{stage_info['stage']}阶段完成！",
        color=Colors.GOLD
    )
    
    embed.add_field(
        name="🎉 恭喜你存活了！",
        value=f"已完成 {stage_info['total_rounds']} 轮",
        inline=False
    )
    
    embed.add_field(
        name="🎰 当前奖励",
        value=format_chips(stage_info['reward']),
        inline=True
    )
    embed.add_field(
        name="🎰 翻倍后奖励",
        value=format_chips(next_info['reward']),
        inline=True
    )
    
    embed.add_field(
        name="⚠️ 下一阶段难度将提升！",
        value=f"• AI智能: {stage_info['ai_level']} → {next_info['ai_level']}\n"
              f"• 弹夹容量: {next_info['magazine_size'][0]}-{next_info['magazine_size'][1]}发\n"
              f"• 道具数量: {next_info['item_count'][0]}-{next_info['item_count'][1]}个",
        inline=False
    )
    
    embed.add_field(
        name="💀 警告",
        value="继续游戏若死亡将失去所有奖励！",
        inline=False
    )
    
    return embed


def create_game_over_embed(session: 'GameSession', won: bool) -> discord.Embed:
    """创建游戏结束Embed"""
    duration = format_duration(session.get_duration())
    
    if session.mode == GameMode.PVE:
        if won:
            # 成功撤离
            embed = discord.Embed(
                title=f"{Emoji.BUCKSHOT} 恶魔轮盘赌 - 成功撤离！",
                color=Colors.SUCCESS
            )
            embed.add_field(
                name="🎉 明智的选择！",
                value="",
                inline=False
            )
        else:
            # 死亡
            embed = discord.Embed(
                title=f"{Emoji.BUCKSHOT} 恶魔轮盘赌 - 游戏结束",
                color=Colors.DANGER
            )
            embed.add_field(
                name="💀 你死了...",
                value="",
                inline=False
            )
        
        stage_info = session.stage_manager.get_stage_info()
        player = session.human_player
        
        embed.add_field(
            name="📊 游戏统计",
            value=f"• 存活轮数: {stage_info['total_rounds']}轮 ({stage_info['stage']}个阶段)\n"
                  f"• 游戏时长: {duration}\n"
                  f"• 使用道具: {player.items_used}个",
            inline=False
        )
        
        if won:
            embed.add_field(
                name="🎰 获得奖励",
                value=format_chips(session.accumulated_reward),
                inline=False
            )
        else:
            # 计算本可领取的奖励
            potential = session.stage_manager.get_current_reward() if stage_info['stage'] > 1 else 0
            if potential > 0:
                embed.add_field(
                    name="💸 损失奖励",
                    value=f"{format_chips(potential)} (本可领取)",
                    inline=False
                )
            embed.add_field(
                name="💡 提示",
                value="见好就收也是一种智慧",
                inline=False
            )
    
    elif session.mode == GameMode.PVP:
        winner = session.get_winner()
        embed = discord.Embed(
            title="⚔️ PvP对战 - 结束",
            color=Colors.GOLD
        )
        
        if winner:
            embed.add_field(
                name=f"🏆 {winner.name} 获胜！",
                value=f"比分: {session.pvp_scores[0]}-{session.pvp_scores[1]}",
                inline=False
            )
            embed.add_field(
                name="🎰 押注池",
                value=format_chips(session.bet_amount * 2),
                inline=True
            )
            embed.add_field(
                name=f"🏆 {winner.name} 获得",
                value=format_chips(session.bet_amount * 2),
                inline=True
            )
    
    else:
        # 快速模式
        difficulty = session.ai_difficulty or "normal"
        diff_config = Config.QUICK_DIFFICULTY_CONFIG.get(difficulty, Config.QUICK_DIFFICULTY_CONFIG["normal"])
        
        winner = session.get_winner()
        if winner and not winner.is_ai:
            embed = discord.Embed(
                title=f"⚡ 快速模式 ({diff_config['name']}) - 胜利！",
                color=Colors.SUCCESS
            )
            embed.add_field(
                name="🎰 获得奖励",
                value=format_chips(diff_config["reward"]),
                inline=False
            )
        else:
            embed = discord.Embed(
                title="⚡ 快速模式 - 失败",
                color=Colors.DANGER
            )
            embed.add_field(
                name="💀 你死了...",
                value="",
                inline=False
            )
            
            # 添加游戏日志
            logs = session.get_recent_logs()
            if logs:
                log_text = "\n".join(f"└ {log}" for log in logs[-5:])
                embed.add_field(
                    name="📜 战斗记录",
                    value=log_text,
                    inline=False
                )
            
            embed.add_field(
                name="💡 提示",
                value="再接再厉！",
                inline=False
            )
    
    return embed


def create_item_select_embed(session: 'GameSession') -> discord.Embed:
    """创建道具选择Embed - 清晰简洁风格"""
    player = session.current_player
    
    embed = discord.Embed(
        title="🎒 道具栏",
        description="选择一个道具使用",
        color=Colors.PRIMARY
    )
    
    if player.items:
        # 分组显示道具（每行2个）
        for i, item in enumerate(player.items):
            # 使用 inline 字段排列道具
            embed.add_field(
                name=f"{item.emoji} {item.name}",
                value=f"*{item.description}*",
                inline=True
            )
            # 每两个道具后添加空白字段保持对齐（如果需要）
            if (i + 1) % 2 == 0 and i < len(player.items) - 1:
                pass  # Discord 会自动换行
        
        # 如果道具数量是奇数，添加空白占位
        if len(player.items) % 2 == 1:
            embed.add_field(name="\u200b", value="\u200b", inline=True)
    else:
        embed.add_field(
            name="🚫 空空如也",
            value="没有可用道具",
            inline=False
        )
    
    embed.set_footer(text="点击下方按钮使用道具")
    
    return embed


def create_adrenaline_select_embed(session: 'GameSession') -> discord.Embed:
    """创建肾上腺素目标选择Embed - 清晰简洁风格"""
    opponent = session.opponent
    
    embed = discord.Embed(
        title="💉 肾上腺素",
        description=f"从 **{opponent.name}** 手中偷取一个道具并立即使用！",
        color=Colors.PURPLE
    )
    
    stealable = [item for item in opponent.items if item.can_be_stolen]
    if stealable:
        # 分组显示可偷取的道具
        for item in stealable:
            embed.add_field(
                name=f"{item.emoji} {item.name}",
                value=f"*{item.description}*",
                inline=True
            )
        
        # 如果道具数量是奇数，添加空白占位
        if len(stealable) % 2 == 1:
            embed.add_field(name="\u200b", value="\u200b", inline=True)
    else:
        embed.add_field(
            name="🚫 无法偷取",
            value=f"{opponent.name} 没有可偷取的道具",
            inline=False
        )
    
    embed.set_footer(text="选择要偷取的道具")
    
    return embed


def create_jammer_select_embed(session: 'GameSession') -> discord.Embed:
    """创建干扰器目标选择Embed"""
    opponent = session.opponent
    
    embed = discord.Embed(
        title="📡 干扰器",
        description=f"选择要干扰 **{opponent.name}** 的哪个道具\n⚠️ 被干扰的手雷会炸伤持有者！",
        color=Colors.PURPLE
    )
    
    if opponent.items:
        for item in opponent.items:
            # 特别标注手雷
            if item.item_type.value == "medkit":  # 手雷的内部类型
                embed.add_field(
                    name=f"{item.emoji} {item.name} 💥",
                    value=f"*{item.description}*\n**⚠️ 干扰后会炸伤持有者**",
                    inline=True
                )
            else:
                embed.add_field(
                    name=f"{item.emoji} {item.name}",
                    value=f"*{item.description}*",
                    inline=True
                )
        
        # 如果道具数量是奇数，添加空白占位
        if len(opponent.items) % 2 == 1:
            embed.add_field(name="\u200b", value="\u200b", inline=True)
    else:
        embed.add_field(
            name="🚫 无法干扰",
            value=f"{opponent.name} 没有道具可干扰",
            inline=False
        )
    
    embed.set_footer(text="选择要干扰的道具")
    
    return embed