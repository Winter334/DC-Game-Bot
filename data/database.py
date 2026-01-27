"""
数据库连接和操作
"""
import aiosqlite
import os
from datetime import datetime
from typing import Optional, List
from .models import PlayerData, PlayerStats, TransferRecord, GameRecord


class Database:
    """数据库管理类"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._connection: Optional[aiosqlite.Connection] = None
    
    async def connect(self) -> None:
        """连接数据库"""
        # 确保目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._create_tables()
    
    async def close(self) -> None:
        """关闭数据库连接"""
        if self._connection:
            await self._connection.close()
            self._connection = None
    
    async def _create_tables(self) -> None:
        """创建数据表"""
        async with self._connection.cursor() as cursor:
            # 玩家数据表
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    user_id INTEGER PRIMARY KEY,
                    chips INTEGER DEFAULT 0,
                    last_daily TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 玩家统计表
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS player_stats (
                    user_id INTEGER PRIMARY KEY,
                    games_played INTEGER DEFAULT 0,
                    games_won INTEGER DEFAULT 0,
                    pve_best_stage INTEGER DEFAULT 0,
                    pve_total_earnings INTEGER DEFAULT 0,
                    pve_best_rounds INTEGER DEFAULT 0,
                    pve_best_reward INTEGER DEFAULT 0,
                    pvp_wins INTEGER DEFAULT 0,
                    pvp_losses INTEGER DEFAULT 0,
                    pvp_total_earnings INTEGER DEFAULT 0,
                    total_chips_earned INTEGER DEFAULT 0,
                    total_chips_spent INTEGER DEFAULT 0
                )
            """)
            
            # 添加新列（如果不存在）- 用于数据库升级
            try:
                await cursor.execute("ALTER TABLE player_stats ADD COLUMN pve_best_rounds INTEGER DEFAULT 0")
            except:
                pass  # 列已存在
            try:
                await cursor.execute("ALTER TABLE player_stats ADD COLUMN pve_best_reward INTEGER DEFAULT 0")
            except:
                pass  # 列已存在
            
            # 转账记录表
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS transfers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_user_id INTEGER,
                    to_user_id INTEGER,
                    amount INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 游戏记录表
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS game_records (
                    id TEXT PRIMARY KEY,
                    mode TEXT,
                    player1_id INTEGER,
                    player2_id INTEGER,
                    winner_id INTEGER,
                    bet_amount INTEGER DEFAULT 0,
                    reward_amount INTEGER DEFAULT 0,
                    stages_completed INTEGER DEFAULT 0,
                    total_rounds INTEGER DEFAULT 0,
                    duration INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await self._connection.commit()
    
    # ==================== 玩家数据操作 ====================
    
    async def get_player(self, user_id: int) -> Optional[PlayerData]:
        """获取玩家数据"""
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                "SELECT * FROM players WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            
            if row is None:
                return None
            
            return PlayerData(
                user_id=row["user_id"],
                chips=row["chips"],
                last_daily=datetime.fromisoformat(row["last_daily"]) if row["last_daily"] else None,
                created_at=datetime.fromisoformat(row["created_at"])
            )
    
    async def create_player(self, user_id: int, initial_chips: int = 0) -> PlayerData:
        """创建新玩家"""
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO players (user_id, chips) VALUES (?, ?)",
                (user_id, initial_chips)
            )
            await self._connection.commit()
        
        return PlayerData(user_id=user_id, chips=initial_chips)
    
    async def get_or_create_player(self, user_id: int, initial_chips: int = 0) -> PlayerData:
        """获取或创建玩家"""
        player = await self.get_player(user_id)
        if player is None:
            player = await self.create_player(user_id, initial_chips)
        return player
    
    async def update_chips(self, user_id: int, chips: int) -> None:
        """更新玩家筹码"""
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                "UPDATE players SET chips = ? WHERE user_id = ?",
                (chips, user_id)
            )
            await self._connection.commit()
    
    async def update_last_daily(self, user_id: int) -> None:
        """更新签到时间"""
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                "UPDATE players SET last_daily = ? WHERE user_id = ?",
                (datetime.now().isoformat(), user_id)
            )
            await self._connection.commit()
    
    # ==================== 玩家统计操作 ====================
    
    async def get_player_stats(self, user_id: int) -> PlayerStats:
        """获取玩家统计"""
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                "SELECT * FROM player_stats WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            
            if row is None:
                # 创建默认统计
                await cursor.execute(
                    "INSERT INTO player_stats (user_id) VALUES (?)",
                    (user_id,)
                )
                await self._connection.commit()
                return PlayerStats(user_id=user_id)
            
            return PlayerStats(
                user_id=row["user_id"],
                games_played=row["games_played"],
                games_won=row["games_won"],
                pve_best_stage=row["pve_best_stage"],
                pve_total_earnings=row["pve_total_earnings"],
                pve_best_rounds=row["pve_best_rounds"] if "pve_best_rounds" in row.keys() else 0,
                pve_best_reward=row["pve_best_reward"] if "pve_best_reward" in row.keys() else 0,
                pvp_wins=row["pvp_wins"],
                pvp_losses=row["pvp_losses"],
                pvp_total_earnings=row["pvp_total_earnings"],
                total_chips_earned=row["total_chips_earned"],
                total_chips_spent=row["total_chips_spent"]
            )
    
    async def update_player_stats(self, stats: PlayerStats) -> None:
        """更新玩家统计"""
        async with self._connection.cursor() as cursor:
            await cursor.execute("""
                UPDATE player_stats SET
                    games_played = ?,
                    games_won = ?,
                    pve_best_stage = ?,
                    pve_total_earnings = ?,
                    pve_best_rounds = ?,
                    pve_best_reward = ?,
                    pvp_wins = ?,
                    pvp_losses = ?,
                    pvp_total_earnings = ?,
                    total_chips_earned = ?,
                    total_chips_spent = ?
                WHERE user_id = ?
            """, (
                stats.games_played,
                stats.games_won,
                stats.pve_best_stage,
                stats.pve_total_earnings,
                stats.pve_best_rounds,
                stats.pve_best_reward,
                stats.pvp_wins,
                stats.pvp_losses,
                stats.pvp_total_earnings,
                stats.total_chips_earned,
                stats.total_chips_spent,
                stats.user_id
            ))
            await self._connection.commit()
    
    # ==================== 转账记录操作 ====================
    
    async def add_transfer_record(self, from_id: int, to_id: int, amount: int) -> None:
        """添加转账记录"""
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO transfers (from_user_id, to_user_id, amount) VALUES (?, ?, ?)",
                (from_id, to_id, amount)
            )
            await self._connection.commit()
    
    async def get_transfer_history(self, user_id: int, limit: int = 10) -> List[TransferRecord]:
        """获取转账历史"""
        async with self._connection.cursor() as cursor:
            await cursor.execute("""
                SELECT * FROM transfers 
                WHERE from_user_id = ? OR to_user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, user_id, limit))
            
            rows = await cursor.fetchall()
            return [
                TransferRecord(
                    id=row["id"],
                    from_user_id=row["from_user_id"],
                    to_user_id=row["to_user_id"],
                    amount=row["amount"],
                    created_at=datetime.fromisoformat(row["created_at"])
                )
                for row in rows
            ]
    
    # ==================== 排行榜 ====================
    
    async def get_chips_leaderboard(self, limit: int = 10) -> List[tuple]:
        """获取筹码排行榜"""
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                "SELECT user_id, chips FROM players ORDER BY chips DESC LIMIT ?",
                (limit,)
            )
            return await cursor.fetchall()
    
    async def get_wins_leaderboard(self, limit: int = 10) -> List[tuple]:
        """获取胜场排行榜"""
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                "SELECT user_id, games_won FROM player_stats ORDER BY games_won DESC LIMIT ?",
                (limit,)
            )
            return await cursor.fetchall()
    
    async def get_rounds_leaderboard(self, limit: int = 10) -> List[tuple]:
        """获取最高轮数排行榜"""
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                "SELECT user_id, pve_best_rounds FROM player_stats WHERE pve_best_rounds > 0 ORDER BY pve_best_rounds DESC LIMIT ?",
                (limit,)
            )
            return await cursor.fetchall()
    
    async def get_reward_leaderboard(self, limit: int = 10) -> List[tuple]:
        """获取最大单局奖励排行榜"""
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                "SELECT user_id, pve_best_reward FROM player_stats WHERE pve_best_reward > 0 ORDER BY pve_best_reward DESC LIMIT ?",
                (limit,)
            )
            return await cursor.fetchall()