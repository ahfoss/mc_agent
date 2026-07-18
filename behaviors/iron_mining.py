import math
import asyncio
from typing import Any
from core.bot import Vec3
import capabilities.movement as um

async def equip_pickaxe(agent: Any) -> bool:
    tool_to_equip = None
    inv = agent.bot.get_inventory()
    for tool in ["iron_pickaxe", "stone_pickaxe", "diamond_pickaxe", "golden_pickaxe", "wooden_pickaxe"]:
        if inv.get(tool, 0) > 0:
            tool_to_equip = tool
            break
    if tool_to_equip:
        await agent.bot.equip(tool_to_equip, "hand")
        return True
    return False

async def dig_block_with_falling_check(agent: Any, pos: Vec3) -> None:
    await equip_pickaxe(agent)
    try:
        await agent.bot.dig(pos)
    except Exception as e:
        print(f"Error digging at {pos}: {e}")
    await asyncio.sleep(0.2)
    # If gravel/sand fell into the block, dig it again
    try:
        block = await agent.bot.get_block(pos)
    except TypeError:
        block = None

    if block and block.name in ["gravel", "sand"]:
        try:
            await agent.bot.dig(pos)
        except Exception:
            pass

async def mine_vein(agent: Any, return_pos: Vec3) -> None:
    vein_dig_count = 0
    while True:
        ore_pos = None
        for ore_type in ["iron_ore", "deepslate_iron_ore"]:
            found = await agent.bot.find_block(ore_type, max_distance=6)
            if found:
                ore_pos = found
                break
        if not ore_pos:
            break
            
        await agent.bot.chat(f"Iron ore vein found at {ore_pos}! Mining...")
        try:
            await agent.bot.move_to(ore_pos, range_val=1, can_dig=True)
            await equip_pickaxe(agent)
            await agent.bot.dig(ore_pos)
            vein_dig_count += 1
            await asyncio.sleep(0.5)
            # Walk directly onto the mined block coordinates to trigger pickup
            try:
                await agent.bot.move_to(ore_pos, range_val=1)
                await asyncio.sleep(0.2)
            except Exception:
                pass
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"Error mining ore block: {e}")
            break
            
    if vein_dig_count > 0:
        # Scan and collect all nearby raw iron drops in the area
        for _ in range(3):
            try:
                nearby = await agent.bot.get_nearby_items(max_distance=8)
            except TypeError:
                nearby = []
            raw_irons = [item for item in nearby if item["name"] == "raw_iron"]
            if raw_irons:
                raw_irons.sort(key=lambda x: x.get("distance", 999))
                closest = raw_irons[0]
                item_pos = Vec3(closest["position"]["x"], closest["position"]["y"], closest["position"]["z"])
                try:
                    await agent.bot.move_to(item_pos, range_val=1)
                    await asyncio.sleep(0.5)
                except Exception:
                    pass
            else:
                break

        try:
            await agent.bot.move_to(return_pos, range_val=0)
        except Exception:
            pass

async def dig_branch(agent: Any, start_pos: Vec3, dx: int, dz: int, length: int) -> None:
    await agent.bot.chat(f"Digging lateral branch tunnel for {length} blocks...")
    curr_pos = start_pos
    
    for i in range(length):
        next_floor = curr_pos + Vec3(dx, 0, dz)
        next_head = curr_pos + Vec3(dx, 1, dz)
        
        await dig_block_with_falling_check(agent, next_head)
        await dig_block_with_falling_check(agent, next_floor)
        
        target_pos = Vec3(curr_pos.x + dx + 0.5, curr_pos.y, curr_pos.z + dz + 0.5)
        try:
            await agent.bot.move_to(target_pos, range_val=0)
        except Exception:
            await dig_block_with_falling_check(agent, next_head)
            await dig_block_with_falling_check(agent, next_floor)
            try:
                await agent.bot.move_to(target_pos, range_val=0)
            except Exception:
                pass
                
        curr_pos = Vec3(math.floor(agent.bot.position.x), math.floor(agent.bot.position.y), math.floor(agent.bot.position.z))
        await mine_vein(agent, target_pos)
        
    # Return to the main tunnel branch point
    await agent.bot.chat("Returning to main tunnel...")
    try:
        await agent.bot.move_to(Vec3(start_pos.x + 0.5, start_pos.y, start_pos.z + 0.5), range_val=0)
    except Exception:
        pass

async def staircase_to_y(agent: Any, target_y: int) -> None:
    await agent.bot.chat(f"Staircasing to Y={target_y}...")
    dx, dz = 1, 0 # Main direction of staircase (+X)
    
    while True:
        pos = agent.bot.position
        curr_y = math.floor(pos.y)
        if curr_y == target_y:
            await agent.bot.chat(f"Reached target level Y={target_y}!")
            break
            
        curr_x = math.floor(pos.x)
        curr_z = math.floor(pos.z)
        
        if curr_y > target_y:
            # Staircase DOWN
            target_floor = Vec3(curr_x + dx, curr_y - 1, curr_z + dz)
            target_head = Vec3(curr_x + dx, curr_y, curr_z + dz)
            target_ceil = Vec3(curr_x + dx, curr_y + 1, curr_z + dz)
            
            await dig_block_with_falling_check(agent, target_ceil)
            await dig_block_with_falling_check(agent, target_head)
            await dig_block_with_falling_check(agent, target_floor)
            
            target_pos = Vec3(curr_x + dx + 0.5, curr_y - 1, curr_z + dz + 0.5)
            try:
                await agent.bot.move_to(target_pos, range_val=0)
            except Exception:
                await dig_block_with_falling_check(agent, target_head)
                await dig_block_with_falling_check(agent, target_floor)
                try:
                    await agent.bot.move_to(target_pos, range_val=0)
                except Exception:
                    pass
        else:
            # Staircase UP
            curr_ceil = Vec3(curr_x, curr_y + 2, curr_z)
            target_head = Vec3(curr_x + dx, curr_y + 2, curr_z + dz)
            target_floor = Vec3(curr_x + dx, curr_y + 1, curr_z + dz)
            
            await dig_block_with_falling_check(agent, curr_ceil)
            await dig_block_with_falling_check(agent, target_head)
            await dig_block_with_falling_check(agent, target_floor)
            
            target_pos = Vec3(curr_x + dx + 0.5, curr_y + 1, curr_z + dz + 0.5)
            try:
                await agent.bot.move_to(target_pos, range_val=0)
            except Exception:
                await dig_block_with_falling_check(agent, target_head)
                await dig_block_with_falling_check(agent, target_floor)
                try:
                    await agent.bot.move_to(target_pos, range_val=0)
                except Exception:
                    pass
                    
        # Check for iron ore after each step
        step_pos = agent.bot.position
        await mine_vein(agent, Vec3(math.floor(step_pos.x) + 0.5, math.floor(step_pos.y), math.floor(step_pos.z) + 0.5))

async def mine_iron(agent: Any) -> None:
    await agent.bot.chat("Starting strip mining for iron...")
    
    # Stone pickaxe or better check
    has_good_pickaxe = False
    for tool in ["iron_pickaxe", "stone_pickaxe", "diamond_pickaxe", "golden_pickaxe"]:
        if agent.bot.get_inventory().get(tool, 0) > 0:
            has_good_pickaxe = True
            break
            
    if not has_good_pickaxe:
        await agent.bot.chat("Warning: I don't have a stone pickaxe or better in my inventory.")

    # Step 1: Staircase to Y=16
    await staircase_to_y(agent, 16)
    
    # Step 2: Main branch mining loop at Y=16
    step_count = 0
    dx, dz = 1, 0 # Main tunnel along +X
    
    while True:
        pos = agent.bot.position
        curr_x = math.floor(pos.x)
        curr_y = math.floor(pos.y)
        curr_z = math.floor(pos.z)
        
        start_pos = Vec3(curr_x, curr_y, curr_z)
        
        # Dig 1 section of main tunnel (height 2)
        next_floor = start_pos + Vec3(dx, 0, dz)
        next_head = start_pos + Vec3(dx, 1, dz)
        
        await dig_block_with_falling_check(agent, next_head)
        await dig_block_with_falling_check(agent, next_floor)
        
        target_step = Vec3(start_pos.x + dx + 0.5, start_pos.y, start_pos.z + dz + 0.5)
        try:
            await agent.bot.move_to(target_step, range_val=0)
        except Exception:
            await dig_block_with_falling_check(agent, next_head)
            await dig_block_with_falling_check(agent, next_floor)
            try:
                await agent.bot.move_to(target_step, range_val=0)
            except Exception:
                pass
                
        # Main tunnel position updated
        curr_pos = Vec3(math.floor(agent.bot.position.x), math.floor(agent.bot.position.y), math.floor(agent.bot.position.z))
        await mine_vein(agent, target_step)
        
        step_count += 1
        
        # Lateral branches every 4 steps
        if step_count % 4 == 0:
            # Dig left branch (90 degrees to +X is -Z)
            await dig_branch(agent, curr_pos, 0, -1, 6)
            # Dig right branch (90 degrees to +X is +Z)
            await dig_branch(agent, curr_pos, 0, 1, 6)
            
        await asyncio.sleep(0.5)
