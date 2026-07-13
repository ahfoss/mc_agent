import json
import argparse
import asyncio
from core.bot import BaseBot
from core.command_registry import CommandRegistry
from bots.farmer_bot import FarmerBot
from commands import movement_cmds, construction_cmds, mining_cmds, items_cmds


async def main():
    # Setup command line parser to allow selecting bot type
    parser = argparse.ArgumentParser(description="Spawn a modular Minecraft bot.")
    parser.add_argument(
        "--type", 
        type=str, 
        default="base", 
        choices=["base", "farmer"], 
        help="Type of bot to spawn (default: base)"
    )
    args = parser.parse_args()

    # Load configuration
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        config = {}

    server_host = config.get("server_host", "localhost")
    server_port = config.get("server_port", 55556)
    server_version = config.get("server_version")
    
    print(f"Server Host: {server_host}")
    print(f"Server Port: {server_port}")
    print(f"Server Version: {server_version}")
    print(f"Bot Type: {args.type}")

    if args.type == "farmer":
        print("Starting FarmerBot...")
        bot = FarmerBot("farmer-bot", server_host=server_host, server_port=server_port, version=server_version)
    else:
        print("Starting BaseBot...")
        registry = CommandRegistry()
        movement_cmds.register_commands(registry)
        construction_cmds.register_commands(registry)
        mining_cmds.register_commands(registry)
        items_cmds.register_commands(registry)
        
        bot = BaseBot(
            "pathfinder-bot",
            server_host=server_host,
            server_port=server_port,
            registry=registry,
            version=server_version
        )

    # Start the bot asynchronously
    await bot.start()

    print("\nBot is successfully running! Press Ctrl+C to disconnect and exit.")
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nDisconnecting bot and exiting...")
    finally:
        await bot.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
