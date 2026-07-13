import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from core.command_registry import CommandRegistry

def test_command_registration_and_case_insensitive_matching():
    registry = CommandRegistry()
    mock_handler = MagicMock()

    registry.register("BUILD SHELTER", mock_handler)
    
    mock_bot = MagicMock()
    
    # Matching exact case
    matched = asyncio.run(registry.dispatch(mock_bot, "Player1", "BUILD SHELTER"))
    assert matched is True
    mock_handler.assert_called_once_with(mock_bot, "Player1", "BUILD SHELTER")

    # Matching case-insensitive
    mock_handler.reset_mock()
    matched = asyncio.run(registry.dispatch(mock_bot, "Player1", "build shelter"))
    assert matched is True
    mock_handler.assert_called_once_with(mock_bot, "Player1", "build shelter")

    # Matching substring
    mock_handler.reset_mock()
    matched = asyncio.run(registry.dispatch(mock_bot, "Player1", "please build shelter right now"))
    assert matched is True
    mock_handler.assert_called_once_with(mock_bot, "Player1", "please build shelter right now")

def test_command_no_match():
    registry = CommandRegistry()
    mock_handler = MagicMock()
    registry.register("mine line", mock_handler)

    mock_bot = MagicMock()
    matched = asyncio.run(registry.dispatch(mock_bot, "Player1", "build shelter"))
    
    assert matched is False
    mock_handler.assert_not_called()
    mock_bot.log.assert_called_with("No command matched for message: 'build shelter'")

def test_command_exception_handling():
    registry = CommandRegistry()
    
    # Handler throws an exception
    mock_handler = MagicMock(side_effect=RuntimeError("Some simulation error"))
    registry.register("quit", mock_handler)

    mock_bot = MagicMock()
    mock_bot.chat = AsyncMock()
    
    # Dispatch should handle exception gracefully, returning True (since it matched)
    matched = asyncio.run(registry.dispatch(mock_bot, "Player1", "quit"))
    
    assert matched is True
    mock_handler.assert_called_once_with(mock_bot, "Player1", "quit")
    mock_bot.chat.assert_called_once_with("I encountered an error executing 'quit'.")
