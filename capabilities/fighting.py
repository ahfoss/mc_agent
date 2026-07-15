import asyncio
from typing import Any
from core.bot import Vec3

async def hunt_mob(agent: Any, mob_id: int, mob_name: str, initial_pos: Any) -> bool:
    """
    Approaches, equips a weapon/axe, attacks the mob until it is dead or out of range,
    and walks to its drop location to collect the meat.
    Returns True if successfully hunted, False otherwise.
    """
    mob_pos = Vec3(initial_pos)
    try:
        # 1. Approach the mob
        await agent.bot.move_to(mob_pos, range_val=2)
        
        # 2. Equip the best weapon/tool in inventory
        tool_to_equip = None
        inv = agent.bot.get_inventory()
        for tool in ["iron_sword", "stone_sword", "wooden_sword", "iron_axe", "stone_axe", "wooden_axe"]:
            if inv.get(tool, 0) > 0:
                tool_to_equip = tool
                break
        if tool_to_equip:
            await agent.bot.equip(tool_to_equip, "hand")
            
        # 3. Attack loop
        for _ in range(5):
            # Verify if mob is still alive and nearby
            updated_mob = await agent.bot.find_entity(mob_name, max_distance=20)
            if not updated_mob or updated_mob["id"] != mob_id:
                break
                
            # Update target position and attack
            pos = updated_mob["position"]
            mob_pos = Vec3(pos["x"], pos["y"], pos["z"])
            await agent.bot.move_to(mob_pos, range_val=2)
            await agent.bot.attack(mob_id)
            await asyncio.sleep(0.5)
            
        # 4. Walk to the last known position of the mob to collect drops
        await agent.bot.move_to(mob_pos, range_val=1)
        await asyncio.sleep(1.0) # wait for collection
        return True
    except asyncio.CancelledError:
        raise
    except Exception as e:
        print(f"Error in hunt_mob capability: {e}")
        return False
