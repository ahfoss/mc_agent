from javascript import require
import math
import time
Vec3 = require('vec3').Vec3

import util.items as ui
import util.crafting as uc

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

def place_block_on_ground_one_forward(agent, item_name):
    # We will use the block directly in front of the agent's feet
    place_block_on_ground_relative_to_self(agent, item_name, 1, -1, 0)

def place_block_on_ground_relative_to_self(agent, item_name, x_offset, y_offset, z_offset):
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
                
        # Define the face vector.
        # Vec3(0, 1, 0) represents the TOP face of the reference block.
        # This tells the agent to place the new block on top of the block beneath it.
        face_vector = Vec3(0, 1, 0)
                
        # Place the block
        agent.bot.placeBlock(reference_block, face_vector)
        agent.bot.chat("Block placed successfully!")
                
    else:
        agent.bot.chat(f"Screw you! You didn't give me any {item_name}!!!.")


def move_absolute(agent, coordinates):
    target_x = coordinates["x"]
    target_y = coordinates["y"]
    target_z = coordinates["z"]
    print(f"Moving to absolute position: {target_x}, {target_y}, {target_z}")
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
        move_relative_to_self(agent, 1, 0, 0)

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

def furnish_shelter1(agent):#, goal_location):
    # Furnish the shelter with basic items:
    # - Crafting Table: 1 log
    # - Large chest: 4 log
    # - Door: 1.5 log (6 planks)
    # - 7 logs in all
    # Check inventory for ingredients
    crafting_list = {"crafting_table": 1}
    agent.bot.chat("Furnishing the shelter with basic items.")
    # Proceed with furnishing the shelter
    # Navigate to shelter location from memory:
    try:
        shelter_location = agent.memory.retrieve("shelter_location")
        move_absolute(agent, shelter_location)
    except KeyError as e:
        agent.bot.chat(f"Coordinates not found in memory. Have you already built the shelter?")
        return
    # Navigate 1 away from crafting table
    move_relative_to_self(agent, 9, -8, 5)
    # Make a crafting table
    uc.craft_direct(agent, "crafting_table")

    # Place the crafting table
    place_block_on_ground_relative_to_self(agent, "crafting_table", 0, -1, 1)
    # Store location of crafting table in memory
    agent.memory.store("crafting_area", agent.bot.entity.position)

    # Craft door
    door_name = uc.craft_any_door(agent, quantity=1)
    # Splitting up stops from getting stuck?
    move_relative_to_self(agent, 0, 0, -5)
    move_relative_to_self(agent, -1, 0, 0)
    # Place door
    place_block_on_ground_relative_to_self(agent, door_name, -1, 1, 0)
    # Reminder: Configure movement so it can open doors (ideally close too)

    # Craft two chests
    # Place them into one big chest

def _furnish_shelter1(agent, goal_location):
    ingredients_list = {}
    # Check inventory for ingredients
    has_enough = ui.check_inventory(agent, ingredients_list)
    if not has_enough:
        agent.bot.chat("Not enough ingredients (7 logs) to furnish the shelter.")
        return
    agent.bot.chat("Furnishing the shelter with basic items.")
    # Proceed with furnishing the shelter
    # Navigate to shelter location from memory:
    try:
        shelter_location = agent.memory.retrieve("shelter_location")
        move_absolute(agent, shelter_location)
    except KeyError as e:
        agent.bot.chat(f"Coordinates not found in memory. Have you already built the shelter?")
    # Navigate 1 away from crafting table
    move_relative_to_self(agent, 9, -8, 5)
    # Make a crafting table
    mcdata = require('minecraft-data')(agent.bot.version)
    item_id = mcdata.itemsByName["crafting_table"].id
    ct_recipes = agent.bot.recipesFor(item_id, None, 1, None)
    print(f"Recipes: {ct_recipes}")
    print(f"Found {getattr(ct_recipes, "length", None)} recipes for crafting table.")
    if not ct_recipes:
        agent.bot.chat("No recipe found for crafting table.")
    else:
        try:
            agent.bot.craft(ct_recipes[0], 1, None)
        except Exception as e:
            agent.bot.chat(f"Craft failed: {e}")

    # Place the crafting table
    place_block_on_ground_relative_to_self(agent, "crafting_table", 0, -1, 1)
            
    # 4. Print the results
    log_blocks = ui.get_log_keywords(agent)
    print(f"Found {len(log_blocks)} log-related blocks:")
    print("-" * 40)
    for name, block_id in log_blocks.items():
        print(f"ID: {block_id:<4} | Name: {name}")

def furnish_shelter2(agent, goal_location):
    # Furnish the shelter with basic items:
    # - Furnace
    # - Torches
    ingredients_list = {}

def furnish_shelter3(agent, goal_location):
    # Furnish the shelter with basic items:
    # - Bed
    ingredients_list = {}


# Build a simple shelter
def build_shelter(agent):
    agent.memory.store("shelter_location", agent.bot.entity.position)
    dig_staircase_down(agent, 8)
    dig_chamber(agent, 8, 8)