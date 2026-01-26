"""
游戏中心 Discord Bot 主入口
"""
import asyncio
import discord
from discord.ext import commands
import logging
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from data.database import Database
from core.economy import Economy
from core.player_data import PlayerDataManager
from core.daily import DailySystem
from games.buckshot_roulette import BuckshotRouletteGame

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('GameCenter')


class GameCenterBot(commands.Bot):
    """游戏中心Bot"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix="!",  # 斜杠命令为主，前缀命令作为备用
            intents=intents,
            help_command=None
        )
        
        # 核心系统
        self.database: Database = None
        self.economy: Economy = None
        self.player_data: PlayerDataManager = None
        self.daily: DailySystem = None
        
        # 游戏模块
        self.buckshot_roulette: BuckshotRouletteGame = None
    
    async def setup_hook(self) -> None:
        """Bot启动时的初始化"""
        logger.info("正在初始化Bot...")
        
        # 初始化数据库
        self.database = Database(Config.DATABASE_PATH)
        await self.database.connect()
        logger.info("数据库连接成功")
        
        # 初始化核心系统
        self.economy = Economy(self.database)
        self.player_data = PlayerDataManager(self.database)
        self.daily = DailySystem(self.database)
        logger.info("核心系统初始化完成")
        
        # 初始化游戏模块
        self.buckshot_roulette = BuckshotRouletteGame(self)
        logger.info("游戏模块初始化完成")
        
        # 加载Cogs
        await self.load_cogs()
        
        # 同步斜杠命令
        logger.info("正在同步斜杠命令...")
        await self.tree.sync()
        logger.info("斜杠命令同步完成")
    
    async def load_cogs(self) -> None:
        """加载所有Cog模块"""
        cogs = [
            "cogs.game_center",
            # "cogs.admin",  # 管理命令（后续添加）
        ]
        
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"已加载Cog: {cog}")
            except Exception as e:
                logger.error(f"加载Cog失败 {cog}: {e}")
    
    async def on_ready(self) -> None:
        """Bot就绪事件"""
        logger.info(f"Bot已登录: {self.user} (ID: {self.user.id})")
        logger.info(f"已连接到 {len(self.guilds)} 个服务器")
        
        # 设置状态
        activity = discord.Activity(
            type=discord.ActivityType.playing,
            name="🎮 /game 开始游戏"
        )
        await self.change_presence(activity=activity)
    
    async def on_command_error(self, ctx: commands.Context, error: Exception) -> None:
        """命令错误处理"""
        if isinstance(error, commands.CommandNotFound):
            return
        
        logger.error(f"命令错误: {error}")
        await ctx.send(f"❌ 发生错误: {error}")
    
    async def close(self) -> None:
        """关闭Bot"""
        logger.info("正在关闭Bot...")
        
        if self.database:
            await self.database.close()
            logger.info("数据库连接已关闭")
        
        await super().close()


async def main():
    """主函数"""
    # 验证配置
    if not Config.validate():
        logger.error("配置验证失败，请检查.env文件")
        return
    
    # 创建并运行Bot
    bot = GameCenterBot()
    
    try:
        await bot.start(Config.BOT_TOKEN)
    except KeyboardInterrupt:
        logger.info("收到中断信号")
    except Exception as e:
        logger.error(f"Bot运行错误: {e}")
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())