"""
阶段和难度管理 - 恶魔轮盘赌
"""
from dataclasses import dataclass
from typing import Tuple
from utils.constants import AIDifficulty
from config import Config


@dataclass
class StageManager:
    """阶段管理器"""
    
    current_stage: int = 1          # 当前阶段（1-5+）
    current_round: int = 1          # 当前轮数（阶段内，1-3）
    total_rounds: int = 0           # 总轮数
    
    # 阶段配置
    ROUNDS_PER_STAGE = 3            # 每阶段轮数
    
    def get_ai_level(self) -> str:
        """获取当前AI难度等级"""
        levels = {
            1: AIDifficulty.EASY,
            2: AIDifficulty.NORMAL,
            3: AIDifficulty.HARD,
            4: AIDifficulty.HARD_PLUS,
            5: AIDifficulty.DEMON,
        }
        stage_key = min(self.current_stage, 5)
        return levels[stage_key]
    
    def get_ai_level_display(self) -> str:
        """获取AI难度显示名称"""
        return AIDifficulty.get_display_name(self.get_ai_level())
    
    def get_magazine_size(self) -> Tuple[int, int]:
        """获取弹夹容量范围
        
        基于阶段和轮数递增：
        - 每个阶段有基础值
        - 轮数越高，弹夹越大
        
        Returns:
            (最小容量, 最大容量)
        """
        # 阶段基础值
        stage_base = {
            1: (2, 3),   # 阶段1基础: 2-3发
            2: (3, 4),   # 阶段2基础: 3-4发
            3: (4, 5),   # 阶段3基础: 4-5发
            4: (5, 6),   # 阶段4基础: 5-6发
            5: (6, 7),   # 阶段5基础: 6-7发
        }
        stage_key = min(self.current_stage, 5)
        base_min, base_max = stage_base[stage_key]
        
        # 轮数加成：第1轮+0，第2轮+1，第3轮+2
        round_bonus = self.current_round - 1
        
        return (base_min + round_bonus, base_max + round_bonus)
    
    def get_item_count(self) -> Tuple[int, int]:
        """获取道具数量范围
        
        基于阶段和轮数递增：
        - 每个阶段有基础值
        - 轮数越高，道具越多
        
        Returns:
            (最小数量, 最大数量)
        """
        # 阶段基础值
        stage_base = {
            1: (1, 1),   # 阶段1基础: 1个
            2: (2, 2),   # 阶段2基础: 2个
            3: (3, 3),   # 阶段3基础: 3个
            4: (4, 4),   # 阶段4基础: 4个
            5: (5, 5),   # 阶段5基础: 5个
        }
        stage_key = min(self.current_stage, 5)
        base_min, base_max = stage_base[stage_key]
        
        # 轮数加成：第1轮+0，第2轮+1，第3轮+2
        round_bonus = self.current_round - 1
        
        return (base_min + round_bonus, base_max + round_bonus)
    
    def get_health(self) -> int:
        """获取当前轮的初始生命值
        
        基于阶段和轮数递增：
        - 阶段1: 2-2-3
        - 阶段2: 3-3-4
        - 阶段3+: 4-4-5
        """
        stage_key = min(self.current_stage, 5)
        
        # 基础生命值（按阶段）
        if stage_key == 1:
            base_health = 2
        elif stage_key == 2:
            base_health = 3
        else:
            base_health = 4
        
        # 第3轮额外+1生命
        if self.current_round >= 3:
            return base_health + 1
        return base_health
    
    def get_reward_multiplier(self) -> int:
        """获取奖励倍率"""
        return 2 ** (self.current_stage - 1)
    
    def get_current_reward(self) -> int:
        """获取当前可领取的奖励"""
        return Config.PVE_BASE_REWARD * self.get_reward_multiplier()
    
    def get_next_reward(self) -> int:
        """获取下一阶段的奖励"""
        return Config.PVE_BASE_REWARD * (2 ** self.current_stage)
    
    def is_stage_complete(self) -> bool:
        """检查当前阶段是否完成"""
        return self.current_round > self.ROUNDS_PER_STAGE
    
    def advance_round(self) -> bool:
        """推进到下一轮
        
        Returns:
            是否完成了一个阶段
        """
        self.current_round += 1
        self.total_rounds += 1
        
        if self.is_stage_complete():
            return True
        return False
    
    def advance_stage(self) -> None:
        """推进到下一阶段"""
        self.current_stage += 1
        self.current_round = 1
    
    def get_stage_info(self) -> dict:
        """获取当前阶段信息"""
        return {
            "stage": self.current_stage,
            "round": self.current_round,
            "total_rounds": self.total_rounds,
            "ai_level": self.get_ai_level_display(),
            "magazine_size": self.get_magazine_size(),
            "item_count": self.get_item_count(),
            "health": self.get_health(),
            "reward": self.get_current_reward(),
            "next_reward": self.get_next_reward(),
            "multiplier": self.get_reward_multiplier(),
        }
    
    def get_next_stage_preview(self) -> dict:
        """获取下一阶段预览信息（第一轮的数值）"""
        next_stage = self.current_stage + 1
        next_stage_key = min(next_stage, 5)
        
        ai_levels = {
            1: AIDifficulty.EASY,
            2: AIDifficulty.NORMAL,
            3: AIDifficulty.HARD,
            4: AIDifficulty.HARD_PLUS,
            5: AIDifficulty.DEMON,
        }
        
        # 下一阶段第一轮的弹夹范围（基础值，无轮数加成）
        magazine_base = {
            1: (2, 3),
            2: (3, 4),
            3: (4, 5),
            4: (5, 6),
            5: (6, 7),
        }
        
        # 下一阶段第一轮的道具数量（基础值，无轮数加成）
        item_base = {
            1: (1, 1),
            2: (2, 2),
            3: (3, 3),
            4: (4, 4),
            5: (5, 5),
        }
        
        # 下一阶段第一轮的生命值
        if next_stage_key == 1:
            health = 2
        elif next_stage_key == 2:
            health = 3
        else:
            health = 4
        
        return {
            "stage": next_stage,
            "ai_level": AIDifficulty.get_display_name(ai_levels[next_stage_key]),
            "magazine_size": magazine_base[next_stage_key],
            "item_count": item_base[next_stage_key],
            "health": health,
            "reward": self.get_next_reward(),
        }
    
    def format_progress(self) -> str:
        """格式化进度显示"""
        # total_rounds 在轮次结束时递增，所以当前轮应该是 total_rounds + 1
        current_total = self.total_rounds + 1
        return f"第{self.current_stage}阶段 第{self.current_round}轮 (总第{current_total}轮)"
    
    def __str__(self) -> str:
        return self.format_progress()