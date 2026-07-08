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
  // Get minecraft-data registries
  const mcData = require('minecraft-data')(bot.version);
  sendEvent('spawn', {
    version: bot.version,
    registry: {
      itemsByName: mcData.itemsByName,
      blocksByName: mcData.blocksByName
    }
  });
});

bot.on('chat', (username, message) => {
  sendEvent('chat', { username, message });
});

bot.on('playerChat', (username, message) => {
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
          food: bot.food
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
        const { x, y, z, range } = params;
        const goalRange = range !== undefined ? range : 1;
        const defaultMovements = new Movements(bot);
        bot.pathfinder.setMovements(defaultMovements);

        await new Promise((resolve, reject) => {
          bot.pathfinder.setGoal(new goals.GoalNear(x, y, z, goalRange));

          function onGoalReached() {
            cleanup();
            resolve();
          }
          function onGoalFailed(err) {
            cleanup();
            reject(err);
          }
          function cleanup() {
            bot.removeListener('goal_reached', onGoalReached);
            bot.removeListener('path_update', onPathUpdate);
          }
          let pathUpdates = 0;
          function onPathUpdate(results) {
            pathUpdates++;
            if (results.status === 'noPath' && pathUpdates > 5) {
              cleanup();
              reject(new Error('No path found to goal'));
            }
          }
          bot.on('goal_reached', onGoalReached);
          bot.on('path_update', onPathUpdate);
        });

        sendResponse(id, true);
        break;
      }

      case 'dig': {
        const { x, y, z } = params;
        const block = bot.blockAt(new vec3.Vec3(x, y, z));
        if (!block) {
          sendResponse(id, false, {}, 'Block not found');
          break;
        }
        await bot.dig(block);
        sendResponse(id, true);
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
        await bot.equip(item, 'hand');
        const refBlock = bot.blockAt(new vec3.Vec3(x, y, z));
        if (!refBlock) {
          sendResponse(id, false, {}, 'Reference block not found');
          break;
        }
        const faceVec = new vec3.Vec3(x_offset || 0, y_offset || 1, z_offset || 0);
        await bot.placeBlock(refBlock, faceVec);
        sendResponse(id, true);
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

      default:
        sendResponse(id, false, {}, 'Unknown command type: ' + type);
    }
  } catch (err) {
    sendResponse(id, false, {}, err.message);
  }
});
