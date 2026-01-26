"""
每日签到系统
"""
from datetime import datetime, timedelta
from typing import Tuple
from data.database import Database
from config import Config


class DailySystem:
    """每日签到系统"""
    
    def __init__(self, database: Database):
        self.db = database
    
    async def claim_daily(self, user_id: int) -> Tuple[bool, int, str]:
        """领取每日奖励
        
        Args:
            user_id: Discord用户ID
            
        Returns:
            (是否成功, 奖励金额, 消息)
        """
        player = await self.db.get_or_create_player(user_id)
        
        # 检查是否可以领取
        if not player.can_claim_daily():
            return False, 0, "今天已经签到过了，明天再来吧！"
        
        # 发放奖励
        reward = Config.DAILY_REWARD
        new_balance = player.chips + reward
        
        await self.db.update_chips(user_id, new_balance)
        await self.db.update_last_daily(user_id)
        
        # 更新统计
        stats = await self.db.get_player_stats(user_id)
        stats.total_chips_earned += reward
        await self.db.update_player_stats(stats)
        
        return True, reward, f"签到成功！获得 {reward} 🎰"
    
    async def can_claim(self, user_id: int) -> bool:
        """检查是否可以签到
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否可以签到
        """
        player = await self.db.get_player(user_id)
        if player is None:
            return True
        return player.can_claim_daily()
    
    async def get_next_claim_time(self, user_id: int) -> str:
        """获取下次可签到时间
        
        Args:
            user_id: 用户ID
            
        Returns:
            下次可签到时间描述
        """
        player = await self.db.get_player(user_id)
        if player is None or player.last_daily is None:
            return "现在就可以签到！"
        
        if player.can_claim_daily():
            return "现在就可以签到！"
        
        # 计算到明天0点的时间
        now = datetime.now()
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        delta = tomorrow - now
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        
        return f"{hours}小时{minutes}分钟后"