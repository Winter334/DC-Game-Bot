"""
游戏会话管理 - 恶魔轮盘赌
"""
import uuid
import random
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING, Any
from enum import Enum

from .player import Player
from .shotgun import Shotgun, BulletType, generate_magazine_config
from .items import Item, ItemType, generate_items, get_item_count_for_stage, get_item
from .stages import StageManager
from utils.constants import GameMode, GameState
from config import Config

if TYPE_CHECKING:
    import discord
    from discord import ui


class ActionType(Enum):
    """动作类型"""
    SHOOT_OPPONENT = "shoot_opponent"
    SHOOT_SELF = "shoot_self"
    USE_ITEM = "use_item"


@dataclass
class ActionResult:
    """动作结果"""
    action_type: ActionType
    success: bool
    message: str
    damage: int = 0
    bullet_type: Optional[BulletType] = None
    extra_turn: bool = False          # 是否获得额外回合
    game_over: bool = False           # 游戏是否结束
    round_over: bool = False          # 轮次是否结束
    item_used: Optional[Item] = None  # 使用的道具
    private_info: Optional[str] = None  # 私密信息（只有使用者可见）


@dataclass
class GameSession:
    """游戏会话"""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    mode: str = GameMode.PVE
    
    # Discord相关
    channel_id: int = 0
    message_id: int = 0
    
    # 玩家
    players: List[Player] = field(default_factory=list)
    current_turn: int = 0             # 当前行动玩家索引
    
    # 游戏状态
    state: str = GameState.WAITING
    stage_manager: StageManager = field(default_factory=StageManager)
    shotgun: Shotgun = field(default_factory=Shotgun)
    
    # 快速模式AI难度
    ai_difficulty: Optional[str] = None
    
    # 日志
    action_log: List[str] = field(default_factory=list)
    _magazine_info_shown: bool = False  # 是否显示过装填信息（用于在动作后移除）
    
    # 经济
    bet_amount: int = 0               # PvP押注金额
    entry_fee: int = 0                # 入场费
    accumulated_reward: int = 0       # 累积奖励
    
    # 时间
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    
    # PvP专用
    pvp_scores: List[int] = field(default_factory=lambda: [0, 0])
    pvp_current_round: int = 1
    challenger_id: int = 0                # PvP挑战发起者ID
    
    # 当前活动的视图（用于防止旧View超时删除消息）
    current_view: Optional[Any] = None  # 实际类型是 ui.View，使用 Any 避免循环导入
    
    def set_current_view(self, view: 'ui.View') -> None:
        """设置当前活动的视图，并停止旧视图
        
        Args:
            view: 新的视图
        """
        # 停止旧的视图（防止旧视图超时触发删除）
        if self.current_view is not None:
            try:
                self.current_view.stop()
            except:
                pass
        self.current_view = view
    
    @property
    def current_player(self) -> Player:
        """获取当前行动玩家"""
        return self.players[self.current_turn]
    
    @property
    def opponent(self) -> Player:
        """获取对手"""
        return self.players[1 - self.current_turn]
    
    @property
    def human_player(self) -> Player:
        """获取人类玩家"""
        for player in self.players:
            if not player.is_ai:
                return player
        return self.players[0]
    
    @property
    def ai_player(self) -> Optional[Player]:
        """获取AI玩家"""
        for player in self.players:
            if player.is_ai:
                return player
        return None
    
    def initialize_pve(self, user_id: int, username: str) -> None:
        """初始化PvE游戏
        
        Args:
            user_id: 玩家Discord ID
            username: 玩家名称
        """
        self.mode = GameMode.PVE
        self.entry_fee = Config.PVE_ENTRY_FEE
        
        # 创建玩家
        health = self.stage_manager.get_health()
        human = Player(
            user_id=user_id,
            name=username,
            is_ai=False,
            health=health,
            max_health=health
        )
        ai = Player(
            user_id=0,
            name="恶魔",
            is_ai=True,
            health=health,
            max_health=health
        )
        
        self.players = [human, ai]
        self.current_turn = 0  # 玩家先手
        self.state = GameState.PLAYING
        self.started_at = datetime.now()
    
    def initialize_pvp(self, player1_id: int, player1_name: str,
                       player2_id: int, player2_name: str, bet: int) -> None:
        """初始化PvP游戏
        
        Args:
            player1_id: 玩家1 Discord ID（挑战发起者）
            player1_name: 玩家1名称
            player2_id: 玩家2 Discord ID
            player2_name: 玩家2名称
            bet: 押注金额
        """
        self.mode = GameMode.PVP
        self.bet_amount = bet
        self.challenger_id = player1_id  # 记录挑战发起者
        
        # 创建玩家 - 使用原版规则，第一轮血量由 stage_manager 决定
        health = self.stage_manager.get_health()
        player1 = Player(
            user_id=player1_id,
            name=player1_name,
            is_ai=False,
            health=health,
            max_health=health
        )
        player2 = Player(
            user_id=player2_id,
            name=player2_name,
            is_ai=False,
            health=health,
            max_health=health
        )
        
        self.players = [player1, player2]
        self.current_turn = random.randint(0, 1)  # 随机先手
        self.state = GameState.PLAYING
        self.started_at = datetime.now()
        self.pvp_scores = [0, 0]
        self.pvp_current_round = 1
    
    def initialize_quick(self, user_id: int, username: str, difficulty: str = "normal") -> None:
        """初始化快速模式
        
        Args:
            user_id: 玩家Discord ID
            username: 玩家名称
            difficulty: AI难度 (easy/normal/hard/hard_plus/demon)
        """
        from utils.constants import AIDifficulty
        
        self.mode = GameMode.QUICK
        self.ai_difficulty = difficulty
        
        # 获取难度配置
        self.quick_difficulty_config = Config.QUICK_DIFFICULTY_CONFIG.get(
            difficulty, Config.QUICK_DIFFICULTY_CONFIG["normal"]
        )
        self.entry_fee = self.quick_difficulty_config["entry_fee"]
        
        # 创建玩家 - 血量根据难度配置
        health = self.quick_difficulty_config["health"]
        human = Player(
            user_id=user_id,
            name=username,
            is_ai=False,
            health=health,
            max_health=health
        )
        # AI名称根据难度变化
        ai_names = {
            AIDifficulty.EASY: "小鬼",
            AIDifficulty.NORMAL: "恶魔",
            AIDifficulty.HARD: "恶魔领主",
            AIDifficulty.HARD_PLUS: "恶魔将军",
            AIDifficulty.DEMON: "恶魔之王",
        }
        ai_name = ai_names.get(difficulty, "恶魔")
        
        ai = Player(
            user_id=0,
            name=ai_name,
            is_ai=True,
            health=health,
            max_health=health
        )
        
        self.players = [human, ai]
        self.current_turn = 0
        self.state = GameState.PLAYING
        self.started_at = datetime.now()
    
    def start_round(self, give_items: bool = True) -> tuple:
        """开始新一轮
        
        Args:
            give_items: 是否发放道具（弹夹打空时为True，新轮次开始时也为True）
            
        Returns:
            (实弹数量, 空包弹数量) 用于发送装填通知
        """
        # 清空之前的日志记录
        self.action_log.clear()
        
        # 装填弹夹
        if self.mode == GameMode.QUICK and hasattr(self, 'quick_difficulty_config'):
            # 快速模式：使用难度配置的弹夹大小
            config = self.quick_difficulty_config
            magazine_size = random.randint(config["magazine_min"], config["magazine_max"])
            
            # 使用加权随机，让极端分布更常见
            possible_live = list(range(1, magazine_size))  # 1 到 magazine_size-1
            if possible_live:
                # U 形权重分布：极端值概率更高
                weights = []
                mid = len(possible_live) / 2
                for i in range(len(possible_live)):
                    distance_from_edge = min(i, len(possible_live) - 1 - i)
                    weight = 3 - (distance_from_edge / mid * 2) if mid > 0 else 3
                    weight = max(1, weight)
                    weights.append(weight)
                live = random.choices(possible_live, weights=weights, k=1)[0]
            else:
                live = 1
            blank = magazine_size - live
        else:
            # PvE/PvP模式：使用阶段管理器获取弹夹范围（固定2-8发）
            min_size, max_size = self.stage_manager.get_magazine_size()
            magazine_size = random.randint(min_size, max_size)
            
            # 使用加权随机，让极端分布更常见
            possible_live = list(range(1, magazine_size))  # 1 到 magazine_size-1
            if possible_live:
                weights = []
                mid = len(possible_live) / 2
                for i in range(len(possible_live)):
                    distance_from_edge = min(i, len(possible_live) - 1 - i)
                    weight = 3 - (distance_from_edge / mid * 2) if mid > 0 else 3
                    weight = max(1, weight)
                    weights.append(weight)
                live = random.choices(possible_live, weights=weights, k=1)[0]
            else:
                live = 1
            blank = magazine_size - live
        
        self.shotgun.load(live, blank)
        
        # 发放道具
        if give_items:
            if self.mode == GameMode.QUICK and hasattr(self, 'quick_difficulty_config'):
                # 快速模式：使用难度配置的道具数量
                config = self.quick_difficulty_config
                item_count = random.randint(config["items_min"], config["items_max"])
            else:
                # PvE/PvP模式：使用阶段管理器（固定1-3个）
                min_items, max_items = self.stage_manager.get_item_count()
                item_count = random.randint(min_items, max_items)
            
            for player in self.players:
                # 清除超量治疗（发放道具时）
                cleared = player.clear_overheal()
                if cleared > 0:
                    self.add_log(f"{player.name} 的超量治疗效果消失了 (-{cleared} 生命)")
                
                items = generate_items(item_count, Config.ENABLE_EXPANSION_ITEMS)
                items_added = 0
                for item in items:
                    if player.add_item(item):
                        items_added += 1
                    else:
                        # 道具栏已满，停止添加
                        break
                
                # 如果有道具因为满了而无法添加，记录日志
                if items_added < len(items):
                    self.add_log(f"⚠️ {player.name} 道具栏已满，部分道具无法获得")
        
        # 显示装填信息（实弹和空包弹数量，会在第一次动作后移除）
        self.add_log(f"🔫 装填完成: 实弹 {live} 发, 空包弹 {blank} 发")
        self._magazine_info_shown = True
        
        return (live, blank)
    
    def _clear_magazine_info(self) -> None:
        """清除装填信息（第一次动作后调用）"""
        if self._magazine_info_shown and self.action_log:
            # 移除包含"装填完成"的日志
            self.action_log = [log for log in self.action_log if "装填完成" not in log]
            self._magazine_info_shown = False
    
    def shoot_opponent(self) -> ActionResult:
        """射击对手"""
        # 清除装填信息
        self._clear_magazine_info()
        
        bullet, damage = self.shotgun.fire()
        
        if bullet is None:
            # 弹夹已空，触发重新装填
            self.add_log("⚠️ 弹夹已空，需要重新装填！")
            return ActionResult(
                action_type=ActionType.SHOOT_OPPONENT,
                success=False,
                message="弹夹已空！",
                round_over=True  # 触发重新装填
            )
        
        target = self.opponent
        shooter = self.current_player
        
        if bullet == BulletType.LIVE:
            # 记录是否有防弹背心（在take_damage之前检查，因为take_damage会清除has_vest）
            had_vest = target.has_vest
            actual_damage = target.take_damage(damage)
            shooter.damage_dealt += actual_damage
            
            message = f"💥 {shooter.name} 射击了 {target.name}！"
            if damage > 1:
                message += f" (锯短枪管)"
            
            if had_vest:
                # 防弹衣减少了1点伤害
                if actual_damage == 0:
                    message += " 🦺防弹背心抵挡了伤害！"
                else:
                    message += f" 🦺防弹背心减伤！({actual_damage}点伤害)"
            else:
                message += f" ({actual_damage}点伤害)"
            
            self.add_log(message)
            
            # 检查是否死亡
            target_dead = not target.is_alive()
            round_over = self.shotgun.is_empty() or target_dead
            
            # 根据游戏模式决定是否直接结束游戏
            # PvE模式：AI死亡不是game_over，需要通过handle_round_end处理
            # PvP模式：玩家死亡不是game_over，需要通过handle_round_end处理（Bo3）
            # 快速模式：任何人死亡都是game_over
            if self.mode == GameMode.QUICK:
                game_over = target_dead
            elif self.mode == GameMode.PVE:
                # PvE模式：只有玩家死亡才是game_over
                game_over = target_dead and not target.is_ai
            else:
                # PvP模式：通过round_over处理，不直接game_over
                game_over = False
            
            return ActionResult(
                action_type=ActionType.SHOOT_OPPONENT,
                success=True,
                message=message,
                damage=actual_damage,
                bullet_type=bullet,
                game_over=game_over,
                round_over=round_over
            )
        else:
            message = f"💨 {shooter.name} 射击了 {target.name}，但是空包弹！"
            self.add_log(message)
            
            round_over = self.shotgun.is_empty()
            
            return ActionResult(
                action_type=ActionType.SHOOT_OPPONENT,
                success=True,
                message=message,
                damage=0,
                bullet_type=bullet,
                round_over=round_over
            )
    
    def shoot_self(self) -> ActionResult:
        """射击自己"""
        # 清除装填信息
        self._clear_magazine_info()
        
        bullet, damage = self.shotgun.fire()
        
        if bullet is None:
            # 弹夹已空，触发重新装填
            self.add_log("⚠️ 弹夹已空，需要重新装填！")
            return ActionResult(
                action_type=ActionType.SHOOT_SELF,
                success=False,
                message="弹夹已空！",
                round_over=True  # 触发重新装填
            )
        
        shooter = self.current_player
        
        if bullet == BulletType.LIVE:
            # 记录是否有防弹背心（在take_damage之前检查）
            had_vest = shooter.has_vest
            actual_damage = shooter.take_damage(damage)
            
            message = f"💥 {shooter.name} 射击了自己！"
            if damage > 1:
                message += f" (锯短枪管)"
            
            if had_vest:
                # 防弹衣减少了1点伤害
                if actual_damage == 0:
                    message += " 🦺防弹背心抵挡了伤害！"
                else:
                    message += f" 🦺防弹背心减伤！({actual_damage}点伤害)"
            else:
                message += f" ({actual_damage}点伤害)"
            
            self.add_log(message)
            
            shooter_dead = not shooter.is_alive()
            round_over = self.shotgun.is_empty() or shooter_dead
            
            # 根据游戏模式决定是否直接结束游戏
            # PvE模式：玩家死亡是game_over，AI死亡通过round_over处理
            # PvP模式：通过round_over处理（Bo3）
            # 快速模式：任何人死亡都是game_over
            if self.mode == GameMode.QUICK:
                game_over = shooter_dead
            elif self.mode == GameMode.PVE:
                # PvE模式：玩家死亡是game_over，AI死亡通过round_over处理
                game_over = shooter_dead and not shooter.is_ai
            else:
                # PvP模式：通过round_over处理，不直接game_over
                game_over = False
            
            return ActionResult(
                action_type=ActionType.SHOOT_SELF,
                success=True,
                message=message,
                damage=actual_damage,
                bullet_type=bullet,
                game_over=game_over,
                round_over=round_over
            )
        else:
            message = f"💨 {shooter.name} 射击了自己，空包弹！保留行动权"
            self.add_log(message)
            
            round_over = self.shotgun.is_empty()
            
            return ActionResult(
                action_type=ActionType.SHOOT_SELF,
                success=True,
                message=message,
                damage=0,
                bullet_type=bullet,
                extra_turn=True,  # 空包弹射自己保留行动权
                round_over=round_over
            )
    
    def use_item(self, item: Item, target_index: Optional[int] = None) -> ActionResult:
        """使用道具
        
        Args:
            item: 要使用的道具
            target_index: 目标索引（用于肾上腺素选择偷取的道具）
        """
        # 清除装填信息
        self._clear_magazine_info()
        
        player = self.current_player
        opponent = self.opponent
        
        # 检查道具是否被干扰（使用道具引用而非索引，避免索引错位问题）
        if player.jammed_item is not None and item is player.jammed_item:
            player.remove_item(item)
            player.jammed_item = None
            
            # 手雷被干扰时会炸伤自己
            if item.item_type == ItemType.MEDKIT:
                damage = player.take_damage(1, ignore_vest=True)
                message = f"⚡ {player.name} 使用了 {item}... 道具被干扰！💣 手雷炸伤了自己！(-1 生命)"
                self.add_log(message)
                
                player_dead = not player.is_alive()
                if self.mode == GameMode.QUICK:
                    game_over = player_dead
                elif self.mode == GameMode.PVE:
                    game_over = player_dead and not player.is_ai
                else:
                    game_over = False
                
                return ActionResult(
                    action_type=ActionType.USE_ITEM,
                    success=False,
                    message=message,
                    item_used=item,
                    game_over=game_over,
                    round_over=player_dead,
                    extra_turn=not player_dead  # 玩家死亡就不能继续行动了
                )
            else:
                message = f"⚡ {player.name} 使用了 {item}... 道具被干扰，失效了！"
                self.add_log(message)
                return ActionResult(
                    action_type=ActionType.USE_ITEM,
                    success=False,
                    message=message,
                    item_used=item,
                    extra_turn=True  # 即使道具被干扰失效，也不消耗回合
                )
        
        # 移除道具
        player.remove_item(item)
        player.items_used += 1
        
        message = f"{player.name} 使用了 {item}"
        extra_info = ""
        private_info = None  # 私密信息，只有使用者可见
        
        # 处理道具效果
        if item.item_type == ItemType.MAGNIFIER:
            bullet = self.shotgun.peek_current()
            if bullet is None:
                extra_info = "⚠️ 弹夹已空，无法查看"
                private_info = extra_info
            elif bullet == BulletType.LIVE:
                private_info = "🔴 当前子弹是实弹！"
                extra_info = "查看了当前子弹"
            else:
                private_info = "⚪ 当前子弹是空包弹"
                extra_info = "查看了当前子弹"
        
        elif item.item_type == ItemType.BEER:
            ejected = self.shotgun.eject_current()
            if ejected is None:
                extra_info = "⚠️ 弹夹已空，无法退弹"
            elif ejected == BulletType.LIVE:
                extra_info = "🔴 退出了一发实弹"
            else:
                extra_info = "⚪ 退出了一发空包弹"
        
        elif item.item_type == ItemType.CIGARETTE:
            if player.health >= player.max_health:
                extra_info = "🚬 抽了口烟（已满血，无法恢复）"
            else:
                healed = player.heal(1)
                extra_info = f"❤️ 恢复了 {healed} 点生命"
        
        elif item.item_type == ItemType.SAW:
            if self.shotgun.is_empty():
                extra_info = "⚠️ 弹夹已空，枪管已锯短但无法生效"
            else:
                self.shotgun.saw_off()
                extra_info = "🔪 枪管已锯短，下一发实弹造成2点伤害"
        
        elif item.item_type == ItemType.HANDCUFFS:
            if opponent.is_handcuffed:
                extra_info = f"🔗 {opponent.name} 已经被铐住了！（效果重复）"
            else:
                opponent.is_handcuffed = True
                extra_info = f"🔗 {opponent.name} 被铐住了，下回合将被跳过"
        
        elif item.item_type == ItemType.MEDICINE:
            if random.random() < 0.5:  # 50%成功概率
                healed = player.heal(2)
                extra_info = f"✅ 药物有效！恢复了 {healed} 点生命"
            else:  # 50%失败概率
                damage = player.take_damage(1)
                extra_info = f"❌ 药物过期！受到 {damage} 点伤害"
        
        elif item.item_type == ItemType.INVERTER:
            new_bullet = self.shotgun.invert_current()
            # 逆转器的结果也应该是私密的
            if new_bullet is None:
                extra_info = "⚠️ 弹夹已空，无法逆转"
                private_info = extra_info
            elif new_bullet == BulletType.LIVE:
                private_info = "🔄 当前子弹变成了实弹"
                extra_info = "逆转了当前子弹"
            else:
                private_info = "🔄 当前子弹变成了空包弹"
                extra_info = "逆转了当前子弹"
        
        elif item.item_type == ItemType.PHONE:
            remaining = self.shotgun.remaining_count()
            if remaining == 0:
                extra_info = "📱 弹夹已空，无法查看"
                private_info = extra_info
            elif remaining == 1:
                extra_info = "📱 弹夹中只剩一发子弹，无法查看其他位置"
                private_info = extra_info
            else:
                pos = random.randint(1, remaining - 1)
                bullet = self.shotgun.peek_position(pos)
                if bullet == BulletType.LIVE:
                    private_info = f"📱 第{pos + 1}发子弹是实弹"
                else:
                    private_info = f"📱 第{pos + 1}发子弹是空包弹"
                extra_info = f"查看了第{pos + 1}发子弹"
        
        elif item.item_type == ItemType.VEST:
            if player.has_vest:
                extra_info = "🦺 已经穿着防弹背心了！（道具浪费）"
            else:
                player.has_vest = True
                extra_info = "🦺 防弹背心已装备，下次受伤减少1点"
        
        elif item.item_type == ItemType.ADRENALINE:
            # 需要选择目标道具
            stealable = [i for i in opponent.items if i.can_be_stolen]
            if stealable and target_index is not None and 0 <= target_index < len(stealable):
                stolen_item = stealable[target_index]
                opponent.remove_item(stolen_item)
                extra_info = f"💉 偷取了 {opponent.name} 的 {stolen_item}，立即使用！"
                self.add_log(f"{message}\n{extra_info}")
                # 递归使用偷取的道具，并返回其结果
                stolen_result = self.use_item(stolen_item)
                # 将偷取道具的私密信息也传递给调用者
                return ActionResult(
                    action_type=ActionType.USE_ITEM,
                    success=True,
                    message=f"{message}\n{extra_info}",
                    item_used=item,
                    game_over=stolen_result.game_over,
                    round_over=stolen_result.round_over,
                    private_info=stolen_result.private_info,
                    extra_turn=stolen_result.extra_turn
                )
            elif stealable:
                # 随机偷取（AI使用时）
                stolen_item = random.choice(stealable)
                opponent.remove_item(stolen_item)
                extra_info = f"💉 偷取了 {opponent.name} 的 {stolen_item}，立即使用！"
                self.add_log(f"{message}\n{extra_info}")
                stolen_result = self.use_item(stolen_item)
                return ActionResult(
                    action_type=ActionType.USE_ITEM,
                    success=True,
                    message=f"{message}\n{extra_info}",
                    item_used=item,
                    game_over=stolen_result.game_over,
                    round_over=stolen_result.round_over,
                    private_info=stolen_result.private_info,
                    extra_turn=stolen_result.extra_turn
                )
            else:
                extra_info = "💉 对手没有可偷取的道具"
        
        elif item.item_type == ItemType.COIN:
            if self.shotgun.is_empty():
                extra_info = "⚠️ 弹夹已空，无法使用"
            else:
                # 抛硬币：正面变实弹，反面变空包弹
                if random.random() < 0.5:
                    # 正面 - 变实弹
                    self.shotgun.set_current_bullet(BulletType.LIVE)
                    private_info = "🪙 正面！当前子弹变成了实弹"
                    extra_info = "抛出了硬币..."
                else:
                    # 反面 - 变空包弹
                    self.shotgun.set_current_bullet(BulletType.BLANK)
                    private_info = "🪙 反面！当前子弹变成了空包弹"
                    extra_info = "抛出了硬币..."
        
        elif item.item_type == ItemType.TELESCOPE:
            remaining = self.shotgun.remaining_count()
            if remaining == 0:
                extra_info = "🔭 弹夹已空，无法查看"
                private_info = extra_info
            elif remaining == 1:
                extra_info = "🔭 弹夹中只有1发子弹，无法查看第2发"
                private_info = extra_info
            else:
                bullet = self.shotgun.peek_position(1)
                if bullet == BulletType.LIVE:
                    private_info = "🔭 第2发子弹是实弹"
                else:
                    private_info = "🔭 第2发子弹是空包弹"
                extra_info = "查看了第2发子弹"
        
        elif item.item_type == ItemType.MEDKIT:
            # 手雷：对对手造成1点直接伤害（无视防弹衣，但不能杀死对手）
            if opponent.health > 1:
                actual_damage = opponent.take_damage(1, ignore_vest=True)
                extra_info = f"💣 手雷爆炸！对 {opponent.name} 造成了 1 点伤害"
            else:
                # 对手只有1血时，手雷无法生效
                extra_info = f"💣 手雷爆炸！但 {opponent.name} 命悬一线，手雷无法杀死他！"
        
        elif item.item_type == ItemType.JAMMER:
            if opponent.items and target_index is not None and 0 <= target_index < len(opponent.items):
                # 玩家选择干扰目标道具
                jammed_item = opponent.items[target_index]
                opponent.jammed_item = jammed_item
                extra_info = f"📡 {opponent.name} 的一个道具已被干扰（对方不可见）"
            elif opponent.items:
                # AI使用时随机选择（或未提供target_index时）
                jammed_item = random.choice(opponent.items)
                opponent.jammed_item = jammed_item
                extra_info = f"📡 {opponent.name} 的一个道具已被干扰（对方不可见）"
            else:
                extra_info = "📡 对手没有道具可干扰"
        
        full_message = f"{message}\n{extra_info}" if extra_info else message
        self.add_log(full_message)
        
        # 检查是否因药物死亡
        player_dead = not player.is_alive()
        
        # 检查弹夹是否为空（啤酒可能退掉最后一发子弹）
        magazine_empty = self.shotgun.is_empty()
        
        # 根据游戏模式决定是否直接结束游戏
        if self.mode == GameMode.QUICK:
            game_over = player_dead
        elif self.mode == GameMode.PVE:
            # PvE模式：玩家死亡是game_over，AI死亡通过round_over处理
            game_over = player_dead and not player.is_ai
        else:
            # PvP模式：通过round_over处理，不直接game_over
            game_over = False
        
        # 如果玩家死亡或弹夹为空，需要设置round_over
        round_over = player_dead or magazine_empty
        
        return ActionResult(
            action_type=ActionType.USE_ITEM,
            success=True,
            message=full_message,
            item_used=item,
            game_over=game_over,
            round_over=round_over,
            private_info=private_info,
            extra_turn=not player_dead and not magazine_empty  # 如果玩家死亡或弹夹为空，不再有额外回合
        )
    
    def next_turn(self) -> None:
        """切换到下一个玩家的回合"""
        next_player_idx = 1 - self.current_turn
        next_player = self.players[next_player_idx]
        
        # 检查是否被手铐锁住
        if next_player.is_handcuffed:
            next_player.is_handcuffed = False
            self.add_log(f"🔗 {next_player.name} 被手铐跳过了回合")
            # 不切换，当前玩家继续
            return
        
        self.current_turn = next_player_idx
    
    def handle_round_end(self) -> bool:
        """处理轮次结束
        
        Returns:
            是否完成了一个阶段
        """
        # 检查是否有玩家死亡
        for player in self.players:
            if not player.is_alive():
                return self.handle_player_death(player)
        
        # 弹夹打空，重新装填并发放道具（保留血量状态）
        # 重置临时效果（手铐等）
        self._reset_temporary_effects()
        # 重新装填并发放道具
        self.start_round(give_items=True)
        return False
    
    def handle_player_death(self, dead_player: Player) -> bool:
        """处理玩家死亡
        
        Args:
            dead_player: 死亡的玩家
            
        Returns:
            是否完成了一个阶段
        """
        if self.mode == GameMode.PVE:
            if dead_player.is_ai:
                # AI死亡，玩家赢得这一轮
                stage_complete = self.stage_manager.advance_round()
                if stage_complete:
                    self.state = GameState.STAGE_COMPLETE
                    return True
                else:
                    # 同阶段内进入下一轮，清除道具（跨轮不保留道具）
                    self.reset_round_state(clear_items=True)
                    # PVE模式：玩家先手
                    self.current_turn = 0
                    self.start_round(give_items=True)
                    return False
            else:
                # 玩家死亡，游戏结束
                self.state = GameState.ENDED
                self.ended_at = datetime.now()
                return True
        
        elif self.mode == GameMode.PVP:
            # PvP模式：记录得分，输家（死亡方）下一轮先手
            dead_player_idx = self.players.index(dead_player)
            winner_idx = 1 - dead_player_idx
            self.pvp_scores[winner_idx] += 1
            
            # 检查是否有人赢得比赛
            if self.pvp_scores[winner_idx] >= Config.PVP_WINS_REQUIRED:
                self.state = GameState.ENDED
                self.ended_at = datetime.now()
                return True
            else:
                # 开始下一轮PvP，使用 stage_manager 递增轮数
                self.pvp_current_round += 1
                self.stage_manager.advance_round()  # 推进轮数，增加血量
                self.reset_pvp_round(loser_first=dead_player_idx)  # 输家先手
                self.start_round(give_items=True)
                return False
        
        else:
            # 快速模式
            self.state = GameState.ENDED
            self.ended_at = datetime.now()
            return True
    
    def _reset_temporary_effects(self) -> None:
        """重置临时效果（弹夹打空时调用）
        
        保留：道具、生命值
        重置：手铐、防弹背心、干扰器效果等临时状态
        注意：超量治疗由 start_round() 处理
        """
        for player in self.players:
            player.is_handcuffed = False
            player.has_vest = False
            player.jammed_item = None
        
        # 重置霰弹枪状态
        self.shotgun.is_sawed = False
    
    def reset_round_state(self, clear_items: bool = False) -> None:
        """重置轮次状态（PvE，玩家死亡后进入下一轮）
        
        Args:
            clear_items: 是否清除道具（新阶段时清除，同阶段内保留）
        """
        health = self.stage_manager.get_health()
        for player in self.players:
            player.reset_round(health, clear_items=clear_items)
        # PvE模式：玩家先手
        self.current_turn = 0
    
    def reset_pvp_round(self, loser_first: Optional[int] = None) -> None:
        """重置PvP轮次状态
        
        Args:
            loser_first: 输家的索引（该玩家先手），如果为None则随机先手
        """
        # 使用 stage_manager 获取当前轮的血量
        health = self.stage_manager.get_health()
        for player in self.players:
            player.reset_round(health, clear_items=True)  # PvP跨轮清除道具
        # 输家先手，如果没有指定则随机
        if loser_first is not None:
            self.current_turn = loser_first
        else:
            self.current_turn = random.randint(0, 1)
    
    def handle_retreat(self) -> int:
        """处理撤离
        
        Returns:
            获得的奖励
        """
        reward = self.stage_manager.get_current_reward()
        self.accumulated_reward = reward
        self.state = GameState.ENDED
        self.ended_at = datetime.now()
        return reward
    
    def handle_continue(self) -> None:
        """处理继续挑战（进入新阶段，清除道具）"""
        self.stage_manager.advance_stage()
        self.reset_round_state(clear_items=True)
        self.start_round(give_items=True)
        self.state = GameState.PLAYING
    
    def get_winner(self) -> Optional[Player]:
        """获取胜利者"""
        if self.mode == GameMode.PVP:
            if self.pvp_scores[0] >= Config.PVP_WINS_REQUIRED:
                return self.players[0]
            elif self.pvp_scores[1] >= Config.PVP_WINS_REQUIRED:
                return self.players[1]
        else:
            for player in self.players:
                if player.is_alive():
                    return player
        return None
    
    def get_duration(self) -> int:
        """获取游戏时长（秒）"""
        if self.started_at is None:
            return 0
        end = self.ended_at or datetime.now()
        return int((end - self.started_at).total_seconds())
    
    def add_log(self, message: str) -> None:
        """添加日志"""
        self.action_log.append(message)
        # 保持日志数量限制
        if len(self.action_log) > Config.ACTION_LOG_SIZE:
            self.action_log.pop(0)
    
    def get_recent_logs(self, count: int = 5) -> List[str]:
        """获取最近的日志"""
        return self.action_log[-count:]