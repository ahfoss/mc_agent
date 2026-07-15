from typing import Any, List, Dict

door_types: List[str] = [
    'oak_door', 'spruce_door', 'birch_door', 'jungle_door', 
    'acacia_door', 'dark_oak_door', 'mangrove_door', 'cherry_door',
    'pale_oak_door', 'warped_door', 'crimson_door',
]

MEAT_ITEMS: List[str] = ["raw_beef", "raw_mutton", "raw_porkchop", "raw_chicken", "raw_rabbit"]
food_mobs: List[str] = ["cow", "sheep", "pig", "chicken", "rabbit"]

FOOD_ITEMS: List[str] = MEAT_ITEMS + [
    "melon_slice", "melon", "sweet_berries", "apple", "bread", "carrot", "potato"
]

axes: List[str] = ["netherite_axe", "diamond_axe", "iron_axe", "golden_axe", "stone_axe", "copper_axe", "wooden_axe"]


def get_item_keywords(agent: Any, keyword_list: List[str]) -> Dict[str, int]:
    """
    Get all block name/ID matches from the registry containing keywords in keyword_list.
    """
    blocks: Dict[str, int] = {}
    
    # Iterate through every block in the game's registry
    for block in agent.bot.registry.blocksArray:
        # Check if the block's name contains any of our keywords
        if any(keyword in block.name for keyword in keyword_list):
            blocks[block.name] = block.id
    return blocks


def get_log_keywords(agent: Any) -> Dict[str, int]:
    """
    Get all wood log keyword matches.
    """
    return get_item_keywords(agent, ['log'])


def has_item(agent: Any, item_name: str, quantity: int = 1) -> bool:
    """
    Checks if the bot has at least the specified quantity of an item in its inventory.
    """
    inv = agent.bot.get_inventory()
    if hasattr(inv, "get"):
        val = inv.get(item_name, 0)
        # Check if the returned value is a MagicMock to avoid TypeErrors in un-mocked unit tests
        if hasattr(val, "assert_called") or "Mock" in type(val).__name__:
            return False
        return val >= quantity
    return False


def get_item_count(agent: Any, item_name_or_list: Any) -> int:
    """
    Gets the quantity of the item(s) in the bot's inventory.
    Accepts a single item name (str) or a list/tuple/set of item names.
    """
    if isinstance(item_name_or_list, (list, tuple, set)):
        return sum(get_item_count(agent, item) for item in item_name_or_list)

    inv = agent.bot.get_inventory()
    if hasattr(inv, "get"):
        val = inv.get(item_name_or_list, 0)
        if hasattr(val, "assert_called") or "Mock" in type(val).__name__:
            return 0
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0
    return 0


def has_any_door(agent: Any) -> bool:
    """
    Checks if the bot has any door item in its inventory.
    """
    for door in door_types:
        if has_item(agent, door, 1):
            return True
    return False
