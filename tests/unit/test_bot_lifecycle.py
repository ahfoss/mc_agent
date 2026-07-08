import pytest
import sys
from unittest.mock import MagicMock, patch
from core.bot import BaseBot

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

def test_bot_initialization_success(mock_mineflayer_and_pathfinder):
    mock_mf, mock_pf = mock_mineflayer_and_pathfinder
    bot = BaseBot("Botty", "localhost", 25565, reconnect=False)
    
    assert bot.bot_name == "Botty"
    assert bot.ready is False  # Ready only after spawn event
    mock_mf.createBot.assert_called_once_with({
        "host": "localhost",
        "port": 25565,
        "username": "Botty",
        "hideErrors": False
    })
    # Verify pathfinder was loaded on the created bot object
    bot.bot.loadPlugin.assert_called_once_with(mock_pf.pathfinder)

def test_bot_initialization_no_version(mock_mineflayer_and_pathfinder):
    mock_mf, mock_pf = mock_mineflayer_and_pathfinder
    mock_mf._bot_version = None  # Simulate connection refusal / lack of version info
    
    with pytest.raises(ConnectionError, match="failed to retrieve the Minecraft version"):
        BaseBot("Botty", "localhost", 25565)

def test_bot_event_spawn(mock_mineflayer_and_pathfinder):
    mock_mf, mock_pf = mock_mineflayer_and_pathfinder
    bot = BaseBot("Botty", "localhost", 25565, reconnect=False)
    
    assert bot.ready is False
    assert hasattr(bot.bot, "_listeners")
    assert "spawn" in bot.bot._listeners
    
    # Trigger spawn listener
    for listener in list(bot.bot._listeners["spawn"]):
        listener()
        
    assert bot.ready is True
    bot.bot.chat.assert_called_with("Hi buddy!")

def test_bot_event_chat_routing(mock_mineflayer_and_pathfinder):
    mock_mf, mock_pf = mock_mineflayer_and_pathfinder
    mock_registry = MagicMock()
    
    bot = BaseBot("Botty", "localhost", 25565, registry=mock_registry, reconnect=False)
    
    # Trigger chat event from other player
    assert "chat" in bot.bot._listeners
    for listener in list(bot.bot._listeners["chat"]):
        listener("Player1", "hello bot")
        
    mock_registry.dispatch.assert_called_once_with(bot, "Player1", "hello bot")

def test_bot_event_chat_self_ignored(mock_mineflayer_and_pathfinder):
    mock_mf, mock_pf = mock_mineflayer_and_pathfinder
    mock_registry = MagicMock()
    
    bot = BaseBot("Botty", "localhost", 25565, registry=mock_registry, reconnect=False)
    
    # Trigger chat event from bot itself
    for listener in list(bot.bot._listeners["chat"]):
        listener("Botty", "hello world")
        
    mock_registry.dispatch.assert_not_called()

def test_bot_event_disconnect_and_reconnect(mock_mineflayer_and_pathfinder):
    mock_mf, mock_pf = mock_mineflayer_and_pathfinder
    
    # Case 1: Reconnect = True
    bot = BaseBot("Botty", "localhost", 25565, reconnect=True)
    mock_mf.createBot.reset_mock()
    
    # Trigger disconnect event
    assert "end" in bot.bot._listeners
    for listener in list(bot.bot._listeners["end"]):
        listener("connReset")
        
    # Since reconnect=True, start_bot should have been called again (which calls createBot)
    mock_mf.createBot.assert_called_once()

    # Case 2: Reconnect = False
    mock_mf.createBot.reset_mock()
    bot_no_reconnect = BaseBot("Botty", "localhost", 25565, reconnect=False)
    
    # Clear calls for mock_mf
    mock_mf.createBot.reset_mock()
    
    for listener in list(bot_no_reconnect.bot._listeners["end"]):
        listener("connReset")
        
    # Since reconnect=False, it should NOT try to reconnect
    mock_mf.createBot.assert_not_called()
