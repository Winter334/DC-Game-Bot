"""
筹码经济系统
"""
from typing import Optional, List, Tuple
from data.database import Database
from config import Config


class Economy:
    """筹码经济系统"""
    
    def __init__(self, database: Database):
        self.db = database
    
    async def get_balance(self, user_id: int) -> int:
        """获取用户余额
        
        Args:
            user_id: Discord用户ID
            
        Returns:
            筹码余额
        """
        player = await self.db.get_player(user_id)
        if player is None:
            return 0
        return player.chips
    
    async def add_chips(self, user_id: int, amount: int, reason: str = "") -> int:
        """增加筹码
        
        Args:
            user_id: Discord用户ID
            amount: 增加数量
            reason: 原因（用于日志）
            
        Returns:
            新余额
        """
        player = await self.db.get_or_create_player(user_id)
        new_balance = player.chips + amount
        await self.db.update_chips(user_id, new_balance)
        
        # 更新统计
        stats = await self.db.get_player_stats(user_id)
        stats.total_chips_earned += amount
        await self.db.update_player_stats(stats)
        
        return new_balance
    
    async def deduct_chips(self, user_id: int, amount: int, reason: str = "") -> bool:
        """扣除筹码
        
        Args:
            user_id: Discord用户ID
            amount: 扣除数量
            reason: 原因（用于日志）
            
        Returns:
            是否成功（余额不足返回False）
        """
        player = await self.db.get_or_create_player(user_id)
        
        if player.chips < amount:
            return False
        
        new_balance = player.chips - amount
        await self.db.update_chips(user_id, new_balance)
        
        # 更新统计
        stats = await self.db.get_player_stats(user_id)
        stats.total_chips_spent += amount
        await self.db.update_player_stats(stats)
        
        return True
    
    async def transfer(self, from_id: int, to_id: int, amount: int) -> Tuple[bool, str]:
        """转账
        
        Args:
            from_id: 转出用户ID
            to_id: 转入用户ID
            amount: 转账金额
            
        Returns:
            (是否成功, 消息)
        """
        # 检查金额
        if amount < Config.MIN_TRANSFER:
            return False, f"最低转账金额为 {Config.MIN_TRANSFER} 🎰"
        
        # 检查是否转给自己
        if from_id == to_id:
            return False, "不能转账给自己"
        
        # 检查余额
        from_player = await self.db.get_or_create_player(from_id)
        if from_player.chips < amount:
            return False, "余额不足"
        
        # 执行转账
        await self.db.get_or_create_player(to_id)  # 确保接收者存在
        
        # 扣除发送者
        await self.db.update_chips(from_id, from_player.chips - amount)
        
        # 增加接收者
        to_player = await self.db.get_player(to_id)
        await self.db.update_chips(to_id, to_player.chips + amount)
        
        # 记录转账
        await self.db.add_transfer_record(from_id, to_id, amount)
        
        return True, f"成功转账 {amount} 🎰"
    
    async def get_transfer_history(self, user_id: int, limit: int = 10) -> List:
        """获取转账历史
        
        Args:
            user_id: 用户ID
            limit: 返回数量限制
            
        Returns:
            转账记录列表
        """
        return await self.db.get_transfer_history(user_id, limit)
    
    async def ensure_player_exists(self, user_id: int) -> bool:
        """确保玩家存在，如果是新玩家则发放新手礼包
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否是新玩家
        """
        player = await self.db.get_player(user_id)
        
        if player is None:
            # 新玩家，发放新手礼包
            await self.db.create_player(user_id, Config.NEW_PLAYER_BONUS)
            await self.db.get_player_stats(user_id)  # 初始化统计
            return True
        
        return False