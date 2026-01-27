"""
数据模型定义
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class PlayerData:
    """玩家基础数据"""
    user_id: int                          # Discord用户ID
    chips: int = 0                        # 筹码余额
    last_daily: Optional[datetime] = None # 上次签到时间
    created_at: datetime = field(default_factory=datetime.now)
    
    def can_claim_daily(self) -> bool:
        """检查是否可以领取每日奖励"""
        if self.last_daily is None:
            return True
        now = datetime.now()
        return now.date() > self.last_daily.date()


@dataclass
class PlayerStats:
    """玩家统计数据"""
    user_id: int
    games_played: int = 0
    games_won: int = 0
    pve_best_stage: int = 0
    pve_total_earnings: int = 0
    pve_best_rounds: int = 0         # 最高轮数
    pve_best_reward: int = 0         # 最大单局奖励
    pvp_wins: int = 0
    pvp_losses: int = 0
    pvp_total_earnings: int = 0
    total_chips_earned: int = 0
    total_chips_spent: int = 0
    
    @property
    def win_rate(self) -> float:
        """计算胜率"""
        if self.games_played == 0:
            return 0.0
        return self.games_won / self.games_played * 100
    
    @property
    def pvp_win_rate(self) -> float:
        """计算PvP胜率"""
        total = self.pvp_wins + self.pvp_losses
        if total == 0:
            return 0.0
        return self.pvp_wins / total * 100


@dataclass
class TransferRecord:
    """转账记录"""
    id: Optional[int] = None
    from_user_id: int = 0
    to_user_id: int = 0
    amount: int = 0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class GameRecord:
    """游戏记录"""
    id: Optional[str] = None
    mode: str = ""                    # pve, pvp, quick
    player1_id: int = 0
    player2_id: Optional[int] = None  # PvE时为None
    winner_id: Optional[int] = None   # 平局时为None
    bet_amount: int = 0
    reward_amount: int = 0
    stages_completed: int = 0
    total_rounds: int = 0
    duration: int = 0                 # 游戏时长（秒）
    created_at: datetime = field(default_factory=datetime.now)