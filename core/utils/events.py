from typing import Any, Callable

def register_event(emitter: Any, event: str, callback: Callable[..., Any]) -> None:
    """
    Registers a callback function for a specific event on the given event emitter.
    """
    if not hasattr(emitter, '_listeners') or not isinstance(emitter._listeners, dict):
        emitter._listeners = {}
    if event not in emitter._listeners:
        emitter._listeners[event] = []
    if callback not in emitter._listeners[event]:
        emitter._listeners[event].append(callback)


def unregister_event(emitter: Any, event: str, callback: Callable[..., Any]) -> None:
    """
    Unregisters a callback function for a specific event on the given event emitter.
    """
    if hasattr(emitter, '_listeners') and isinstance(emitter._listeners, dict) and event in emitter._listeners:
        if callback in emitter._listeners[event]:
            emitter._listeners[event].remove(callback)
