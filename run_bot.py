import json
import argparse
from core.bot import BaseBot
from core.command_registry import CommandRegistry
from bots.farmer_bot import FarmerBot
from commands import movement_cmds, construction_cmds, mining_cmds


def main():
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
    
    print(f"Server Host: {server_host}")
    print(f"Server Port: {server_port}")
    print(f"Bot Type: {args.type}")

    if args.type == "farmer":
        print("Starting FarmerBot...")
        # FarmerBot initializes its own registry and triggers internally
        bot = FarmerBot("farmer-bot", server_host=server_host, server_port=server_port)
    else:
        print("Starting BaseBot...")
        # Setup registry and load standard commands for BaseBot
        registry = CommandRegistry()
        movement_cmds.register_commands(registry)
        construction_cmds.register_commands(registry)
        mining_cmds.register_commands(registry)
        
        bot = BaseBot(
            "pathfinder-bot",
            server_host=server_host,
            server_port=server_port,
            registry=registry
        )


if __name__ == "__main__":
    main()
