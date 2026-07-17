import asyncio
from typing import Any
from core.bot import Vec3
import capabilities.items as ui

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
        await ui.equip_best_weapon(agent)
            
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
            
        # 4. Walk to last known position first
        try:
            await agent.bot.move_to(mob_pos, range_val=2)
        except Exception:
            pass
            
        # 5. Scan for expected dropped meat and collect it directly
        expected_meat = ui.MOB_TO_MEAT.get(mob_name)
        if expected_meat:
            for _ in range(3): # Try up to 3 times to find and walk to the meat item
                try:
                    nearby_items = await agent.bot.get_nearby_items(max_distance=15)
                except TypeError:
                    nearby_items = []
                target_items = [item for item in nearby_items if item["name"] == expected_meat]
                if target_items:
                    # Sort by distance
                    target_items.sort(key=lambda x: x.get("distance", 999))
                    closest_item = target_items[0]
                    item_pos = Vec3(closest_item["position"]["x"], closest_item["position"]["y"], closest_item["position"]["z"])
                    await agent.bot.chat(f"Collecting dropped {expected_meat}...")
                    try:
                        await agent.bot.move_to(item_pos, range_val=1)
                        await asyncio.sleep(0.5)
                    except Exception:
                        pass
                else:
                    break
        else:
            # Fallback to last known position
            await agent.bot.move_to(mob_pos, range_val=1)
            await asyncio.sleep(1.0)
            
        return True
    except asyncio.CancelledError:
        raise
    except Exception as e:
        print(f"Error in hunt_mob capability: {e}")
        return False
