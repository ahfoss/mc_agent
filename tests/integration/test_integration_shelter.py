import pytest
import time
import socket
import subprocess
import os
import asyncio
from functools import wraps

# Suppress Node.js warnings in the background Node process.
os.environ["NODE_NO_WARNINGS"] = "1"
import json
import shutil
from unittest.mock import MagicMock

# Helper decorator for async tests
def async_test(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper

def is_port_open(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex((host, port)) == 0

@pytest.fixture(scope="module")
def integration_server():
    """
    Looks for an active Minecraft server on localhost:25565.
    If none exists, it attempts to boot a Flying Squid node server dynamically.
    If that fails, it gracefully skips the test.
    """
    host = "127.0.0.1"
    port = 52188
    server_process = None

    try:
        config_path = "config.json"
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            config_port = config.get("server_port", 25565)
            if is_port_open(host, config_port):
                port = config_port
            elif is_port_open(host, 25565):
                port = 25565
    except Exception as e:
        print(f"[Integration Server Setup] Warn: Failed to read config.json: {e}")
    
    config_dir = "config"
    settings_file = os.path.join(config_dir, "settings.json")
    created_config_dir = False
    created_settings_file = False

    if not is_port_open(host, port):
        print(f"\n[Integration Server Setup] No Minecraft server found on {host}:{port}. Attempting npx flying-squid...")
        try:
            if not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)
                created_config_dir = True
            
            if not os.path.exists(settings_file):
                settings_data = {
                    "port": port,
                    "max-players": 10,
                    "online-mode": False,
                    "logging": False,
                    "gameMode": 1,
                    "difficulty": 1,
                    "generation": {
                        "name": "diamond_square"
                    }
                }
                with open(settings_file, "w", encoding="utf-8") as sf:
                    json.dump(settings_data, sf, indent=2)
                created_settings_file = True
        except Exception as e:
            print(f"[Integration Server Setup] Failed to create settings file: {e}")

        try:
            server_process = subprocess.Popen(
                ["npx", "-y", "flying-squid"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True
            )
            for i in range(30):
                if is_port_open(host, port):
                    print(f"[Integration Server Setup] Server booted successfully after {i} seconds.")
                    break
                time.sleep(1)
        except Exception as e:
            print(f"[Integration Server Setup] Failed to boot flying-squid subprocess: {e}")

    if not is_port_open(host, port):
        pytest.skip(
            f"Integration test skipped: No Minecraft server is running on {host}:{port}, "
            "and local 'flying-squid' server could not be booted dynamically."
        )

    yield host, port

    if server_process:
        print("[Integration Server Teardown] Terminating flying-squid process...")
        try:
            if os.name == 'nt':
                subprocess.run(
                    f"taskkill /F /T /PID {server_process.pid}",
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                server_process.terminate()
        except Exception:
            pass
        server_process.wait()

    if created_settings_file and os.path.exists(settings_file):
        try:
            os.remove(settings_file)
        except Exception:
            pass
    if created_config_dir and os.path.exists(config_dir):
        try:
            shutil.rmtree(config_dir)
        except Exception:
            pass

@async_test
async def test_integration_build_and_furnish_shelter(integration_server):
    host, port = integration_server
    
    from bots.farmer_bot import FarmerBot
    
    bot_agent = None
    try:
        # 1. Connect bot client
        bot_agent = FarmerBot(
            bot_name="TesterBot",
            server_host=host,
            server_port=port,
            reconnect=False
        )
        await bot_agent.start()
        
        # 2. Wait for the spawn event
        timeout = 25
        start_time = time.time()
        while not bot_agent.ready and (time.time() - start_time) < timeout:
            await asyncio.sleep(0.5)
    
        assert bot_agent.ready is True, "Bot failed to spawn inside the world in the allocated time."
        assert bot_agent.bot.position is not None, "Bot position was not initialized."
    
        original_pos = bot_agent.bot.position
        print(f"Bot spawned successfully at: {original_pos}")
    
        # 3. Test "build shelter" command execution via chat emission
        print("Testing command: 'build shelter'...")
        bot_agent.bot.emit("chat", "Player1", "build shelter")
        await asyncio.sleep(20.0)  # excavation delay
    
        shelter_loc = bot_agent.memory.retrieve("shelter_location")
        assert shelter_loc is not None, "Bot did not store 'shelter_location' in memory."
        assert abs(shelter_loc.x - original_pos.x) < 1.0
        assert abs(shelter_loc.z - original_pos.z) < 1.0
    
        # 4. Test "furnish shelter" command execution via chat emission
        print("Testing command: 'furnish shelter'...")
        await bot_agent.bot.chat("/give @s oak_planks 64")
        await bot_agent.bot.chat("/give @s cobblestone 64")
        await asyncio.sleep(1.0)
        
        bot_agent.bot.emit("chat", "Player1", "furnish shelter")
        
        # Wait up to 30 seconds for the adjacent coordinate in memory
        timeout = 30
        start_time = time.time()
        adjacent_spot = None
        while (time.time() - start_time) < timeout:
            adjacent_spot = bot_agent.memory.retrieve("adjacent_crafting_table")
            if adjacent_spot is not None:
                break
            await asyncio.sleep(1)
            
        assert adjacent_spot is not None, "Bot failed to store 'adjacent_crafting_table' in memory (furnish shelter failed or timed out)."
    
    finally:
        if bot_agent:
            try:
                await bot_agent.close()
            except Exception:
                pass
