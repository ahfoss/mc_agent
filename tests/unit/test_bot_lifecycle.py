import pytest
import sys
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from core.bot import BaseBot

from functools import wraps

# Helper decorator for async tests
def async_test(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper

@pytest.fixture
def mock_mineflayer_and_pathfinder():
    mock_mf = MagicMock()
    mock_pf = MagicMock()
    
    # Store dynamic bot version config
    mock_mf._bot_version = "1.19.2"
    
    def create_mock_bot(*args, **kwargs):
        mock_bot = MagicMock()
        mock_bot.version = mock_mf._bot_version
        mock_bot.username = "Botty"
        mock_bot._listeners = {}
        def mock_on(event, listener):
            if event not in mock_bot._listeners:
                mock_bot._listeners[event] = []
            mock_bot._listeners[event].append(listener)
        mock_bot.on = mock_on
        def mock_off(event, listener):
            if event in mock_bot._listeners and listener in mock_bot._listeners[event]:
                mock_bot._listeners[event].remove(listener)
        mock_bot.off = mock_off
        return mock_bot
        
    mock_mf.createBot.side_effect = create_mock_bot
    
    # Setup pathfinder movements mock
    mock_movements = MagicMock()
    mock_pf.Movements.return_value = mock_movements
    
    with patch('core.bot.mineflayer', mock_mf), \
         patch('core.bot.mineflayer_pathfinder', mock_pf), \
         patch('core.bot.require') as mock_req:
        
        # Configure require to return mock_movements etc.
        def mock_require_func(name):
            if name == 'minecraft-data':
                return lambda v: MagicMock()
            return MagicMock()
        mock_req.side_effect = mock_require_func
        
        yield mock_mf, mock_pf

@async_test
async def test_bot_initialization_success(mock_mineflayer_and_pathfinder):
    mock_mf, mock_pf = mock_mineflayer_and_pathfinder
    bot = BaseBot("Botty", "localhost", 25565, reconnect=False)
    await bot.start()
    
    assert bot.bot_name == "Botty"
    assert bot.ready is True  # In mock mode, start() sets ready to True
    mock_mf.createBot.assert_called_once_with({
        "host": "localhost",
        "port": 25565,
        "username": "Botty",
        "hideErrors": False
    })
    # Verify pathfinder was loaded on the created bot object
    bot.bot.loadPlugin.assert_called_once_with(mock_pf.pathfinder)

@async_test
async def test_bot_initialization_no_version(mock_mineflayer_and_pathfinder):
    mock_mf, mock_pf = mock_mineflayer_and_pathfinder
    mock_mf._bot_version = None  # Simulate connection refusal / lack of version info
    
    with pytest.raises(ConnectionError, match="failed to retrieve the Minecraft version"):
        BaseBot("Botty", "localhost", 25565)

@async_test
async def test_bot_event_spawn(mock_mineflayer_and_pathfinder):
    mock_mf, mock_pf = mock_mineflayer_and_pathfinder
    bot = BaseBot("Botty", "localhost", 25565, reconnect=False)
    await bot.start()
    
    assert bot.ready is True

@async_test
async def test_bot_event_chat_routing(mock_mineflayer_and_pathfinder):
    mock_mf, mock_pf = mock_mineflayer_and_pathfinder
    mock_registry = MagicMock()
    mock_registry.dispatch = AsyncMock(return_value=True)
    
    bot = BaseBot("Botty", "localhost", 25565, registry=mock_registry, reconnect=False)
    await bot.start()
    
    # Trigger chat event from other player
    bot.emit("chat", "Player1", "hello bot")
    
    mock_registry.dispatch.assert_called_once_with(bot, "Player1", "hello bot")

@async_test
async def test_bot_event_chat_self_ignored(mock_mineflayer_and_pathfinder):
    mock_mf, mock_pf = mock_mineflayer_and_pathfinder
    mock_registry = MagicMock()
    mock_registry.dispatch = AsyncMock(return_value=True)
    
    bot = BaseBot("Botty", "localhost", 25565, registry=mock_registry, reconnect=False)
    await bot.start()
    
    # Trigger chat event from bot itself
    bot.emit("chat", "Botty", "hello world")
        
    mock_registry.dispatch.assert_not_called()
