import capabilities.movement as um
import capabilities.crafting as uc
import capabilities.construction as ucon
import behaviors.mining as bm


def build_shelter(agent):
    """
    Builds a simple underground shelter by digging down and creating a chamber.
    """
    agent.memory.store("shelter_location", agent.bot.entity.position)
    bm.dig_staircase_down(agent, 8)
    bm.dig_chamber(agent, 8, 8)


def furnish_shelter1(agent):
    """
    Furnishes the shelter with basic items: crafting table and a door.
    """
    agent.bot.chat("Furnishing the shelter with basic items.")
    
    # Retrieve shelter coordinates from memory
    shelter_location = agent.memory.retrieve("shelter_location")
    if not shelter_location:
        agent.bot.chat("Coordinates not found in memory. Have you already built the shelter?")
        return

    # Navigate to shelter
    um.move_absolute(agent, shelter_location)
    
    # Move relative inside shelter
    um.move_relative_to_self(agent, 9, -8, 5)
    
    # Craft a crafting table
    uc.craft_direct(agent, "crafting_table")

    # Place the crafting table on ground relative to self
    ucon.place_block_on_ground_relative_to_self(agent, "crafting_table", 0, -1, 1)
    
    # Store crafting table area location
    agent.memory.store("crafting_area", agent.bot.entity.position)

    # Craft door
    door_name = uc.craft_any_door(agent, quantity=1)
    if door_name:
        # Move away to avoid getting stuck or placing it directly on self
        um.move_relative_to_self(agent, 0, 0, -5)
        um.move_relative_to_self(agent, -1, 0, 0)
        # Place door
        ucon.place_block_on_ground_relative_to_self(agent, door_name, -1, 1, 0)
    else:
        agent.bot.chat("Could not craft a door (missing planks).")
