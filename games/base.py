"""
游戏基类
"""
from abc import ABC, abstractmethod
from typing import Optional, List, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime
import uuid

if TYPE_CHECKING:
    from bot import GameCenterBot


@dataclass
class GamePlayer:
    """游戏玩家基类"""
    user_id: int
    name: str
    health: int = 0
    max_health: int = 0
    items: List[str] = field(default_factory=list)
    is_ai: bool = False
    
    @property
    def is_alive(self) -> bool:
        return self.health > 0
    
    def take_damage(self, amount: int) -> int:
        """受到伤害，返回实际伤害值"""
        actual = min(amount, self.health)
        self.health -= actual
        return actual
    
    def heal(self, amount: int) -> int:
        """恢复生命，返回实际恢复值"""
        actual = min(amount, self.max_health - self.health)
        self.health += actual
        return actual


class BaseGame(ABC):
    """游戏基类"""
    
    def __init__(self, bot: 'GameCenterBot', channel_id: int, host_id: int):
        self.id = str(uuid.uuid4())[:8]
        self.bot = bot
        self.channel_id = channel_id
        self.host_id = host_id
        self.message_id: Optional[int] = None
        self.players: List[GamePlayer] = []
        self.current_turn: int = 0
        self.state: str = "waiting"
        self.action_log: List[str] = []
        self.started_at: Optional[datetime] = None
        self.ended_at: Optional[datetime] = None
    
    @property
    def current_player(self) -> Optional[GamePlayer]:
        """获取当前行动的玩家"""
        if not self.players:
            return None
        return self.players[self.current_turn % len(self.players)]
    
    @property
    def duration(self) -> int:
        """获取游戏时长（秒）"""
        if self.started_at is None:
            return 0
        end = self.ended_at or datetime.now()
        return int((end - self.started_at).total_seconds())
    
    def add_log(self, message: str, max_logs: int = 5) -> None:
        """添加操作日志"""
        self.action_log.append(message)
        if len(self.action_log) > max_logs:
            self.action_log = self.action_log[-max_logs:]
    
    def next_turn(self) -> None:
        """切换到下一个玩家"""
        self.current_turn = (self.current_turn + 1) % len(self.players)
    
    @abstractmethod
    async def start(self) -> None:
        """开始游戏"""
        pass
    
    @abstractmethod
    async def update_message(self) -> None:
        """更新游戏消息"""
        pass
    
    @abstractmethod
    async def end_game(self, winner: Optional[GamePlayer] = None) -> None:
        """结束游戏"""
        pass