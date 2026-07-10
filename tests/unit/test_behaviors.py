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
    
    with patch('capabilities.movement.move_absolute') as mock_move:
        bm.mine_line(mock_agent, 3)
        
        # Should dig the floor first: (10, 63, 10)
        # Then loop 3 times: dig forward (11, 64, 10), (12, 64, 10), (13, 64, 10) and move absolute
        assert mock_bot.dig.call_count == 4
        mock_move.assert_any_call(mock_agent, MockVec3(11.5, 64.0, 10.5))
        mock_move.assert_any_call(mock_agent, MockVec3(12.5, 64.0, 10.5))
        mock_move.assert_any_call(mock_agent, MockVec3(13.5, 64.0, 10.5))
        assert mock_move.call_count == 3

def test_burrow_one_block_down_positive_x():
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_bot.position = MockVec3(10, 64, 10)
    mock_agent.bot = mock_bot
    
    with patch('capabilities.movement.move_absolute') as mock_move:
        bm.burrow_one_block_down_positive_x(mock_agent)
        
        # Digs 3 blocks: (11, 65, 10), (11, 64, 10), (11, 63, 10)
        assert mock_bot.dig.call_count == 3
        mock_bot.dig.assert_any_call(MockVec3(11, 65, 10))
        mock_bot.dig.assert_any_call(MockVec3(11, 64, 10))
        mock_bot.dig.assert_any_call(MockVec3(11, 63, 10))
        # Moves to target block center: (11.5, 63.0, 10.5)
        mock_move.assert_called_once_with(mock_agent, MockVec3(11.5, 63.0, 10.5))

def test_tunnel_forward_height_2():
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_bot.position = MockVec3(10, 64, 10)
    mock_agent.bot = mock_bot
    
    with patch('capabilities.movement.move_absolute') as mock_move:
        bm.tunnel_forward(mock_agent, length=2, height=2, direction='x', direction_sign=1)
        
        # Length is 2, height is 2, so it digs 4 blocks total
        assert mock_bot.dig.call_count == 4
        mock_move.assert_any_call(mock_agent, MockVec3(11.5, 64.0, 10.5))
        mock_move.assert_any_call(mock_agent, MockVec3(12.5, 64.0, 10.5))
        assert mock_move.call_count == 2

def test_tunnel_forward_height_3():
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_bot.position = MockVec3(10, 64, 10)
    mock_agent.bot = mock_bot
    
    with patch('capabilities.movement.move_absolute') as mock_move:
        bm.tunnel_forward(mock_agent, length=2, height=3, direction='x', direction_sign=1)
        
        # Length is 2, height is 3, so it digs 6 blocks total
        assert mock_bot.dig.call_count == 6
        mock_move.assert_any_call(mock_agent, MockVec3(11.5, 64.0, 10.5))
        mock_move.assert_any_call(mock_agent, MockVec3(12.5, 64.0, 10.5))
        assert mock_move.call_count == 2

def test_tunnel_forward_invalid_height():
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_bot.position = MockVec3(10, 64, 10)
    mock_agent.bot = mock_bot
    
    with patch('capabilities.movement.move_absolute') as mock_move:
        bm.tunnel_forward(mock_agent, length=1, height=5, direction='x')
        # Height should default back to 2, logging a warning
        mock_agent.log.assert_called_with("Height must be 2 or 3. Defaulting to 2.")
        assert mock_bot.dig.call_count == 2
        mock_move.assert_called_once_with(mock_agent, MockVec3(11.5, 64.0, 10.5))

def test_dig_chamber_volume():
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_bot.position = MockVec3(10, 64, 10)
    mock_agent.bot = mock_bot
    
    # Store dug positions
    dug_positions = set()
    def mock_dig(pos):
        dug_positions.add((int(pos.x), int(pos.y), int(pos.z)))
    mock_bot.dig.side_effect = mock_dig
    
    # Mock move_absolute and move_relative_to_self to update bot position
    def mock_move_abs(agent, target):
        mock_bot.position = target
    def mock_move_rel(agent, dx, dy, dz):
        curr = mock_bot.position
        mock_bot.position = MockVec3(curr.x + dx, curr.y + dy, curr.z + dz)
    with patch('capabilities.movement.move_absolute', side_effect=mock_move_abs), \
         patch('capabilities.movement.move_relative_to_self', side_effect=mock_move_rel):
        bm.dig_chamber(mock_agent, xdim=4, zdim=3)
        
    # Verify that all blocks in the 4x3x3 chamber (starting relative to (10, 64, 10)) are dug
    expected_blocks = set()
    for x in range(11, 15):
        for z in range(10, 13):
            for y in range(64, 67):
                expected_blocks.add((x, y, z))
                
    # Verify no block outside the chamber was dug
    assert dug_positions == expected_blocks

def test_dig_staircase_volume():
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_bot.position = MockVec3(10, 64, 10)
    mock_agent.bot = mock_bot
    
    # Setup mock memory store/retrieve
    mem_store = {}
    mock_agent.memory.retrieve.side_effect = lambda key: mem_store.get(key)
    mock_agent.memory.store.side_effect = lambda key, val: mem_store.__setitem__(key, val)
    mock_agent.memory.delete.side_effect = lambda key: mem_store.pop(key, None)
    
    dug_positions = set()
    def mock_dig(pos):
        dug_positions.add((int(pos.x), int(pos.y), int(pos.z)))
    mock_bot.dig.side_effect = mock_dig
    
    def mock_move(agent, target):
        mock_bot.position = target
    with patch('capabilities.movement.move_absolute', side_effect=mock_move):
        bm.dig_staircase_down(mock_agent, depth=3)
        
    # Verify that exactly the staircase blocks are dug
    expected_blocks = set()
    for step in range(3):
        ref_x = 10 + step
        ref_y = 64 - step
        expected_blocks.add((ref_x + 1, ref_y + 1, 10))
        expected_blocks.add((ref_x + 1, ref_y, 10))
        expected_blocks.add((ref_x + 1, ref_y - 1, 10))
        
    assert dug_positions == expected_blocks


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
    mock_bot.get_block.return_value = None
    mock_bot.get_inventory.return_value = {"oak_planks": 64, "cobblestone": 64, "charcoal": 5}
    mock_agent.bot = mock_bot
    
    # Mock memory retrieval
    def retrieve_mock(key):
        if key == "shelter_location":
            return MockVec3(100, 64, 100)
        elif key == "crafting_table_position":
            return MockVec3(100, 56, 106)
        elif key == "adjacent_crafting_table":
            return MockVec3(100, 56, 105)
        return None
    mock_agent.memory.retrieve.side_effect = retrieve_mock
    
    with patch('capabilities.movement.move_absolute') as mock_move_abs, \
         patch('capabilities.movement.move_relative_to_self') as mock_move_rel, \
         patch('capabilities.crafting.craft_tree') as mock_craft_tree, \
         patch('capabilities.construction.place_block_on_ground_relative_to_self') as mock_place, \
         patch('capabilities.construction.place_block_relative_to_block') as mock_place_rel_block, \
         patch('capabilities.crafting.craft_any_door') as mock_craft_door:
         
         mock_craft_door.return_value = "oak_door"
         mock_craft_tree.return_value = True  # Successful crafting of table, furnace, and chests
         
         bs.furnish_shelter1(mock_agent)
         
         # 1. Navigation
         mock_move_abs.assert_any_call(mock_agent, MockVec3(109, 56, 105))
         
         # 2. Craft & Place crafting table
         mock_craft_tree.assert_any_call(mock_agent, "crafting_table")
         mock_place.assert_any_call(mock_agent, "crafting_table", 0, -1, 1)
         mock_agent.memory.store.assert_any_call("crafting_area", MockVec3(100, 56, 105))
         mock_agent.memory.store.assert_any_call("adjacent_crafting_table", MockVec3(100, 56, 105))
         mock_agent.memory.store.assert_any_call("crafting_table_position", MockVec3(100, 56, 106))
         
         # 3. Craft & Place door
         mock_craft_door.assert_called_once_with(mock_agent, quantity=1)
         mock_move_rel.assert_any_call(mock_agent, 0, 0, -5)
         mock_move_rel.assert_any_call(mock_agent, -1, 0, 0)
         mock_place.assert_any_call(mock_agent, "oak_door", -1, 1, 0)

         # Walk back to adjacent crafting table spot
         mock_move_abs.assert_any_call(mock_agent, MockVec3(100, 56, 105))

         # 4. Craft & Place furnace at offset (1, 0, 0)
         mock_craft_tree.assert_any_call(mock_agent, "furnace", quantity=1, crafting_table_loc=MockVec3(100, 56, 106))
         mock_place_rel_block.assert_any_call(mock_agent, "furnace", MockVec3(100, 56, 106), 1, 0, 0)
        # 5. Craft & Place chests at offset (+4, 0, 0) and (+5, 0, 0) after moving close (+4, 0, -1) and (+5, 0, -1)
         mock_craft_tree.assert_any_call(mock_agent, "chest", quantity=2, crafting_table_loc=MockVec3(100, 56, 106))
         mock_move_abs.assert_any_call(mock_agent, MockVec3(104, 56, 105))
         mock_move_abs.assert_any_call(mock_agent, MockVec3(105, 56, 105))
         mock_place_rel_block.assert_any_call(mock_agent, "chest", MockVec3(100, 56, 106), 4, 0, 0)
         mock_place_rel_block.assert_any_call(mock_agent, "chest", MockVec3(100, 56, 106), 5, 0, 0)
         
         # 6. Craft torches recursively
         mock_craft_tree.assert_any_call(mock_agent, "torch", quantity=4, crafting_table_loc=MockVec3(100, 56, 106))

def test_furnish_shelter1_door_craft_fails():
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_bot.position = MockVec3(100, 56, 105)
    mock_bot.get_block.return_value = None
    mock_bot.get_inventory.return_value = {"oak_planks": 64, "cobblestone": 64, "charcoal": 5}
    mock_agent.bot = mock_bot
    
    # Mock memory retrieval
    def retrieve_mock(key):
        if key == "shelter_location":
            return MockVec3(100, 64, 100)
        elif key == "crafting_table_position":
            return MockVec3(100, 56, 106)
        elif key == "adjacent_crafting_table":
            return MockVec3(100, 56, 105)
        return None
    mock_agent.memory.retrieve.side_effect = retrieve_mock
    
    with patch('capabilities.movement.move_absolute') as mock_move_abs, \
         patch('capabilities.movement.move_relative_to_self') as mock_move_rel, \
         patch('capabilities.crafting.craft_tree'), \
         patch('capabilities.construction.place_block_on_ground_relative_to_self'), \
         patch('capabilities.construction.place_block_relative_to_block'), \
         patch('capabilities.crafting.craft_any_door') as mock_craft_door:
         
         mock_craft_door.return_value = None  # Door crafting fails due to lack of wood
         
         bs.furnish_shelter1(mock_agent)
         
         # Verify it logs that door crafting failed and does not place or move relative for door
         mock_bot.chat.assert_any_call("Could not craft a door.")
         # No relative move is performed since navigation was direct
         mock_move_rel.assert_not_called()

def test_build_shelter_integration_volume():
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_bot.position = MockVec3(100, 64, 100)
    mock_agent.bot = mock_bot
    
    # Real-like memory store
    mem_store = {}
    mock_agent.memory.retrieve.side_effect = lambda key: mem_store.get(key)
    mock_agent.memory.store.side_effect = lambda key, val: mem_store.__setitem__(key, val)
    mock_agent.memory.delete.side_effect = lambda key: mem_store.pop(key, None)
    
    dug_positions = set()
    def mock_dig(pos):
        dug_positions.add((int(pos.x), int(pos.y), int(pos.z)))
    mock_bot.dig.side_effect = mock_dig
    
    def mock_move_abs(agent, target):
        mock_bot.position = target
    def mock_move_rel(agent, dx, dy, dz):
        curr = mock_bot.position
        mock_bot.position = MockVec3(curr.x + dx, curr.y + dy, curr.z + dz)
    with patch('capabilities.movement.move_absolute', side_effect=mock_move_abs), \
         patch('capabilities.movement.move_relative_to_self', side_effect=mock_move_rel):
        bs.build_shelter(mock_agent)
        
    # Expected blocks dug by staircase (depth=8, starting at 100, 64, 100)
    expected_blocks = set()
    for step in range(8):
        ref_x = 100 + step
        ref_y = 64 - step
        expected_blocks.add((ref_x + 1, ref_y + 1, 100))
        expected_blocks.add((ref_x + 1, ref_y, 100))
        expected_blocks.add((ref_x + 1, ref_y - 1, 100))
        
    # Expected landing/chamber start block: (108, 56, 100)
    # The chamber (8x8x3) starts at (109, 56, 100) and ends at (116, 58, 107)
    for x in range(109, 117):
        for z in range(100, 108):
            for y in range(56, 59):
                expected_blocks.add((x, y, z))
                
    # Verify that all expected blocks were dug exactly
    assert dug_positions == expected_blocks


def test_furnish_shelter1_smelt_charcoal():
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_bot.position = MockVec3(100, 56, 105)
    mock_bot.get_block.return_value = None
    
    inventory = {"oak_planks": 64, "cobblestone": 64, "oak_log": 10}
    mock_bot.get_inventory.side_effect = lambda: inventory
    
    def send_command_mock(cmd_type, params, *args, **kwargs):
        if cmd_type == "smelt" and params.get("fuel_item_name") == "oak_planks":
            inventory["charcoal"] = 1
            inventory["oak_log"] -= 1
            inventory["oak_planks"] -= 1
        elif cmd_type == "smelt" and params.get("fuel_item_name") == "charcoal":
            inventory["charcoal"] = 5
            inventory["oak_log"] -= 5
        return {}
    mock_bot.send_command.side_effect = send_command_mock
    mock_agent.bot = mock_bot
    
    # Mock memory retrieval
    def retrieve_mock(key):
        if key == "shelter_location":
            return MockVec3(100, 64, 100)
        elif key == "crafting_table_position":
            return MockVec3(100, 56, 106)
        elif key == "adjacent_crafting_table":
            return MockVec3(100, 56, 105)
        return None
    mock_agent.memory.retrieve.side_effect = retrieve_mock
    
    with patch('capabilities.movement.move_absolute') as mock_move_abs, \
         patch('capabilities.movement.move_relative_to_self') as mock_move_rel, \
         patch('capabilities.crafting.craft_tree') as mock_craft_tree, \
         patch('capabilities.construction.place_block_on_ground_relative_to_self') as mock_place, \
         patch('capabilities.construction.place_block_relative_to_block') as mock_place_rel_block, \
         patch('capabilities.crafting.craft_any_door') as mock_craft_door:
         
         mock_craft_door.return_value = "oak_door"
         mock_craft_tree.return_value = True
         
         bs.furnish_shelter1(mock_agent)
         
         # Verify navigation back to adjacent crafting table spot
         mock_move_abs.assert_any_call(mock_agent, MockVec3(100, 56, 105))
         
         # Verify first smelt call
         mock_bot.send_command.assert_any_call("smelt", {
             "furnace_x": 101,
             "furnace_y": 56,
             "furnace_z": 106,
             "input_item_name": "oak_log",
             "fuel_item_name": "oak_planks",
             "input_count": 1,
             "fuel_count": 1
         }, timeout=75.0)
         
         # Verify second smelt call
         mock_bot.send_command.assert_any_call("smelt", {
             "furnace_x": 101,
             "furnace_y": 56,
             "furnace_z": 106,
             "input_item_name": "oak_log",
             "fuel_item_name": "charcoal",
             "input_count": 5,
             "fuel_count": 1
         }, timeout=75.0)
         
         # Verify recursive torch crafting call
         mock_craft_tree.assert_any_call(mock_agent, "torch", quantity=4, crafting_table_loc=MockVec3(100, 56, 106))
