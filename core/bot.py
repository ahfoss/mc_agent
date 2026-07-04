from javascript import require, On, off
from simple_chalk import chalk
from core.memory import Memory

mineflayer = require("mineflayer")
mineflayer_pathfinder = require("mineflayer-pathfinder")


class BaseBot:
    """
    Core BaseBot wrapping Mineflayer connection, basic events, and command routing.
    """
    def __init__(self, bot_name, server_host, server_port, registry=None, reconnect=True, can_dig=False):
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
        self.registry = registry

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

        self.memory = Memory(server_port=server_port)

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
        # 1. Failure Event: Catches connection timeouts and bad credentials
        @On(self.bot, "error")
        def on_error(err, *args):
            print(f"CRITICAL ERROR: The bot encountered a problem: {err}")

        # 2. Rejection Event: Catches server bans, whitelists, or full servers
        @On(self.bot, "kicked")
        def on_kicked(reason, loggedIn, *args):
            print(f"KICKED: The server rejected the bot. Reason: {reason}")

        # 3. Disconnect Event: Catches server shutdowns or network drops
        @On(self.bot, "end")
        def on_end(reason, *args):
            print(f"DISCONNECTED: The bot lost connection to the server. Reason: {reason}")

        # Login event: Triggers on bot login
        @On(self.bot, "login")
        def login(*args):
            # Displays which server you are currently connected to
            self.bot_socket = self.bot._client.socket
            host = self.bot_socket.server if self.bot_socket.server else self.bot_socket._host
            self.log(chalk.green(f"Logged in to {host}"))

        # Spawn event: Triggers on bot entity spawn
        @On(self.bot, "spawn")
        def spawn(*args):
            self.ready = True
            self.log("Spawned in the world!")
            self.bot.chat("Hi buddy!")

        @On(self.bot, "chat")
        def handle_chat(username, message, *args):
            # Ignore the bot's own messages so it doesn't talk to itself
            if username == self.bot.username:
                return
            
            self.log(f"Chat received from {username}: '{message}'")
            
            # Delegate command processing to dynamic registry
            if self.registry:
                self.registry.dispatch(self, username, message)

        # End event: Triggers on disconnect from server
        @On(self.bot, "end")
        def end_listener(reason):
            self.log(chalk.red(f"Disconnected: {reason}"))

            # Turn off old events
            off(self.bot, "login", login)
            off(self.bot, "spawn", spawn)
            off(self.bot, "error", on_error)
            off(self.bot, "kicked", on_kicked)

            # Reconnect
            if self.reconnect:
                self.log(chalk.cyanBright("Attempting to reconnect"))
                self.start_bot()

            # Last event listener
            off(self.bot, "end", end_listener)
