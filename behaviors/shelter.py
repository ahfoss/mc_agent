import asyncio
import time
import math
from typing import Any
from core.memory import get_vec3
import capabilities.items as ui
import capabilities.movement as um
import capabilities.crafting as uc
import capabilities.construction as ucon
import behaviors.mining as bm

async def build_shelter(agent: Any, depth: int = 8) -> None:
    """
    Builds a simple underground shelter by digging down and creating a chamber.
    """
    agent.memory.store("shelter_location", agent.bot.position)
    await bm.dig_staircase_down(agent, depth)
    await bm.dig_chamber(agent, 8, 8)


async def furnish_shelter1(agent: Any) -> None:
    """
    Furnishes the shelter with basic items: crafting table, a door, a furnace, and two chests.
    Skips items that are already placed in their target coordinates, and skips crafting if already in inventory.
    """
    await agent.bot.chat("Checking shelter furnishing requirements.")
    
    # Retrieve shelter coordinates from memory
    shelter_location = agent.memory.retrieve("shelter_location")
    if not shelter_location:
        await agent.bot.chat("Coordinates not found in memory. Have you already built the shelter?")
        return

    # Floor coordinates to integer values to avoid pathfinding errors with floating offsets
    Vec3Class = get_vec3()
    shelter_location = Vec3Class(math.floor(shelter_location.x), math.floor(shelter_location.y), math.floor(shelter_location.z))

    # Navigate to shelter plus offset inside
    print(f"{shelter_location=}")
    target_pos = shelter_location + (9, -8, 5)
    print(f"{target_pos=}")
    await um.move_absolute(agent, target_pos)

    # 1. Determine target block locations
    pos = agent.bot.position
    floored_pos = Vec3Class(math.floor(pos.x), math.floor(pos.y), math.floor(pos.z))
    
    # Stored crafting table position or fallback
    crafting_table_pos = agent.memory.retrieve("crafting_table_position")
    expected_y = shelter_location.y - 8
    if crafting_table_pos:
        crafting_table_pos = Vec3Class(math.floor(crafting_table_pos.x), math.floor(crafting_table_pos.y), math.floor(crafting_table_pos.z))
        print(f"[DIAGNOSTIC] Stored crafting table Y: {crafting_table_pos.y}, expected Y: {expected_y} (shelter_location: {shelter_location})")
        if crafting_table_pos.y != expected_y:
            print(f"[DIAGNOSTIC] Y-level mismatch! Discarding stale memory crafting table position.")
            await agent.bot.chat(f"Discarding stale crafting table position at Y={crafting_table_pos.y}")
            agent.memory.delete("crafting_table_position")
            agent.memory.delete("crafting_area")
            agent.memory.delete("adjacent_crafting_table")
            crafting_table_pos = None

    if not crafting_table_pos:
        # Fallback to finding one nearby in the world
        found_pos = await agent.bot.find_block("crafting_table", max_distance=10)
        if found_pos:
            found_pos = Vec3Class(math.floor(found_pos.x), math.floor(found_pos.y), math.floor(found_pos.z))
            print(f"[DIAGNOSTIC] Found crafting table in world at: {found_pos}")
            if found_pos.y == expected_y:
                crafting_table_pos = found_pos
                agent.memory.store("crafting_table_position", found_pos)
                agent.memory.store("crafting_area", found_pos - (0, 0, 1))
                agent.memory.store("adjacent_crafting_table", found_pos - (0, 0, 1))
            else:
                print(f"[DIAGNOSTIC] Found crafting table at wrong Y-level: {found_pos.y}. Ignoring.")
        
        if not crafting_table_pos:
            crafting_table_pos = floored_pos + (0, 0, 1)
            print(f"[DIAGNOSTIC] No valid crafting table found. Fallback placement coordinate: {crafting_table_pos}")

    door_pos = floored_pos + (-2, 2, -5)
    furnace_pos = crafting_table_pos + (1, 0, 0)
    chest_1_pos = crafting_table_pos + (4, 0, 0)
    chest_2_pos = crafting_table_pos + (5, 0, 0)

    print(f"[DIAGNOSTIC] Target positions: door={door_pos}, ct={crafting_table_pos}, furnace={furnace_pos}")

    # 2. Query block presence in the world
    block_ct = await agent.bot.get_block(crafting_table_pos)
    block_door = await agent.bot.get_block(door_pos)
    block_furnace = await agent.bot.get_block(furnace_pos)
    block_chest1 = await agent.bot.get_block(chest_1_pos)
    block_chest2 = await agent.bot.get_block(chest_2_pos)

    ct_built = (block_ct is not None and block_ct.name == "crafting_table")
    door_built = (block_door is not None and block_door.name.endswith("_door"))
    furnace_built = (block_furnace is not None and block_furnace.name == "furnace")
    chest_1_built = (block_chest1 is not None and block_chest1.name == "chest")
    chest_2_built = (block_chest2 is not None and block_chest2.name == "chest")

    print(f"[DIAGNOSTIC] World checks: ct_built={ct_built} ({block_ct.name if block_ct else 'None'}), door_built={door_built} ({block_door.name if block_door else 'None'})")

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
        await agent.bot.chat("I still need: " + ", ".join(still_need))
        return

    # 4. Craft & Place crafting table if missing
    if not ct_built:
        if not ui.has_item(agent, "crafting_table"):
            if not await uc.craft_tree(agent, "crafting_table"):
                await agent.bot.chat("Crafting table crafting failed.")
                return
        
        await ucon.place_block_on_ground_relative_to_self(agent, "crafting_table", 0, -1, 1)
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
            door_in_inv = await uc.craft_any_door(agent, quantity=1)
            
        if door_in_inv:
            print(f"[DIAGNOSTIC] Bot position before door placement: {agent.bot.position}")
            # Move away to avoid getting stuck or placing it directly on self
            await um.move_relative_to_self(agent, 0, 0, -5)
            await um.move_relative_to_self(agent, -1, 0, 0)
            print(f"[DIAGNOSTIC] Bot position after moving relative for door: {agent.bot.position}")
            await ucon.place_block_on_ground_relative_to_self(agent, door_in_inv, -1, 0, 0)
            placed_door_block = await agent.bot.get_block(door_pos)
            print(f"[DIAGNOSTIC] Block at door_pos ({door_pos}) after placement: {placed_door_block.name if placed_door_block else 'None'}")
        else:
            await agent.bot.chat("Could not craft a door.")

    # Walk back to the crafting table area to be in range
    adjacent_spot = agent.memory.retrieve("adjacent_crafting_table") or floored_pos
    print(f"[DIAGNOSTIC] Walking back to adjacent crafting table spot: {adjacent_spot}")
    await um.move_absolute(agent, adjacent_spot)

    # 6. Craft & Place furnace if missing
    if not furnace_built:
        if not ui.has_item(agent, "furnace"):
            if not await uc.craft_tree(agent, "furnace", quantity=1, crafting_table_loc=crafting_table_pos):
                await agent.bot.chat("Furnace crafting failed.")
                return
        
        await ucon.place_block_relative_to_block(agent, "furnace", crafting_table_pos, 1, 0, 0)

    # 7. Craft & Place chests if missing
    if chests_to_place > 0:
        chests_needed_to_craft = max(0, chests_to_place - ui.get_item_count(agent, "chest"))
        if chests_needed_to_craft > 0:
            if not await uc.craft_tree(agent, "chest", quantity=chests_needed_to_craft, crafting_table_loc=crafting_table_pos):
                await agent.bot.chat("Chest crafting failed.")
                return

        # Walk close to the chest placement coordinates first (e.g. +3, 0, 0 from table)
        target_standing_pos = crafting_table_pos + (4, 0, -1)
        await um.move_absolute(agent, target_standing_pos)
        if not chest_1_built:
            await ucon.place_block_relative_to_block(agent, "chest", crafting_table_pos, 4, 0, 0)
            await asyncio.sleep(1.0)
            
        target_standing_pos = crafting_table_pos + (5, 0, -1)
        await um.move_absolute(agent, target_standing_pos)
        if not chest_2_built:
            await ucon.place_block_relative_to_block(agent, "chest", crafting_table_pos, 5, 0, 0)

    # Move back to crafting/furnace area
    adjacent_spot = agent.memory.retrieve("adjacent_crafting_table") or floored_pos
    await um.move_absolute(agent, adjacent_spot)

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
            await agent.bot.chat(f"Smelting 1 charcoal using {log_name} and {plank_name}...")
            furnace_pos = crafting_table_pos + (1, 0, 0)
            try:
                await agent.bot.send_command("smelt", {
                    "furnace_x": int(furnace_pos.x),
                    "furnace_y": int(furnace_pos.y),
                    "furnace_z": int(furnace_pos.z),
                    "input_item_name": log_name,
                    "fuel_item_name": plank_name,
                    "input_count": 1,
                    "fuel_count": 1
                }, timeout=75.0)
            except Exception as e:
                await agent.bot.chat(f"Smelting 1 charcoal failed: {e}")
        else:
            await agent.bot.chat("Missing logs or planks to smelt 1 charcoal.")

    # Make 3 charcoal by burning 3 logs with charcoal
    if ui.get_item_count(agent, "charcoal") < 3:
        log_name = None
        for item_name in agent.bot.get_inventory():
            if item_name.endswith("_log") or item_name.endswith("_stem"):
                if ui.get_item_count(agent, item_name) > 0:
                    log_name = item_name
                    break

        if log_name and ui.has_item(agent, "charcoal", 1):
            await agent.bot.chat(f"Smelting 3 charcoal using {log_name} and charcoal fuel...")
            furnace_pos = crafting_table_pos + (1, 0, 0)
            try:
                await agent.bot.send_command("smelt", {
                    "furnace_x": int(furnace_pos.x),
                    "furnace_y": int(furnace_pos.y),
                    "furnace_z": int(furnace_pos.z),
                    "input_item_name": log_name,
                    "fuel_item_name": "charcoal",
                    "input_count": 3,
                    "fuel_count": 1
                }, timeout=75.0)
            except Exception as e:
                await agent.bot.chat(f"Smelting 3 charcoal failed: {e}")
        else:
            await agent.bot.chat("Missing logs or charcoal fuel to smelt 3 charcoal.")

    # Craft three torches
    if ui.get_item_count(agent, "torch") < 3:
        await agent.bot.chat("Attempting to craft three torches recursively...")
        if not await uc.craft_tree(agent, "torch", quantity=3, crafting_table_loc=crafting_table_pos):
            await agent.bot.chat("Failed to craft torches recursively.")

    # Place three torches
    adjacent_table = agent.memory.retrieve("adjacent_crafting_table")
    if adjacent_table:
        adjacent_table = Vec3Class(math.floor(adjacent_table.x), math.floor(adjacent_table.y), math.floor(adjacent_table.z))
        
        torch_offsets = [
            # Block location, block face to use.
            ((1, 2, 2), (0, 0, -1)),
            ((7, 2, -2), (-1, 0, 0)),
            ((1, 2, -5), (0, 0, 1)),
        ]
        for torch_offset, iface in torch_offsets:
            torch_abs = adjacent_table + torch_offset
            block = await agent.bot.get_block(torch_abs)
            if block is None or "torch" not in block.name:
                try:
                    await agent.bot.move_to(torch_abs, range_val=3)
                except Exception as e:
                    print(f"Pathfinding to torch at {torch_abs} failed: {e}")
                if ui.has_item(agent, "torch", 1):
                    await agent.bot.chat(f"Placing torch at {torch_abs}...")
                    await agent.bot.place_block("torch", torch_abs - iface, Vec3Class(0,0,0) + iface)
                else:
                    await agent.bot.chat("No torches left in inventory to place.")

    await agent.bot.chat("Shelter furnishing sequence completed.")
