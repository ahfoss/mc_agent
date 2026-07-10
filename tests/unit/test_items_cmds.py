from unittest.mock import MagicMock
from commands.items_cmds import handle_tell_inventory

def test_handle_tell_inventory_empty():
    mock_agent = MagicMock()
    mock_agent.bot.get_inventory.return_value = {}
    
    handle_tell_inventory(mock_agent, "Player1", "tell inventory")
    mock_agent.bot.chat.assert_called_with("My inventory is empty.")

def test_handle_tell_inventory_with_items():
    mock_agent = MagicMock()
    mock_agent.bot.get_inventory.return_value = {"oak_planks": 64, "cobblestone": 8, "dirt": 0}
    
    handle_tell_inventory(mock_agent, "Player1", "tell inventory")
    mock_agent.bot.chat.assert_called_with("Inventory: 8 cobblestone, 64 oak_planks")
