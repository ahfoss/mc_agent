import math
import asyncio
from typing import Any
from core.bot import Vec3
import capabilities.movement as um

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

    Vec3Class = Vec3
    
    while True:
        pos = agent.bot.position
        start_pos = Vec3Class(math.floor(pos.x), math.floor(pos.y), math.floor(pos.z))
        
        # Dig 1x2 tunnel block directly in front
        front_lower = start_pos + (1, 0, 0)
        front_upper = start_pos + (1, 1, 0)
        
        await agent.bot.dig(front_upper)
        await agent.bot.dig(front_lower)
        
        # Short sleep to let gravel/sand fall and clear
        await asyncio.sleep(0.2)
        await agent.bot.dig(front_upper)
        await agent.bot.dig(front_lower)
        
        target_step = start_pos + (1.5, 0.0, 0.5)
        try:
            await agent.bot.move_to(target_step, range_val=0)
        except Exception:
            # Retry digging in case of blockage
            await agent.bot.dig(front_upper)
            await agent.bot.dig(front_lower)
            try:
                await agent.bot.move_to(target_step, range_val=0)
            except Exception:
                pass
                
        # Scan for iron ore nearby
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
                
            await agent.bot.chat(f"Iron ore vein found at {ore_pos}!")
            try:
                await agent.bot.move_to(ore_pos, range_val=2)
                
                # Equip pickaxe
                tool_to_equip = None
                for tool in ["iron_pickaxe", "stone_pickaxe", "diamond_pickaxe", "golden_pickaxe", "wooden_pickaxe"]:
                    if agent.bot.get_inventory().get(tool, 0) > 0:
                        tool_to_equip = tool
                        break
                if tool_to_equip:
                    await agent.bot.equip(tool_to_equip, "hand")
                    
                await agent.bot.dig(ore_pos)
                vein_dig_count += 1
                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"Error mining ore block: {e}")
                break
                
        if vein_dig_count > 0:
            try:
                await agent.bot.move_to(target_step, range_val=0)
            except Exception:
                pass
                
        await asyncio.sleep(0.5)
