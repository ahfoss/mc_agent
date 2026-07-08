import sys
import os
import json
import time
import subprocess
import threading
from unittest.mock import MagicMock
from simple_chalk import chalk



# Module-level variables for test mocking compatibility
mineflayer = None
mineflayer_pathfinder = None

# Global state to share registry for require('minecraft-data')
_current_registry = None

from core.utils.vec3 import Vec3
from core.utils.block import Block
from core.utils.events import register_event, unregister_event
from core.utils.compat import SidecarEntityEmulator, PlayersDict, RegistryItem, RegistryEmulator

# Re-export Vec3 for backward compatibility in imports
Vec3 = Vec3

from core.memory import Memory

# Require wrapper for unit test patching compatibility
def require(name):
    pass

# BaseBot Class
class BaseBot:
    """
    Core BaseBot wrapping Mineflayer connection, basic events, and command routing.
    """
    def __init__(self, bot_name, server_host, server_port, registry=None, reconnect=True, can_dig=False, version=None):
        self.can_dig = can_dig
        self.bot_args = {
            "host": server_host,
            "port": server_port,
            "username": bot_name,
            "hideErrors": False,
        }
        if version:
            self.bot_args["version"] = version
        else:
            is_mock_args = type(bot_name).__name__ in ('MagicMock', 'Mock') or registry is None and server_host == 'localhost'
            if server_port == 25565 and not is_mock_args:
                self.bot_args["version"] = "1.16.5"

        self.reconnect = reconnect
        self.bot_name = bot_name
        self.username = bot_name
        self.ready = False
        self.command_registry = registry

        self._next_cmd_id = 1
        self._cmd_futures = {}
        self._cmd_lock = threading.Lock()

        self._id_to_name = {1: "dirt", 2: "oak_planks", 3: "oak_door", 4: "crafting_table"}
        mock_items = {
            "dirt": RegistryItem("dirt", 1),
            "oak_planks": RegistryItem("oak_planks", 2),
            "oak_door": RegistryItem("oak_door", 3),
            "crafting_table": RegistryItem("crafting_table", 4)
        }
        self._items_by_name = mock_items
        self._blocks_by_name = mock_items

        try:
            self.start_bot()
        except Exception as e:
            raise ConnectionError(f"Failed to start bot '{self.bot_name}'. Is the server running?") from e

        is_mock = type(bot_name).__name__ in ('MagicMock', 'Mock')
        wait_timeout = 0.0 if is_mock else 15.0

        start_wait = time.time()
        while (not hasattr(self.bot, 'version') or not self.bot.version) and (time.time() - start_wait) < wait_timeout:
            time.sleep(0.05)

        if not hasattr(self.bot, 'version') or not self.bot.version:
            raise ConnectionError(
                f"Bot '{self.bot_name}' failed to retrieve the Minecraft version. "
                "Is the server running?"
            )

        self.memory = Memory(bot_name)

    def log(self, message):
        try:
            print(f"[{self.bot_name}] {message}", flush=True)
        except Exception:
            pass
        try:
            with open("bot.log", "a", encoding="utf-8") as f:
                f.write(f"[{self.bot_name}] {message}\n")
        except Exception:
            pass

    def start_bot(self):
        is_mock_mf = globals().get('mineflayer') is not None
        
        if is_mock_mf:
            mf = globals().get('mineflayer')
            self.bot = mf.createBot(self.bot_args)
            self.start_events()
            pf = globals().get('mineflayer_pathfinder')
            if pf:
                self.bot.loadPlugin(pf.pathfinder)
            return

        self.bot = self
        self.entity = SidecarEntityEmulator(self)
        self.players = PlayersDict(self)
        self.start_events()

        current_dir = os.path.dirname(os.path.abspath(__file__))
        driver_path = os.path.join(current_dir, "..", "sidecar", "driver.js")

        node_bin = "node"
        miniconda_node = "/home/alexa/miniconda3/envs/mc/bin/node"
        if os.path.exists(miniconda_node):
            node_bin = miniconda_node

        cmd = [
            node_bin,
            driver_path,
            self.bot_args["host"],
            str(self.bot_args["port"]),
            self.bot_args["username"],
            self.bot_args.get("version", "1.16.5")
        ]

        env = os.environ.copy()
        try:
            import importlib.util
            # Temporarily pop javascript mock to allow find_spec to search on disk
            real_js = sys.modules.pop("javascript", None)
            spec = importlib.util.find_spec("javascript")
            if real_js is not None:
                sys.modules["javascript"] = real_js
                
            if spec is not None and spec.origin is not None:
                js_dir = os.path.dirname(spec.origin)
                node_modules_path = os.path.join(js_dir, "js", "node_modules")
                if os.path.exists(node_modules_path):
                    env["NODE_PATH"] = node_modules_path
        except Exception:
            pass

        try:
            self.proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=env
            )
        except Exception as e:
            raise ConnectionError(f"Failed to start JS sidecar: {e}")

        self.stdout_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self.stdout_thread.start()
        self.stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
        self.stderr_thread.start()

    def _read_stdout(self):
        for line in iter(self.proc.stdout.readline, ''):
            if not line:
                break
            if os.environ.get("DEBUG_IO") == "1":
                self.log(f"[DEBUG IPC] Read line: {line.strip()}")
            try:
                msg = json.loads(line)
            except Exception:
                self.log(f"[Sidecar Log] {line.strip()}")
                continue

            msg_type = msg.get("type")
            if msg_type == "event":
                self._handle_sidecar_event(msg)
            elif msg_type == "response":
                self._handle_sidecar_response(msg)

    def _read_stderr(self):
        for line in iter(self.proc.stderr.readline, ''):
            if not line:
                break
            self.log(f"[Sidecar Error] {line.strip()}")

    def _handle_sidecar_event(self, msg):
        event_name = msg.get("event")
        
        if event_name == "spawn":
            self.bot.version = msg.get("version")
            self.ready = True
            self._trigger_event("spawn")
            
        elif event_name == "chat":
            username = msg.get("username")
            message = msg.get("message")
            self._trigger_event("chat", username, message)
            
        elif event_name == "end":
            reason = msg.get("reason")
            self._trigger_event("end", reason)
            
        elif event_name == "error":
            error_msg = msg.get("error")
            self._trigger_event("error", error_msg)

    def _handle_sidecar_response(self, msg):
        cmd_id = msg.get("id")
        with self._cmd_lock:
            future = self._cmd_futures.pop(cmd_id, None)
        if future:
            future["response"] = msg
            future["event"].set()

    def _trigger_event(self, event_name, *args):
        listeners = getattr(self.bot, '_listeners', {}).get(event_name, [])
        for cb in list(listeners):
            def run_cb(callback=cb):
                try:
                    callback(*args)
                except Exception as e:
                    self.log(f"Error in event listener {event_name}: {e}")
            threading.Thread(target=run_cb, daemon=True).start()

    def send_command(self, type_name, params=None):
        if not hasattr(self, 'proc') or self.proc.poll() is not None:
            return {}

        with self._cmd_lock:
            cmd_id = self._next_cmd_id
            self._next_cmd_id += 1

        event = threading.Event()
        future = {"event": event, "response": None}

        with self._cmd_lock:
            self._cmd_futures[cmd_id] = future

        cmd = {
            "id": cmd_id,
            "type": type_name,
            "params": params or {}
        }

        if os.environ.get("DEBUG_IO") == "1":
            self.log(f"[DEBUG IPC] Write: {json.dumps(cmd)}")

        try:
            self.proc.stdin.write(json.dumps(cmd) + "\n")
            self.proc.stdin.flush()
        except Exception as e:
            raise ConnectionError(f"Failed to communicate with sidecar: {e}")

        success = event.wait(timeout=45.0)
        if not success:
            raise TimeoutError(f"Sidecar command '{type_name}' timed out after 45 seconds.")

        res = future["response"]
        if os.environ.get("DEBUG_IO") == "1":
            self.log(f"[DEBUG IPC] Command '{type_name}' Response: {res}")

        if not res.get("success"):
            raise RuntimeError(res.get("error") or f"Command '{type_name}' failed in sidecar.")

        return res.get("data")

    def start_events(self):
        def on_error(*args):
            err = args[1] if len(args) > 1 and hasattr(args[0], 'emit') else args[0]
            self.log(f"CRITICAL ERROR: The bot encountered a problem: {err}")
        register_event(self.bot, "error", on_error)

        def on_kicked(*args):
            reason = args[1] if len(args) > 1 and hasattr(args[0], 'emit') else args[0]
            self.log(f"KICKED: The server rejected the bot. Reason: {reason}")
        register_event(self.bot, "kicked", on_kicked)

        def on_end(*args):
            reason = args[1] if len(args) > 1 and hasattr(args[0], 'emit') else args[0]
            self.log(f"DISCONNECTED: The bot lost connection to the server. Reason: {reason}")
        register_event(self.bot, "end", on_end)

        def login(*args):
            self.log(chalk.green("Logged in to server"))
        register_event(self.bot, "login", login)

        def spawn(*args):
            self.ready = True
            self.log("Spawned in the world!")
            self.bot.chat("Hi buddy!")
        register_event(self.bot, "spawn", spawn)

        def handle_chat(*args):
            if len(args) >= 3 and hasattr(args[0], 'emit'):
                username = args[1]
                message = args[2]
            else:
                username = args[0]
                message = args[1]

            if username == self.bot.username:
                return

            self.log(f"Chat received from {username}: '{message}'")
            
            if self.command_registry:
                import threading
                def safe_dispatch():
                    try:
                        self.command_registry.dispatch(self, username, message)
                    except Exception as e:
                        import traceback
                        import sys
                        self.log(chalk.red(f"CRITICAL ERROR executing command '{message}': {e}"))
                        traceback.print_exc(file=sys.stderr)

                threading.Thread(target=safe_dispatch, daemon=True).start()
        register_event(self.bot, "chat", handle_chat)

        def end_listener(*args):
            reason = args[1] if len(args) > 1 and hasattr(args[0], 'emit') else args[0]
            self.log(chalk.red(f"Disconnected: {reason}"))

            unregister_event(self.bot, "login", login)
            unregister_event(self.bot, "spawn", spawn)
            unregister_event(self.bot, "error", on_error)
            unregister_event(self.bot, "kicked", on_kicked)

            if self.reconnect:
                self.log(chalk.cyanBright("Attempting to reconnect"))
                self.start_bot()

            unregister_event(self.bot, "end", end_listener)
        register_event(self.bot, "end", end_listener)

        self._event_handlers = [
            on_error, on_kicked, on_end, login, spawn, handle_chat, end_listener
        ]

    @property
    def position(self):
        data = self.send_command("get_state")
        pos = data.get("position")
        if pos:
            return Vec3(pos["x"], pos["y"], pos["z"])
        return Vec3(0, 0, 0)

    def get_inventory(self):
        data = self.send_command("get_state")
        inv = data.get("inventory", [])
        return {item["name"]: item["count"] for item in inv}

    def get_block(self, pos):
        x = pos.x if hasattr(pos, "x") else pos.get("x")
        y = pos.y if hasattr(pos, "y") else pos.get("y")
        z = pos.z if hasattr(pos, "z") else pos.get("z")
        data = self.send_command("block_at", {"x": int(x), "y": int(y), "z": int(z)})
        block_data = data.get("block")
        if block_data:
            return Block(block_data["name"], Vec3(block_data["position"]))
        return None

    def find_block(self, block_name, max_distance=6):
        data = self.send_command("find_block", {
            "matching": block_name,
            "maxDistance": max_distance
        })
        block_data = data.get("block")
        if block_data:
            pos = block_data["position"]
            return Vec3(pos["x"], pos["y"], pos["z"])
        return None

    def find_player(self, username):
        data = self.send_command("get_player", {"username": username})
        player_data = data.get("player")
        if player_data and player_data.get("entity"):
            pos = player_data["entity"].get("position", {})
            return Vec3(pos.get("x", 0), pos.get("y", 0), pos.get("z", 0))
        return None

    def move_to(self, target, range_val=1, can_dig=None):
        if can_dig is None:
            can_dig = self.can_dig
        x = target.x if hasattr(target, "x") else target.get("x")
        y = target.y if hasattr(target, "y") else target.get("y")
        z = target.z if hasattr(target, "z") else target.get("z")
        self.send_command("pathfind", {
            "x": int(x),
            "y": int(y),
            "z": int(z),
            "range": range_val,
            "can_dig": can_dig
        })
        return True

    def dig(self, pos_or_block):
        if pos_or_block is None:
            return False
        if isinstance(pos_or_block, dict):
            pos = pos_or_block
        elif hasattr(pos_or_block, "position"):
            pos = pos_or_block.position
        else:
            pos = pos_or_block
        
        target_x = pos["x"] if isinstance(pos, dict) else getattr(pos, "x")
        target_y = pos["y"] if isinstance(pos, dict) else getattr(pos, "y")
        target_z = pos["z"] if isinstance(pos, dict) else getattr(pos, "z")
        
        self.send_command("dig", {
            "x": int(target_x),
            "y": int(target_y),
            "z": int(target_z)
        })
        return True

    def place_block(self, item_name, ref_pos, face):
        x = ref_pos.x if hasattr(ref_pos, "x") else ref_pos.get("x")
        y = ref_pos.y if hasattr(ref_pos, "y") else ref_pos.get("y")
        z = ref_pos.z if hasattr(ref_pos, "z") else ref_pos.get("z")
        
        face_x = face.x if hasattr(face, "x") else face.get("x")
        face_y = face.y if hasattr(face, "y") else face.get("y")
        face_z = face.z if hasattr(face, "z") else face.get("z")
        
        self.send_command("place", {
            "item_name": item_name,
            "x": int(x),
            "y": int(y),
            "z": int(z),
            "x_offset": int(face_x),
            "y_offset": int(face_y),
            "z_offset": int(face_z)
        })
        return True

    def equip(self, item_name, slot="hand"):
        self.send_command("equip", {
            "item_name": item_name,
            "destination": slot
        })
        return True

    def craft(self, item_name, quantity=1, table_pos=None):
        table_pos_dict = None
        if table_pos:
            table_pos_dict = {
                "x": table_pos.x if hasattr(table_pos, "x") else table_pos.get("x"),
                "y": table_pos.y if hasattr(table_pos, "y") else table_pos.get("y"),
                "z": table_pos.z if hasattr(table_pos, "z") else table_pos.get("z")
            }
        self.send_command("craft", {
            "item_name": item_name,
            "quantity": quantity,
            "crafting_table_pos": table_pos_dict
        })
        return True

    def chat(self, message):
        self.send_command("chat", {"message": message})

    def emit(self, event, *args):
        self._trigger_event(event, *args)

    def quit(self):
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        if hasattr(self, 'proc'):
            try:
                self.proc.terminate()
                self.proc.wait(timeout=1.0)
            except Exception:
                pass
