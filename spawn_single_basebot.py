import json
import agents.base_bot as abb

# load config.json
with open("config.json", "r") as f:
    config = json.load(f)
server_host = config.get("server_host")
server_port = config.get("server_port")
print(f"Server host: {server_host}")
print(f"Server port: {server_port}")

# Run function that starts the bot(s)
bot = abb.BaseBot("pathfinder-bot", server_host=server_host, server_port=server_port)