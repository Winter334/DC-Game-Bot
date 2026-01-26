"""
菜单组件
"""
import discord
from discord import ui
from typing import Optional, Callable, Awaitable
from utils.constants import Emoji


class MenuButton(ui.Button):
    """通用菜单按钮"""
    
    def __init__(
        self,
        label: str,
        callback: Callable[[discord.Interaction], Awaitable[None]],
        style: discord.ButtonStyle = discord.ButtonStyle.primary,
        emoji: Optional[str] = None,
        disabled: bool = False,
        row: Optional[int] = None
    ):
        super().__init__(
            label=label,
            style=style,
            emoji=emoji,
            disabled=disabled,
            row=row
        )
        self._callback = callback
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await self._callback(interaction)


class BackButton(ui.Button):
    """返回按钮"""
    
    def __init__(
        self,
        callback: Callable[[discord.Interaction], Awaitable[None]],
        label: str = "返回",
        row: Optional[int] = None
    ):
        super().__init__(
            label=label,
            style=discord.ButtonStyle.secondary,
            emoji=Emoji.BACK,
            row=row
        )
        self._callback = callback
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await self._callback(interaction)


class SelectMenu(ui.Select):
    """通用选择菜单"""
    
    def __init__(
        self,
        placeholder: str,
        options: list[discord.SelectOption],
        callback: Callable[[discord.Interaction, list[str]], Awaitable[None]],
        min_values: int = 1,
        max_values: int = 1,
        row: Optional[int] = None
    ):
        super().__init__(
            placeholder=placeholder,
            options=options,
            min_values=min_values,
            max_values=max_values,
            row=row
        )
        self._callback = callback
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await self._callback(interaction, self.values)


class UserSelectMenu(ui.UserSelect):
    """用户选择菜单"""
    
    def __init__(
        self,
        placeholder: str,
        callback: Callable[[discord.Interaction, list[discord.User]], Awaitable[None]],
        row: Optional[int] = None
    ):
        super().__init__(
            placeholder=placeholder,
            row=row
        )
        self._callback = callback
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await self._callback(interaction, self.values)