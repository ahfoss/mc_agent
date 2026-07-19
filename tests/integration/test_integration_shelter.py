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
    Dynamically boots a local Flying Squid server on a free port.
    """
    host = "127.0.0.1"
    port = 52188
    while is_port_open(host, port):
        port += 1

    server_process = None
    config_dir = "config"
    settings_file = os.path.join(config_dir, "settings.json")
    created_config_dir = False
    created_settings_file = False

    if True:
        print(f"\n[Integration Server Setup] No Minecraft server found on {host}:{port}. Attempting npx flying-squid...")
        try:
            if not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)
                created_config_dir = True
            
            if True:
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
                "npx -y flying-squid",
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=True
            )
            for i in range(60):
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

    # Clean up memory file if exists to prevent stale coordinates
    memory_path = "data/memory/memory_TesterBot.json"
    if os.path.exists(memory_path):
        try:
            os.remove(memory_path)
        except Exception:
            pass

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
    
        # 3. Test "build shelter" command execution
        print("Testing command: 'build shelter'...")
        matched = await bot_agent.command_registry.dispatch(bot_agent, "Player1", "build shelter")
        assert matched is True, "Command 'build shelter' did not match."
    
        shelter_loc = bot_agent.memory.retrieve("shelter_location")
        assert shelter_loc is not None, "Bot did not store 'shelter_location' in memory."
        assert abs(shelter_loc.x - original_pos.x) < 1.0
        assert abs(shelter_loc.z - original_pos.z) < 1.0
    
        # 4. Test "furnish shelter" command execution
        print("Testing command: 'furnish shelter'...")
        await bot_agent.bot.chat("/give TesterBot oak_planks 64")
        await bot_agent.bot.chat("/give TesterBot cobblestone 64")
        await bot_agent.bot.chat("/give TesterBot oak_log 64")
        await asyncio.sleep(1.0)
        
        matched = await bot_agent.command_registry.dispatch(bot_agent, "Player1", "furnish shelter")
        assert matched is True, "Command 'furnish shelter' did not match."

        # 5. Verify actual placed blocks in the world
        print("Verifying placed blocks in the world...")
        
        # Crafting Table
        ct_pos = bot_agent.memory.retrieve("crafting_table_position")
        assert ct_pos is not None, "Crafting table position was not stored in memory."
        assert ct_pos.y == shelter_loc.y - 8, f"Crafting table Y ({ct_pos.y}) was not underground Y ({shelter_loc.y - 8})."
        block_ct = await bot_agent.bot.get_block(ct_pos)
        assert block_ct is not None and block_ct.name == "crafting_table", f"Expected crafting table at {ct_pos}, found: {block_ct.name if block_ct else 'None'}"
        
        # Door (top half at Y-6)
        floored_pos = shelter_loc + (9, -8, 5)
        door_pos = floored_pos + (-2, 2, -5)
        block_door = await bot_agent.bot.get_block(door_pos)
        assert block_door is not None and block_door.name.endswith("_door"), f"Expected door at {door_pos}, found: {block_door.name if block_door else 'None'}"
        
        # Furnace (at crafting table + 1, 0, 0)
        furnace_pos = ct_pos + (1, 0, 0)
        block_furnace = await bot_agent.bot.get_block(furnace_pos)
        assert block_furnace is not None and block_furnace.name == "furnace", f"Expected furnace at {furnace_pos}, found: {block_furnace.name if block_furnace else 'None'}"
        
        # Chest 1 & Chest 2 (at crafting table + 4, 0, 0 and +5, 0, 0)
        chest1_pos = ct_pos + (4, 0, 0)
        chest2_pos = ct_pos + (5, 0, 0)
        block_chest1 = await bot_agent.bot.get_block(chest1_pos)
        block_chest2 = await bot_agent.bot.get_block(chest2_pos)
        assert block_chest1 is not None and block_chest1.name == "chest", f"Expected chest at {chest1_pos}, found: {block_chest1.name if block_chest1 else 'None'}"
        assert block_chest2 is not None and block_chest2.name == "chest", f"Expected chest at {chest2_pos}, found: {block_chest2.name if block_chest2 else 'None'}"
        
        print("All placed blocks successfully verified in the world!")
    
    finally:
        if bot_agent:
            try:
                await bot_agent.close()
            except Exception:
                pass
