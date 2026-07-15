import math
from typing import Any
from core.bot import Vec3

async def pathfind_to_goal(agent: Any, goal_location: Any) -> Any:
    """
    Directs the bot to pathfind to a specific location in the world.
    """
    target = Vec3(goal_location)
    return await agent.bot.move_to(target, range_val=1)


async def move_absolute(agent: Any, coordinates: Any) -> None:
    """
    Commands the bot to walk to absolute block coordinates.
    Supports dictionary coordinates and Vec3 objects.
    """
    target = Vec3(coordinates)
    try:
        print(f"Attempting to pathfind to {target.x}, {target.y}, {target.z}...")
        await agent.bot.move_to(target, range_val=0)
    except Exception as e:
        print(f"Pathfinding failed: {e}")


async def move_relative_to_self(agent: Any, x_offset: float, y_offset: float, z_offset: float) -> None:
    """
    Commands the bot to walk to relative block coordinates, aligned to block centers.
    """
    current_pos = agent.bot.position
    fx = math.floor(current_pos.x) + 0.5 + x_offset
    fy = math.floor(current_pos.y) + y_offset
    fz = math.floor(current_pos.z) + 0.5 + z_offset
    target = Vec3(fx, fy, fz)
    try:
        print(f"Attempting to pathfind to {target.x}, {target.y}, {target.z}...")
        await agent.bot.move_to(target, range_val=0)
    except Exception as e:
        print(f"Pathfinding failed: {e}")
