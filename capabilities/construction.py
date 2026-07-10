from core.bot import Vec3

def place_block_on_ground_relative_to_self(agent, item_name, x_offset, y_offset, z_offset):
    """
    Equips a block from inventory and places it relative to the bot.
    """
    # Check if we have the item in inventory
    if agent.bot.get_inventory().get(item_name, 0) > 0:
        pos_below = agent.bot.position + (x_offset, y_offset, z_offset)
        face_vector = Vec3(0, 1, 0)
        agent.bot.place_block(item_name, pos_below, face_vector)
        agent.bot.chat("Block placed successfully!")
    else:
        agent.bot.chat(f"Screw you! You didn't give me any {item_name}!!!.")


def place_block_on_ground_one_forward(agent, item_name):
    """
    Places a block directly in front of the bot's feet.
    """
    place_block_on_ground_relative_to_self(agent, item_name, 1, -1, 0)


def place_block_relative_to_block(agent, item_name, ref_block_pos, dx, dy, dz):
    """
    Places a block relative to a reference block position.
    """
    target_pos = ref_block_pos + (dx, dy, dz)
    # The reference block to place against (one block below the target spot)
    pos_below = target_pos - (0, 1, 0)
    face_vector = Vec3(0, 1, 0)
    
    # Verify we have the item in inventory
    if agent.bot.get_inventory().get(item_name, 0) > 0:
        agent.bot.place_block(item_name, pos_below, face_vector)
        agent.bot.chat(f"{item_name} placed relative to block!")
        return True
    else:
        agent.bot.chat(f"I don't have a {item_name} to place.")
        return False
