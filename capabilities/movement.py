import math
import time
from javascript import require

Vec3 = require('vec3').Vec3
mineflayer_pathfinder = require("mineflayer-pathfinder")


def pathfind_to_goal(agent, goal_location):
    """
    Directs the bot to pathfind to a specific location in the world.
    """
    if not agent.bot or not getattr(agent.bot, 'entity', None):
        print("CRITICAL: Bot is disconnected or dead. Aborting pathfind.")
        return False

    # Pre-flight check: is pathfinder loaded?
    if not getattr(agent.bot, 'pathfinder', None):
        print("CRITICAL: Pathfinder plugin is missing!")
        return False

    def extract_coord(loc, key):
        if isinstance(loc, dict):
            value = loc.get(key)
        else:
            value = getattr(loc, key, None)
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    x = extract_coord(goal_location, "x")
    y = extract_coord(goal_location, "y")
    z = extract_coord(goal_location, "z")

    if x is None or y is None or z is None:
        agent.log(f"Invalid goal location data: {goal_location}")
        return False

    # Reset any existing movement state before pathfinding
    try:
        agent.bot.pathfinder.setGoal(None)
    except Exception:
        pass

    # Ensure pathfinder goto exists
    if not getattr(agent.bot, 'pathfinder', None) or not getattr(agent.bot.pathfinder, 'goto', None):
        agent.log("Pathfinder.goto is unavailable. Reloading plugin...")
        try:
            agent.bot.loadPlugin(mineflayer_pathfinder.pathfinder)
            time.sleep(0.25)
        except Exception as e:
            agent.log(f"Failed to reload pathfinder plugin: {e}")

    if not getattr(agent.bot, 'pathfinder', None) or not getattr(agent.bot.pathfinder, 'goto', None):
        agent.log("Pathfinder.goto is unavailable after reload.")
        return False

    # Try once, then retry after a short pause if first attempt fails
    for attempt in range(2):
        try:
            agent.log(f"Pathfinding to {x}, {y}, {z} (attempt {attempt + 1})")
            agent.bot.pathfinder.goto(
                mineflayer_pathfinder.pathfinder.goals.GoalNear(x, y, z, 1),
                timeout=300000,
            )
            time.sleep(0.5)
            return True
        except Exception as e:
            agent.log(f"Error while trying to run pathfind_to_goal: {e}")
            try:
                agent.bot.pathfinder.setGoal(None)
            except Exception:
                pass
            if attempt == 0:
                time.sleep(0.25)
                continue
            return False


def move_absolute(agent, coordinates):
    """
    Commands the bot to walk to absolute block coordinates.
    """
    target_x = coordinates["x"]
    target_y = coordinates["y"]
    target_z = coordinates["z"]
    print(f"Moving to absolute position: {target_x}, {target_y}, {target_z}")
    goal = mineflayer_pathfinder.goals.GoalBlock(target_x, target_y, target_z)
    
    try:
        print(f"Attempting to pathfind to {target_x}, {target_y}, {target_z}...")
        agent.bot.pathfinder.goto(goal, timeout=300000)
    except Exception as e:
        error_msg = str(e)
        print(f"Pathfinding failed: {error_msg}")
        if agent.bot.pathfinder.isMoving():
            agent.bot.pathfinder.setGoal(None)


def move_relative_to_self(agent, x_offset, y_offset, z_offset):
    """
    Commands the bot to walk to relative block coordinates.
    """
    if not agent.bot or not getattr(agent.bot, 'entity', None):
        print("CRITICAL: Bot is disconnected. Aborting relative move.")
        return

    current_pos = agent.bot.entity.position

    target_x = math.floor(current_pos.x + x_offset)
    target_y = math.floor(current_pos.y + y_offset)
    target_z = math.floor(current_pos.z + z_offset)

    goal = mineflayer_pathfinder.goals.GoalBlock(target_x, target_y, target_z)

    try:
        print(f"Attempting to pathfind to {target_x}, {target_y}, {target_z}...")
        agent.bot.pathfinder.goto(goal, timeout=300000)
    except Exception as e:
        error_msg = str(e)
        print(f"Pathfinding failed: {error_msg}")
        if agent.bot.pathfinder.isMoving():
            agent.bot.pathfinder.setGoal(None)
