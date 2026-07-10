#import math
from typing import Any#, Union
from core.bot import Vec3

def pathfind_to_goal(agent: Any, goal_location: Any) -> Any:
    """
    Directs the bot to pathfind to a specific location in the world.
    """
    target = Vec3(goal_location)
    return agent.bot.move_to(target, range_val=1)


def move_absolute(agent: Any, coordinates: Any) -> None:
    """
    Commands the bot to walk to absolute block coordinates.
    Supports dictionary coordinates and Vec3 objects.
    """
    target = Vec3(coordinates)
    try:
        print(f"Attempting to pathfind to {target.x}, {target.y}, {target.z}...")
        agent.bot.move_to(target, range_val=0)
    except Exception as e:
        print(f"Pathfinding failed: {e}")


def move_relative_to_self(agent: Any, x_offset: float, y_offset: float, z_offset: float) -> None:
    """
    Commands the bot to walk to relative block coordinates, aligned to block centers.
    """
    current_pos = agent.bot.position
    # Floor coordinates to align target to exact integer grid block centers
    fx = current_pos.x + x_offset
    fy = current_pos.y + y_offset
    fz = current_pos.z + z_offset
    #fx = math.floor(current_pos.x) + x_offset + 0.5
    #fy = math.floor(current_pos.y) + y_offset
    #fz = math.floor(current_pos.z) + z_offset + 0.5
    target = Vec3(fx, fy, fz)
    try:
        print(f"Attempting to pathfind to {target.x}, {target.y}, {target.z}...")
        agent.bot.move_to(target, range_val=0)
    except Exception as e:
        print(f"Pathfinding failed: {e}")
