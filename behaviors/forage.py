import math
import asyncio
from typing import Any
from core.bot import Vec3
import capabilities.items as ui
import capabilities.fighting as uf

async def forage_food(agent: Any, amount: int) -> None:
    await agent.bot.chat(f"Foraging for {amount} food items...")
    
    start_food = ui.get_item_count(agent, ui.FOOD_ITEMS)
    target = start_food + amount
    
    while ui.get_item_count(agent, ui.FOOD_ITEMS) < target:
        found_food = None
        # Incremental search distance
        for dist in [32, 64, 128, 256]:
            # 1. Search for food blocks to harvest (melon)
            for block_type in ["melon", "sweet_berry_bush"]:
                found_block = await agent.bot.find_block(block_type, max_distance=dist)
                if found_block:
                    found_food = {"type": "block", "data": found_block, "name": block_type}
                    break
            if found_food:
                break

            # 2. Search for passive mobs to hunt
            for mob in ui.food_mobs:
                found_mob = await agent.bot.find_entity(mob, max_distance=dist)
                if found_mob:
                    found_food = {"type": "mob", "data": found_mob}
                    break
            if found_food:
                break
                
        if not found_food:
            await agent.bot.chat("No food sources (mobs or crops) found within 256 blocks.")
            break
            
        if found_food["type"] == "mob":
            mob = found_food["data"]
            mob_name = mob["name"]
            mob_id = mob["id"]
            pos = mob["position"]
            await agent.bot.chat(f"Foraging: Found a {mob_name}! Hunting...")
            success = await uf.hunt_mob(agent, mob_id, mob_name, pos)
            if not success:
                await asyncio.sleep(1.0)
                
        elif found_food["type"] == "block":
            block_pos = found_food["data"]
            block_name = found_food["name"]
            await agent.bot.chat(f"Foraging: Found a {block_name} block! Harvesting...")
            try:
                await agent.bot.move_to(block_pos, range_val=2)
                
                tool_to_equip = None
                if block_name == "melon":
                    for axe in ui.axes:
                        if agent.bot.get_inventory().get(axe, 0) > 0:
                            tool_to_equip = axe
                            break
                if tool_to_equip:
                    await agent.bot.equip(tool_to_equip, "hand")
                    
                await agent.bot.dig(block_pos)
                await agent.bot.move_to(block_pos, range_val=1)
                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"Error harvesting block: {e}")
                await asyncio.sleep(1.0)
                
    await agent.bot.chat("Finished foraging. Returning to shelter...")
    
    shelter_location = agent.memory.retrieve("shelter_location")
    if not shelter_location:
        await agent.bot.chat("Shelter location not found in memory. Cannot deposit food.")
        return
        
    shelter_location = Vec3(math.floor(shelter_location.x), math.floor(shelter_location.y), math.floor(shelter_location.z))
    target_pos = shelter_location + (9, -8, 5)
    
    try:
        await agent.bot.move_to(target_pos, range_val=1)
        
        ct_pos = agent.memory.retrieve("crafting_table_position")
        if ct_pos:
            ct_pos = Vec3(math.floor(ct_pos.x), math.floor(ct_pos.y), math.floor(ct_pos.z))
            chest_pos = ct_pos + (4, 0, 0)
        else:
            chest_pos = await agent.bot.find_block("chest", max_distance=12)
            
        if not chest_pos:
            await agent.bot.chat("No chest found inside shelter to deposit food.")
            return
            
        await agent.bot.move_to(chest_pos, range_val=2)
        
        for item in ui.FOOD_ITEMS:
            count = agent.bot.get_inventory().get(item, 0)
            if count > 0:
                await agent.bot.chat(f"Depositing {count} {item} into chest...")
                await agent.bot.deposit(chest_pos, item, count)
                await asyncio.sleep(0.5)
        await agent.bot.chat("Foraged food deposited successfully.")
    except asyncio.CancelledError:
        raise
    except Exception as e:
        await agent.bot.chat(f"Failed to deposit food: {e}")
