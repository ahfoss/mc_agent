# Architecture Design: Inline Bridge vs. Decoupled Agent-Driver

This document compares the prior architecture of the Minecraft Agent (Inline Python-to-JavaScript Bridge) with the current architecture (Decoupled Agent-Driver Sidecar).

---

## 1. Prior Architecture: Inline Bridge (javascript-python)

The old setup relied on the Python `javascript` package, which ran an embedded Node.js process and used standard I/O pipes to dynamically bridge Python objects to JavaScript proxies.

### Pros
* **Single Language Codebase**: Developers write Python code that mimics JavaScript, without managing a separate `.js` file explicitly.
* **Direct Library Import**: Allows importing npm packages directly in Python (e.g., `from javascript import require`).

### Cons
* **Brittle IPC**: Any capturing of `stdout` or `stderr` (e.g., by testing frameworks like Pytest or by custom logging) interrupts the IPC communication protocol, leading to immediate socket disconnection (`socketClosed`).
* **Complex Mocking**: Testing requires monkeypatching the entire proxy layer (`MagicMock` for Javascript proxies), which is highly prone to subtle bugs and requires test-isolation runners.
* **Poor Developer Experience**: Python programmers must write code that is fundamentally JavaScript (handling JS `Vec3` classes, JS event callback arguments, and JS promise handlers wrapped in PyProxy types), defeating the purpose of a clean Python library.
* **High Latency**: Every single property access (e.g., reading `bot.entity.position.x`) goes back and forth through standard I/O translation layers, making high-frequency loops slow.

---

## 2. Current Architecture: Decoupled Agent-Driver (Sidecar Pattern)

The current architecture splits the system into two independent processes: a **JavaScript Driver** (high-frequency Minecraft world interaction using Mineflayer) and a **Python Agent** (the high-level brain). They communicate via a simple, typed standard I/O IPC channel using JSON payloads.

```text
+------------------------------+             +-------------------------------+
|     Python Process (Brain)   |             |     Node.js Process (Body)    |
|                              |             |                               |
|   +-----------------------+  |  StdIO IPC  |   +-----------------------+   |
|   |  Decoupled Python     |<==============>|   |  Standalone JS        |   |
|   |  Agent (Pure Python)  |  | (JSON Cmds) |   |  Driver (Mineflayer)  |   |
|   +-----------------------+  |             |   +-----------------------+   |
+------------------------------+             +---------------+---------------+
                                                             |
                                                             | (Minecraft Protocol)
                                                             v
                                             +-------------------------------+
                                             |       Minecraft Server        |
                                             +-------------------------------+
```

### Pros
* **100% Idiomatic Python**: Python developers write pure Python code, dealing with standard native dictionaries, lists, and floats. They do not need to know any JavaScript.
* **Hermetic & Independent Testing**: Python tests can mock standard I/O pipes with simple JSON assertions. No complex multi-process Pytest hacks are required.
* **High Reliability**: The JavaScript and Python processes run as separate operating system processes. If the JavaScript driver or Minecraft client crashes, it can be cleanly restarted by the Python process without taking down the agent.
* **Easier Debugging**: Clear separation of concern means that any Javascript exception (like pathfinding failures) gets printed cleanly to the sidecar log, and Python exceptions get standard Python tracebacks.
* **Performance**: Read and write operations can be batched or cached locally in Python, drastically reducing the IPC overhead.

### Cons
* **Process Management**: Requires the Python package to launch, monitor, and clean up the background Node.js child process.
* **API Maintenance**: Requires maintaining a simple JSON protocol mapping actions (e.g., `{"command": "pathfind"}`) to their Javascript handlers.

---

## 3. Architecture Decision

We successfully transitioned to the **Decoupled Agent-Driver Sidecar** architecture. It establishes a robust separation of concerns, guarantees reliable test execution, and ensures that python developers can contribute to and maintain the codebase with ease.
