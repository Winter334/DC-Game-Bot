"""
AI系统 - 恶魔轮盘赌（增强版）
"""
import random
from typing import Dict, Any, Optional, List, TYPE_CHECKING

from .items import Item, ItemType
from .shotgun import BulletType
from utils.constants import AIDifficulty
from config import Config

if TYPE_CHECKING:
    from .session import GameSession


class AIPlayer:
    """AI玩家决策系统（增强版）"""
    
    def __init__(self, difficulty: str = AIDifficulty.NORMAL):
        self.difficulty = difficulty
    
    def decide_action(self, session: 'GameSession') -> Dict[str, Any]:
        """决定AI的行动
        
        Args:
            session: 游戏会话
            
        Returns:
            动作字典 {"type": "shoot_opponent"|"shoot_self"|"use_item", ...}
        """
        # 根据难度决定策略
        if self.difficulty == AIDifficulty.EASY:
            return self._easy_strategy(session)
        elif self.difficulty == AIDifficulty.NORMAL:
            return self._normal_strategy(session)
        elif self.difficulty == AIDifficulty.HARD:
            return self._hard_strategy(session)
        elif self.difficulty == AIDifficulty.HARD_PLUS:
            return self._hard_plus_strategy(session)
        else:  # DEMON
            return self._demon_strategy(session)
    
    # ============ 核心分析方法 ============
    
    def _analyze_situation(self, session: 'GameSession') -> Dict[str, Any]:
        """分析当前局势"""
        ai = session.current_player
        opponent = session.opponent
        shotgun = session.shotgun
        
        live_prob = shotgun.get_probability_live()
        remaining = shotgun.remaining_count()
        
        # 推断当前子弹
        current_bullet = shotgun.known_bullets.get(0)
        
        # 如果知道其他位置的子弹，可以进行推理
        if current_bullet is None and remaining > 0:
            current_bullet = self._infer_current_bullet(shotgun)
        
        # 计算双方血量危险程度
        ai_danger = ai.health <= 1
        opponent_danger = opponent.health <= 1
        can_kill_opponent = opponent.health <= (2 if shotgun.is_sawed else 1)
        
        return {
            "live_prob": live_prob,
            "remaining": remaining,
            "current_bullet": current_bullet,
            "ai_danger": ai_danger,
            "opponent_danger": opponent_danger,
            "can_kill_opponent": can_kill_opponent,
            "ai_health": ai.health,
            "opponent_health": opponent.health,
            "is_sawed": shotgun.is_sawed,
        }
    
    def _infer_current_bullet(self, shotgun) -> Optional[BulletType]:
        """根据已知信息推断当前子弹"""
        if not shotgun.magazine:
            return None
        
        remaining = shotgun.remaining_count()
        known = shotgun.known_bullets
        
        # 统计已知的实弹和空包弹数量
        known_live = sum(1 for b in known.values() if b == BulletType.LIVE)
        known_blank = sum(1 for b in known.values() if b == BulletType.BLANK)
        
        # 如果已知所有实弹的位置，其他位置都是空包弹
        if known_live == shotgun.live_count and 0 not in known:
            return BulletType.BLANK
        
        # 如果已知所有空包弹的位置，其他位置都是实弹
        if known_blank == shotgun.blank_count and 0 not in known:
            return BulletType.LIVE
        
        # 如果只剩一种子弹
        if shotgun.live_count == 0:
            return BulletType.BLANK
        if shotgun.blank_count == 0:
            return BulletType.LIVE
        
        return None
    
    # ============ 道具使用策略 ============
    
    def _should_use_saw(self, session: 'GameSession', situation: Dict) -> bool:
        """判断是否应该使用手锯"""
        ai = session.current_player
        shotgun = session.shotgun
        
        if shotgun.is_sawed:
            return False
        
        saw = self._get_items_by_type(ai.items, [ItemType.SAW])
        if not saw:
            return False
        
        # 确定是实弹时使用
        if situation["current_bullet"] == BulletType.LIVE:
            return True
        
        # 高概率是实弹且能击杀时使用
        if situation["live_prob"] >= 0.7 and situation["can_kill_opponent"]:
            return True
        
        return False
    
    def _should_use_handcuffs(self, session: 'GameSession', situation: Dict) -> bool:
        """判断是否应该使用手铐"""
        ai = session.current_player
        opponent = session.opponent
        
        if opponent.is_handcuffed:
            return False
        
        handcuffs = self._get_items_by_type(ai.items, [ItemType.HANDCUFFS])
        if not handcuffs:
            return False
        
        # 当前是实弹时，使用手铐锁住对手再射击
        if situation["current_bullet"] == BulletType.LIVE:
            return True
        
        # 对手有危险道具时使用
        opponent_dangerous_items = self._get_items_by_type(
            opponent.items,
            [ItemType.SAW, ItemType.HANDCUFFS, ItemType.INVERTER]
        )
        if opponent_dangerous_items:
            return True
        
        # 高概率实弹时使用
        if situation["live_prob"] >= 0.6:
            return True
        
        return False
    
    def _should_use_beer(self, session: 'GameSession', situation: Dict) -> bool:
        """判断是否应该使用啤酒退弹"""
        ai = session.current_player
        shotgun = session.shotgun
        
        beer = self._get_items_by_type(ai.items, [ItemType.BEER])
        if not beer or situation["remaining"] <= 0:
            return False
        
        # 确定当前是实弹且危险时退弹
        if situation["current_bullet"] == BulletType.LIVE and situation["ai_danger"]:
            return True
        
        # 高概率实弹且自己血量低时退弹
        if situation["live_prob"] >= 0.7 and ai.health <= 2:
            return True
        
        return False
    
    def _should_use_inverter(self, session: 'GameSession', situation: Dict) -> bool:
        """判断是否应该使用逆转器"""
        ai = session.current_player
        
        inverter = self._get_items_by_type(ai.items, [ItemType.INVERTER])
        if not inverter:
            return False
        
        # 确定当前是实弹，逆转后射自己保留回合
        if situation["current_bullet"] == BulletType.LIVE:
            return True
        
        # 确定当前是空包弹，逆转后射对手
        if situation["current_bullet"] == BulletType.BLANK and situation["can_kill_opponent"]:
            return True
        
        return False
    
    def _get_best_steal_target(self, session: 'GameSession') -> Optional[int]:
        """获取肾上腺素最佳偷取目标"""
        opponent = session.opponent
        stealable = [i for i in opponent.items if i.can_be_stolen]
        
        if not stealable:
            return None
        
        # 优先级：放大镜 > 手铐 > 手锯 > 逆转器 > 啤酒 > 其他
        priority = [
            ItemType.MAGNIFIER,
            ItemType.HANDCUFFS,
            ItemType.SAW,
            ItemType.INVERTER,
            ItemType.BEER,
            ItemType.CIGARETTE,
            ItemType.MEDKIT,
        ]
        
        for item_type in priority:
            for i, item in enumerate(stealable):
                if item.item_type == item_type:
                    return i
        
        return 0  # 默认偷第一个
    
    # ============ 难度策略 ============
    
    def _easy_strategy(self, session: 'GameSession') -> Dict[str, Any]:
        """简单AI策略 - 基础逻辑但会犯错"""
        ai = session.current_player
        situation = self._analyze_situation(session)
        
        # 60%概率做出正确决策
        if random.random() > 0.6:
            # 犯错：随机决策
            if ai.items and random.random() < 0.3:
                item = random.choice(ai.items)
                return {"type": "use_item", "item": item}
            return {"type": "shoot_opponent"} if random.random() < 0.5 else {"type": "shoot_self"}
        
        # 正确决策
        if situation["current_bullet"] == BulletType.BLANK:
            return {"type": "shoot_self"}
        elif situation["current_bullet"] == BulletType.LIVE:
            return {"type": "shoot_opponent"}
        
        # 使用放大镜
        magnifier = self._get_items_by_type(ai.items, [ItemType.MAGNIFIER])
        if magnifier:
            return {"type": "use_item", "item": magnifier[0]}
        
        # 根据概率决策
        if situation["live_prob"] >= 0.5:
            return {"type": "shoot_opponent"}
        else:
            return {"type": "shoot_self"}
    
    def _normal_strategy(self, session: 'GameSession') -> Dict[str, Any]:
        """普通AI策略 - 合理的道具使用和决策"""
        ai = session.current_player
        opponent = session.opponent
        shotgun = session.shotgun
        situation = self._analyze_situation(session)
        
        # 紧急治疗
        if ai.health == 1:
            cigarette = self._get_items_by_type(ai.items, [ItemType.CIGARETTE])
            if cigarette:
                return {"type": "use_item", "item": cigarette[0]}
            medkit = self._get_items_by_type(ai.items, [ItemType.MEDKIT])
            if medkit:
                return {"type": "use_item", "item": medkit[0]}
        
        # 如果知道当前子弹类型
        if situation["current_bullet"] is not None:
            if situation["current_bullet"] == BulletType.BLANK:
                return {"type": "shoot_self"}
            else:
                # 实弹 - 考虑使用手锯
                if self._should_use_saw(session, situation):
                    saw = self._get_items_by_type(ai.items, [ItemType.SAW])
                    return {"type": "use_item", "item": saw[0]}
                return {"type": "shoot_opponent"}
        
        # 使用放大镜获取信息
        magnifier = self._get_items_by_type(ai.items, [ItemType.MAGNIFIER])
        if magnifier:
            return {"type": "use_item", "item": magnifier[0]}
        
        # 使用电话获取信息
        phone = self._get_items_by_type(ai.items, [ItemType.PHONE])
        if phone and situation["remaining"] > 1:
            return {"type": "use_item", "item": phone[0]}
        
        # 高概率实弹时使用啤酒
        if self._should_use_beer(session, situation):
            beer = self._get_items_by_type(ai.items, [ItemType.BEER])
            return {"type": "use_item", "item": beer[0]}
        
        # 根据概率决策
        if situation["live_prob"] > 0.55:
            return {"type": "shoot_opponent"}
        elif situation["live_prob"] < 0.45:
            return {"type": "shoot_self"}
        else:
            # 50/50时倾向于射击对手（更激进）
            return {"type": "shoot_opponent"} if random.random() < 0.6 else {"type": "shoot_self"}
    
    def _hard_strategy(self, session: 'GameSession') -> Dict[str, Any]:
        """困难AI策略 - 完美记忆，最优决策，智能道具组合"""
        ai = session.current_player
        opponent = session.opponent
        shotgun = session.shotgun
        situation = self._analyze_situation(session)
        
        # 1. 紧急情况处理
        if ai.health == 1:
            # 优先使用防弹背心
            vest = self._get_items_by_type(ai.items, [ItemType.VEST])
            if vest and not ai.has_vest:
                return {"type": "use_item", "item": vest[0]}
            # 然后治疗
            cigarette = self._get_items_by_type(ai.items, [ItemType.CIGARETTE])
            if cigarette:
                return {"type": "use_item", "item": cigarette[0]}
            medkit = self._get_items_by_type(ai.items, [ItemType.MEDKIT])
            if medkit:
                return {"type": "use_item", "item": medkit[0]}
        
        # 2. 如果确定当前子弹类型
        if situation["current_bullet"] is not None:
            if situation["current_bullet"] == BulletType.BLANK:
                # 空包弹 - 考虑逆转后射对手
                if situation["can_kill_opponent"]:
                    inverter = self._get_items_by_type(ai.items, [ItemType.INVERTER])
                    if inverter:
                        return {"type": "use_item", "item": inverter[0]}
                return {"type": "shoot_self"}
            else:
                # 实弹 - 最大化伤害
                # 先手铐
                if self._should_use_handcuffs(session, situation):
                    handcuffs = self._get_items_by_type(ai.items, [ItemType.HANDCUFFS])
                    return {"type": "use_item", "item": handcuffs[0]}
                # 再手锯
                if self._should_use_saw(session, situation):
                    saw = self._get_items_by_type(ai.items, [ItemType.SAW])
                    return {"type": "use_item", "item": saw[0]}
                return {"type": "shoot_opponent"}
        
        # 3. 获取信息
        magnifier = self._get_items_by_type(ai.items, [ItemType.MAGNIFIER])
        if magnifier:
            return {"type": "use_item", "item": magnifier[0]}
        
        phone = self._get_items_by_type(ai.items, [ItemType.PHONE])
        if phone and situation["remaining"] > 1:
            return {"type": "use_item", "item": phone[0]}
        
        telescope = self._get_items_by_type(ai.items, [ItemType.TELESCOPE])
        if telescope and situation["remaining"] > 1:
            return {"type": "use_item", "item": telescope[0]}
        
        # 4. 策略性道具使用
        # 高概率实弹时先手铐
        if situation["live_prob"] >= 0.65 and self._should_use_handcuffs(session, situation):
            handcuffs = self._get_items_by_type(ai.items, [ItemType.HANDCUFFS])
            return {"type": "use_item", "item": handcuffs[0]}
        
        # 危险时使用啤酒
        if self._should_use_beer(session, situation):
            beer = self._get_items_by_type(ai.items, [ItemType.BEER])
            return {"type": "use_item", "item": beer[0]}
        
        # 5. 最终决策
        if situation["live_prob"] >= 0.5:
            # 高概率实弹时使用手锯
            if situation["live_prob"] >= 0.6 and not shotgun.is_sawed:
                saw = self._get_items_by_type(ai.items, [ItemType.SAW])
                if saw:
                    return {"type": "use_item", "item": saw[0]}
            return {"type": "shoot_opponent"}
        else:
            return {"type": "shoot_self"}
    
    def _hard_plus_strategy(self, session: 'GameSession') -> Dict[str, Any]:
        """困难+AI策略 - 激进打法，智能偷取，偶尔作弊"""
        ai = session.current_player
        opponent = session.opponent
        shotgun = session.shotgun
        situation = self._analyze_situation(session)
        
        # 作弊：小概率直接知道答案
        if random.random() < Config.HARD_PLUS_CHEAT_CHANCE and shotgun.magazine:
            actual_bullet = shotgun.magazine[0]
            situation["current_bullet"] = actual_bullet
        
        # 如果对手有好道具，优先使用肾上腺素偷取
        adrenaline = self._get_items_by_type(ai.items, [ItemType.ADRENALINE])
        if adrenaline and opponent.items:
            # 检查对手是否有值得偷的道具
            valuable_items = self._get_items_by_type(
                opponent.items,
                [ItemType.MAGNIFIER, ItemType.SAW, ItemType.HANDCUFFS, ItemType.INVERTER]
            )
            if valuable_items:
                target = self._get_best_steal_target(session)
                if target is not None:
                    return {"type": "use_item", "item": adrenaline[0], "target": target}
        
        # 使用干扰器干扰对手
        jammer = self._get_items_by_type(ai.items, [ItemType.JAMMER])
        if jammer and len(opponent.items) >= 2:
            return {"type": "use_item", "item": jammer[0]}
        
        # 其他情况使用困难策略
        return self._hard_strategy(session)
    
    def _demon_strategy(self, session: 'GameSession') -> Dict[str, Any]:
        """恶魔AI策略 - 高概率作弊，完美决策"""
        ai = session.current_player
        opponent = session.opponent
        shotgun = session.shotgun
        situation = self._analyze_situation(session)
        
        # 高概率作弊
        if random.random() < Config.DEMON_CHEAT_CHANCE and shotgun.magazine:
            actual_bullet = shotgun.magazine[0]
            
            if actual_bullet == BulletType.BLANK:
                # 确定是空包弹 - 考虑逆转
                if situation["can_kill_opponent"]:
                    inverter = self._get_items_by_type(ai.items, [ItemType.INVERTER])
                    if inverter:
                        return {"type": "use_item", "item": inverter[0]}
                return {"type": "shoot_self"}
            else:
                # 确定是实弹 - 最大化伤害
                # 先手铐
                handcuffs = self._get_items_by_type(ai.items, [ItemType.HANDCUFFS])
                if handcuffs and not opponent.is_handcuffed:
                    return {"type": "use_item", "item": handcuffs[0]}
                # 再手锯
                saw = self._get_items_by_type(ai.items, [ItemType.SAW])
                if saw and not shotgun.is_sawed:
                    return {"type": "use_item", "item": saw[0]}
                return {"type": "shoot_opponent"}
        
        # 非作弊时使用困难+策略
        return self._hard_plus_strategy(session)
    
    # ============ 工具方法 ============
    
    def _get_items_by_type(self, items: List[Item], types: List[ItemType]) -> List[Item]:
        """获取指定类型的道具"""
        return [item for item in items if item.item_type in types]