# pyrefly: ignore [missing-import]
import pytest
from unittest.mock import MagicMock, patch
from javascript import require
MockVec3 = require('vec3').Vec3

# Import our behavior modules
import behaviors.mining as bm
import behaviors.shelter as bs

# ==================== MINING BEHAVIORS TESTS ====================

def test_mine_line():
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_bot.position = MockVec3(10, 64, 10)
    mock_agent.bot = mock_bot
    
    with patch('capabilities.movement.move_relative_to_self') as mock_move:
        bm.mine_line(mock_agent, 3)
        
        # Should dig the floor first: (10, 63, 10)
        # Then loop 3 times: dig forward (11, 64, 10) and move relative 1, 0, 0
        assert mock_bot.dig.call_count == 4
        mock_move.assert_called_with(mock_agent, 1, 0, 0)
        assert mock_move.call_count == 3

def test_burrow_one_block_down_positive_x():
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_bot.position = MockVec3(10, 64, 10)
    mock_agent.bot = mock_bot
    
    with patch('capabilities.movement.move_relative_to_self') as mock_move:
        bm.burrow_one_block_down_positive_x(mock_agent)
        
        # Digs 3 blocks: (11, 65, 10), (11, 64, 10), (11, 63, 10)
        assert mock_bot.dig.call_count == 3
        mock_bot.dig.assert_any_call(MockVec3(11, 65, 10))
        mock_bot.dig.assert_any_call(MockVec3(11, 64, 10))
        mock_bot.dig.assert_any_call(MockVec3(11, 63, 10))
        # Moves 1, -1, 0
        mock_move.assert_called_once_with(mock_agent, 1, -1, 0)

def test_tunnel_forward_height_2():
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_bot.position = MockVec3(10, 64, 10)
    mock_agent.bot = mock_bot
    
    with patch('capabilities.movement.move_relative_to_self') as mock_move:
        bm.tunnel_forward(mock_agent, length=2, height=2, direction='x', direction_sign=1)
        
        # Length is 2, height is 2, so it digs 4 blocks total
        assert mock_bot.dig.call_count == 4
        mock_move.assert_called_with(mock_agent, 1, 0, 0)
        assert mock_move.call_count == 2

def test_tunnel_forward_height_3():
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_bot.position = MockVec3(10, 64, 10)
    mock_agent.bot = mock_bot
    
    with patch('capabilities.movement.move_relative_to_self') as mock_move:
        bm.tunnel_forward(mock_agent, length=2, height=3, direction='x', direction_sign=1)
        
        # Length is 2, height is 3, so it digs 6 blocks total
        assert mock_bot.dig.call_count == 6
        mock_move.assert_called_with(mock_agent, 1, 0, 0)
        assert mock_move.call_count == 2

def test_tunnel_forward_invalid_height():
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_bot.position = MockVec3(10, 64, 10)
    mock_agent.bot = mock_bot
    
    with patch('capabilities.movement.move_relative_to_self') as mock_move:
        bm.tunnel_forward(mock_agent, length=1, height=5, direction='x')
        # Height should default back to 2, logging a warning
        mock_agent.log.assert_called_with("Height must be 2 or 3. Defaulting to 2.")
        assert mock_bot.dig.call_count == 2

def test_dig_chamber():
    mock_agent = MagicMock()
    
    with patch('behaviors.mining.tunnel_forward') as mock_tunnel, \
         patch('capabilities.movement.move_relative_to_self') as mock_move:
         
         bm.dig_chamber(mock_agent, xdim=4, zdim=3)
         
         # Should call tunnel_forward and move_relative_to_self to route chamber coordinates
         assert mock_tunnel.call_count == 5
         assert mock_move.call_count == 3

def test_dig_staircase_down():
    mock_agent = MagicMock()
    
    with patch('behaviors.mining.burrow_one_block_down_positive_x') as mock_burrow:
        bm.dig_staircase_down(mock_agent, depth=5)
        
        assert mock_burrow.call_count == 5


# ==================== SHELTER BEHAVIORS TESTS ====================

def test_build_shelter():
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_bot.position = MockVec3(100, 64, 100)
    mock_agent.bot = mock_bot
    
    with patch('behaviors.mining.dig_staircase_down') as mock_stair, \
         patch('behaviors.mining.dig_chamber') as mock_chamber:
          
         bs.build_shelter(mock_agent)
          
         mock_agent.memory.store.assert_called_once_with("shelter_location", MockVec3(100, 64, 100))
         mock_stair.assert_called_once_with(mock_agent, 8)
         mock_chamber.assert_called_once_with(mock_agent, 8, 8)

def test_furnish_shelter1_no_coordinates():
    mock_agent = MagicMock()
    mock_agent.memory.retrieve.return_value = None  # No coordinates stored
    
    bs.furnish_shelter1(mock_agent)
    
    mock_agent.bot.chat.assert_called_with("Coordinates not found in memory. Have you already built the shelter?")

def test_furnish_shelter1_success():
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_bot.position = MockVec3(100, 56, 105)
    mock_agent.bot = mock_bot
    
    # Coordinates exist in memory
    mock_agent.memory.retrieve.side_effect = lambda key: MockVec3(100, 64, 100) if key == "shelter_location" else None
    
    with patch('capabilities.movement.move_absolute') as mock_move_abs, \
         patch('capabilities.movement.move_relative_to_self') as mock_move_rel, \
         patch('capabilities.crafting.craft_direct') as mock_craft_direct, \
         patch('capabilities.construction.place_block_on_ground_relative_to_self') as mock_place, \
         patch('capabilities.crafting.craft_any_door') as mock_craft_door:
         
         mock_craft_door.return_value = "oak_door"
         
         bs.furnish_shelter1(mock_agent)
         
         # 1. Navigation
         mock_move_abs.assert_called_once_with(mock_agent, MockVec3(109, 56, 105))
         
         # 2. Craft & Place crafting table
         mock_craft_direct.assert_called_once_with(mock_agent, "crafting_table")
         mock_place.assert_any_call(mock_agent, "crafting_table", 0, -1, 1)
         mock_agent.memory.store.assert_called_once_with("crafting_area", MockVec3(100, 56, 105))
         
         # 3. Craft & Place door
         mock_craft_door.assert_called_once_with(mock_agent, quantity=1)
         mock_move_rel.assert_any_call(mock_agent, 0, 0, -5)
         mock_move_rel.assert_any_call(mock_agent, -1, 0, 0)
         mock_place.assert_any_call(mock_agent, "oak_door", -1, 1, 0)

def test_furnish_shelter1_door_craft_fails():
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_bot.position = MockVec3(100, 56, 105)
    mock_agent.bot = mock_bot
    
    mock_agent.memory.retrieve.side_effect = lambda key: MockVec3(100, 64, 100) if key == "shelter_location" else None
    
    with patch('capabilities.movement.move_absolute') as mock_move_abs, \
         patch('capabilities.movement.move_relative_to_self') as mock_move_rel, \
         patch('capabilities.crafting.craft_direct'), \
         patch('capabilities.construction.place_block_on_ground_relative_to_self'), \
         patch('capabilities.crafting.craft_any_door') as mock_craft_door:
         
         mock_craft_door.return_value = None  # Door crafting fails due to lack of wood
         
         bs.furnish_shelter1(mock_agent)
         
         # Verify it logs that door crafting failed and does not place or move relative for door
         mock_bot.chat.assert_any_call("Could not craft a door (missing planks).")
         # No relative move is performed since navigation was direct
         mock_move_rel.assert_not_called()
