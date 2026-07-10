# Minecraft Bot Framework

A modular, extensible Python framework for creating autonomous Minecraft bots using a **Decoupled Node.js Sidecar Pattern** running `mineflayer`.

---

## Bot chat commands

### Basic commands
 - `come to me`: Moves the bot to the position of the player who sent the command.
 - `tell inventory`: Bot lists items in inventory
 - `quit`: Disconnects the bot from the server.

### Startup commands
 - `build shelter`: Builds a shelter for the bot.
 - `furnish shelter`: Furnishes the shelter with a crafting table, furnace, and chests.

### Roadmap
 - `tell location` to get bot location.

Mining commands to actually get the resources for initial furnish shelter.

Additional mining commands to strip mine for iron, coal, and other resources.

Hunting bot to get food and roast.

Lumberjack bot to get wood.

Farmer bot once an iron bucket is attained.

Mayor to orchestrate resources and assign tasks to bots.


## Architecture Overview

The framework separates high-level brain logic (Python) from high-frequency game interaction and standard Minecraft protocol handling (Node.js). They communicate asynchronously over stdin/stdout using a typed JSON payload IPC channel.

```
mc_agent/
│   config.json                  # Server connection details (Host and Port)
│   pyproject.toml               # Package manager and metadata
│   run_bot.py                   # Unified entry point
│
├───core/                        # Bot orchestrator and framework components
│   │   bot.py                   # BaseBot lifecycle and command orchestration
│   │   command_registry.py      # Dynamic command registration & routing
│   │   memory.py                # State persistence and disk serialization
│   │
│   └───utils/                   # Modular pure-Python utility classes
│           block.py             # Block representation model
│           compat.py            # Lightweight wrappers for Mineflayer-like lookups
│           events.py            # Event listener helpers
│           vec3.py              # Math vector representation with operators (+, -)
│
├───sidecar/                     # Node.js sidecar module
│       driver.js                # Mineflayer event-loop standard I/O IPC server
│       package.json             # NPM package manifest
│
├───bots/                        # Specialized bot implementations
│       farmer_bot.py            # Subclass of BaseBot for agricultural tasks
│
├───capabilities/                # Low-level atomic wrappers around the bot API
│       construction.py          # Block placing/digging actions
│       crafting.py              # Recipe lookups and block crafting
│       items.py                 # Keyword-based selectors
│       movement.py              # Pathfinder routing and translation
│
├───behaviors/                   # Complex multi-step routines coordinating capabilities
│       mining.py                # Staircase, chamber, line mining
│       shelter.py               # Shelter construction and furnishing
│
├───commands/                    # Chat command handlers mapping triggers to behaviors
│       construction_cmds.py     # Handles "build shelter", "furnish shelter", etc.
│       mining_cmds.py           # Handles "mine line"
│       movement_cmds.py         # Handles "come to me", "quit", etc.
│
└───data/                        # Persistent storage folder
    └───memory/                  # JSON files representing bot state
```

---

## Design Decisions

### 1. Decoupled Sidecar Subprocess Pattern
Instead of running JavaScript inline using a bridge library (which leads to heavy runtime dependencies and slow initialization), we run a separate Node.js subprocess (`sidecar/driver.js`). The Python brain remains fully sandboxed, highly responsive, and only exchanges actions and state updates via lightweight JSON communication.

### 2. Pure Python Capabilities & Vector Math
* All interactions, from pathfinding (`bot.move_to`) to crafting (`bot.craft`), run as standard Python functions returning standard types.
* Standardized coordinate operations (`+`, `-`) are implemented in pure Python in the `Vec3` utility class, allowing seamless navigation arithmetic without invoking any JavaScript libraries.

### 3. Modular Utilities
Testing and emulator structures are isolated. Test-only mocks live inside the testing suite (`tests/conftest.py`), while production compatibility wrappers and event helpers live in `core/utils/` to ensure a minimal, highly maintainable core codebase.

### 4. Dynamic Command Registry
Instead of a monolithic command dispatcher inside the bot event loop, we use `CommandRegistry`. Triggers are registered dynamically (either during startup in `run_bot.py` or within a subclass constructor). The bot delegates chat events to this registry, keeping event hooks clean and isolated.

### 5. Capabilities vs. Behaviors
* **Capabilities** (`capabilities/`) are simple, atomic actions that interact directly with the bot API. They are stateless and do not contain multi-step loops.
* **Behaviors** (`behaviors/`) are orchestrators that sequence multiple capabilities together to perform high-level tasks (e.g. "dig staircase down, then dig chamber, then craft crafting table, then place it").

### 6. Editable Package Installation (`pyproject.toml`)
Rather than relying on `sys.path` hacks (like `sys.path.insert(0, ...)`), the framework is structured as a standard Python package. Running `pip install -e .` registers the workspace, allowing clean absolute imports like `import capabilities.movement as um` from anywhere in the codebase.

### 7. Specialized Subclasses (`bots/`)
Specific roles (like a Farmer or a Hunter) are implemented as subclasses of `BaseBot` under `bots/`. These subclasses automatically register their own command sets and hook into custom event listeners, keeping different bot logics encapsulated.

---

## How to Run

### Setup Dependencies
Make sure you are inside your virtual environment and run:
```bash
pip install -e .
```

### Start the Bot
1. Ensure your Minecraft server is running on the host/port defined in `config.json`.
2. Spawn the **Base Bot**:
   ```bash
   python run_bot.py --type base
   ```
3. Spawn the **Farmer Bot** stub:
   ```bash
   python run_bot.py --type farmer
   ```

---

## Extending the Framework

### Registering a New Chat Command
1. Create or open a module under `commands/`.
2. Define a handler function:
   ```python
   def handle_hello(agent, username, message):
       agent.bot.chat(f"Hello, {username}!")
   ```
3. Register the trigger inside `register_commands(registry)`:
   ```python
   def register_commands(registry):
       registry.register("hello bot", handle_hello)
   ```
