"""
霰弹枪和弹夹系统 - 恶魔轮盘赌
"""
import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum


class BulletType(Enum):
    """子弹类型"""
    LIVE = "live"       # 实弹
    BLANK = "blank"     # 空包弹


@dataclass
class Shotgun:
    """霰弹枪"""
    
    magazine: List[BulletType] = field(default_factory=list)
    live_count: int = 0           # 实弹数量
    blank_count: int = 0          # 空包弹数量
    is_sawed: bool = False        # 是否被锯短（下一发双倍伤害）
    
    # 已知子弹信息（用于AI和道具效果）
    known_bullets: dict = field(default_factory=dict)  # {index: BulletType}
    
    def load(self, live: int, blank: int) -> None:
        """装填弹夹
        
        Args:
            live: 实弹数量
            blank: 空包弹数量
        """
        self.magazine = (
            [BulletType.LIVE] * live + 
            [BulletType.BLANK] * blank
        )
        random.shuffle(self.magazine)
        
        self.live_count = live
        self.blank_count = blank
        self.is_sawed = False
        self.known_bullets.clear()
    
    def reload_shuffle(self) -> None:
        """重新打乱弹夹顺序（幸运硬币效果）"""
        random.shuffle(self.magazine)
        self.known_bullets.clear()
    
    def peek_current(self) -> Optional[BulletType]:
        """查看当前子弹（放大镜效果）
        
        Returns:
            当前子弹类型，弹夹空返回None
        """
        if not self.magazine:
            return None
        bullet = self.magazine[0]
        self.known_bullets[0] = bullet
        return bullet
    
    def peek_position(self, position: int) -> Optional[BulletType]:
        """查看指定位置的子弹（望远镜/窃贼电话效果）
        
        Args:
            position: 位置索引（0为当前子弹）
            
        Returns:
            子弹类型，位置无效返回None
        """
        if 0 <= position < len(self.magazine):
            bullet = self.magazine[position]
            self.known_bullets[position] = bullet
            return bullet
        return None
    
    def eject_current(self) -> Optional[BulletType]:
        """退出当前子弹（啤酒效果）
        
        Returns:
            被退出的子弹类型
        """
        if not self.magazine:
            return None
        
        bullet = self.magazine.pop(0)
        
        # 更新计数
        if bullet == BulletType.LIVE:
            self.live_count -= 1
        else:
            self.blank_count -= 1
        
        # 更新已知子弹索引
        new_known = {}
        for idx, b in self.known_bullets.items():
            if idx > 0:
                new_known[idx - 1] = b
        self.known_bullets = new_known
        
        return bullet
    
    def invert_current(self) -> Optional[BulletType]:
        """反转当前子弹（逆转器效果）
        
        原版规则：使用后玩家不知道结果，需要清除已知信息
        
        Returns:
            反转后的子弹类型
        """
        if not self.magazine:
            return None
        
        current = self.magazine[0]
        if current == BulletType.LIVE:
            self.magazine[0] = BulletType.BLANK
            self.live_count -= 1
            self.blank_count += 1
        else:
            self.magazine[0] = BulletType.LIVE
            self.blank_count -= 1
            self.live_count += 1
        
        # 原版规则：逆转后玩家不知道结果，清除已知信息
        if 0 in self.known_bullets:
            del self.known_bullets[0]
        
        return self.magazine[0]
    
    def set_current_bullet(self, bullet_type: BulletType) -> Optional[BulletType]:
        """设置当前子弹类型（命运硬币效果）
        
        Args:
            bullet_type: 要设置的子弹类型
            
        Returns:
            设置后的子弹类型
        """
        if not self.magazine:
            return None
        
        current = self.magazine[0]
        if current == bullet_type:
            # 已经是目标类型，不需要改变
            pass
        else:
            # 需要改变类型
            self.magazine[0] = bullet_type
            if bullet_type == BulletType.LIVE:
                self.blank_count -= 1
                self.live_count += 1
            else:
                self.live_count -= 1
                self.blank_count += 1
        
        # 更新已知信息
        self.known_bullets[0] = self.magazine[0]
        
        return self.magazine[0]
    
    def fire(self) -> Tuple[Optional[BulletType], int]:
        """开枪
        
        Returns:
            (子弹类型, 伤害值)
        """
        if not self.magazine:
            return None, 0
        
        bullet = self.magazine.pop(0)
        
        # 更新计数
        if bullet == BulletType.LIVE:
            self.live_count -= 1
        else:
            self.blank_count -= 1
        
        # 计算伤害
        damage = 0
        if bullet == BulletType.LIVE:
            damage = 2 if self.is_sawed else 1
        
        # 重置锯短状态
        self.is_sawed = False
        
        # 更新已知子弹索引
        new_known = {}
        for idx, b in self.known_bullets.items():
            if idx > 0:
                new_known[idx - 1] = b
        self.known_bullets = new_known
        
        return bullet, damage
    
    def saw_off(self) -> None:
        """锯短枪管（手锯效果）"""
        self.is_sawed = True
    
    def is_empty(self) -> bool:
        """检查弹夹是否为空"""
        return len(self.magazine) == 0
    
    def remaining_count(self) -> int:
        """获取剩余子弹数量"""
        return len(self.magazine)
    
    def get_probability_live(self) -> float:
        """获取当前子弹是实弹的概率"""
        total = len(self.magazine)
        if total == 0:
            return 0.0
        return self.live_count / total
    
    def format_magazine(self, reveal: bool = False) -> str:
        """格式化弹夹显示
        
        Args:
            reveal: 是否显示所有子弹
            
        Returns:
            格式化的字符串
        """
        if reveal:
            symbols = []
            for bullet in self.magazine:
                if bullet == BulletType.LIVE:
                    symbols.append("🔴")
                else:
                    symbols.append("⚪")
            return " ".join(symbols)
        else:
            # 使用 ● 符号表示未知子弹
            return " ".join(["●"] * len(self.magazine))
    
    def format_info(self) -> str:
        """格式化弹夹信息（只显示剩余数量）"""
        return f"{len(self.magazine)} 发子弹"
    
    def format_initial_info(self) -> str:
        """格式化初始弹夹信息（用于轮次开始时）"""
        return f"实弹 {self.live_count} 发, 空包弹 {self.blank_count} 发"
    
    def __str__(self) -> str:
        return f"🔫 弹夹: {self.format_magazine()} | {self.format_info()}"


def generate_magazine_config(stage: int, round_in_stage: int, max_health: int = 5) -> Tuple[int, int]:
    """根据阶段和血量生成平衡的弹夹配置
    
    核心平衡原则：
    1. 实弹总伤害潜力不应远超双方总血量
    2. 实弹比例应与血量成反比关系
    3. 保持随机性的同时避免极端不平衡
    
    Args:
        stage: 当前阶段（1-5+）
        round_in_stage: 阶段内的轮数（1-3）
        max_health: 玩家最大血量（用于平衡计算）
        
    Returns:
        (实弹数量, 空包弹数量)
    """
    # 基础弹夹大小范围（根据阶段递增）
    size_ranges = {
        1: (2, 4),   # 第1阶段: 2-4发
        2: (3, 5),   # 第2阶段: 3-5发
        3: (4, 6),   # 第3阶段: 4-6发
        4: (5, 7),   # 第4阶段: 5-7发
        5: (6, 8),   # 第5阶段+: 6-8发
    }
    
    stage_key = min(stage, 5)
    min_size, max_size = size_ranges[stage_key]
    
    # 随机总数
    total = random.randint(min_size, max_size)
    
    # === 平衡策略：基于血量限制实弹数量 ===
    #
    # 核心理念：实弹数量应该给双方留有博弈空间
    # - 低血量时(2点)：实弹过多会导致先手必胜
    # - 高血量时(5点)：可以容忍更多实弹增加紧张感
    #
    # 实弹上限公式：min(total - 1, max_health + 1)
    # - 确保至少有1颗空包弹
    # - 实弹不超过 (血量+1)，给后手方反击机会
    
    max_live = min(total - 1, max_health + 1)
    
    # 实弹下限：至少1颗，但不超过上限
    min_live = 1
    
    # 如果血量极低(<=2)，进一步限制实弹比例
    # 避免出现"2血量 + 4实弹2空弹"这种高压局面
    if max_health <= 2:
        # 低血量时，实弹不超过总数的60%
        max_live = min(max_live, max(1, int(total * 0.6)))
    elif max_health <= 3:
        # 中低血量，实弹不超过总数的70%
        max_live = min(max_live, max(2, int(total * 0.7)))
    
    # 确保 max_live >= min_live
    max_live = max(max_live, min_live)
    
    # 生成可能的实弹数量列表
    possible_live = list(range(min_live, max_live + 1))
    
    if len(possible_live) == 1:
        live = possible_live[0]
    else:
        # 使用轻微的 U 形权重分布，但不那么极端
        # 这样保持随机性的同时，避免总是中间值
        weights = []
        mid = len(possible_live) / 2
        for i in range(len(possible_live)):
            # 距离两端越近，权重略高
            distance_from_edge = min(i, len(possible_live) - 1 - i)
            # 边缘权重为2，中间权重为1（相比原来的3:1更温和）
            weight = 2 - (distance_from_edge / mid) if mid > 0 else 2
            weight = max(1, weight)
            weights.append(weight)
        
        live = random.choices(possible_live, weights=weights, k=1)[0]
    
    blank = total - live
    
    return live, blank