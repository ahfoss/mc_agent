import os
import json
from typing import Any, Dict, Type

def get_vec3() -> Type[Any]:
    """
    Dynamically loads and returns the Vec3 class, prioritizing the JavaScript-backed Vec3.
    """
    import sys
    if "javascript" in sys.modules:
        try:
            return sys.modules["javascript"].require("vec3").Vec3
        except Exception:
            pass
    from core.utils.vec3 import Vec3
    return Vec3


def _is_number(value: Any) -> bool:
    """
    Checks if a value is a number (float or int).
    """
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _is_vec3(value: Any) -> bool:
    """
    Verifies whether a given object is compatible with a 3D Vector interface.
    """
    if value is None:
        return False

    Vec3Class = get_vec3()
    try:
        if isinstance(value, Vec3Class):
            return True
    except TypeError:
        if type(value).__name__ == 'Vec3' or (hasattr(value, "constructor") and value.constructor == Vec3Class):
            return True

    if isinstance(value, dict):
        return all(key in value for key in ("x", "y", "z")) and all(_is_number(value[key]) for key in ("x", "y", "z"))

    if not (hasattr(value, "x") and hasattr(value, "y") and hasattr(value, "z")):
        return False

    try:
        x = getattr(value, "x")
        y = getattr(value, "y")
        z = getattr(value, "z")
    except Exception:
        return False

    return all(_is_number(coord) for coord in (x, y, z))


def serialize(value: Any) -> Dict[str, Any]:
    """
    Serializes standard values and vector instances into a persistent dictionary format.
    """
    if isinstance(value, (int, float, str, bool, type(None))):
        return {"type": "primitive", "value": value}
    elif _is_vec3(value):
        if isinstance(value, dict):
            coords = value
        else:
            coords = {"x": getattr(value, "x"), "y": getattr(value, "y"), "z": getattr(value, "z")}
        return {"type": "Vec3", "value": {"x": coords["x"], "y": coords["y"], "z": coords["z"]}}
    else:
        return {"type": "unknown", "value": str(value)}


def serialize_for_storage(value: Any) -> Dict[str, Any]:
    """
    Prepares values for persistent JSON storage.
    """
    if isinstance(value, dict) and value.get("type") in {"primitive", "Vec3", "unknown"} and "value" in value:
        return value
    return serialize(value)


def deserialize(serialized_value: Any) -> Any:
    """
    Reconstructs deserialized types (primitives, vectors) from their serialized representation.
    """
    if isinstance(serialized_value, dict) and serialized_value.get("type") == "primitive":
        return serialized_value["value"]
    elif isinstance(serialized_value, dict) and serialized_value.get("type") == "Vec3":
        coords = serialized_value["value"]
        Vec3Class = get_vec3()
        return Vec3Class(coords["x"], coords["y"], coords["z"])
    elif isinstance(serialized_value, dict) and all(key in serialized_value for key in ("x", "y", "z")) and all(_is_number(serialized_value[key]) for key in ("x", "y", "z")):
        Vec3Class = get_vec3()
        return Vec3Class(serialized_value["x"], serialized_value["y"], serialized_value["z"])
    elif isinstance(serialized_value, dict) and serialized_value.get("type") == "unknown":
        return serialized_value["value"]
    else:
        return serialized_value


class Memory:
    """
    Memory module that persists state to disk and restores automatically on startup.
    Saves JSON files inside the data/memory/ directory.
    """

    def __init__(self, server_port: int) -> None:
        """
        Initializes the Memory instance, computing file path based on server port.
        """
        self.path: str = f"data/memory/memory_{server_port}.json"
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """
        Restores persisted memory from storage disk.
        """
        if not os.path.exists(self.path):
            self.data = {}
            return

        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                raw_data = json.load(handle)

            self.data = {}
            for key, value in raw_data.items():
                if isinstance(value, dict) and value.get("type") == "Vec3":
                    self.data[key] = deserialize(value)
                elif isinstance(value, dict) and all(k in value for k in ("x", "y", "z")) and all(_is_number(value[k]) for k in ("x", "y", "z")):
                    self.data[key] = deserialize(value)
                else:
                    self.data[key] = value
        except (OSError, json.JSONDecodeError):
            self.data = {}

    def save(self) -> None:
        """
        Saves local memory data to files on disk.
        """
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        normalized = {}
        for key, value in self.data.items():
            normalized[key] = serialize_for_storage(value)

        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(normalized, handle, indent=2, sort_keys=True)

    def store(self, key: str, value: Any) -> None:
        """
        Associates value to a specific key in memory, storing it dynamically.
        """
        serialized_value = serialize(value)
        self.data[key] = serialized_value
        self.save()

    def retrieve(self, key: str) -> Any:
        """
        Retrieves the deserialized value associated with key.
        """
        serialized_value = self.data.get(key)
        return deserialize(serialized_value)

    def delete(self, key: str) -> None:
        """
        Deletes key-value mapping from memory.
        """
        if key in self.data:
            del self.data[key]
            self.save()
