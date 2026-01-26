"""
道具系统 - 恶魔轮盘赌
"""
import random
from dataclasses import dataclass
from typing import Optional, List, TYPE_CHECKING, Callable, Awaitable
from enum import Enum

from config import Config

if TYPE_CHECKING:
    from .session import GameSession
    from .player import Player


class ItemRarity(Enum):
    """道具稀有度"""
    COMMON = "common"     # 普通 70%
    RARE = "rare"         # 稀有 25%
    EPIC = "epic"         # 史诗 5%


class ItemType(Enum):
    """道具类型"""
    # 原版道具
    MAGNIFIER = "magnifier"       # 放大镜
    BEER = "beer"                 # 啤酒
    CIGARETTE = "cigarette"       # 香烟
    SAW = "saw"                   # 手锯
    HANDCUFFS = "handcuffs"       # 手铐
    MEDICINE = "medicine"         # 过期药物
    INVERTER = "inverter"         # 逆转器
    PHONE = "phone"               # 窃贼电话
    
    # 扩充道具
    VEST = "vest"                 # 防弹背心
    ADRENALINE = "adrenaline"     # 肾上腺素
    COIN = "coin"                 # 幸运硬币
    TELESCOPE = "telescope"       # 望远镜
    MEDKIT = "medkit"             # 急救包
    JAMMER = "jammer"             # 干扰器


@dataclass
class Item:
    """道具基类"""
    item_type: ItemType
    name: str
    emoji: str
    description: str
    rarity: ItemRarity
    
    # 是否需要选择目标
    needs_target: bool = False
    # 是否可以被偷取（肾上腺素不能偷取肾上腺素）
    can_be_stolen: bool = True
    
    def __str__(self) -> str:
        return f"{self.emoji} {self.name}"


# 道具定义
ITEMS = {
    # ===== 原版道具 =====
    ItemType.MAGNIFIER: Item(
        item_type=ItemType.MAGNIFIER,
        name="放大镜",
        emoji="🔍",
        description="查看当前子弹是实弹还是空包弹",
        rarity=ItemRarity.COMMON
    ),
    ItemType.BEER: Item(
        item_type=ItemType.BEER,
        name="啤酒",
        emoji="🍺",
        description="退出当前子弹（跳过这一发）",
        rarity=ItemRarity.COMMON
    ),
    ItemType.CIGARETTE: Item(
        item_type=ItemType.CIGARETTE,
        name="香烟",
        emoji="🚬",
        description="恢复1点生命值（不超过上限）",
        rarity=ItemRarity.COMMON
    ),
    ItemType.SAW: Item(
        item_type=ItemType.SAW,
        name="手锯",
        emoji="🔪",
        description="本发实弹造成2点伤害（仅限下一枪）",
        rarity=ItemRarity.COMMON
    ),
    ItemType.HANDCUFFS: Item(
        item_type=ItemType.HANDCUFFS,
        name="手铐",
        emoji="🔗",
        description="对手下回合被跳过",
        rarity=ItemRarity.COMMON
    ),
    ItemType.MEDICINE: Item(
        item_type=ItemType.MEDICINE,
        name="过期药物",
        emoji="💊",
        description="50%恢复2点生命 / 50%扣除1点生命",
        rarity=ItemRarity.COMMON
    ),
    ItemType.INVERTER: Item(
        item_type=ItemType.INVERTER,
        name="逆转器",
        emoji="🔄",
        description="将当前子弹在实弹/空包弹之间切换",
        rarity=ItemRarity.COMMON
    ),
    ItemType.PHONE: Item(
        item_type=ItemType.PHONE,
        name="窃贼电话",
        emoji="📱",
        description="随机得知某个位置的子弹类型",
        rarity=ItemRarity.COMMON
    ),
    
    # ===== 扩充道具 =====
    ItemType.VEST: Item(
        item_type=ItemType.VEST,
        name="防弹背心",
        emoji="🦺",
        description="下一次受到伤害时减少1点（最少受到1点）",
        rarity=ItemRarity.RARE
    ),
    ItemType.ADRENALINE: Item(
        item_type=ItemType.ADRENALINE,
        name="肾上腺素",
        emoji="💉",
        description="偷取对手一个道具并立即使用",
        rarity=ItemRarity.RARE,
        needs_target=True,
        can_be_stolen=False
    ),
    ItemType.COIN: Item(
        item_type=ItemType.COIN,
        name="幸运硬币",
        emoji="🪙",
        description="重新打乱弹夹顺序（不改变实弹/空包弹数量）",
        rarity=ItemRarity.COMMON
    ),
    ItemType.TELESCOPE: Item(
        item_type=ItemType.TELESCOPE,
        name="望远镜",
        emoji="🔭",
        description="查看弹夹中第2发子弹的类型",
        rarity=ItemRarity.RARE
    ),
    ItemType.MEDKIT: Item(
        item_type=ItemType.MEDKIT,
        name="急救包",
        emoji="🩹",
        description="立即恢复2点生命（可超过上限，但额外生命值会在回合结束后消失）",
        rarity=ItemRarity.RARE
    ),
    ItemType.JAMMER: Item(
        item_type=ItemType.JAMMER,
        name="干扰器",
        emoji="📡",
        description="使对手随机一个道具失效（隐藏标记）",
        rarity=ItemRarity.EPIC
    ),
}


# 道具池配置
ITEM_POOL = {
    ItemRarity.COMMON: [
        ItemType.MAGNIFIER,
        ItemType.BEER,
        ItemType.CIGARETTE,
        ItemType.SAW,
        ItemType.HANDCUFFS,
        ItemType.MEDICINE,
        ItemType.INVERTER,
        ItemType.PHONE,
        ItemType.COIN,
    ],
    ItemRarity.RARE: [
        ItemType.VEST,
        ItemType.ADRENALINE,
        ItemType.TELESCOPE,
        ItemType.MEDKIT,
    ],
    ItemRarity.EPIC: [
        ItemType.JAMMER,
    ],
}


def get_item(item_type: ItemType) -> Item:
    """获取道具实例"""
    return ITEMS[item_type]


def generate_random_item(include_expansion: bool = True) -> Item:
    """随机生成一个道具
    
    Args:
        include_expansion: 是否包含扩充道具
        
    Returns:
        随机道具
    """
    # 稀有度权重
    roll = random.random()
    
    common_threshold = Config.ITEM_RARITY_COMMON
    rare_threshold = common_threshold + Config.ITEM_RARITY_RARE
    
    if roll < common_threshold:
        rarity = ItemRarity.COMMON
    elif roll < rare_threshold:
        rarity = ItemRarity.RARE
    else:
        rarity = ItemRarity.EPIC
    
    # 从对应稀有度池中随机选择
    pool = ITEM_POOL[rarity].copy()
    
    # 如果不包含扩充道具，过滤掉
    if not include_expansion:
        expansion_items = {
            ItemType.VEST, ItemType.ADRENALINE, ItemType.COIN,
            ItemType.TELESCOPE, ItemType.MEDKIT, ItemType.JAMMER
        }
        pool = [item for item in pool if item not in expansion_items]
    
    if not pool:
        # 如果池为空，从普通池选择原版道具
        pool = [
            ItemType.MAGNIFIER, ItemType.BEER, ItemType.CIGARETTE,
            ItemType.SAW, ItemType.HANDCUFFS, ItemType.MEDICINE,
            ItemType.INVERTER, ItemType.PHONE
        ]
    
    item_type = random.choice(pool)
    return get_item(item_type)


def generate_items(count: int, include_expansion: bool = True) -> List[Item]:
    """生成多个随机道具
    
    Args:
        count: 道具数量
        include_expansion: 是否包含扩充道具
        
    Returns:
        道具列表
    """
    return [generate_random_item(include_expansion) for _ in range(count)]


def get_item_count_for_stage(stage: int) -> tuple:
    """根据阶段获取道具数量范围
    
    Args:
        stage: 当前阶段
        
    Returns:
        (最小数量, 最大数量)
    """
    ranges = {
        1: (0, 2),
        2: (2, 3),
        3: (3, 4),
        4: (4, 5),
        5: (5, 6),
    }
    stage_key = min(stage, 5)
    return ranges[stage_key]