"""
玩家类 - 恶魔轮盘赌
"""
from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .items import Item


@dataclass
class Player:
    """游戏中的玩家"""
    
    user_id: int                          # Discord用户ID（AI为0）
    name: str                             # 显示名称
    is_ai: bool = False                   # 是否是AI
    
    # 生命值
    health: int = 2                       # 当前生命值
    max_health: int = 2                   # 最大生命值
    
    # 道具
    items: List['Item'] = field(default_factory=list)
    
    # 状态效果
    is_handcuffed: bool = False           # 是否被手铐锁住
    has_vest: bool = False                # 是否有防弹背心效果
    overheal: int = 0                     # 超量治疗的额外生命值（急救包）
    jammed_item: Optional['Item'] = None  # 被干扰的道具（存储道具引用而非索引，避免索引错位）
    
    # 统计
    damage_dealt: int = 0                 # 造成的伤害
    items_used: int = 0                   # 使用的道具数量
    
    def is_alive(self) -> bool:
        """检查是否存活"""
        return self.health > 0
    
    def take_damage(self, amount: int, ignore_vest: bool = False) -> int:
        """受到伤害
        
        Args:
            amount: 伤害量
            ignore_vest: 是否无视防弹衣（手雷等）
            
        Returns:
            实际受到的伤害
        """
        actual_damage = amount
        
        # 防弹背心减少1点伤害（除非无视防弹衣）
        if self.has_vest and amount > 0 and not ignore_vest:
            actual_damage = max(0, amount - 1)
            self.has_vest = False
        
        # 先消耗超量治疗
        if self.overheal > 0:
            if self.overheal >= actual_damage:
                self.overheal -= actual_damage
                return actual_damage  # 伤害被超量治疗完全吸收
            else:
                actual_damage -= self.overheal
                self.overheal = 0
        
        self.health = max(0, self.health - actual_damage)
        return actual_damage  # 返回实际伤害量
    
    def heal(self, amount: int, allow_overheal: bool = False) -> int:
        """恢复生命值
        
        Args:
            amount: 恢复量
            allow_overheal: 是否允许超过上限（超量治疗）
            
        Returns:
            实际恢复的生命值
        """
        old_health = self.health
        if allow_overheal:
            # 先恢复到上限
            normal_heal = min(self.max_health - self.health, amount)
            self.health = min(self.max_health, self.health + amount)
            # 超出上限的部分作为超量治疗
            if amount > normal_heal:
                self.overheal += (amount - normal_heal)
            return amount  # 返回总治疗量
        else:
            self.health = min(self.max_health, self.health + amount)
            return self.health - old_health
    
    def add_item(self, item: 'Item') -> bool:
        """添加道具
        
        Args:
            item: 道具
            
        Returns:
            是否成功添加（道具栏满返回False）
        """
        from config import Config
        if len(self.items) >= Config.MAX_ITEMS:
            return False
        self.items.append(item)
        return True
    
    def remove_item(self, item: 'Item') -> bool:
        """移除道具
        
        Args:
            item: 道具
            
        Returns:
            是否成功移除
        """
        if item in self.items:
            self.items.remove(item)
            return True
        return False
    
    def get_item_by_index(self, index: int) -> Optional['Item']:
        """通过索引获取道具"""
        if 0 <= index < len(self.items):
            return self.items[index]
        return None
    
    def clear_overheal(self) -> int:
        """清除超量治疗（轮次结束时）
        
        Returns:
            清除的超量治疗量
        """
        cleared = self.overheal
        self.overheal = 0
        return cleared
    
    def reset_turn_effects(self) -> None:
        """重置回合效果"""
        # 手铐效果在跳过回合后解除
        pass
    
    def reset_round(self, new_health: int, clear_items: bool = True) -> None:
        """重置轮次状态
        
        Args:
            new_health: 新的生命值
            clear_items: 是否清除道具（新阶段时清除，同阶段内保留）
        """
        self.health = new_health
        self.max_health = new_health
        if clear_items:
            self.items.clear()
        self.is_handcuffed = False
        self.has_vest = False
        self.overheal = 0
        self.jammed_item = None
    
    def format_health(self) -> str:
        """格式化生命值显示（进度条风格）"""
        # 使用 ❤️ 和 🖤 创建进度条，💛 表示超量治疗
        hearts = "❤️" * self.health
        empty = "🖤" * (self.max_health - self.health)
        overheal_hearts = "💛" * self.overheal if self.overheal > 0 else ""
        
        total_hp = self.health + self.overheal
        if self.overheal > 0:
            return f"{hearts}{empty}{overheal_hearts} {total_hp}/{self.max_health}"
        else:
            return f"{hearts}{empty} {self.health}/{self.max_health}"
    
    def format_items(self) -> str:
        """格式化道具显示"""
        if not self.items:
            return "无道具"
        return "".join(item.emoji for item in self.items)
    
    def __str__(self) -> str:
        prefix = "💀" if self.is_ai else "👤"
        return f"{prefix} {self.name}"