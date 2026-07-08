import sys
from unittest.mock import MagicMock

# Subclass list to mock Javascript bridge arrays with .length properties
class MockJSArray(list):
    @property
    def length(self):
        return len(self)

# 2. Setup mock bridge object
mock_js = MagicMock()

def mock_on(emitter, event):
    try:
        listeners = emitter._listeners
        if not isinstance(listeners, dict):
            emitter._listeners = {}
            listeners = emitter._listeners
    except Exception:
        emitter._listeners = {}
        listeners = emitter._listeners

    def decorator(f):
        if event not in listeners:
            listeners[event] = []
        listeners[event].append(f)
        return f
    return decorator

def mock_off(emitter, event, handler):
    try:
        listeners = emitter._listeners
        if isinstance(listeners, dict) and event in listeners:
            if handler in listeners[event]:
                listeners[event].remove(handler)
    except Exception:
        pass

mock_js.On = mock_on
mock_js.off = mock_off

# Mock Vec3 class to represent vec3 library objects
class MockVec3:
    def __init__(self, x=0, y=0, z=0):
        if isinstance(x, dict):
            self.x = float(x.get("x", 0))
            self.y = float(x.get("y", 0))
            self.z = float(x.get("z", 0))
        elif hasattr(x, "x") and hasattr(x, "y") and hasattr(x, "z"):
            self.x = float(getattr(x, "x"))
            self.y = float(getattr(x, "y"))
            self.z = float(getattr(x, "z"))
        else:
            self.x = float(x)
            self.y = float(y)
            self.z = float(z)

    def offset(self, dx, dy, dz):
        return MockVec3(self.x + dx, self.y + dy, self.z + dz)

    def __add__(self, other):
        if isinstance(other, MockVec3):
            return MockVec3(self.x + other.x, self.y + other.y, self.z + other.z)
        elif hasattr(other, 'x') and hasattr(other, 'y') and hasattr(other, 'z'):
            return MockVec3(self.x + getattr(other, 'x'), self.y + getattr(other, 'y'), self.z + getattr(other, 'z'))
        elif isinstance(other, dict):
            return MockVec3(self.x + other.get("x", 0), self.y + other.get("y", 0), self.z + other.get("z", 0))
        elif isinstance(other, (tuple, list)) and len(other) == 3:
            return MockVec3(self.x + other[0], self.y + other[1], self.z + other[2])
        return NotImplemented

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if isinstance(other, MockVec3):
            return MockVec3(self.x - other.x, self.y - other.y, self.z - other.z)
        elif hasattr(other, 'x') and hasattr(other, 'y') and hasattr(other, 'z'):
            return MockVec3(self.x - getattr(other, 'x'), self.y - getattr(other, 'y'), self.z - getattr(other, 'z'))
        elif isinstance(other, dict):
            return MockVec3(self.x - other.get("x", 0), self.y - other.get("y", 0), self.z - other.get("z", 0))
        elif isinstance(other, (tuple, list)) and len(other) == 3:
            return MockVec3(self.x - other[0], self.y - other[1], self.z - other[2])
        return NotImplemented

    def __rsub__(self, other):
        if isinstance(other, (tuple, list)) and len(other) == 3:
            return MockVec3(other[0] - self.x, other[1] - self.y, other[2] - self.z)
        elif hasattr(other, 'x') and hasattr(other, 'y') and hasattr(other, 'z'):
            return MockVec3(getattr(other, 'x') - self.x, getattr(other, 'y') - self.y, getattr(other, 'z') - self.z)
        elif isinstance(other, dict):
            return MockVec3(other.get("x", 0) - self.x, other.get("y", 0) - self.y, other.get("z", 0) - self.z)
        return NotImplemented

    def __eq__(self, other):
        if not hasattr(other, 'x') or not hasattr(other, 'y') or not hasattr(other, 'z'):
            return False
        return self.x == other.x and self.y == other.y and self.z == other.z

    def __str__(self):
        return f"Vec3({self.x}, {self.y}, {self.z})"

    def __repr__(self):
        return str(self)

# Wire require() mock to return Vec3 class and standard blocks/items
def require_mock(module_name):
    if module_name == 'vec3':
        mock_vec3_mod = MagicMock()
        mock_vec3_mod.Vec3 = MockVec3
        return mock_vec3_mod
    elif module_name == 'minecraft-data':
        def mc_data_builder(version):
            import core.bot
            if core.bot._current_registry is not None:
                return core.bot._current_registry
            
            mock_data = MagicMock()
            item_dirt = MagicMock()
            item_dirt.id = 1
            item_dirt.name = "dirt"
            
            item_wood = MagicMock()
            item_wood.id = 2
            item_wood.name = "oak_planks"
            
            item_door = MagicMock()
            item_door.id = 3
            item_door.name = "oak_door"

            mock_data.itemsByName = {
                "dirt": item_dirt,
                "oak_planks": item_wood,
                "oak_door": item_door,
                "crafting_table": MagicMock(id=4, name="crafting_table"),
                "chest": MagicMock(id=5, name="chest")
            }

            mock_data.blocksByName = {
                "dirt": MagicMock(id=1, name="dirt"),
                "oak_planks": MagicMock(id=2, name="oak_planks"),
                "crafting_table": MagicMock(id=4, name="crafting_table")
            }
            return mock_data
        return mc_data_builder
    elif module_name == 'mineflayer-pathfinder':
        class PathfinderEmulatorModule:
            class goals:
                class GoalNear:
                    def __init__(self, x, y, z, range_val=1):
                        self.x = x
                        self.y = y
                        self.z = z
                        self.range = range_val
                class GoalBlock:
                    def __init__(self, x, y, z):
                        self.x = x
                        self.y = y
                        self.z = z
                        self.range = 0
            class pathfinder:
                pass
            Movements = lambda *args: MagicMock()
        PathfinderEmulatorModule.pathfinder.goals = PathfinderEmulatorModule.goals
        return PathfinderEmulatorModule
    return MagicMock()

mock_js.require = require_mock

# Inject the mock javascript module for unit tests to mock and intercept (conditional on not integration)
import sys
is_integration = any("tests/integration" in arg for arg in sys.argv)
if not is_integration:
    sys.modules['javascript'] = mock_js
