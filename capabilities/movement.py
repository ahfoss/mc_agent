from core.bot import Vec3

def pathfind_to_goal(agent, goal_location):
    """
    Directs the bot to pathfind to a specific location in the world.
    """
    target = Vec3(goal_location)
    return agent.bot.move_to(target, range_val=1)


def move_absolute(agent, coordinates):
    """
    Commands the bot to walk to absolute block coordinates.
    Supports dictionary coordinates and Vec3 objects.
    """
    target = Vec3(coordinates)
    print(f"Moving to absolute position: {target.x}, {target.y}, {target.z}")
    try:
        print(f"Attempting to pathfind to {target.x}, {target.y}, {target.z}...")
        agent.bot.move_to(target, range_val=0)
    except Exception as e:
        print(f"Pathfinding failed: {e}")


def move_relative_to_self(agent, x_offset, y_offset, z_offset):
    """
    Commands the bot to walk to relative block coordinates.
    """
    current_pos = agent.bot.position
    target = current_pos + (x_offset, y_offset, z_offset)
    try:
        print(f"Attempting to pathfind to {target.x}, {target.y}, {target.z}...")
        agent.bot.move_to(target, range_val=0)
    except Exception as e:
        print(f"Pathfinding failed: {e}")
