from javascript import require, On, Once, AsyncTask, once, off
from simple_chalk import chalk
import math
import json
import time

def vec3_to_str(v):
    return f"x: {v['x']:.3f}, y: {v['y']:.3f}, z: {v['z']:.3f}"

def vec3_to_dict(v):
    return {"x": v["x"], "y": v["y"], "z": v["z"]}

# Import the javascript libraries
mineflayer = require("mineflayer")
mineflayer_pathfinder = require("mineflayer-pathfinder")
vec3 = require("vec3")

# Global bot parameters
server_host = "localhost"
# load config.json
with open("config.json", "r") as f:
    config = json.load(f)
server_port = config.get("server_port")
print(f"Server port: {server_port}")

class MCBot:

    def __init__(self, bot_name, reconnect = True, can_dig = False):
        self.can_dig = can_dig
        self.bot_args = {
            "host": server_host,
            "port": server_port,
            "username": bot_name,
            "hideErrors": False,
        }
        self.reconnect = reconnect
        self.bot_name = bot_name

        try:
            self.start_bot()
        except Exception as e:
            raise ConnectionError(f"Failed to start bot '{self.bot_name}'. Is the server running?") from e

        # Validate the connection / version explicitly
        if not hasattr(self.bot, 'version') or not self.bot.version:
            raise ConnectionError(
                f"Bot '{self.bot_name}' failed to retrieve the Minecraft version. "
                f"This usually means the server at {self.bot_args['host']}:{self.bot_args['port']} "
                f"refused the connection (ECONNREFUSED) or is offline."
            )

        self.bot.pathfinder.thinkTimeout = 10000 

        # Control the bot's ability to dig
        self.mcData = require('minecraft-data')(self.bot.version)
        movements = mineflayer_pathfinder.Movements(self.bot, self.mcData)
        movements.canDig = self.can_dig
        self.bot.pathfinder.setMovements(movements)

    # Tags bot username before console messages
    def log(self, message):
        print(f"[{self.bot.username}] {message}")

    # Mineflayer: Pathfind to goal
    def pathfind_to_goal(self, goal_location):
        if not self.bot or not getattr(self.bot, 'entity', None):
            print("CRITICAL: Bot is disconnected or dead. Aborting pathfind.")
            return False

        # 2. PRE-FLIGHT CHECK: Did the pathfinder plugin crash/disappear?
        if not getattr(self.bot, 'pathfinder', None):
            print("CRITICAL: Pathfinder plugin is missing! Reloading plugin...")
            return False

        # 3. Clear any lingering ghost states from the last failure
        if self.bot.pathfinder.isMoving():
            self.bot.pathfinder.setGoal(None)
            #time.sleep(0.5) # Give the bridge a moment to breathe

        try:
            self.bot.pathfinder.goto(
                mineflayer_pathfinder.pathfinder.goals.GoalNear(
                    goal_location["x"], goal_location["y"], goal_location["z"], 1
                ),
                timeout=300000,
            )

        except Exception as e:
            self.log(f"Error while trying to run pathfind_to_goal: {e}")
            if self.bot.pathfinder.isMoving():
                self.bot.pathfinder.setGoal(None)
            
        # 4. Let the bridge threads breathe and synchronize before the loop continues
        time.sleep(1)

    # Start mineflayer bot
    def start_bot(self):
        self.bot = mineflayer.createBot(self.bot_args)
        self.bot.loadPlugin(mineflayer_pathfinder.pathfinder)
        self.start_events()

    def move_relative_to_self(self, x_offset, y_offset, z_offset):
        # Get the bot's current position
        current_pos = self.bot.entity.position

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
            self.bot.pathfinder.goto(goal, timeout = 300000)
        except Exception as e:
            error_msg = str(e)
            print(f"Pathfinding failed: {error_msg}")
            if self.bot.pathfinder.isMoving():
                self.bot.pathfinder.setGoal(None)

    def mine_line(self, length):
        next_pos = self.bot.entity.position.offset(0, -1, 0)
        next_block = self.bot.blockAt(next_pos)
        self.bot.dig(next_block)
        for i in range(length):
            next_pos = self.bot.entity.position.offset(1, 0, 0)
            next_block = self.bot.blockAt(next_pos)
            self.bot.dig(next_block)
            self.move_relative_to_self(1, 0, 0)

    def burrow_one_block_down_positive_x(self):
        self.bot.dig(self.bot.blockAt(self.bot.entity.position.offset(1, 1, 0)))
        self.bot.dig(self.bot.blockAt(self.bot.entity.position.offset(1, 0, 0)))
        self.bot.dig(self.bot.blockAt(self.bot.entity.position.offset(1, -1, 0)))
        self.move_relative_to_self(1, -1, 0)

    def tunnel_forward(self, length, height = 2, direction = 'x', direction_sign = 1):
        if height < 2 or height > 3:
            self.log(f"Height must be 2 or 3. Defaulting to 2.")
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
            self.bot.dig(self.bot.blockAt(self.bot.entity.position.offset(xcoord, 1, zcoord)))
            self.bot.dig(self.bot.blockAt(self.bot.entity.position.offset(xcoord, 0, zcoord)))
            if height == 3:
                self.bot.dig(self.bot.blockAt(self.bot.entity.position.offset(xcoord, 2, zcoord)))
            self.move_relative_to_self(xcoord, 0, zcoord)

    # Dig out chamber
    def dig_chamber(self, xdim, zdim):
        """
        TODO:
        Dig out an xdim X zdim prism with corner centered in front of the bot.
        """
        self.tunnel_forward(xdim, height = 3)
        self.move_relative_to_self(1 - xdim, 0, 0)
        for _ in range(zdim - 1):
            self.tunnel_forward(1, height = 3, direction = 'z', direction_sign = 1)
            self.tunnel_forward(xdim - 1, height = 3)
            self.move_relative_to_self(1 - xdim, 0, 0)

    # Dig staircase pattern
    def dig_staircase_down(self, depth):
        for i in range(depth):
            self.burrow_one_block_down_positive_x()

    # Build a simple shelter
    def build_shelter(self, goal_location):
        self.dig_staircase_down(8)
        self.dig_chamber(8, 8)

    # Attach mineflayer events to bot
    def start_events(self):

        # 3. Failure Event: Catches connection timeouts and bad credentials
        @On(self.bot, "error")
        def on_error(this, err, *args):
            print(f"CRITICAL ERROR: The bot encountered a problem: {err}")

        # 4. Rejection Event: Catches server bans, whitelists, or full servers
        @On(self.bot, "kicked")
        def on_kicked(this, reason, loggedIn, *args):
            print(f"KICKED: The server rejected the bot. Reason: {reason}")

        # 5. Disconnect Event: Catches server shutdowns or network drops
        @On(self.bot, "end")
        def on_end(this, reason, *args):
            print(f"DISCONNECTED: The bot lost connection to the server. Reason: {reason}")

        # Login event: Triggers on bot login
        @On(self.bot, "login")
        def login(*args):

            # Displays which server you are currently connected to
            self.bot_socket = self.bot._client.socket
            self.log(
                chalk.green(
                    f"Logged in to {self.bot_socket.server if self.bot_socket.server else self.bot_socket._host }"
                )
            )

        # Spawn event: Triggers on bot entity spawn
        @On(self.bot, "spawn")
        def spawn(*args):
            self.bot.chat("Hi buddy!")

        @On(self.bot, "chat")
        def handle_chat(this, username, message, *args):
            # 1. Ignore the bot's own messages so it doesn't talk to itself
            if username == self.bot.username:
                return
            sender = self.bot.players[username]
                
            # 2. Check if the player actually exists and is rendered
            if not sender or not sender.entity:
                self.bot.chat(f"I can't see you, {username}! You might be too far away.")
                return
                    
            # 3. Grab the exact position
            player_loc = sender.entity.position

            if "quit" in message:
                self.bot.chat("Goodbye!")
                self.reconnect = False
                this.quit()
            elif "build shelter" in message:
                self.build_shelter(player_loc)
            elif "dig to me" in message:
                # Set to digging
                self.mcData = require('minecraft-data')(self.bot.version)
                movements = mineflayer_pathfinder.Movements(self.bot, self.mcData)
                movements.canDig = True
                self.bot.pathfinder.setMovements(movements)

                if player_loc:
                    self.pathfind_to_goal(player_loc)

                # Set to original setting
                self.mcData = require('minecraft-data')(self.bot.version)
                movements = mineflayer_pathfinder.Movements(self.bot, self.mcData)
                movements.canDig = self.can_dig
                self.bot.pathfinder.setMovements(movements)
            elif "come to me" in message:
                if player_loc:
                    self.pathfind_to_goal(player_loc)
            elif "teleport to me" in message:
                #self.bot.chat(f"/tp {self.bot.username} {sender}")
                safe_username = str(username).strip()
                self.bot.chat(f"/tp {safe_username}")
            elif "mine line" in message:
                self.mine_line(10)

        # End event: Triggers on disconnect from server
        @On(self.bot, "end")
        def end(this, reason):
            self.log(chalk.red(f"Disconnected: {reason}"))

            # Turn off old events
            off(self.bot, "login", login)
            off(self.bot, "spawn", spawn)
            off(self.bot, "kicked", kicked)
            off(self.bot, "messagestr", messagestr)

            # Reconnect
            if self.reconnect:
                self.log(chalk.cyanBright(f"Attempting to reconnect"))
                self.start_bot()

            # Last event listener
            off(self.bot, "end", end)


# Run function that starts the bot(s)
bot = MCBot("pathfinder-bot")