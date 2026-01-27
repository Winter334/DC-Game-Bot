"""
游戏中心配置文件
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Config:
    """配置类"""
    
    # Bot配置
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    
    # 经济配置
    DAILY_REWARD: int = 100           # 每日签到奖励
    NEW_PLAYER_BONUS: int = 500       # 新手礼包
    PVE_ENTRY_FEE: int = 10           # PvE入场费
    PVE_BASE_REWARD: int = 50         # PvE基础奖励
    MIN_BET: int = 10                 # 最低押注
    
    # 快速模式难度配置
    # 难度越高：入场费和奖励越高，血量和道具越多，弹夹越大
    QUICK_DIFFICULTY_CONFIG = {
        "easy": {
            "entry_fee": 5, "reward": 10, "name": "简单", "emoji": "🟢",
            "health": 2,                    # 血量
            "items_min": 1, "items_max": 2, # 道具数量范围
            "magazine_min": 2, "magazine_max": 4,  # 弹夹大小范围
        },
        "normal": {
            "entry_fee": 10, "reward": 25, "name": "普通", "emoji": "🟡",
            "health": 2,
            "items_min": 2, "items_max": 3,
            "magazine_min": 3, "magazine_max": 5,
        },
        "hard": {
            "entry_fee": 20, "reward": 60, "name": "困难", "emoji": "🟠",
            "health": 3,
            "items_min": 3, "items_max": 4,
            "magazine_min": 4, "magazine_max": 6,
        },
        "hard_plus": {
            "entry_fee": 35, "reward": 120, "name": "困难+", "emoji": "🔴",
            "health": 4,
            "items_min": 4, "items_max": 5,
            "magazine_min": 5, "magazine_max": 7,
        },
        "demon": {
            "entry_fee": 50, "reward": 200, "name": "恶魔", "emoji": "👿",
            "health": 5,
            "items_min": 5, "items_max": 6,
            "magazine_min": 6, "magazine_max": 8,
        },
    }
    MIN_TRANSFER: int = 10            # 最低转账
    
    # 游戏配置
    TURN_TIMEOUT: int = 300           # 回合超时（秒）- 5分钟，给玩家足够思考时间
    CHALLENGE_TIMEOUT: int = 180      # 挑战超时（秒）- 3分钟
    ITEM_SELECT_TIMEOUT: int = 180    # 道具选择超时（秒）- 3分钟
    STAGE_COMPLETE_TIMEOUT: int = 180 # 阶段完成选择超时（秒）- 3分钟
    GAME_OVER_TIMEOUT: int = 300      # 游戏结束界面超时（秒）- 5分钟
    MAX_ITEMS: int = 8                # 最大道具数
    ACTION_LOG_SIZE: int = 5          # 操作记录条数
    
    # 游戏模式配置
    PVP_WINS_REQUIRED: int = 2        # PvP模式获胜所需胜场（Bo3=2）
    # PvP血量采用原版规则，由 stage_manager.get_health() 决定（第1轮2点，第2轮4点，第3轮5点）
    AI_THINK_DELAY: float = 1.5       # AI思考延迟（秒）
    RELOAD_DELAY: float = 5.0         # 装填延迟（秒）- 弹夹打空后等待时间
    
    # 道具配置
    ENABLE_EXPANSION_ITEMS: bool = True
    ITEM_RARITY_COMMON: float = 0.70  # 普通道具概率
    ITEM_RARITY_RARE: float = 0.25    # 稀有道具概率（剩余为史诗）
    
    # AI配置
    DEMON_CHEAT_CHANCE: float = 0.15  # 恶魔AI作弊概率
    HARD_PLUS_CHEAT_CHANCE: float = 0.08  # 困难+AI作弊概率
    
    # 消息清理配置
    AUTO_DELETE_MESSAGES: bool = True           # 是否自动删除消息
    GAME_OVER_DELETE_DELAY: int = 180           # 游戏结束后删除延迟（秒）- 3分钟
    CHALLENGE_DELETE_DELAY: int = 120           # 挑战消息删除延迟（秒）- 2分钟
    
    # 数据库配置
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/games.db")
    
    @classmethod
    def validate(cls) -> bool:
        """验证配置是否有效"""
        if not cls.BOT_TOKEN:
            print("错误: 未设置 BOT_TOKEN")
            return False
        return True