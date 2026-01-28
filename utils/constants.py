"""
常量定义
"""

# 表情符号
class Emoji:
    """游戏中使用的表情符号"""
    # 通用
    CHIPS = "🎰"
    GAME = "🎮"
    GIFT = "🎁"
    STATS = "📊"
    TROPHY = "🏆"
    BACK = "◀️"
    TRANSFER = "💸"
    
    # 恶魔轮盘赌
    BUCKSHOT = "🎰"
    ROBOT = "🤖"
    PVP = "⚔️"
    QUICK = "⚡"
    RULES = "📖"
    
    # PokeRogue
    POKEROGUE = "🎮"
    
    # 生命值
    HEART = "❤️"
    HEART_EMPTY = "🖤"
    SKULL = "💀"
    
    # 道具
    MAGNIFIER = "🔍"
    BEER = "🍺"
    CIGARETTE = "🚬"
    SAW = "🔪"
    HANDCUFFS = "🔗"
    MEDICINE = "💊"
    INVERTER = "🔄"
    PHONE = "📱"
    VEST = "🦺"
    ADRENALINE = "💉"
    COIN = "🪙"
    TELESCOPE = "🔭"
    MEDKIT = "🩹"
    JAMMER = "📡"
    
    # 动作
    SHOOT = "🔫"
    TARGET = "🎯"
    ITEM = "📦"
    RUN = "🏃"
    CONTINUE = "🎰"
    RELOAD = "🔄"
    
    # 状态
    SUCCESS = "✅"
    FAIL = "❌"
    WARNING = "⚠️"
    INFO = "💡"
    TIME = "⏰"


# 颜色
class Colors:
    """Embed颜色"""
    PRIMARY = 0x5865F2      # Discord蓝
    SUCCESS = 0x57F287      # 绿色
    WARNING = 0xFEE75C      # 黄色
    DANGER = 0xED4245       # 红色
    SECONDARY = 0x99AAB5    # 灰色
    GOLD = 0xF1C40F         # 金色
    PURPLE = 0x9B59B6       # 紫色


# 游戏模式
class GameMode:
    """游戏模式"""
    PVE = "pve"
    PVP = "pvp"
    QUICK = "quick"


# 游戏状态
class GameState:
    """游戏状态"""
    WAITING = "waiting"         # 等待开始
    PLAYING = "playing"         # 游戏中
    STAGE_COMPLETE = "stage"    # 阶段完成
    ENDED = "ended"             # 游戏结束


# AI难度
class AIDifficulty:
    """AI难度等级"""
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"
    HARD_PLUS = "hard_plus"
    DEMON = "demon"
    
    @classmethod
    def get_display_name(cls, difficulty: str) -> str:
        """获取显示名称"""
        names = {
            cls.EASY: "简单",
            cls.NORMAL: "普通",
            cls.HARD: "困难",
            cls.HARD_PLUS: "困难+",
            cls.DEMON: "恶魔"
        }
        return names.get(difficulty, difficulty)