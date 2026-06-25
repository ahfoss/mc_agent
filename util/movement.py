from javascript import require
import math
import time

# Import the javascript libraries
mineflayer = require("mineflayer")
mineflayer_pathfinder = require("mineflayer-pathfinder")

def pathfind_to_goal(agent, goal_location):
    if not agent.bot or not getattr(agent.bot, 'entity', None):
        print("CRITICAL: Bot is disconnected or dead. Aborting pathfind.")
        return False

    # 2. PRE-FLIGHT CHECK: Did the pathfinder plugin crash/disappear?
    if not getattr(agent.bot, 'pathfinder', None):
        print("CRITICAL: Pathfinder plugin is missing! Reloading plugin...")
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

    # 3. Reset any existing movement state before attempting a new path.
    try:
        agent.bot.pathfinder.setGoal(None)
    except Exception:
        pass

    # 4. Ensure the pathfinder plugin is ready and has the goto method.
    if not getattr(agent.bot, 'pathfinder', None) or not getattr(agent.bot.pathfinder, 'goto', None):
        agent.log("Pathfinder plugin isn't ready yet; reloading plugin.")
        try:
            agent.bot.loadPlugin(mineflayer_pathfinder.pathfinder)
            time.sleep(0.25)
        except Exception as e:
            agent.log(f"Failed to reload pathfinder plugin: {e}")

    if not getattr(agent.bot, 'pathfinder', None) or not getattr(agent.bot.pathfinder, 'goto', None):
        agent.log("Pathfinder.goto is unavailable after reload.")
        return False

    # 5. Try once, then retry after a short pause if the first attempt fails.
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


def move_relative_to_self(agent, x_offset, y_offset, z_offset):
    # Get the bot's current position
    current_pos = agent.bot.entity.position

    # 2. Calculate the exact relative block coordinate
    # We use math.floor() to ensure we get the integer block coordinate, 
    # regardless of where the bot is standing inside its current block.
    target_x = math.floor(current_pos.x + x_offset)
    target_y = math.floor(current_pos.y + y_offset)
    target_z = math.floor(current_pos.z + z_offset)

    goal = mineflayer_pathfinder.goals.GoalBlock(target_x, target_y, target_z)

    # Assign the goal to make the bot walk
    try:
        print(f"Attempting to pathfind to {target_x}, {target_y}, {target_z}...")
        agent.bot.pathfinder.goto(goal, timeout = 300000)
    except Exception as e:
        error_msg = str(e)
        print(f"Pathfinding failed: {error_msg}")
        if agent.bot.pathfinder.isMoving():
            agent.bot.pathfinder.setGoal(None)

def mine_line(agent, length):
    next_pos = agent.bot.entity.position.offset(0, -1, 0)
    next_block = agent.bot.blockAt(next_pos)
    agent.bot.dig(next_block)
    for i in range(length):
        next_pos = agent.bot.entity.position.offset(1, 0, 0)
        next_block = agent.bot.blockAt(next_pos)
        agent.bot.dig(next_block)
        move_relative_to_self(1, 0, 0)

def burrow_one_block_down_positive_x(agent):
    agent.bot.dig(agent.bot.blockAt(agent.bot.entity.position.offset(1, 1, 0)))
    agent.bot.dig(agent.bot.blockAt(agent.bot.entity.position.offset(1, 0, 0)))
    agent.bot.dig(agent.bot.blockAt(agent.bot.entity.position.offset(1, -1, 0)))
    move_relative_to_self(agent, 1, -1, 0)

def tunnel_forward(agent, length, height = 2, direction = 'x', direction_sign = 1):
    if height < 2 or height > 3:
        agent.log(f"Height must be 2 or 3. Defaulting to 2.")
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
        agent.bot.dig(agent.bot.blockAt(agent.bot.entity.position.offset(xcoord, 1, zcoord)))
        agent.bot.dig(agent.bot.blockAt(agent.bot.entity.position.offset(xcoord, 0, zcoord)))
        if height == 3:
            agent.bot.dig(agent.bot.blockAt(agent.bot.entity.position.offset(xcoord, 2, zcoord)))
        move_relative_to_self(agent, xcoord, 0, zcoord)

# Dig out chamber
def dig_chamber(agent, xdim, zdim):
    """
    TODO:
    Dig out an xdim X zdim prism with corner centered in front of the bot.
    """
    tunnel_forward(agent, xdim, height = 3)
    move_relative_to_self(agent, 1 - xdim, 0, 0)
    for _ in range(zdim - 1):
        tunnel_forward(agent, 1, height = 3, direction = 'z', direction_sign = 1)
        tunnel_forward(agent, xdim - 1, height = 3)
        move_relative_to_self(agent, 1 - xdim, 0, 0)

# Dig staircase pattern
def dig_staircase_down(agent, depth):
    for i in range(depth):
        burrow_one_block_down_positive_x(agent)

# Build a simple shelter
def build_shelter(agent, goal_location):
    dig_staircase_down(agent, 8)
    dig_chamber(agent, 8, 8)