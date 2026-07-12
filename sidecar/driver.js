const mineflayer = require('mineflayer');
const pathfinder = require('mineflayer-pathfinder').pathfinder;
const Movements = require('mineflayer-pathfinder').Movements;
const goals = require('mineflayer-pathfinder').goals;
const vec3 = require('vec3');
const readline = require('readline');

// Parse command line arguments
const host = process.argv[2] || 'localhost';
const port = parseInt(process.argv[3]) || 25565;
const username = process.argv[4] || 'TesterBot';
const version = process.argv[5] || '1.16.5';

const bot = mineflayer.createBot({
  host,
  port,
  username,
  version,
  hideErrors: false
});

bot.loadPlugin(pathfinder);

// Standard Input reader for commands from Python
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false
});

// Helper function to send JSON events to Python
function sendEvent(type, data = {}) {
  console.log(JSON.stringify({ type: 'event', event: type, ...data }));
}

// Helper function to send command responses
function sendResponse(id, success, data = {}, error = null) {
  console.log(JSON.stringify({ type: 'response', id, success, data, error }));
}

// Bot lifecycle events
bot.once('spawn', () => {
  sendEvent('spawn', {
    version: bot.version
  });
});

bot.on('chat', (username, message) => {
  sendEvent('chat', { username, message });
});

bot.on('end', (reason) => {
  sendEvent('end', { reason });
  process.exit(0);
});

bot.on('error', (err) => {
  sendEvent('error', { error: err.message });
});

// Process incoming JSON commands from Python
rl.on('line', async (line) => {
  if (!line.trim()) return;
  let cmd;
  try {
    cmd = JSON.parse(line);
  } catch (err) {
    sendEvent('error', { error: 'Malformed JSON command: ' + err.message });
    return;
  }

  const { id, type, params } = cmd;

  try {
    switch (type) {
      case 'get_state': {
        const pos = bot.entity ? bot.entity.position : null;
        const inv = bot.inventory ? bot.inventory.items().map(item => ({
          name: item.name,
          count: item.count,
          type: item.type
        })) : [];
        sendResponse(id, true, {
          position: pos ? { x: pos.x, y: pos.y, z: pos.z } : null,
          inventory: inv,
          health: bot.health,
          food: bot.food,
          window_open: bot.currentWindow !== null && bot.currentWindow !== undefined,
          held_item: bot.heldItem ? bot.heldItem.name : null
        });
        break;
      }

      case 'chat': {
        const { message } = params;
        bot.chat(message);
        sendResponse(id, true);
        break;
      }

      case 'get_player': {
        const { username } = params;
        const player = bot.players[username];
        if (player) {
          const entity = player.entity ? {
            position: {
              x: player.entity.position.x,
              y: player.entity.position.y,
              z: player.entity.position.z
            }
          } : null;
          sendResponse(id, true, {
            player: {
              username: player.username,
              entity: entity
            }
          });
        } else {
          sendResponse(id, true, { player: null });
        }
        break;
      }

      case 'block_at': {
        const { x, y, z } = params;
        const block = bot.blockAt(new vec3.Vec3(x, y, z));
        if (block) {
          sendResponse(id, true, {
            block: {
              name: block.name,
              type: block.type,
              position: { x: block.position.x, y: block.position.y, z: block.position.z }
            }
          });
        } else {
          sendResponse(id, true, { block: null });
        }
        break;
      }

      case 'find_block': {
        const { matching, maxDistance } = params;
        const block = bot.findBlock({
          matching: parseInt(matching),
          maxDistance: parseInt(maxDistance) || 5
        });
        if (block) {
          sendResponse(id, true, {
            block: {
              name: block.name,
              type: block.type,
              position: { x: block.position.x, y: block.position.y, z: block.position.z }
            }
          });
        } else {
          sendResponse(id, true, { block: null });
        }
        break;
      }

      case 'pathfind': {
        const { x, y, z, range, can_dig } = params;
        const goalRange = range !== undefined ? range : 1;
        const defaultMovements = new Movements(bot);
        defaultMovements.canDig = can_dig !== undefined ? can_dig : false;
        defaultMovements.canOpenDoors = true;
        bot.pathfinder.setMovements(defaultMovements);

        let goal;
        if (goalRange === 0) {
          goal = new goals.GoalBlock(x, y, z);
        } else {
          goal = new goals.GoalNear(x, y, z, goalRange);
        }

        try {
          await bot.pathfinder.goto(goal);
          sendResponse(id, true);
        } catch (err) {
          sendResponse(id, false, {}, err.message);
        }
        break;
      }

      case 'dig': {
        const { x, y, z } = params;
        const block = bot.blockAt(new vec3.Vec3(x, y, z));
        console.log(`[DEBUG SIDECAR dig] Bot position: ${bot.entity.position.toString()}`);
        console.log(`[DEBUG SIDECAR dig] Target block coordinates: ${x}, ${y}, ${z}`);
        if (!block) {
          console.log(`[DEBUG SIDECAR dig] Block not found at ${x}, ${y}, ${z}`);
          sendResponse(id, false, {}, 'Block not found');
          break;
        }
        console.log(`[DEBUG SIDECAR dig] Found block: ${block.name} (type: ${block.type})`);
        try {
          await bot.dig(block);
          console.log(`[DEBUG SIDECAR dig] Digging successful for block: ${block.name}`);
          sendResponse(id, true);
        } catch (err) {
          console.error(`[DEBUG SIDECAR dig] Digging failed for block ${block.name}: ${err.message}`);
          sendResponse(id, false, {}, err.message);
        }
        break;
      }

      case 'place': {
        const { item_name, x, y, z, x_offset, y_offset, z_offset } = params;
        const mcData = require('minecraft-data')(bot.version);
        const item_id = mcData.itemsByName[item_name].id;
        const item = bot.inventory.findInventoryItem(item_id, null);
        if (!item) {
          console.error(`[DEBUG PLACE ERROR] Item ${item_name} not found in inventory`);
          sendResponse(id, false, {}, `Item ${item_name} not found in inventory`);
          break;
        }

        if (bot.currentWindow) {
          console.log('[DEBUG PLACE] Closing active window before equip...');
          bot.closeWindow(bot.currentWindow);
        }

        console.log(`[DEBUG PLACE] Equipping ${item_name}...`);
        await bot.equip(item, 'hand');
        console.log(`[DEBUG PLACE] Held item after equip: ${bot.heldItem ? bot.heldItem.name : 'nothing'}`);

        const refBlock = bot.blockAt(new vec3.Vec3(x, y, z));
        if (!refBlock) {
          console.error(`[DEBUG PLACE ERROR] Reference block not found at (${x}, ${y}, ${z})`);
          sendResponse(id, false, {}, 'Reference block not found');
          break;
        }

        const faceVec = new vec3.Vec3(
          x_offset !== undefined ? x_offset : 0,
          y_offset !== undefined ? y_offset : 1,
          z_offset !== undefined ? z_offset : 0
        );
        const targetPos = refBlock.position.plus(faceVec);
        const targetBlock = bot.blockAt(targetPos);
        const targetAboveBlock = bot.blockAt(targetPos.offset(0, 1, 0));

        console.log(`[DEBUG PLACE] Reference block: ${refBlock.name} (type: ${refBlock.type}) at ${refBlock.position.toString()}`);
        console.log(`[DEBUG PLACE] Face vector: ${faceVec.toString()}`);
        console.log(`[DEBUG PLACE] Target position: ${targetPos.toString()} is currently ${targetBlock ? targetBlock.name : 'unknown'}`);
        console.log(`[DEBUG PLACE] Target above position: ${targetPos.offset(0, 1, 0).toString()} is currently ${targetAboveBlock ? targetAboveBlock.name : 'unknown'}`);
        console.log(`[DEBUG PLACE] Bot position: ${bot.entity.position.toString()}`);

        console.log(`[DEBUG PLACE] Forcing lookAt target block face...`);
        const faceCenter = refBlock.position.offset(
          0.5 + faceVec.x * 0.5,
          0.5 + faceVec.y * 0.5,
          0.5 + faceVec.z * 0.5
        );
        await bot.lookAt(faceCenter);

        try {
          console.log(`[DEBUG PLACE] Calling bot.placeBlock...`);
          await bot.placeBlock(refBlock, faceVec);
          console.log(`[DEBUG PLACE] bot.placeBlock resolved successfully!`);
          sendResponse(id, true);
        } catch (err) {
          console.error(`[DEBUG PLACE ERROR] bot.placeBlock failed: ${err.message}`);
          sendResponse(id, false, {}, err.message);
        }
        break;
      }

      case 'equip': {
        const { item_name, destination } = params;
        const mcData = require('minecraft-data')(bot.version);
        const item_id = mcData.itemsByName[item_name].id;
        const item = bot.inventory.findInventoryItem(item_id, null);
        if (!item) {
          sendResponse(id, false, {}, `Item ${item_name} not found`);
          break;
        }
        if (bot.currentWindow) {
          console.log('[DEBUG EQUIP] Closing active window before equip...');
          bot.closeWindow(bot.currentWindow);
        }
        const dest = (destination === 'mainHand') ? 'hand' : (destination || 'hand');
        await bot.equip(item, dest);
        sendResponse(id, true);
        break;
      }

      case 'recipes_for': {
        const { item_name, item_id, quantity, crafting_table_pos } = params;
        const mcData = require('minecraft-data')(bot.version);
        const resolved_id = (item_id !== undefined && item_id !== null) ? item_id : mcData.itemsByName[item_name].id;
        let ct_block = null;
        if (crafting_table_pos) {
          ct_block = bot.blockAt(new vec3.Vec3(crafting_table_pos.x, crafting_table_pos.y, crafting_table_pos.z));
        }
        const recipes = bot.recipesFor(resolved_id, null, quantity, ct_block);
        sendResponse(id, true, {
          recipes: recipes.map((recipe, index) => ({
            id: recipe.result.id,
            index: index
          }))
        });
        break;
      }

      case 'craft': {
        const { item_name, item_id, quantity, crafting_table_pos } = params;
        const mcData = require('minecraft-data')(bot.version);

        let resolved_id;
        if (item_id !== undefined && item_id !== null) {
          resolved_id = item_id;
        } else {
          const itemInfo = mcData.itemsByName[item_name];
          if (!itemInfo) {
            sendResponse(id, false, {}, `Item '${item_name}' does not exist in this Minecraft version.`);
            break;
          }
          resolved_id = itemInfo.id;
        }

        let ct_block = null;
        if (crafting_table_pos) {
          ct_block = bot.blockAt(new vec3.Vec3(crafting_table_pos.x, crafting_table_pos.y, crafting_table_pos.z));
        }
        const recipes = bot.recipesFor(resolved_id, null, quantity, ct_block);
        if (!recipes || recipes.length === 0) {
          sendResponse(id, false, {}, 'No recipes found');
          break;
        }
        if (ct_block) {
          await bot.lookAt(ct_block.position.offset(0.5, 0.5, 0.5));
        }

        const countBefore = bot.inventory.count(resolved_id);
        let checkInterval;
        const inventoryCheck = new Promise((resolve) => {
          checkInterval = setInterval(() => {
            if (bot.inventory.count(resolved_id) > countBefore) {
              clearInterval(checkInterval);
              resolve({ success: true });
            }
          }, 50);
        });

        const craftAction = (async () => {
          try {
            await bot.craft(recipes[0], quantity, ct_block);
            clearInterval(checkInterval);
            return { success: true };
          } catch (err) {
            clearInterval(checkInterval);
            if (bot.inventory.count(resolved_id) > countBefore) {
              return { success: true };
            }
            return { success: false, error: err.message };
          }
        })();

        const result = await Promise.race([inventoryCheck, craftAction]);
        if (result.success) {
          sendResponse(id, true);
        } else {
          sendResponse(id, false, {}, result.error);
        }
        break;
      }

      case 'test_case_1': {
        const { x, y, z } = params;
        const ct_block = bot.blockAt(new vec3.Vec3(x, y, z));
        if (!ct_block || ct_block.name !== 'crafting_table') {
          sendResponse(id, false, {}, 'No crafting table found at specified coordinates');
          break;
        }

        try {
          console.log('[TEST 1] Opening crafting table...');
          const window = await bot.openBlock(ct_block);
          console.log(`[TEST 1] Crafting table open. bot.currentWindow is ${bot.currentWindow ? 'active' : 'null'}`);
          
          const items = bot.inventory.items();
          if (items.length === 0) {
            bot.closeWindow(window);
            sendResponse(id, false, {}, 'No items in inventory to equip for test');
            break;
          }
          const item = items[0];

          console.log(`[TEST 1] Equipping ${item.name} while window is open...`);
          await bot.equip(item, 'hand');
          console.log(`[TEST 1] Held item after equip: ${bot.heldItem ? bot.heldItem.name : 'nothing'}`);

          await bot.lookAt(ct_block.position.offset(0.5, 3.0, 0.5));

          console.log('[TEST 1] Closing crafting window...');
          bot.closeWindow(window);

          console.log(`[TEST 1] Held item after window close: ${bot.heldItem ? bot.heldItem.name : 'nothing'}`);
          
          sendResponse(id, true, {
            held_after_equip: item.name,
            held_after_close: bot.heldItem ? bot.heldItem.name : 'nothing'
          });
        } catch (err) {
          sendResponse(id, false, {}, err.message);
        }
        break;
      }

      case 'test_case_2': {
        const { x, y, z } = params;
        const refBlock = bot.blockAt(new vec3.Vec3(x, y, z));
        console.log(`[TEST 2] Reference block type: ${refBlock ? refBlock.name : 'null'}`);
        
        try {
          const items = bot.inventory.items();
          if (items.length === 0) {
            sendResponse(id, false, {}, 'No items in inventory to place for test');
            break;
          }
          const item = items[0];
          await bot.equip(item, 'hand');

          console.log(`[TEST 2] Calling bot.placeBlock against ${refBlock ? refBlock.name : 'null'}...`);
          const placePromise = bot.placeBlock(refBlock, new vec3.Vec3(0, 1, 0));
          const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 2000));
          
          await Promise.race([placePromise, timeoutPromise]);
          sendResponse(id, true, { status: 'success' });
        } catch (err) {
          console.log(`[TEST 2] bot.placeBlock failed: ${err.message}`);
          sendResponse(id, true, { status: 'failed', error: err.message });
        }
        break;
      }

      case 'smelt': {
        const { furnace_x, furnace_y, furnace_z, input_item_name, fuel_item_name, quantity, input_count, fuel_count } = params;
        const mcData = require('minecraft-data')(bot.version);

        const furnaceBlock = bot.blockAt(new vec3.Vec3(furnace_x, furnace_y, furnace_z));
        if (!furnaceBlock || furnaceBlock.name !== 'furnace') {
          sendResponse(id, false, {}, 'Furnace block not found at specified coordinates');
          break;
        }

        const furnace = await bot.openFurnace(furnaceBlock);

        const inputItemInfo = mcData.itemsByName[input_item_name];
        const fuelItemInfo = mcData.itemsByName[fuel_item_name];
        if (!inputItemInfo) {
          furnace.close();
          sendResponse(id, false, {}, `Invalid input item name: ${input_item_name}`);
          break;
        }
        if (!fuelItemInfo) {
          furnace.close();
          sendResponse(id, false, {}, `Invalid fuel item name: ${fuel_item_name}`);
          break;
        }

        const input_id = inputItemInfo.id;
        const fuel_id = fuelItemInfo.id;

        const resolved_input_count = input_count !== undefined ? input_count : (quantity !== undefined ? quantity : 1);
        const resolved_fuel_count = fuel_count !== undefined ? fuel_count : (quantity !== undefined ? quantity : 1);

        try {
          await furnace.putFuel(fuel_id, null, resolved_fuel_count);
          await furnace.putInput(input_id, null, resolved_input_count);
        } catch (err) {
          furnace.close();
          sendResponse(id, false, {}, `Failed to load furnace: ${err.message}`);
          break;
        }

        let expectedOutput = "charcoal";
        const totalTimeout = 15000 * resolved_input_count;
        const startTime = Date.now();
        let success = false;

        while (Date.now() - startTime < totalTimeout) {
          const outItem = furnace.outputItem();
          if (outItem && outItem.name === expectedOutput && outItem.count >= resolved_input_count) {
            success = true;
            break;
          }
          await new Promise(r => setTimeout(r, 500));
        }

        if (success) {
          try {
            await furnace.takeOutput();
            furnace.close();
            sendResponse(id, true);
          } catch (err) {
            furnace.close();
            sendResponse(id, false, {}, `Failed to retrieve output: ${err.message}`);
          }
        } else {
          furnace.close();
          sendResponse(id, false, {}, 'Smelting timed out or failed');
        }
        break;
      }


      default:
        sendResponse(id, false, {}, 'Unknown command type: ' + type);
    }
  } catch (err) {
    sendResponse(id, false, {}, err.message);
  }
});
