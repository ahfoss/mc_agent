import capabilities.movement as um

def mine_line(agent, length):
    """
    Digs a straight line of length blocks, moving relative to current position.
    """
    next_pos = agent.bot.position + (0, -1, 0)
    agent.bot.dig(next_pos)
    for _ in range(length):
        next_pos = agent.bot.position + (1, 0, 0)
        agent.bot.dig(next_pos)
        um.move_relative_to_self(agent, 1, 0, 0)


def burrow_one_block_down_positive_x(agent):
    """
    Digs blocks in positive x and moves down by one block.
    """
    agent.bot.dig(agent.bot.position + (1, 1, 0))
    agent.bot.dig(agent.bot.position + (1, 0, 0))
    agent.bot.dig(agent.bot.position + (1, -1, 0))
    um.move_relative_to_self(agent, 1, -1, 0)


def tunnel_forward(agent, length, height=2, direction='x', direction_sign=1):
    """
    Digs out a tunnel of specified dimensions.
    """
    if height < 2 or height > 3:
        agent.log("Height must be 2 or 3. Defaulting to 2.")
        height = 2
        
    xcoord = 0
    zcoord = 0
    if direction == 'x':
        xcoord = 1 * direction_sign
    elif direction == 'z':
        zcoord = 1 * direction_sign
    else:
        raise RuntimeError("Invalid direction.")
        
    for _ in range(length):
        agent.bot.dig(agent.bot.position + (xcoord, 1, zcoord))
        agent.bot.dig(agent.bot.position + (xcoord, 0, zcoord))
        if height == 3:
            agent.bot.dig(agent.bot.position + (xcoord, 2, zcoord))
        um.move_relative_to_self(agent, xcoord, 0, zcoord)


def dig_chamber(agent, xdim, zdim):
    """
    Digs out a 3D rectangular chamber.
    """
    tunnel_forward(agent, xdim, height=3)
    um.move_relative_to_self(agent, 1 - xdim, 0, 0)
    for _ in range(zdim - 1):
        tunnel_forward(agent, 1, height=3, direction='z', direction_sign=1)
        tunnel_forward(agent, xdim - 1, height=3)
        um.move_relative_to_self(agent, 1 - xdim, 0, 0)


def dig_staircase_down(agent, depth):
    """
    Digs a staircase down for depth levels.
    """
    for _ in range(depth):
        burrow_one_block_down_positive_x(agent)
