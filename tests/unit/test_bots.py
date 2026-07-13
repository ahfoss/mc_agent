import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from bots.farmer_bot import FarmerBot, handle_harvest

from functools import wraps

# Helper decorator for async tests
def async_test(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper

@pytest.fixture
def mock_bot_dependencies():
    mock_mf = MagicMock()
    mock_pf = MagicMock()
    mock_bot_obj = MagicMock()
    mock_bot_obj.version = "1.19.2"
    mock_bot_obj._listeners = {}
    def mock_on(event, listener):
        if event not in mock_bot_obj._listeners:
            mock_bot_obj._listeners[event] = []
        mock_bot_obj._listeners[event].append(listener)
    mock_bot_obj.on = mock_on
    def mock_off(event, listener):
        if event in mock_bot_obj._listeners and listener in mock_bot_obj._listeners[event]:
            mock_bot_obj._listeners[event].remove(listener)
    mock_bot_obj.off = mock_off
    mock_mf.createBot.return_value = mock_bot_obj
    
    with patch('core.bot.mineflayer', mock_mf), \
         patch('core.bot.mineflayer_pathfinder', mock_pf), \
         patch('core.bot.require') as mock_req:
        
        # Configure require to return mock objects
        def mock_require_func(name):
            if name == 'minecraft-data':
                return lambda v: MagicMock()
            return MagicMock()
        mock_req.side_effect = mock_require_func
        
        yield mock_mf, mock_pf, mock_bot_obj

def test_farmer_bot_initialization(mock_bot_dependencies):
    mock_mf, mock_pf, mock_bot_obj = mock_bot_dependencies
    
    # Instantiate FarmerBot
    bot = FarmerBot("FarmerJoe", "localhost", 25565, reconnect=False)
    
    # 1. Verify inheritance and attributes
    assert bot.bot_name == "FarmerJoe"
    assert bot.command_registry is not None
    
    # 2. Verify command registrations
    registered_commands = [trigger for trigger, _ in bot.command_registry.commands]
    
    # Verify standard movement commands registered
    assert "come to me" in registered_commands
    assert "quit" in registered_commands
    
    # Verify construction commands registered
    assert "build shelter" in registered_commands
    assert "furnish shelter" in registered_commands
    
    # Verify mining commands registered
    assert "mine line" in registered_commands
    
    # Verify farming specific command registered
    assert "harvest" in registered_commands

@async_test
async def test_handle_harvest():
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_bot.chat = AsyncMock()
    mock_agent.bot = mock_bot
    
    await handle_harvest(mock_agent, "Player1", "harvest please")
    
    mock_bot.chat.assert_called_once_with("Harvesting capability is not fully implemented yet, but I am ready to farm!")
