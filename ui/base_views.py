"""
基础View类
"""
import discord
from discord import ui
from typing import Optional, Callable, Any
import asyncio

from config import Config


class BaseView(ui.View):
    """基础View类，提供通用功能"""
    
    def __init__(self, user_id: int, timeout: float = 180.0):
        """
        Args:
            user_id: 允许交互的用户ID
            timeout: 超时时间（秒）
        """
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.message: Optional[discord.Message] = None
        self.value: Any = None
        self._timeout_duration = timeout  # 保存超时时长用于重置
    
    def reset_timeout(self) -> None:
        """重置超时计时器（每次交互时调用）"""
        if self._timeout_duration is not None:
            # 使用 timeout setter 来刷新超时
            # 这会触发 discord.py 内部的超时刷新逻辑
            self.timeout = self._timeout_duration
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """检查交互是否来自正确的用户"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ 这不是你的面板！",
                ephemeral=True
            )
            return False
        # 每次有效交互时重置超时
        self.reset_timeout()
        return True
    
    async def on_timeout(self) -> None:
        """超时处理"""
        if self.message:
            try:
                # 如果启用自动删除，直接删除消息
                if Config.AUTO_DELETE_MESSAGES:
                    await self.message.delete()
                else:
                    # 否则禁用所有按钮
                    for item in self.children:
                        if isinstance(item, (ui.Button, ui.Select)):
                            item.disabled = True
                    await self.message.edit(view=self)
            except discord.NotFound:
                pass
            except discord.Forbidden:
                pass
            except Exception:
                pass
    
    async def on_error(self, interaction: discord.Interaction, error: Exception, item: ui.Item) -> None:
        """错误处理"""
        import logging
        logger = logging.getLogger(__name__)
        
        # 记录错误日志
        logger.error(f"View交互错误: {error}", exc_info=error)
        
        # 检查是否是交互超时错误
        if isinstance(error, discord.NotFound) and error.code == 10062:
            # 交互已过期，无法响应
            logger.warning("交互已过期，无法发送错误消息")
            return
        
        try:
            # 尝试检查交互状态
            if interaction.response.is_done():
                # 交互已响应过，使用 followup
                await interaction.followup.send(
                    f"❌ 发生错误，请重试",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"❌ 发生错误，请重试",
                    ephemeral=True
                )
        except discord.NotFound:
            # 交互已过期
            logger.warning("无法发送错误消息：交互已过期")
        except Exception as e:
            logger.error(f"发送错误消息失败: {e}")
    
    def disable_all(self) -> None:
        """禁用所有组件"""
        for item in self.children:
            if isinstance(item, (ui.Button, ui.Select)):
                item.disabled = True
    
    async def schedule_delete(self, delay: int = None) -> None:
        """计划删除消息
        
        Args:
            delay: 延迟秒数，None则使用默认配置
        """
        if not Config.AUTO_DELETE_MESSAGES:
            return
        
        if self.message is None:
            return
        
        if delay is None:
            delay = Config.GAME_OVER_DELETE_DELAY
        
        await asyncio.sleep(delay)
        
        try:
            await self.message.delete()
        except discord.NotFound:
            pass  # 消息已被删除
        except discord.Forbidden:
            pass  # 没有删除权限
        except Exception:
            pass


class ConfirmView(BaseView):
    """确认对话框View"""
    
    def __init__(self, user_id: int, timeout: float = 60.0):
        super().__init__(user_id, timeout)
        self.confirmed: Optional[bool] = None
    
    @ui.button(label="确认", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_button(self, interaction: discord.Interaction, button: ui.Button):
        self.confirmed = True
        self.stop()
        await interaction.response.defer()
    
    @ui.button(label="取消", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: ui.Button):
        self.confirmed = False
        self.stop()
        await interaction.response.defer()


class TimeoutView(BaseView):
    """带倒计时的View"""
    
    def __init__(self, user_id: int, timeout: float = 60.0, 
                 on_timeout_callback: Optional[Callable] = None):
        super().__init__(user_id, timeout)
        self.on_timeout_callback = on_timeout_callback
        self.remaining_time = int(timeout)
        self._countdown_task: Optional[asyncio.Task] = None
    
    async def start_countdown(self, interaction: discord.Interaction) -> None:
        """开始倒计时"""
        self._countdown_task = asyncio.create_task(self._countdown())
    
    async def _countdown(self) -> None:
        """倒计时任务"""
        while self.remaining_time > 0:
            await asyncio.sleep(1)
            self.remaining_time -= 1
    
    async def on_timeout(self) -> None:
        """超时处理"""
        if self._countdown_task:
            self._countdown_task.cancel()
        
        if self.on_timeout_callback:
            await self.on_timeout_callback()
        
        await super().on_timeout()
    
    def stop(self) -> None:
        """停止View"""
        if self._countdown_task:
            self._countdown_task.cancel()
        super().stop()