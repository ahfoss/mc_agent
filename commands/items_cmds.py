from typing import Any

async def handle_tell_inventory(agent: Any, username: str, message: str) -> None:
    """
    Handles the 'tell inventory' chat command by printing all items in the bot's inventory.
    """
    inventory = agent.bot.get_inventory()
    if not inventory:
        await agent.bot.chat("My inventory is empty.")
        return
        
    items_desc = []
    for item_name, count in sorted(inventory.items()):
        if count > 0:
            items_desc.append(f"{count} {item_name}")
            
    if not items_desc:
        await agent.bot.chat("My inventory is empty.")
    else:
        await agent.bot.chat("Inventory: " + ", ".join(items_desc))


def register_commands(registry: Any) -> None:
    """
    Registers the inventory-related chat commands.
    """
    registry.register("tell inventory", handle_tell_inventory)
