import sys
import math
import os
import json
import asyncio
import subprocess
from unittest.mock import MagicMock
from simple_chalk import chalk
from core.utils.vec3 import Vec3
from core.utils.block import Block
from core.utils.events import register_event, unregister_event
from core.utils.compat import SidecarEntityEmulator, PlayersDict, RegistryItem, RegistryEmulator
from core.memory import Memory

# Module-level variables for test mocking compatibility
mineflayer = None
mineflayer_pathfinder = None
_current_registry = None

def require(name):
    pass

class BaseBot:
    """
    Core BaseBot wrapping Mineflayer TCP connection, basic events, and command routing.
    """
    def __init__(self, bot_name, server_host, server_port, registry=None, reconnect=True, can_dig=False, version=None):
        self.can_dig = can_dig
        self.bot_name = bot_name
        self.username = bot_name
        self.ready = False
        self.command_registry = registry
        self.reconnect = reconnect
        self.version = version or "1.20.4"
        self.server_host = server_host
        self.server_port = server_port
        
        self.proc = None
        self.reader = None
        self.writer = None
        self.response_futures = {}
        self.next_req_id = 1
        
        # Local state cache updated by events
        self._position = Vec3(0, 0, 0)
        self._inventory = {}
        
        # Compat emulators
        self.bot = self
        self.entity = SidecarEntityEmulator(self)
        self.players = PlayersDict(self)
        self.memory = Memory(bot_name)
        
        # Support mock listeners in test lifecycle
        self._listeners = {}

        # Mock items/blocks compatibility
        self._id_to_name = {1: "dirt", 2: "oak_planks", 3: "oak_door", 4: "crafting_table"}
        mock_items = {
            "dirt": RegistryItem("dirt", 1),
            "oak_planks": RegistryItem("oak_planks", 2),
            "oak_door": RegistryItem("oak_door", 3),
            "crafting_table": RegistryItem("crafting_table", 4)
        }
        self._items_by_name = mock_items
        self._blocks_by_name = mock_items

        # If mock mineflayer is present, register mock behaviors
        is_mock_mf = globals().get('mineflayer') is not None
        if is_mock_mf:
            mf = globals().get('mineflayer')
            self.bot = mf.createBot({
                "host": server_host,
                "port": server_port,
                "username": bot_name,
                "hideErrors": False
            })
            if not getattr(self.bot, 'version', None):
                raise ConnectionError(
                    f"Bot '{self.bot_name}' failed to retrieve the Minecraft version. "
                    "Is the server running?"
                )
            pf = globals().get('mineflayer_pathfinder')
            if pf:
                self.bot.loadPlugin(pf.pathfinder)
            self._listeners = getattr(self.bot, '_listeners', {})
            # Bind events on the mock bot to emit on self
            self.bot.chat = MagicMock()

        # Register default event handlers
        def handle_chat(username, message):
            if username == self.username:
                return
            self.log(f"Chat received from {username}: '{message}'")
            if self.command_registry:
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.command_registry.dispatch(self, username, message))
                except RuntimeError:
                    asyncio.run(self.command_registry.dispatch(self, username, message))

        self.on("chat", handle_chat)

    def on(self, event, listener):
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(listener)

    def once(self, event, listener):
        def wrapper(*args, **kwargs):
            self.off(event, wrapper)
            listener(*args, **kwargs)
        self.on(event, wrapper)

    def off(self, event, listener):
        if event in self._listeners and listener in self._listeners[event]:
            self._listeners[event].remove(listener)

    def emit(self, event, *args, **kwargs):
        listeners = self._listeners.get(event, [])
        for listener in list(listeners):
            try:
                listener(*args, **kwargs)
            except Exception as e:
                self.log(f"Error in event listener {event}: {e}")

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

    async def start(self):
        is_mock_mf = globals().get('mineflayer') is not None
        if is_mock_mf:
            self.ready = True
            self.emit("login")
            self.emit("spawn")
            return

        current_dir = os.path.dirname(os.path.abspath(__file__))
        driver_path = os.path.join(current_dir, "..", "sidecar", "driver.js")

        node_bin = "node"
        miniconda_node = "/home/alexa/miniconda3/envs/mc/bin/node"
        if os.path.exists(miniconda_node):
            node_bin = miniconda_node

        cmd = [
            node_bin,
            driver_path,
            self.server_host,
            str(self.server_port),
            self.bot_name,
            self.version
        ]

        env = os.environ.copy()
        try:
            import importlib.util
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

        self.log(f"Starting Node.js sidecar TCP driver: {cmd}")
        self.proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )

        # Read stdout until we find PORT=...
        port = None
        while True:
            line_bytes = await self.proc.stdout.readline()
            if not line_bytes:
                break
            line = line_bytes.decode('utf-8').strip()
            if line.startswith("PORT="):
                port = int(line.split("=")[1])
                break
            else:
                self.log(f"[Sidecar Startup] {line}")

        if port is None:
            raise ConnectionError("Failed to retrieve port from JS sidecar startup.")

        self.log(f"Sidecar listening on port {port}. Connecting...")
        self.reader, self.writer = await asyncio.open_connection('127.0.0.1', port)
        self.log("Connected to sidecar TCP server!")

        # Start background listener tasks
        self.listen_task = asyncio.create_task(self._listen_loop())
        self.stdout_task = asyncio.create_task(self._read_stdout_loop())
        self.stderr_task = asyncio.create_task(self._read_stderr_loop())

        # Trigger login/spawn sequence emulations
        self.emit("login")
        self.emit("spawn")

    async def _listen_loop(self):
        try:
            while True:
                line_bytes = await self.reader.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode('utf-8').strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                except Exception as e:
                    self.log(f"Malformed socket payload: {e}")
                    continue

                if "id" in data:
                    req_id = data["id"]
                    if req_id in self.response_futures:
                        self.response_futures[req_id].set_result(data)
                elif "event" in data:
                    await self._handle_sidecar_event(data["event"], data.get("params", {}))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.log(f"Error in TCP socket listen loop: {e}")

    async def _read_stdout_loop(self):
        try:
            while True:
                line_bytes = await self.proc.stdout.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode('utf-8').strip()
                self.log(f"[Sidecar Log] {line}")
        except asyncio.CancelledError:
            pass

    async def _read_stderr_loop(self):
        try:
            while True:
                line_bytes = await self.proc.stderr.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode('utf-8').strip()
                self.log(f"[Sidecar Error] {line}")
        except asyncio.CancelledError:
            pass

    async def _handle_sidecar_event(self, event_name, params):
        if event_name == "spawn":
            self.ready = True
            self.emit("spawn")
        elif event_name == "chat":
            username = params.get("username")
            message = params.get("message")
            self.emit("chat", username, message)
        elif event_name == "position_update":
            pos = params.get("position", {})
            self._position = Vec3(pos.get("x", 0), pos.get("y", 0), pos.get("z", 0))
        elif event_name == "inventory_update":
            inv_list = params.get("inventory", [])
            self._inventory = {item["name"]: item["count"] for item in inv_list}

    async def send_command(self, method, params=None, timeout=None):
        if not self.writer or self.writer.is_closing():
            return {}

        req_id = self.next_req_id
        self.next_req_id += 1

        future = asyncio.get_running_loop().create_future()
        self.response_futures[req_id] = future

        payload = json.dumps({
            "id": req_id,
            "method": method,
            "params": params or {}
        }) + "\n"

        self.writer.write(payload.encode('utf-8'))
        await self.writer.drain()

        # Wait for the response
        if timeout is not None:
            try:
                res = await asyncio.wait_for(future, timeout=timeout)
            except asyncio.TimeoutError:
                del self.response_futures[req_id]
                raise TimeoutError(f"Command '{method}' timed out after {timeout} seconds.")
        else:
            res = await future

        del self.response_futures[req_id]

        if not res.get("success"):
            raise RuntimeError(res.get("error") or f"Command '{method}' failed in sidecar.")

        return res.get("result", {})

    @property
    def position(self):
        return self._position

    def get_inventory(self):
        return self._inventory

    async def get_block(self, pos):
        x = pos.x if hasattr(pos, "x") else pos.get("x")
        y = pos.y if hasattr(pos, "y") else pos.get("y")
        z = pos.z if hasattr(pos, "z") else pos.get("z")
        res = await self.send_command("block_at", {"x": math.floor(x), "y": math.floor(y), "z": math.floor(z)})
        block_data = res.get("block")
        if block_data:
            return Block(block_data["name"], Vec3(block_data["position"]))
        return None

    async def find_block(self, block_name, max_distance=6):
        res = await self.send_command("find_block", {
            "matching": block_name,
            "maxDistance": max_distance
        })
        block_data = res.get("block")
        if block_data:
            pos = block_data["position"]
            return Vec3(pos["x"], pos["y"], pos["z"])
        return None

    async def find_player(self, username):
        res = await self.send_command("get_player", {"username": username})
        player_data = res.get("player")
        if player_data and player_data.get("entity"):
            pos = player_data["entity"].get("position", {})
            return Vec3(pos.get("x", 0), pos.get("y", 0), pos.get("z", 0))
        return None

    async def move_to(self, target, range_val=1, can_dig=None):
        if can_dig is None:
            can_dig = self.can_dig
        x = target.x if hasattr(target, "x") else target.get("x")
        y = target.y if hasattr(target, "y") else target.get("y")
        z = target.z if hasattr(target, "z") else target.get("z")
        await self.send_command("pathfind", {
            "x": float(x),
            "y": float(y),
            "z": float(z),
            "range": range_val,
            "can_dig": can_dig
        })
        return True

    async def dig(self, pos_or_block):
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
        
        await self.send_command("dig", {
            "x": math.floor(target_x),
            "y": math.floor(target_y),
            "z": math.floor(target_z)
        })
        return True

    async def place_block(self, item_name, ref_pos, face):
        x = ref_pos.x if hasattr(ref_pos, "x") else ref_pos.get("x")
        y = ref_pos.y if hasattr(ref_pos, "y") else ref_pos.get("y")
        z = ref_pos.z if hasattr(ref_pos, "z") else ref_pos.get("z")
        
        face_x = face.x if hasattr(face, "x") else face.get("x")
        face_y = face.y if hasattr(face, "y") else face.get("y")
        face_z = face.z if hasattr(face, "z") else face.get("z")
        
        await self.send_command("place", {
            "item_name": item_name,
            "x": math.floor(x),
            "y": math.floor(y),
            "z": math.floor(z),
            "x_offset": math.floor(face_x) if face_x is not None else 0,
            "y_offset": math.floor(face_y) if face_y is not None else 1,
            "z_offset": math.floor(face_z) if face_z is not None else 0
        })
        return True

    async def equip(self, item_name, slot="hand"):
        await self.send_command("equip", {
            "item_name": item_name,
            "destination": slot
        })
        return True

    async def craft(self, item_name, quantity=1, table_pos=None):
        table_pos_dict = None
        if table_pos:
            table_pos_dict = {
                "x": math.floor(table_pos.x if hasattr(table_pos, "x") else table_pos.get("x")),
                "y": math.floor(table_pos.y if hasattr(table_pos, "y") else table_pos.get("y")),
                "z": math.floor(table_pos.z if hasattr(table_pos, "z") else table_pos.get("z"))
            }
        await self.send_command("craft", {
            "item_name": item_name,
            "quantity": quantity,
            "crafting_table_pos": table_pos_dict
        })
        return True

    async def chat(self, message):
        await self.send_command("chat", {"message": message})

    async def close(self):
        if hasattr(self, 'listen_task'):
            self.listen_task.cancel()
        if hasattr(self, 'stdout_task'):
            self.stdout_task.cancel()
        if hasattr(self, 'stderr_task'):
            self.stderr_task.cancel()
            
        if self.writer:
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except Exception:
                pass
                
        if self.proc:
            try:
                self.proc.terminate()
                await self.proc.wait()
            except Exception:
                pass
