import os
import json
import pytest
from unittest.mock import MagicMock
from javascript import require
MockVec3 = require('vec3').Vec3
from core.memory import Memory, serialize, deserialize, _is_vec3, _is_number

def test_is_number():
    assert _is_number(42) is True
    assert _is_number(4.2) is True
    assert _is_number("42") is True
    assert _is_number("abc") is False
    assert _is_number(None) is False

def test_is_vec3():
    assert _is_vec3(None) is False
    assert _is_vec3("not a vec") is False
    
    # Dict form
    assert _is_vec3({"x": 1, "y": 2, "z": 3}) is True
    assert _is_vec3({"x": 1, "y": 2}) is False
    assert _is_vec3({"x": 1, "y": 2, "z": "not a number"}) is False
    
    # Class form
    vec = MockVec3(10.5, 64, -20.2)
    assert _is_vec3(vec) is True
    
    # Missing attribute
    bad_obj = MagicMock()
    del bad_obj.z
    assert _is_vec3(bad_obj) is False

def test_serialization_and_deserialization():
    # Primitives
    assert serialize(42) == {"type": "primitive", "value": 42}
    assert serialize("test") == {"type": "primitive", "value": "test"}
    assert serialize(True) == {"type": "primitive", "value": True}
    assert serialize(None) == {"type": "primitive", "value": None}
    
    assert deserialize({"type": "primitive", "value": 42}) == 42
    assert deserialize({"type": "primitive", "value": "test"}) == "test"

    # Vec3
    vec = MockVec3(10.5, 64, -20)
    serialized_vec = serialize(vec)
    assert serialized_vec["type"] == "Vec3"
    assert serialized_vec["value"] == {"x": 10.5, "y": 64.0, "z": -20.0}
    
    deserialized_vec = deserialize(serialized_vec)
    assert isinstance(deserialized_vec, MockVec3)
    assert deserialized_vec.x == 10.5
    assert deserialized_vec.y == 64.0
    assert deserialized_vec.z == -20.0

    # Unknown
    obj = object()
    serialized_unk = serialize(obj)
    assert serialized_unk["type"] == "unknown"
    assert serialized_unk["value"] == str(obj)
    assert deserialize(serialized_unk) == str(obj)

def test_memory_load_save_delete(tmp_path):
    # Setup tmp path for port
    server_port = 9999
    memory = Memory(server_port=server_port)
    
    # Redirect file to pytest tmp_path
    memory.path = str(tmp_path / f"memory_{server_port}.json")
    
    # Fresh initialization has no data
    assert memory.data == {}
    
    # Store items
    memory.store("name", "Botty")
    memory.store("spawn_point", MockVec3(100, 64, 200))
    
    # Check memory file has been created on disk
    assert os.path.exists(memory.path)
    with open(memory.path, "r", encoding="utf-8") as f:
        stored_raw = json.load(f)
    assert stored_raw["name"] == {"type": "primitive", "value": "Botty"}
    assert stored_raw["spawn_point"] == {"type": "Vec3", "value": {"x": 100.0, "y": 64.0, "z": 200.0}}
    
    # Test retrieving
    assert memory.retrieve("name") == "Botty"
    retrieved_vec = memory.retrieve("spawn_point")
    assert isinstance(retrieved_vec, MockVec3)
    assert retrieved_vec.x == 100.0
    assert retrieved_vec.y == 64.0
    assert retrieved_vec.z == 200.0

    # Load in new memory instance
    new_memory = Memory(server_port=server_port)
    new_memory.path = memory.path
    new_memory.load()
    
    assert new_memory.retrieve("name") == "Botty"
    assert new_memory.retrieve("spawn_point").y == 64.0
    
    # Delete item
    new_memory.delete("name")
    assert new_memory.retrieve("name") is None
    
    # Reload and ensure delete persisted
    third_memory = Memory(server_port=server_port)
    third_memory.path = memory.path
    third_memory.load()
    assert third_memory.retrieve("name") is None
    assert third_memory.retrieve("spawn_point").z == 200.0
