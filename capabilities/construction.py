import math
from core.bot import Vec3

async def place_block_on_ground_relative_to_self(agent, item_name, x_offset, y_offset, z_offset):
    """
    Equips a block from inventory and places it relative to the bot.
    """
    # Check if we have the item in inventory
    if agent.bot.get_inventory().get(item_name, 0) > 0:
        pos = agent.bot.position
        floored_pos = Vec3(math.floor(pos.x), math.floor(pos.y), math.floor(pos.z))
        pos_below = floored_pos + (x_offset, y_offset, z_offset)
        face_vector = Vec3(0, 1, 0)
        await agent.bot.place_block(item_name, pos_below, face_vector)
        await agent.bot.chat("Block placed successfully!")
    else:
        await agent.bot.chat(f"Screw you! You didn't give me any {item_name}!!!.")


async def place_block_on_ground_one_forward(agent, item_name):
    """
    Places a block directly in front of the bot's feet.
    """
    await place_block_on_ground_relative_to_self(agent, item_name, 1, -1, 0)


async def place_block_relative_to_block(agent, item_name, ref_block_pos, dx, dy, dz):
    """
    Places a block relative to a reference block position.
    """
    target_pos = ref_block_pos + (dx, dy, dz)
    pos_below = target_pos - (0, 1, 0)
    face_vector = Vec3(0, 1, 0)
    
    # Verify we have the item in inventory
    if agent.bot.get_inventory().get(item_name, 0) > 0:
        await agent.bot.place_block(item_name, pos_below, face_vector)
        await agent.bot.chat(f"{item_name} placed relative to block!")
        return True
    else:
        await agent.bot.chat(f"I don't have a {item_name} to place.")
        return False
