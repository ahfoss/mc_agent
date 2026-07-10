import math
from typing import Any, Dict, List, Tuple, Optional
from core.memory import get_vec3
import capabilities.items as ui
import capabilities.movement as um

# A dictionary mapping target items to a tuple of (yield_quantity, list of alternative ingredient lists).
# Each ingredient list consists of tuples of (ingredient_name, required_quantity).
RECIPES: Dict[str, Tuple[int, List[List[Tuple[str, int]]]]] = {
    "crafting_table": (1, [
        [("oak_planks", 4)], [("spruce_planks", 4)], [("birch_planks", 4)], 
        [("jungle_planks", 4)], [("acacia_planks", 4)], [("dark_oak_planks", 4)], 
        [("mangrove_planks", 4)], [("cherry_planks", 4)], [("pale_oak_planks", 4)],
        [("warped_planks", 4)], [("crimson_planks", 4)]
    ]),
    "chest": (1, [
        [("oak_planks", 8)], [("spruce_planks", 8)], [("birch_planks", 8)], 
        [("jungle_planks", 8)], [("acacia_planks", 8)], [("dark_oak_planks", 8)], 
        [("mangrove_planks", 8)], [("cherry_planks", 8)], [("pale_oak_planks", 8)],
        [("warped_planks", 8)], [("crimson_planks", 8)]
    ]),
    "furnace": (1, [
        [("cobblestone", 8)]
    ]),
    "oak_door": (3, [[("oak_planks", 6)]]),
    "spruce_door": (3, [[("spruce_planks", 6)]]),
    "birch_door": (3, [[("birch_planks", 6)]]),
    "jungle_door": (3, [[("jungle_planks", 6)]]),
    "acacia_door": (3, [[("acacia_planks", 6)]]),
    "dark_oak_door": (3, [[("dark_oak_planks", 6)]]),
    "mangrove_door": (3, [[("mangrove_planks", 6)]]),
    "cherry_door": (3, [[("cherry_planks", 6)]]),
    "pale_oak_door": (3, [[("pale_oak_planks", 6)]]),
    "warped_door": (3, [[("warped_planks", 6)]]),
    "crimson_door": (3, [[("crimson_planks", 6)]]),
    "oak_planks": (4, [[("oak_log", 1)], [("oak_wood", 1)]]),
    "spruce_planks": (4, [[("spruce_log", 1)], [("spruce_wood", 1)]]),
    "birch_planks": (4, [[("birch_log", 1)], [("birch_wood", 1)]]),
    "jungle_planks": (4, [[("jungle_log", 1)], [("jungle_wood", 1)]]),
    "acacia_planks": (4, [[("acacia_log", 1)], [("acacia_wood", 1)]]),
    "dark_oak_planks": (4, [[("dark_oak_log", 1)], [("dark_oak_wood", 1)]]),
    "mangrove_planks": (4, [[("mangrove_log", 1)], [("mangrove_wood", 1)]]),
    "cherry_planks": (4, [[("cherry_log", 1)], [("cherry_wood", 1)]]),
    "pale_oak_planks": (4, [[("pale_oak_log", 1)], [("pale_oak_wood", 1)]]),
    "warped_planks": (4, [[("warped_stem", 1)]]),
    "crimson_planks": (4, [[("crimson_stem", 1)]]),
    "stick": (4, [
        [("oak_planks", 2)], [("spruce_planks", 2)], [("birch_planks", 2)], 
        [("jungle_planks", 2)], [("acacia_planks", 2)], [("dark_oak_planks", 2)], 
        [("mangrove_planks", 2)], [("cherry_planks", 2)], [("pale_oak_planks", 2)],
        [("warped_planks", 2)], [("crimson_planks", 2)]
    ]),
    "torch": (4, [
        [("coal", 1), ("stick", 1)], [("charcoal", 1), ("stick", 1)]
    ]),
}


def craft_direct(agent: Any, item_name: str, quantity: int = 1, crafting_table_loc: Any = None) -> bool:
    """
    Craft an item directly if the ingredients are present.
    """
    try:
        success = agent.bot.craft(item_name, quantity, crafting_table_loc)
        if not success:
            display_name = item_name.replace("_", " ")
            agent.bot.chat(f"No recipe found for {display_name}.")
            return False
        return True
    except Exception as e:
        agent.bot.chat(f"Craft failed: {e}")
        return False


def craft_tree(agent: Any, item_name: str, quantity: int = 1, crafting_table_loc: Any = None) -> bool:
    """
    Crafts an item, recursively crafting prerequisite ingredients if necessary.
    """
    # 1. Check if we already have the required quantity in our inventory
    if ui.has_item(agent, item_name, quantity):
        return True

    # 2. Check if the item is craftable according to our recipes
    if item_name not in RECIPES:
        return False  # Raw/uncraftable material (e.g. logs, cobblestone)

    current_qty = agent.bot.get_inventory().get(item_name, 0)
    needed = quantity - current_qty
    yield_qty, alternatives = RECIPES[item_name]

    # Calculate how many crafting operations we need
    crafts_needed = math.ceil(needed / yield_qty)

    # Try each alternative set of ingredients
    for option in alternatives:
        can_craft_option = True
        
        # Check if we can satisfy the requirements for this option
        for ing_name, ing_qty in option:
            total_ing_needed = ing_qty * crafts_needed
            # Recursively ensure we have the required ingredients
            if not craft_tree(agent, ing_name, total_ing_needed, crafting_table_loc):
                can_craft_option = False
                break
        
        if can_craft_option:
            # We successfully satisfied all prerequisite ingredients! Craft it.
            return craft_direct(agent, item_name, crafts_needed, crafting_table_loc)

    return False


def craft_any_door(agent: Any, quantity: int = 1) -> Optional[str]:
    """
    Finds a nearby crafting table, walks to it, and attempts to craft any door type.
    """
    crafting_table_loc = agent.memory.retrieve("crafting_area")
    if not crafting_table_loc:
        print("Crafting failed: No crafting area location stored in memory.")
        return None

    um.move_absolute(agent, crafting_table_loc)

    # Locate crafting table block using memory first, falling back to block search
    crafting_table_pos = agent.memory.retrieve("crafting_table_position")
    if crafting_table_pos:
        Vec3Class = get_vec3()
        crafting_table_pos = Vec3Class(math.floor(crafting_table_pos.x), math.floor(crafting_table_pos.y), math.floor(crafting_table_pos.z))
    else:
        crafting_table_pos = agent.bot.find_block("crafting_table", max_distance=5)

    if not crafting_table_pos:
        print("Crafting failed: I cannot find a crafting table nearby.")
        return None

    print(f"Found a crafting table at {crafting_table_pos}!")

    # Standard wooden doors
    door_types = ui.door_types

    for door_name in door_types:
        print(f"Found materials for a {door_name}. Attempting to craft...")
        if craft_tree(agent, door_name, quantity, crafting_table_pos):
            print(f"Success! Crafted {quantity} {door_name}(s).")
            return door_name

    print("Crafting failed: I don't have enough matching planks or logs of any wood type.")
    return None
