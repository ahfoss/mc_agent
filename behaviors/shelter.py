
from _pytest import pytester_assertions
import time
import math
from typing import Any
from core.memory import get_vec3
import capabilities.items as ui
import capabilities.movement as um
import capabilities.crafting as uc
import capabilities.construction as ucon
import behaviors.mining as bm

def build_shelter(agent: Any, depth: int = 8) -> None:
    """
    Builds a simple underground shelter by digging down and creating a chamber.
    """
    agent.memory.store("shelter_location", agent.bot.position)
    bm.dig_staircase_down(agent, depth)
    bm.dig_chamber(agent, 8, 8)


def furnish_shelter1(agent: Any) -> None:
    """
    Furnishes the shelter with basic items: crafting table, a door, a furnace, and two chests.
    Skips items that are already placed in their target coordinates, and skips crafting if already in inventory.
    """
    agent.bot.chat("Checking shelter furnishing requirements.")
    
    # Retrieve shelter coordinates from memory
    shelter_location = agent.memory.retrieve("shelter_location")
    if not shelter_location:
        agent.bot.chat("Coordinates not found in memory. Have you already built the shelter?")
        return

    # Floor coordinates to integer values to avoid pathfinding errors with floating offsets
    Vec3Class = get_vec3()
    shelter_location = Vec3Class(math.floor(shelter_location.x), math.floor(shelter_location.y), math.floor(shelter_location.z))

    # Navigate to shelter plus offset inside
    print(f"{shelter_location=}")
    target_pos = shelter_location + (9, -8, 5)
    print(f"{target_pos=}")
    um.move_absolute(agent, target_pos)

    # 1. Determine target block locations
    pos = agent.bot.position
    Vec3Class = get_vec3()
    floored_pos = Vec3Class(math.floor(pos.x), math.floor(pos.y), math.floor(pos.z))
    
    # Stored crafting table position or fallback
    crafting_table_pos = agent.memory.retrieve("crafting_table_position")
    if crafting_table_pos:
        crafting_table_pos = Vec3Class(math.floor(crafting_table_pos.x), math.floor(crafting_table_pos.y), math.floor(crafting_table_pos.z))
    else:
        # Fallback to finding one nearby in the world
        found_pos = agent.bot.find_block("crafting_table", max_distance=10)
        if found_pos:
            crafting_table_pos = found_pos
            # Update memory to correct position
            agent.memory.store("crafting_table_position", found_pos)
            agent.memory.store("crafting_area", found_pos - (0, 0, 1))
            agent.memory.store("adjacent_crafting_table", found_pos - (0, 0, 1))
        else:
            crafting_table_pos = floored_pos + (0, 0, 1)

    door_pos = floored_pos + (-2, 2, -5)
    furnace_pos = crafting_table_pos + (1, 0, 0)
    chest_1_pos = crafting_table_pos + (4, 0, 0)
    chest_2_pos = crafting_table_pos + (5, 0, 0)

    # 2. Query block presence in the world
    block_ct = agent.bot.get_block(crafting_table_pos)
    block_door = agent.bot.get_block(door_pos)
    block_furnace = agent.bot.get_block(furnace_pos)
    block_chest1 = agent.bot.get_block(chest_1_pos)
    block_chest2 = agent.bot.get_block(chest_2_pos)

    ct_built = (block_ct is not None and block_ct.name == "crafting_table")
    door_built = (block_door is not None and block_door.name.endswith("_door"))
    furnace_built = (block_furnace is not None and block_furnace.name == "furnace")
    chest_1_built = (block_chest1 is not None and block_chest1.name == "chest")
    chest_2_built = (block_chest2 is not None and block_chest2.name == "chest")

    chests_to_place = (0 if chest_1_built else 1) + (0 if chest_2_built else 1)

    # 3. Calculate missing materials
    total_planks = sum(ui.get_item_count(agent, p + "_planks") for p in ["oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove", "cherry", "pale_oak", "warped", "crimson"])
    total_logs = sum(ui.get_item_count(agent, l + "_log") for l in ["oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove", "cherry", "pale_oak"])
    total_logs += sum(ui.get_item_count(agent, s + "_stem") for s in ["warped", "crimson"])
    
    charcoal_have = ui.get_item_count(agent, "charcoal")
    logs_needed_for_smelting = 0
    if charcoal_have < 5:
        if charcoal_have < 1:
            logs_needed_for_smelting = 6
        else:
            logs_needed_for_smelting = 5

    plank_equivalent = total_planks + (max(0, total_logs - logs_needed_for_smelting) * 4)

    planks_needed = 0
    if not ct_built and not ui.has_item(agent, "crafting_table"):
        planks_needed += 4
    if not door_built and not ui.has_any_door(agent):
        planks_needed += 6
    
    chests_in_inv = ui.get_item_count(agent, "chest")
    chests_needed_to_craft = max(0, chests_to_place - chests_in_inv)
    planks_needed += 8 * chests_needed_to_craft

    torches_have = ui.get_item_count(agent, "torch")
    if torches_have < 4:
        sticks_have = ui.get_item_count(agent, "stick")
        if sticks_have < 1:
            planks_needed += 2

    cobble_needed = 0
    if not furnace_built and not ui.has_item(agent, "furnace"):
        cobble_needed += 8

    cobble_have = ui.get_item_count(agent, "cobblestone")
    
    planks_missing = max(0, planks_needed - plank_equivalent)
    cobble_missing = max(0, cobble_needed - cobble_have)
    logs_missing = max(0, logs_needed_for_smelting - total_logs)

    # If ingredients are missing, tell in chat and exit
    if planks_missing > 0 or cobble_missing > 0 or logs_missing > 0:
        still_need = []
        if planks_missing > 0:
            still_need.append(f"{planks_missing} planks")
        if cobble_missing > 0:
            still_need.append(f"{cobble_missing} cobblestone")
        if logs_missing > 0:
            still_need.append(f"{logs_missing} logs")
        agent.bot.chat("I still need: " + ", ".join(still_need))
        return
    # 4. Craft & Place crafting table if missing
    if not ct_built:
        if not ui.has_item(agent, "crafting_table"):
            if not uc.craft_tree(agent, "crafting_table"):
                agent.bot.chat("Crafting table crafting failed.")
                return
        
        ucon.place_block_on_ground_relative_to_self(agent, "crafting_table", 0, -1, 1)
        agent.memory.store("crafting_area", floored_pos)
        agent.memory.store("adjacent_crafting_table", floored_pos)
        agent.memory.store("crafting_table_position", floored_pos + (0, 0, 1))
        crafting_table_pos = floored_pos + (0, 0, 1)

    # 5. Craft & Place door if missing
    if not door_built:
        door_in_inv = None
        for door in ui.door_types:
            if ui.has_item(agent, door, 1):
                door_in_inv = door
                break
        
        if not door_in_inv:
            door_in_inv = uc.craft_any_door(agent, quantity=1)
            
        if door_in_inv:
            # Move away to avoid getting stuck or placing it directly on self
            um.move_relative_to_self(agent, 0, 0, -5)
            um.move_relative_to_self(agent, -1, 0, 0)
            ucon.place_block_on_ground_relative_to_self(agent, door_in_inv, -1, 1, 0)
        else:
            agent.bot.chat("Could not craft a door.")

    # Walk back to the crafting table area to be in range
    adjacent_spot = agent.memory.retrieve("adjacent_crafting_table") or floored_pos
    um.move_absolute(agent, adjacent_spot)

    # 6. Craft & Place furnace if missing
    if not furnace_built:
        if not ui.has_item(agent, "furnace"):
            if not uc.craft_tree(agent, "furnace", quantity=1, crafting_table_loc=crafting_table_pos):
                agent.bot.chat("Furnace crafting failed.")
                return
        
        ucon.place_block_relative_to_block(agent, "furnace", crafting_table_pos, 1, 0, 0)

    # 7. Craft & Place chests if missing
    if chests_to_place > 0:
        chests_needed_to_craft = max(0, chests_to_place - ui.get_item_count(agent, "chest"))
        if chests_needed_to_craft > 0:
            if not uc.craft_tree(agent, "chest", quantity=chests_needed_to_craft, crafting_table_loc=crafting_table_pos):
                agent.bot.chat("Chest crafting failed.")
                return

        # Walk close to the chest placement coordinates first (e.g. +3, 0, 0 from table)
        target_standing_pos = crafting_table_pos + (4, 0, -1)
        um.move_absolute(agent, target_standing_pos)
        if not chest_1_built:
            ucon.place_block_relative_to_block(agent, "chest", crafting_table_pos, 4, 0, 0)
            time.sleep(1.0)
            
        target_standing_pos = crafting_table_pos + (5, 0, -1)
        um.move_absolute(agent, target_standing_pos)
        if not chest_2_built:
            ucon.place_block_relative_to_block(agent, "chest", crafting_table_pos, 5, 0, 0)

    # Move back to crafting/furnace area
    adjacent_spot = agent.memory.retrieve("adjacent_crafting_table") or floored_pos
    um.move_absolute(agent, adjacent_spot)

    # Make 1 charcoal by burning a log with a plank
    if ui.get_item_count(agent, "charcoal") < 1:
        log_name = None
        for item_name in agent.bot.get_inventory():
            if item_name.endswith("_log") or item_name.endswith("_stem"):
                if ui.get_item_count(agent, item_name) > 0:
                    log_name = item_name
                    break
        
        plank_name = None
        for item_name in agent.bot.get_inventory():
            if item_name.endswith("_planks"):
                if ui.get_item_count(agent, item_name) > 0:
                    plank_name = item_name
                    break

        if log_name and plank_name:
            agent.bot.chat(f"Smelting 1 charcoal using {log_name} and {plank_name}...")
            furnace_pos = crafting_table_pos + (1, 0, 0)
            try:
                agent.bot.send_command("smelt", {
                    "furnace_x": int(furnace_pos.x),
                    "furnace_y": int(furnace_pos.y),
                    "furnace_z": int(furnace_pos.z),
                    "input_item_name": log_name,
                    "fuel_item_name": plank_name,
                    "input_count": 1,
                    "fuel_count": 1
                }, timeout=75.0)
            except Exception as e:
                agent.bot.chat(f"Smelting 1 charcoal failed: {e}")
        else:
            agent.bot.chat("Missing logs or planks to smelt 1 charcoal.")

    # Make 5 charcoal by burning 5 logs with charcoal
    if ui.get_item_count(agent, "charcoal") < 5:
        log_name = None
        for item_name in agent.bot.get_inventory():
            if item_name.endswith("_log") or item_name.endswith("_stem"):
                if ui.get_item_count(agent, item_name) > 0:
                    log_name = item_name
                    break

        if log_name and ui.has_item(agent, "charcoal", 1):
            agent.bot.chat(f"Smelting 5 charcoal using {log_name} and charcoal fuel...")
            furnace_pos = crafting_table_pos + (1, 0, 0)
            try:
                agent.bot.send_command("smelt", {
                    "furnace_x": int(furnace_pos.x),
                    "furnace_y": int(furnace_pos.y),
                    "furnace_z": int(furnace_pos.z),
                    "input_item_name": log_name,
                    "fuel_item_name": "charcoal",
                    "input_count": 5,
                    "fuel_count": 1
                }, timeout=75.0)
            except Exception as e:
                agent.bot.chat(f"Smelting 5 charcoal failed: {e}")
        else:
            agent.bot.chat("Missing logs or charcoal fuel to smelt 5 charcoal.")

    # Craft three torches
    if ui.get_item_count(agent, "torch") < 3:
        agent.bot.chat("Attempting to craft three torches recursively...")
        if not uc.craft_tree(agent, "torch", quantity=3, crafting_table_loc=crafting_table_pos):
            agent.bot.chat("Failed to craft torches recursively.")

    # Place three torches
    adjacent_table = agent.memory.retrieve("adjacent_crafting_table")
    if adjacent_table:
        Vec3Class = get_vec3()
        adjacent_table = Vec3Class(math.floor(adjacent_table.x), math.floor(adjacent_table.y), math.floor(adjacent_table.z))
        
        #torch_offsets = [(1, 2, 2), (7, 2, -2), (1, 2, -5)]
        torch_offsets = [
            # Block location, standing location, block face to use.
            ((1, 2, 3), (1, 0, 2), (0, 0, -1)),
            ((8, 2, -2), (7, 0, -2), (-1, 0, 0)),
            ((1, 2, -6), (1, 0, -5), (0, 0, 1)),
        ]
        #for offset in torch_offsets:
        for torch_offset, stand_offset, iface in torch_offsets:
            torch_abs = adjacent_table + torch_offset
            block = agent.bot.get_block(torch_abs)
            if block is None or "torch" not in block.name:
                # Stand near the target position on the floor
                um.move_absolute(agent, adjacent_table + stand_offset)
                
                if ui.has_item(agent, "torch", 1):
                    agent.bot.chat(f"Placing torch at {torch_abs}...")
                    agent.bot.place_block("torch", torch_abs, iface)
                else:
                    agent.bot.chat("No torches left in inventory to place.")

    agent.bot.chat("Shelter furnishing sequence completed.")
