import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import capabilities.crafting as uc
from core.utils.vec3 import Vec3 as MockVec3

from functools import wraps

# Helper decorator for async tests
def async_test(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper

@async_test
async def test_craft_tree_already_has_item():
    mock_agent = MagicMock()
    # Bot already has 2 chests in inventory
    mock_agent.bot.get_inventory.return_value = {"chest": 2}
    
    res = await uc.craft_tree(mock_agent, "chest", quantity=2)
    assert res is True
    mock_agent.bot.craft.assert_not_called()

@async_test
async def test_craft_tree_planks_from_logs():
    mock_agent = MagicMock()
    # Needs 4 planks, has 0 planks, has 1 oak_log
    mock_agent.bot.get_inventory.return_value = {"oak_planks": 0, "oak_log": 1}
    mock_agent.bot.craft = AsyncMock(return_value=True)
    mock_agent.bot.chat = AsyncMock()
    
    with patch('capabilities.items.has_item') as mock_has:
        # First call has_item("oak_planks", 4) -> False
        # Second call has_item("oak_log", 1) -> True
        # Third call has_item("oak_planks", 4) -> True (after craft)
        mock_has.side_effect = [False, True, True]
        
        res = await uc.craft_tree(mock_agent, "oak_planks", quantity=4)
        assert res is True
        # Should craft oak_planks from oak_log (quantity = 1 craft operation)
        mock_agent.bot.craft.assert_called_once_with("oak_planks", 1, None)

@async_test
async def test_craft_tree_hierarchical_chest():
    mock_agent = MagicMock()
    # Needs chest (1), has 0 chests, has 0 planks, has 2 oak_log
    mock_agent.bot.get_inventory.return_value = {"chest": 0, "oak_planks": 0, "oak_log": 2}
    mock_agent.bot.craft = AsyncMock(return_value=True)
    mock_agent.bot.chat = AsyncMock()
    
    with patch('capabilities.items.has_item') as mock_has:
        # 1. has_item("chest", 1) -> False
        # 2. has_item("oak_planks", 8) -> False
        # 3. has_item("oak_log", 2) -> True
        # 4. has_item("oak_planks", 8) -> True (after planks craft)
        # 5. has_item("chest", 1) -> True (after chest craft)
        mock_has.side_effect = [False, False, True, True, True]
        
        res = await uc.craft_tree(mock_agent, "chest", quantity=1)
        assert res is True
        
        # Should call craft for planks (2 crafts to get 8 planks from 2 logs)
        # And then craft for chest (1 craft)
        assert mock_agent.bot.craft.call_count == 2
        mock_agent.bot.craft.assert_any_call("oak_planks", 2, None)
        mock_agent.bot.craft.assert_any_call("chest", 1, None)
