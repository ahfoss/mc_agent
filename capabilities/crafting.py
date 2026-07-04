from javascript import require
import capabilities.items as ui
import capabilities.movement as um


def craft_direct(agent, item_name, quantity=1, crafting_table_loc=None) -> bool:
    """
    Craft an item directly if the ingredients are present.
    """
    mcdata = require('minecraft-data')(agent.bot.version)
    item_id = mcdata.itemsByName[item_name].id
    
    ct_recipes = agent.bot.recipesFor(item_id, None, quantity, crafting_table_loc)
    print(f"Recipes: {ct_recipes}")
    print(f"Found {getattr(ct_recipes, 'length', None)} recipes for crafting table.")
    
    if not ct_recipes:
        agent.bot.chat("No recipe found for crafting table.")
        return False
    else:
        try:
            agent.bot.craft(ct_recipes[0], quantity, crafting_table_loc)
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
    mcdata = require('minecraft-data')(agent.bot.version)

    # Navigate to crafting area if it is set, otherwise break
    crafting_table_loc = agent.memory.retrieve("crafting_area")
    if not crafting_table_loc:
        print("Crafting failed: No crafting area location stored in memory.")
        return None

    um.move_absolute(agent, crafting_table_loc)

    # Locate crafting table block
    crafting_table_id = mcdata.blocksByName['crafting_table'].id
    crafting_table_block = agent.bot.findBlock({
        'matching': crafting_table_id,
        'maxDistance': 5
    })

    if not crafting_table_block:
        print("Crafting failed: I cannot find a crafting table nearby.")
        return None

    print(f"Found a crafting table at {crafting_table_block.position}!")

    # Standard wooden doors
    door_types = ui.door_types

    for door_name in door_types:
        if door_name not in mcdata.itemsByName:
            continue
            
        item_data = mcdata.itemsByName[door_name]
        recipes = agent.bot.recipesFor(item_data.id, None, quantity, crafting_table_block)
        recipe_count = getattr(recipes, "length", 0)
        
        if recipe_count > 0:
            print(f"Found materials for a {door_name}. Attempting to craft...")
            try:
                agent.bot.craft(recipes[0], quantity, crafting_table_block)
                print(f"Success! Crafted {quantity} {door_name}(s).")
                return door_name
            except Exception as err:
                print(f"Failed to craft {door_name}: {err}")

    print("Crafting failed: I don't have 6 matching planks of any wood type.")
    return None
