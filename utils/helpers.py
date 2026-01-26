"""
辅助函数
"""
from typing import Optional


def format_chips(amount: int) -> str:
    """格式化筹码显示
    
    Args:
        amount: 筹码数量
        
    Returns:
        格式化后的字符串，如 "🎰 1,250"
    """
    return f"🎰 {amount:,}"


def format_health(current: int, max_health: int) -> str:
    """格式化生命值显示
    
    Args:
        current: 当前生命值
        max_health: 最大生命值
        
    Returns:
        格式化后的字符串，如 "❤️❤️❤️🖤 (3/4)"
    """
    hearts = "❤️" * current + "🖤" * (max_health - current)
    return f"{hearts} ({current}/{max_health})"


def format_duration(seconds: int) -> str:
    """格式化时长显示
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化后的字符串，如 "8:32"
    """
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """截断文本
    
    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 截断后缀
        
    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def create_progress_bar(current: int, total: int, length: int = 10, 
                        filled: str = "█", empty: str = "░") -> str:
    """创建进度条
    
    Args:
        current: 当前值
        total: 总值
        length: 进度条长度
        filled: 填充字符
        empty: 空白字符
        
    Returns:
        进度条字符串
    """
    if total <= 0:
        return empty * length
    
    progress = min(current / total, 1.0)
    filled_length = int(length * progress)
    return filled * filled_length + empty * (length - filled_length)


def ordinal(n: int) -> str:
    """获取序数词（中文）
    
    Args:
        n: 数字
        
    Returns:
        序数词，如 "第1"
    """
    return f"第{n}"