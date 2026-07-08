# pyrefly: ignore [missing-import]
import pytest
import time
import socket
import subprocess
import os
# Suppress Node.js warnings (like punycode deprecations) in the background Node process.
# Otherwise, warnings written to stderr pollute the stream, causing bridge JSONDecodeErrors.
os.environ["NODE_NO_WARNINGS"] = "1"
import json
import shutil
import sys
from unittest.mock import MagicMock



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

    # Dynamically resolve host/port using config.json (especially for WSL-to-Windows host mapping)
    try:
        config_path = "config.json"
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            host = config.get("server_host", "127.0.0.1")
            config_port = config.get("server_port", 25565)
            # If the custom port in config.json is open, use it; otherwise check default port 25565
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
        
        # Setup settings.json to enforce offline-mode
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
            # Run flying-squid mock server on default port
            server_process = subprocess.Popen(
                ["npx", "-y", "flying-squid"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True
            )
            # Give the server up to 30 seconds to boot
            for i in range(30):
                if is_port_open(host, port):
                    print(f"[Integration Server Setup] Server booted successfully after {i} seconds.")
                    break
                time.sleep(1)
        except Exception as e:
            print(f"[Integration Server Setup] Failed to boot flying-squid subprocess: {e}")

    # Final check
    if not is_port_open(host, port):
        pytest.skip(
            f"Integration test skipped: No Minecraft server is running on {host}:{port}, "
            "and local 'flying-squid' server could not be booted dynamically. "
            "Please start your Minecraft test server or ensure Node/npm is installed to run integration tests."
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

    # Cleanup config files
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

def test_integration_build_and_furnish_shelter(integration_server):
    host, port = integration_server
    
    from bots.farmer_bot import FarmerBot
    from behaviors.shelter import build_shelter, furnish_shelter1
    
    bot_agent = None
    try:
        # 1. Connect bot client (FarmerBot automatically inherits construction and movement behaviors)
        # Reconnect is set to False to avoid infinite reconnect loops during test failures.
        bot_agent = FarmerBot(
            bot_name="TesterBot",
            server_host=host,
            server_port=port,
            reconnect=False
        )
        
        # 2. Wait for the spawn event
        timeout = 25
        start_time = time.time()
        while not bot_agent.ready and (time.time() - start_time) < timeout:
            time.sleep(0.5)
    
        assert bot_agent.ready is True, "Bot failed to spawn inside the world in the allocated time."
        assert bot_agent.bot.position is not None, "Bot position was not initialized."
    
        original_pos = bot_agent.bot.position
        print(f"Bot spawned successfully at: {original_pos}")
    
        # 3. Test "build shelter" command execution via chat emission
        print("Testing command: 'build shelter'...")
        bot_agent.bot.emit("chat", "Player1", "build shelter")
        time.sleep(2)  # Give time for command dispatch and processing
    
        # Check if "shelter_location" is registered in the bot memory
        shelter_loc = bot_agent.memory.retrieve("shelter_location")
        assert shelter_loc is not None, "Bot did not store 'shelter_location' in memory."
        assert abs(shelter_loc.x - original_pos.x) < 1.0
        assert abs(shelter_loc.z - original_pos.z) < 1.0
    
        # 4. Test "furnish shelter" command execution via chat emission
        print("Testing command: 'furnish shelter'...")
        bot_agent.bot.emit("chat", "Player1", "furnish shelter")
        time.sleep(2)
    
    finally:
        # Clean up bot connection
        if bot_agent and hasattr(bot_agent, 'bot') and bot_agent.bot:
            try:
                bot_agent.bot.close()
            except Exception:
                pass
        # Explicitly terminate the bridge's Node.js background process to prevent orphaned processes
        try:
            import javascript
            if hasattr(javascript.config, 'event_loop') and hasattr(javascript.config.event_loop, 'process'):
                proc = javascript.config.event_loop.process
                if proc:
                    proc.terminate()
                    proc.wait(timeout=2)
        except Exception:
            pass
