"""
玩家数据管理
"""
from typing import Optional
from data.database import Database
from data.models import PlayerData, PlayerStats


class PlayerDataManager:
    """玩家数据管理器"""
    
    def __init__(self, database: Database):
        self.db = database
    
    async def get_player(self, user_id: int) -> Optional[PlayerData]:
        """获取玩家数据
        
        Args:
            user_id: Discord用户ID
            
        Returns:
            玩家数据，不存在返回None
        """
        return await self.db.get_player(user_id)
    
    async def get_or_create_player(self, user_id: int, initial_chips: int = 0) -> PlayerData:
        """获取或创建玩家
        
        Args:
            user_id: Discord用户ID
            initial_chips: 初始筹码
            
        Returns:
            玩家数据
        """
        return await self.db.get_or_create_player(user_id, initial_chips)
    
    async def get_stats(self, user_id: int) -> PlayerStats:
        """获取玩家统计
        
        Args:
            user_id: Discord用户ID
            
        Returns:
            玩家统计数据
        """
        return await self.db.get_player_stats(user_id)
    
    async def update_stats(self, stats: PlayerStats) -> None:
        """更新玩家统计
        
        Args:
            stats: 玩家统计数据
        """
        await self.db.update_player_stats(stats)
    
    async def record_game_win(self, user_id: int, mode: str, earnings: int = 0,
                               total_rounds: int = 0) -> None:
        """记录游戏胜利
        
        Args:
            user_id: 用户ID
            mode: 游戏模式 (pve/pvp/quick)
            earnings: 获得的筹码
            total_rounds: 总轮数（用于PvE记录最高轮数）
        """
        stats = await self.db.get_player_stats(user_id)
        stats.games_played += 1
        stats.games_won += 1
        
        if mode == "pvp":
            stats.pvp_wins += 1
            stats.pvp_total_earnings += earnings
        elif mode == "pve":
            stats.pve_total_earnings += earnings
            # 更新最高轮数
            if total_rounds > stats.pve_best_rounds:
                stats.pve_best_rounds = total_rounds
            # 更新最大单局奖励
            if earnings > stats.pve_best_reward:
                stats.pve_best_reward = earnings
        
        await self.db.update_player_stats(stats)
    
    async def record_game_loss(self, user_id: int, mode: str) -> None:
        """记录游戏失败
        
        Args:
            user_id: 用户ID
            mode: 游戏模式
        """
        stats = await self.db.get_player_stats(user_id)
        stats.games_played += 1
        
        if mode == "pvp":
            stats.pvp_losses += 1
        
        await self.db.update_player_stats(stats)
    
    async def update_pve_best_stage(self, user_id: int, stage: int) -> None:
        """更新PvE最佳阶段
        
        Args:
            user_id: 用户ID
            stage: 达到的阶段
        """
        stats = await self.db.get_player_stats(user_id)
        if stage > stats.pve_best_stage:
            stats.pve_best_stage = stage
            await self.db.update_player_stats(stats)