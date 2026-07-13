const net = require('net');
const mineflayer = require('mineflayer');
const pathfinder = require('mineflayer-pathfinder').pathfinder;
const Movements = require('mineflayer-pathfinder').Movements;
const goals = require('mineflayer-pathfinder').goals;
const vec3 = require('vec3');

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

let clientSocket = null;

// Helper to send event notification to Python
function sendEvent(type, data = {}) {
  if (clientSocket && !clientSocket.destroyed) {
    try {
      clientSocket.write(JSON.stringify({ event: type, params: data }) + '\n');
    } catch (err) {
      console.error('[Sidecar TCP Event Error]', err.message);
    }
  }
}

// Helper to send response to Python
function sendResponse(id, success, result = {}, error = null) {
  if (clientSocket && !clientSocket.destroyed) {
    try {
      clientSocket.write(JSON.stringify({ id, success, result, error }) + '\n');
    } catch (err) {
      console.error('[Sidecar TCP Response Error]', err.message);
    }
  }
}

// Bot listeners
bot.once('spawn', () => {
  sendEvent('spawn', { version: bot.version });
  // Send initial state update
  triggerStateUpdates();
});

bot.on('chat', (username, message) => {
  sendEvent('chat', { username, message });
});

bot.on('move', () => {
  if (bot.entity) {
    const pos = bot.entity.position;
    sendEvent('position_update', { position: { x: pos.x, y: pos.y, z: pos.z } });
  }
});

// Helper to poll or trigger state updates
function triggerStateUpdates() {
  if (bot.inventory) {
    const inv = bot.inventory.items().map(item => ({
      name: item.name,
      count: item.count,
      type: item.type
    }));
    sendEvent('inventory_update', { inventory: inv });
  }
}

// Monitor inventory updates
bot.on('playerCollect', () => triggerStateUpdates());
bot.on('chestLooted', () => triggerStateUpdates());

// Create TCP Server for IPC communication with Python
const server = net.createServer((socket) => {
  console.log('[Sidecar TCP] Python client connected.');
  clientSocket = socket;

  // Send state updates on connect
  triggerStateUpdates();

  let buffer = '';
  socket.on('data', async (chunk) => {
    buffer += chunk.toString('utf-8');
    let boundary = buffer.indexOf('\n');
    while (boundary !== -1) {
      const line = buffer.substring(0, boundary).trim();
      buffer = buffer.substring(boundary + 1);
      boundary = buffer.indexOf('\n');

      if (!line) continue;
      try {
        const cmd = JSON.parse(line);
        const { id, method, params } = cmd;
        await handleCommand(id, method, params);
      } catch (err) {
        console.error('[Sidecar TCP Error] Error handling payload line:', err.message);
      }
    }
  });

  socket.on('close', () => {
    console.log('[Sidecar TCP] Python client disconnected.');
    clientSocket = null;
  });

  socket.on('error', (err) => {
    console.error('[Sidecar TCP Error] Socket error:', err.message);
  });
});

// Command dispatch handler
async function handleCommand(id, method, params) {
  try {
    switch (method) {
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
        let match;
        const mcData = require('minecraft-data')(bot.version);
        if (isNaN(matching)) {
          const blockInfo = mcData.blocksByName[matching];
          if (blockInfo) {
            match = blockInfo.id;
          } else {
            sendResponse(id, true, { block: null });
            break;
          }
        } else {
          match = parseInt(matching);
        }

        const block = bot.findBlock({
          matching: match,
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
        defaultMovements.allow1by1tunnels = true;
        bot.pathfinder.setMovements(defaultMovements);

        let goal;
        if (goalRange === 0) {
          goal = new goals.GoalBlock(x, y, z);
        } else {
          goal = new goals.GoalNear(x, y, z, goalRange);
        }

        try {
          await bot.pathfinder.goto(goal);
          triggerStateUpdates();
          sendResponse(id, true);
        } catch (err) {
          sendResponse(id, false, {}, err.message);
        }
        break;
      }

      case 'dig': {
        const { x, y, z } = params;
        const block = bot.blockAt(new vec3.Vec3(x, y, z));
        if (!block) {
          sendResponse(id, false, {}, 'Block not found');
          break;
        }
        try {
          await bot.dig(block);
          triggerStateUpdates();
          sendResponse(id, true);
        } catch (err) {
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
          sendResponse(id, false, {}, `Item ${item_name} not found in inventory`);
          break;
        }

        if (bot.currentWindow) {
          bot.closeWindow(bot.currentWindow);
          await new Promise(r => setTimeout(r, 100));
        }

        await bot.equip(item, 'hand');

        const refBlock = bot.blockAt(new vec3.Vec3(x, y, z));
        if (!refBlock) {
          sendResponse(id, false, {}, 'Reference block not found');
          break;
        }

        const faceVec = new vec3.Vec3(
          x_offset !== undefined ? x_offset : 0,
          y_offset !== undefined ? y_offset : 1,
          z_offset !== undefined ? z_offset : 0
        );

        const faceCenter = refBlock.position.offset(
          0.5 + faceVec.x * 0.5,
          0.5 + faceVec.y * 0.5,
          0.5 + faceVec.z * 0.5
        );
        await bot.lookAt(faceCenter);

        try {
          await bot.placeBlock(refBlock, faceVec);
          triggerStateUpdates();
          sendResponse(id, true);
        } catch (err) {
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
          bot.closeWindow(bot.currentWindow);
          await new Promise(r => setTimeout(r, 100));
        }
        const dest = (destination === 'mainHand') ? 'hand' : (destination || 'hand');
        await bot.equip(item, dest);
        triggerStateUpdates();
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
        if (bot.currentWindow) {
          bot.closeWindow(bot.currentWindow);
          await new Promise(r => setTimeout(r, 100));
        }
        if (result.success) {
          triggerStateUpdates();
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
          const window = await bot.openBlock(ct_block);
          const items = bot.inventory.items();
          if (items.length === 0) {
            bot.closeWindow(window);
            sendResponse(id, false, {}, 'No items in inventory to equip for test');
            break;
          }
          const item = items[0];

          await bot.equip(item, 'hand');
          await bot.lookAt(ct_block.position.offset(0.5, 3.0, 0.5));
          bot.closeWindow(window);

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
        
        try {
          const items = bot.inventory.items();
          if (items.length === 0) {
            sendResponse(id, false, {}, 'No items in inventory to place for test');
            break;
          }
          const item = items[0];
          await bot.equip(item, 'hand');

          const placePromise = bot.placeBlock(refBlock, new vec3.Vec3(0, 1, 0));
          const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 2000));
          
          await Promise.race([placePromise, timeoutPromise]);
          triggerStateUpdates();
          sendResponse(id, true, { status: 'success' });
        } catch (err) {
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
            triggerStateUpdates();
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
        sendResponse(id, false, {}, 'Unknown command method: ' + method);
    }
  } catch (err) {
    sendResponse(id, false, {}, err.message);
  }
}

// Start local TCP server
const serverPort = 0; // Bind to random free port
server.listen(serverPort, '127.0.0.1', () => {
  const boundPort = server.address().port;
  console.log(`PORT=${boundPort}`); // Python reads this on stdout to know where to connect!
});
