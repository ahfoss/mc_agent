from javascript import require

Vec3 = require('vec3').Vec3


def place_block_on_ground_relative_to_self(agent, item_name, x_offset, y_offset, z_offset):
    """
    Equips a block from inventory and places it relative to the bot.
    """
    # Get the item ID for the block you want to place (e.g., dirt)
    item_id = agent.bot.registry.itemsByName[item_name].id
            
    # Find the item in the agent's inventory
    item_to_equip = agent.bot.inventory.findInventoryItem(item_id, None)
            
    if item_to_equip:
        # Equip the item to the agent's main hand
        agent.bot.equip(item_to_equip, 'hand')
                
        # Find a reference block. 
        pos_below = agent.bot.entity.position.offset(x_offset, y_offset, z_offset)
        reference_block = agent.bot.blockAt(pos_below)
                
        # Define the face vector (TOP face).
        face_vector = Vec3(0, 1, 0)
                
        # Place the block
        agent.bot.placeBlock(reference_block, face_vector)
        agent.bot.chat("Block placed successfully!")
    else:
        agent.bot.chat(f"Screw you! You didn't give me any {item_name}!!!.")


def place_block_on_ground_one_forward(agent, item_name):
    """
    Places a block directly in front of the bot's feet.
    """
    place_block_on_ground_relative_to_self(agent, item_name, 1, -1, 0)
