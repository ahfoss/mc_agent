from javascript import require
import util.items as ui
import util.movement as um

def craft_direct(agent, item_name, quantity=1, crafting_table_loc=None) -> bool:
    """
    Craft an item unless the ingredients aren't present.
    """
    mcdata = require('minecraft-data')(agent.bot.version)
    item_id = mcdata.itemsByName[item_name].id
    # recipesFor(item_id, metadata, #results to require, crafting table location.)
    ct_recipes = agent.bot.recipesFor(item_id, None, quantity, crafting_table_loc)
    print(f"Recipes: {ct_recipes}")
    print(f"Found {getattr(ct_recipes, "length", None)} recipes for crafting table.")
    if not ct_recipes:
        agent.bot.chat("No recipe found for crafting table.")
    else:
        try:
            agent.bot.craft(ct_recipes[0], 1, crafting_table_loc)
        except Exception as e:
            agent.bot.chat(f"Craft failed: {e}")

def craft_tree(agent, crafting_list):
    """
    Craft an item, and craft requisite items hierarchically if necessary.
    """
    if craft_direct(agent, crafting_list):
        return
    else:
        pass
        # Get requirements
        # Identify which aren't in memory
        # Craft them if necessary, calling craft_tree recursively.
        # return False if can't craft something, and gives all missing blocks.


# Assuming 'bot' is already initialized
#minecraft_data_module = require('minecraft-data')
#mcdata = minecraft_data_module(bot.version)

def craft_any_door(agent, quantity = 1):
    mcdata = require('minecraft-data')(agent.bot.version)

    # Navigate to crafting area if it is set, otherwise break
    crafting_table_loc = agent.memory.retrieve("crafting_area")
    um.move_absolute(agent, crafting_table_loc)

    # Locate crafting table
    # Get the numeric ID for a crafting table block
    crafting_table_id = mcdata.blocksByName['crafting_table'].id
    
    # Search the world for this block
    crafting_table_block = agent.bot.findBlock({
        'matching': crafting_table_id,
        'maxDistance': 5 # Search within a 32 block radius
    })

    if not crafting_table_block:
        print("Crafting failed: I cannot find a crafting table nearby.")
        return

    print(f"Found a crafting table at {crafting_table_block.position}!")

    # A list of standard wooden doors in modern Minecraft
    door_types = ui.door_types

    for door_name in door_types:
        # Check if the door exists in this version of Minecraft
        # The bridge allows checking JS object keys using Python's 'in' operator
        if door_name not in mcdata.itemsByName:
            continue
            
        item_data = mcdata.itemsByName[door_name]
        
        # bot.recipesFor(itemId, metadata, count, craftingTable)
        # We pass Python's 'None' to represent JS's 'null' for the metadata argument
        recipes = agent.bot.recipesFor(item_data.id, None, quantity, crafting_table_block)

        # JS arrays have a 'length' property; use getattr to safely read it
        recipe_count = getattr(recipes, "length", 0)
        if recipe_count > 0:
            print(f"Found materials for a {door_name}. Attempting to craft...")
            
            try:
                # The bridge resolves this Promise synchronously, blocking execution
                # until the craft is complete or it fails.
                agent.bot.craft(recipes[0], quantity, crafting_table_block)
                print(f"Success! Crafted {quantity} {door_name}(s).")
                return(door_name)
            except Exception as err:
                print(f"Failed to craft {door_name}: {err}")

    # If the loop finishes without returning, we didn't have materials for any door
    print("Crafting failed: I don't have 6 matching planks of any wood type.")