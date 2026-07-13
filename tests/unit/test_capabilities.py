import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from core.utils.vec3 import Vec3 as MockVec3

# Import our capability modules
import capabilities.items as ui
import capabilities.movement as um
import capabilities.construction as ucon
import capabilities.crafting as uc

from functools import wraps

# Helper decorator for async tests
def async_test(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper

# ==================== ITEMS CAPABILITY TESTS ====================

def test_get_item_keywords():
    mock_agent = MagicMock()
    
    # Setup mock registry blocksArray
    block1 = MagicMock()
    block1.name = "oak_log"
    block1.id = 17
    block2 = MagicMock()
    block2.name = "stone"
    block2.id = 1
    block3 = MagicMock()
    block3.name = "birch_log"
    block3.id = 18

    mock_agent.bot.registry.blocksArray = [block1, block2, block3]

    res = ui.get_item_keywords(mock_agent, ["log"])
    assert len(res) == 2
    assert res["oak_log"] == 17
    assert res["birch_log"] == 18

    res_logs = ui.get_log_keywords(mock_agent)
    assert "oak_log" in res_logs


# ==================== MOVEMENT CAPABILITY TESTS ====================

@async_test
async def test_pathfind_to_goal_success():
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_bot.move_to = AsyncMock(return_value=True)
    mock_agent.bot = mock_bot
    
    goal = MockVec3(10, 64, 20)
    
    res = await um.pathfind_to_goal(mock_agent, goal)
    
    assert res is True
    mock_bot.move_to.assert_called_once_with(goal, range_val=1)

@async_test
async def test_move_absolute():
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_bot.move_to = AsyncMock()
    mock_agent.bot = mock_bot
    
    await um.move_absolute(mock_agent, {"x": 5, "y": 60, "z": -5})
    
    mock_bot.move_to.assert_called_once_with(MockVec3(5, 60, -5), range_val=0)

@async_test
async def test_move_relative_to_self():
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_bot.move_to = AsyncMock()
    
    mock_bot.position = MockVec3(10, 64, 10)
    mock_agent.bot = mock_bot
    
    await um.move_relative_to_self(mock_agent, 1, 0, -2)
    
    mock_bot.move_to.assert_called_once_with(MockVec3(11, 64, 8), range_val=0)


# ==================== CONSTRUCTION CAPABILITY TESTS ====================

@async_test
async def test_place_block_on_ground_relative_to_self_success():
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_bot.place_block = AsyncMock()
    mock_bot.chat = AsyncMock()
    
    mock_bot.get_inventory.return_value = {"dirt": 5}
    mock_bot.position = MockVec3(10, 64, 10)
    mock_agent.bot = mock_bot
    
    await ucon.place_block_on_ground_relative_to_self(mock_agent, "dirt", 0, -1, 1)
    
    mock_bot.place_block.assert_called_once_with("dirt", MockVec3(10, 63, 11), MockVec3(0, 1, 0))
    mock_bot.chat.assert_called_with("Block placed successfully!")

@async_test
async def test_place_block_on_ground_relative_to_self_missing_item():
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_bot.chat = AsyncMock()
    
    mock_bot.get_inventory.return_value = {}
    mock_agent.bot = mock_bot
    
    await ucon.place_block_on_ground_relative_to_self(mock_agent, "dirt", 0, -1, 1)
    
    mock_bot.chat.assert_called_with("Screw you! You didn't give me any dirt!!!.")

@async_test
async def test_place_block_on_ground_one_forward():
    with patch('capabilities.construction.place_block_on_ground_relative_to_self', new_callable=AsyncMock) as mock_place:
        mock_agent = MagicMock()
        await ucon.place_block_on_ground_one_forward(mock_agent, "dirt")
        mock_place.assert_called_once_with(mock_agent, "dirt", 1, -1, 0)

@async_test
async def test_place_block_relative_to_block_success():
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_bot.place_block = AsyncMock()
    mock_bot.chat = AsyncMock()
    
    mock_bot.get_inventory.return_value = {"furnace": 1}
    mock_agent.bot = mock_bot
    
    ref_pos = MockVec3(100, 60, 100)
    res = await ucon.place_block_relative_to_block(mock_agent, "furnace", ref_pos, 1, 0, 0)
    
    assert res is True
    mock_bot.place_block.assert_called_once_with("furnace", MockVec3(101, 59, 100), MockVec3(0, 1, 0))
    mock_bot.chat.assert_called_with("furnace placed relative to block!")

@async_test
async def test_place_block_relative_to_block_missing():
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_bot.chat = AsyncMock()
    
    mock_bot.get_inventory.return_value = {}
    mock_agent.bot = mock_bot
    
    ref_pos = MockVec3(100, 60, 100)
    res = await ucon.place_block_relative_to_block(mock_agent, "furnace", ref_pos, 1, 0, 0)
    
    assert res is False
    mock_bot.chat.assert_called_with("I don't have a furnace to place.")


# ==================== CRAFTING CAPABILITY TESTS ====================

@async_test
async def test_craft_direct_success():
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_bot.craft = AsyncMock(return_value=True)
    mock_agent.bot = mock_bot
    
    res = await uc.craft_direct(mock_agent, "crafting_table", quantity=1)
    
    assert res is True
    mock_bot.craft.assert_called_once_with("crafting_table", 1, None)

@async_test
async def test_craft_direct_no_recipe():
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_bot.craft = AsyncMock(return_value=False)
    mock_bot.chat = AsyncMock()
    mock_agent.bot = mock_bot
    
    res = await uc.craft_direct(mock_agent, "crafting_table")
    
    assert res is False
    mock_bot.chat.assert_called_with("No recipe found for crafting table.")

@async_test
async def test_craft_tree():
    with patch('capabilities.crafting.craft_direct', new_callable=AsyncMock) as mock_direct:
        mock_direct.return_value = True
        mock_agent = MagicMock()
        mock_agent.bot.get_inventory.return_value = {"oak_planks": 8}
        assert await uc.craft_tree(mock_agent, "chest") is True
        mock_direct.assert_called_once_with(mock_agent, "chest", 1, None)

@async_test
async def test_craft_any_door_no_crafting_area():
    mock_agent = MagicMock()
    mock_agent.memory.retrieve.return_value = None
    
    res = await uc.craft_any_door(mock_agent)
    assert res is None

@async_test
async def test_craft_any_door_no_table_block():
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_bot.find_block = AsyncMock(return_value=None)
    
    mock_agent.memory.retrieve.side_effect = lambda key: MockVec3(10, 64, 10) if key == "crafting_area" else None
    mock_agent.bot = mock_bot
    
    res = await uc.craft_any_door(mock_agent)
    assert res is None
    mock_bot.find_block.assert_called_once_with("crafting_table", max_distance=5)

@async_test
async def test_craft_any_door_success():
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_bot.get_inventory.return_value = {"oak_planks": 6}
    mock_agent.bot = mock_bot
    
    mock_agent.memory.retrieve.side_effect = lambda key: MockVec3(10, 64, 10) if key == "crafting_area" else None
    
    table_pos = MockVec3(11, 64, 10)
    mock_bot.find_block = AsyncMock(return_value=table_pos)
    mock_bot.craft = AsyncMock(return_value=True)
    
    res = await uc.craft_any_door(mock_agent, quantity=1)
    
    assert res == "oak_door"
    mock_bot.craft.assert_any_call("oak_door", 1, table_pos)

@async_test
async def test_craft_any_door_memory_success():
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_bot.get_inventory.return_value = {"oak_planks": 6}
    mock_bot.find_block = AsyncMock()
    mock_agent.bot = mock_bot
    
    def retrieve_mock(key):
        if key == "crafting_area":
            return MockVec3(10, 64, 10)
        elif key == "crafting_table_position":
            return MockVec3(10, 63, 11)
        return None
    mock_agent.memory.retrieve.side_effect = retrieve_mock
    mock_bot.craft = AsyncMock(return_value=True)
    
    res = await uc.craft_any_door(mock_agent, quantity=1)
    
    assert res == "oak_door"
    mock_bot.find_block.assert_not_called()
    mock_bot.craft.assert_any_call("oak_door", 1, MockVec3(10, 63, 11))
