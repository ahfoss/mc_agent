def get_item_keywords(agent, keyword_list):
    """
    Get all block name/ID matches from the registry containing keywords in keyword_list.
    """
    blocks = {}
    
    # Iterate through every block in the game's registry
    for block in agent.bot.registry.blocksArray:
        # Check if the block's name contains any of our keywords
        if any(keyword in block.name for keyword in keyword_list):
            blocks[block.name] = block.id
    return blocks


door_types = [
    'oak_door', 'spruce_door', 'birch_door', 'jungle_door', 
    'acacia_door', 'dark_oak_door', 'mangrove_door', 'cherry_door',
    'pale_oak_door', 'warped_door', 'crimson_door',
]


def get_log_keywords(agent):
    return get_item_keywords(agent, ['log'])
