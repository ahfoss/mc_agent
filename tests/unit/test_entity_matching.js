// Test script to verify the new getCleanEntityName, isLivingEntity, and matchEntity functions.

// Helper to clean entity names (removes namespaces like "minecraft:")
function getCleanEntityName(entity) {
  if (!entity) return '';
  
  let rawName = '';
  // Handle dropped items
  if (entity.name === 'item' || entity.name === 'Item' || entity.name === 'item_stack') {
    if (typeof entity.getDroppedItem === 'function') {
      const dropped = entity.getDroppedItem();
      if (dropped && dropped.name) {
        rawName = dropped.name;
      }
    }
  }

  if (!rawName) {
    rawName = entity.name || entity.displayName || '';
  }
  
  if (!rawName) return '';
  const parts = rawName.split(':');
  return parts[parts.length - 1].toLowerCase();
}

// Helper to check if an entity represents a living entity/mob (excluding players, items, projectiles, etc.)
function isLivingEntity(entity) {
  if (!entity) return false;
  const nonLivingTypes = new Set(['player', 'object', 'orb', 'other']);
  return !nonLivingTypes.has(entity.type);
}

// Helper to match an entity against a search type
function matchEntity(entity, type) {
  if (!entity) return false;
  if (type === undefined) {
    return isLivingEntity(entity);
  }

  const searchType = type.toLowerCase();

  // Check if it matches as a living entity/mob
  if (isLivingEntity(entity)) {
    const cleanName = getCleanEntityName(entity);
    if (cleanName === searchType) return true;
    if (entity.displayName && entity.displayName.toLowerCase() === searchType) return true;
  }

  // Check if it matches as a dropped item
  if (entity.name === 'item' || entity.name === 'Item' || entity.name === 'item_stack') {
    const cleanName = getCleanEntityName(entity);
    if (cleanName === searchType) return true;
  }

  return false;
}

// Test Runner
const tests = [
  {
    name: "Control Case: Standard matching name and type",
    entity: { type: 'mob', name: 'chicken' },
    searchType: 'chicken',
    expected: true
  },
  {
    name: "Hypothesis 1: Namespaced name (minecraft:chicken)",
    entity: { type: 'mob', name: 'minecraft:chicken' },
    searchType: 'chicken',
    expected: true
  },
  {
    name: "Hypothesis 1: Case-insensitivity check (Chicken vs chicken)",
    entity: { type: 'mob', name: 'Chicken' },
    searchType: 'chicken',
    expected: true
  },
  {
    name: "Hypothesis 2: Entity type is 'animal' instead of 'mob'",
    entity: { type: 'animal', name: 'chicken' },
    searchType: 'chicken',
    expected: true
  },
  {
    name: "Hypothesis 2: Entity type is 'passive' instead of 'mob'",
    entity: { type: 'passive', name: 'chicken' },
    searchType: 'chicken',
    expected: true
  },
  {
    name: "Hypothesis 2: Entity type is 'hostile' (skeleton)",
    entity: { type: 'hostile', name: 'skeleton' },
    searchType: 'skeleton',
    expected: true
  },
  {
    name: "Filter check: Entity is 'player' (should be excluded from living entities search)",
    entity: { type: 'player', name: 'Player1' },
    searchType: 'Player1',
    expected: false
  },
  {
    name: "Filter check: Entity is dropped 'item' (should be excluded if no type given)",
    entity: { type: 'other', name: 'item', getDroppedItem: () => ({ name: 'raw_porkchop' }) },
    searchType: undefined,
    expected: false
  },
  {
    name: "Dropped item check: Match raw_porkchop specifically",
    entity: { type: 'other', name: 'item', getDroppedItem: () => ({ name: 'raw_porkchop' }) },
    searchType: 'raw_porkchop',
    expected: true
  },
  {
    name: "Dropped item check: Match namespaced item minecraft:raw_chicken",
    entity: { type: 'other', name: 'item', getDroppedItem: () => ({ name: 'minecraft:raw_chicken' }) },
    searchType: 'raw_chicken',
    expected: true
  }
];

console.log("=== RUNNING ENTITY MATCHING TESTS ===");
let passedAll = true;

tests.forEach((t) => {
  const result = matchEntity(t.entity, t.searchType);
  const passed = result === t.expected;
  
  if (passed) {
    console.log(`[PASS] ${t.name}: Match result: ${result}`);
  } else {
    console.log(`[FAIL] ${t.name}`);
    console.log(`       Entity: ${JSON.stringify(t.entity)}`);
    console.log(`       Search Type: '${t.searchType}'`);
    console.log(`       Expected match: ${t.expected}, but got: ${result}`);
    passedAll = false;
  }
});

if (passedAll) {
  console.log("\nAll entity matching checks passed successfully!");
} else {
  console.log("\nSome tests failed. Please refine the matching helpers.");
}
