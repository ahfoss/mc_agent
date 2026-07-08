# Contributing to Tests

This guide explains the architecture of the testing suite for the Minecraft Bot Framework and provides instructions on how to run tests, write new tests, and debug them.

---

## 1. Getting Started

### Install Test Dependencies
To install the package in editable mode along with its test-specific dependencies, run:
```bash
pip install -e .[test]
```

### Run Tests
*   **Run all tests**:
    ```bash
    pytest
    ```
*   **Run unit tests only**:
    ```bash
    pytest tests/unit
    ```
*   **Run integration tests only**:
    ```bash
    pytest tests/integration
    ```
*   **Run with a coverage report**:
    ```bash
    pytest --cov=core --cov=capabilities --cov=behaviors --cov=bots --cov=commands
    ```

> [!TIP]
> **Troubleshooting Duplicate Package Checkouts:**
> If you have multiple checkouts of this repository and imports resolve to the wrong directory (e.g., inside your virtualenv or a global site-packages path), prefix your run command with `PYTHONPATH=.` to force Python to prioritize importing files from your current workspace directory first:
> ```bash
> PYTHONPATH=. pytest tests/unit
> ```

## 2. Test Architecture

The framework splits tests into two tiers to optimize speed and reliability:

### Unit Tests (`tests/unit/`)
*   **Purpose**: Test pure Python logic (like the command routing, math calculations, and coordinate offsets) in isolation.
*   **Execution Time**: Very fast (<1s total).
*   **Key Feature**: Mocks the Node.js/JavaScript bridge library entirely (using [conftest.py](file:///c:/Users/alexa/antigravity_git/mc_agent/mc_agent/tests/conftest.py)). **No Node.js or active Minecraft server is required** to run unit tests.

### Integration Tests (`tests/integration/`)
*   **Purpose**: Verify the complete end-to-end socket connection, packet processing, and actual Mineflayer plugin lifecycle.
*   **Execution Time**: Moderate (10-30s).
*   **Key Feature**: Attempts to connect to a Minecraft server on `localhost:25565`. If none is active, it dynamically boots a local [Flying Squid](https://github.com/PrismarineJS/flying-squid) Node.js server to run the tests offline, then shuts it down. If neither is available, it skips integration tests gracefully.

---

## 3. How to Write Unit Tests

Because code in `mc_agent` imports:
```python
from javascript import require, On, off
```
any normal Python execution will try to spin up a Node.js subprocess. 

For unit tests, [conftest.py](file:///c:/Users/alexa/antigravity_git/mc_agent/mc_agent/tests/conftest.py) intercepts this import by injecting a mock module into `sys.modules['javascript']`.

### Key Mocks Available in Unit Tests:
1.  **`MockVec3`**: A mock replacement for the javascript `vec3` library object. Supports offset addition:
    ```python
    from tests.conftest import MockVec3
    v1 = MockVec3(10, 64, 10)
    v2 = v1.offset(1, 0, 0)  # Vec3(11.0, 64.0, 10.0)
    ```
2.  **`_listeners` dictionary**: When you initialize `BaseBot` under tests, the mock `@On` decorator registers all event handlers in a `_listeners` dictionary on the bot object. You can simulate events in your tests like this:
    ```python
    # Simulate spawn event
    for listener in bot.bot._listeners["spawn"]:
        listener()
    
    # Simulate incoming chat event
    for listener in bot.bot._listeners["chat"]:
        listener("PlayerName", "come to me")
    ```

### Unit Test Template for a New Capability
If you create a new capability `capabilities/woodcutting.py`:
```python
# tests/unit/test_woodcutting.py
import pytest
from unittest.mock import MagicMock
from capabilities.woodcutting import cut_tree

def test_cut_tree():
    # 1. Setup mock agent and bot
    mock_agent = MagicMock()
    mock_bot = MagicMock()
    mock_agent.bot = mock_bot
    
    # 2. Call the function
    cut_tree(mock_agent, tree_id=12)
    
    # 3. Assert correct actions were taken
    mock_bot.dig.assert_called_once()
```

---

## 4. How to Write Integration Tests

Integration tests require a running Minecraft server. We set this up automatically in `tests/integration/test_integration_shelter.py` using a pytest fixture:

```python
def test_new_behavior_integration(integration_server):
    host, port = integration_server
    
    # Connect client
    bot = BaseBot("TestClient", host, port, reconnect=False)
    
    # Wait for ready spawn state
    # ...
    
    # Assert actual bot changes or chat logs
```

---

## 5. Adding New Capabilities checklist
When adding new functionality:
1.  Write the implementation in `capabilities/` (atomic action) or `behaviors/` (complex sequence).
2.  Write unit tests under `tests/unit/` using mocked interfaces.
3.  Ensure unit tests do not import the real `javascript` Node bridge (verify `pytest tests/unit` runs in less than a second).
4.  Add integration test cases in `tests/integration/` for end-to-end command-to-world assertions.
