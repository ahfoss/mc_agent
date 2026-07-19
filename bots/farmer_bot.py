from core.bot import BaseBot
from core.command_registry import CommandRegistry

async def handle_harvest(agent, username, message):
    await agent.bot.chat("Harvesting capability is not fully implemented yet, but I am ready to farm!")


class FarmerBot(BaseBot):
    """
    A specialized bot subclass for farming activities.
    Inherits from the BaseBot and registers farming-specific chat triggers.
    """
    def __init__(self, bot_name, server_host, server_port, reconnect=True, can_dig=True, version=None):
        # Initialize a custom command registry for the Farmer Bot
        registry = CommandRegistry()
        
        from commands.movement_cmds import register_commands as reg_move
        from commands.construction_cmds import register_commands as reg_const
        from commands.mining_cmds import register_commands as reg_mine
        from commands.items_cmds import register_commands as reg_items
        
        reg_move(registry)
        reg_const(registry)
        reg_mine(registry)
        reg_items(registry)
        
        # Register specialized farming commands
        registry.register("harvest", handle_harvest)
        
        # Call the parent BaseBot initialization with our custom registry and settings
        super().__init__(
            bot_name=bot_name,
            server_host=server_host,
            server_port=server_port,
            registry=registry,
            reconnect=reconnect,
            can_dig=can_dig,
            version=version
        )
        
    def start_events(self):
        pass
