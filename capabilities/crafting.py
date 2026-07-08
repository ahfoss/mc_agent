import capabilities.items as ui
import capabilities.movement as um

def craft_direct(agent, item_name, quantity=1, crafting_table_loc=None) -> bool:
    """
    Craft an item directly if the ingredients are present.
    """
    try:
        success = agent.bot.craft(item_name, quantity, crafting_table_loc)
        if not success:
            agent.bot.chat("No recipe found for crafting table.")
            return False
        return True
    except Exception as e:
        agent.bot.chat(f"Craft failed: {e}")
        return False


def craft_tree(agent, crafting_list):
    """
    Craft an item, and craft requisite items hierarchically if necessary (Stub/WIP).
    """
    if craft_direct(agent, crafting_list):
        return True
    else:
        pass
        return False


def craft_any_door(agent, quantity=1):
    """
    Finds a nearby crafting table, walks to it, and attempts to craft any door type.
    """
    crafting_table_loc = agent.memory.retrieve("crafting_area")
    if not crafting_table_loc:
        print("Crafting failed: No crafting area location stored in memory.")
        return None

    um.move_absolute(agent, crafting_table_loc)

    # Locate crafting table block
    crafting_table_pos = agent.bot.find_block("crafting_table", max_distance=5)

    if not crafting_table_pos:
        print("Crafting failed: I cannot find a crafting table nearby.")
        return None

    print(f"Found a crafting table at {crafting_table_pos}!")

    # Standard wooden doors
    door_types = ui.door_types

    for door_name in door_types:
        print(f"Found materials for a {door_name}. Attempting to craft...")
        try:
            success = agent.bot.craft(door_name, quantity, crafting_table_pos)
            if success:
                print(f"Success! Crafted {quantity} {door_name}(s).")
                return door_name
        except Exception as err:
            print(f"Failed to craft {door_name}: {err}")

    print("Crafting failed: I don't have 6 matching planks of any wood type.")
    return None
