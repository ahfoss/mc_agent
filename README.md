# Minecraft Bot Framework

A modular, extensible Python framework for creating autonomous Minecraft bots using `mineflayer` via the `python-javascript` bridge.

---

## Architecture Overview

The codebase is organized into discrete packages to separate concerns, enforce a clean unidirectional dependency hierarchy, and prevent circular imports:

```
mc_agent/
│   config.json                  # Server connection details (Host and Port)
│   pyproject.toml               # Package manager and metadata
│   run_bot.py                   # unified entry point
│
├───core/                        # Bot orchestrator and framework components
│       bot.py                   # BaseBot lifecycle and mineflayer connection
│       command_registry.py      # Dynamic command registration & routing
│       memory.py                # State persistence and disk serialization
│
├───bots/                        # Specialized bot implementations
│       farmer_bot.py            # Subclass of BaseBot for agricultural tasks
│
├───capabilities/                # Low-level atomic wrappers around Mineflayer APIs
│       construction.py          # Block placing/digging actions
│       crafting.py              # Recipe lookups and block crafting
│       items.py                 # Registry-based keyword selectors
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
    └───memory/                  # JSON files representing bot state (replacing _memory/)
```

---

## Design Decisions

### 1. Dynamic Command Registry
Instead of a monolithic `if/elif` command dispatcher inside the bot event loop, we use `CommandRegistry`. Triggers are registered dynamically (either during startup in `run_bot.py` or within a subclass constructor). The bot delegates chat events to this registry, keeping event hooks clean and isolated.

### 2. Capabilities vs. Behaviors
*   **Capabilities** (`capabilities/`) are simple, atomic actions that interact directly with mineflayer (e.g. "walk to coordinate X", "place block in front"). They are stateless and do not contain multi-step loops.
*   **Behaviors** (`behaviors/`) are orchestrators that sequence multiple capabilities together to perform high-level tasks (e.g. "dig staircase down, then dig chamber, then craft crafting table, then place it").

### 3. Editable Package Installation (`pyproject.toml`)
Rather than relying on `sys.path` hacks (like `sys.path.insert(0, ...)`), the framework is structured as a standard Python package. Running `pip install -e .` registers the workspace, allowing clean absolute imports like `import capabilities.movement as um` from anywhere in the codebase.

### 4. Specialized Subclasses (`bots/`)
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
