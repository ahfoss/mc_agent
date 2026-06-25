from javascript import require, On, AsyncTask, off
from simple_chalk import chalk

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import util.movement as um

# Import the javascript libraries
mineflayer = require("mineflayer")
mineflayer_pathfinder = require("mineflayer-pathfinder")
vec3 = require("vec3")

class BaseBot:

    def __init__(self, bot_name, server_host, server_port, reconnect = True, can_dig = False):
        self.can_dig = can_dig
        self.bot_args = {
            "host": server_host,
            "port": server_port,
            "username": bot_name,
            "hideErrors": False,
        }
        self.reconnect = reconnect
        self.bot_name = bot_name
        self.ready = False

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

    # Start mineflayer bot
    def start_bot(self):
        self.bot = mineflayer.createBot(self.bot_args)
        self.bot.loadPlugin(mineflayer_pathfinder.pathfinder)
        self.start_events()

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
            self.ready = True
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
                um.build_shelter(self, player_loc)
            elif "dig to me" in message:
                # Set to digging
                self.mcData = require('minecraft-data')(self.bot.version)
                movements = mineflayer_pathfinder.Movements(self.bot, self.mcData)
                movements.canDig = True
                self.bot.pathfinder.setMovements(movements)

                if player_loc:
                    um.pathfind_to_goal(self, player_loc)

                # Set to original setting
                self.mcData = require('minecraft-data')(self.bot.version)
                movements = mineflayer_pathfinder.Movements(self.bot, self.mcData)
                movements.canDig = self.can_dig
                self.bot.pathfinder.setMovements(movements)
            elif "come to me" in message:
                if not self.ready or not getattr(self.bot, 'entity', None):
                    self.bot.chat("Hold on, I'm still spawning. Try again in a moment.")
                    return
                if player_loc:
                    # Reinitialize movement settings before pathfinding.
                    self.mcData = require('minecraft-data')(self.bot.version)
                    movements = mineflayer_pathfinder.Movements(self.bot, self.mcData)
                    movements.canDig = self.can_dig
                    self.bot.pathfinder.setMovements(movements)

                    location = {
                        "x": float(player_loc.x),
                        "y": float(player_loc.y),
                        "z": float(player_loc.z),
                    }
                    self.log(f"come_to_me target: {location}")
                    if not um.pathfind_to_goal(self, location):
                        self.bot.chat("I couldn't start moving yet. Please try again in a moment.")
            elif "teleport to me" in message:
                #self.bot.chat(f"/tp {self.bot.username} {sender}")
                safe_username = str(username).strip()
                self.bot.chat(f"/tp {safe_username}")
            elif "mine line" in message:
                um.mine_line(self, 10)

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