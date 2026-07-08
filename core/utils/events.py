def register_event(emitter, event, callback):
    if not hasattr(emitter, '_listeners') or not isinstance(emitter._listeners, dict):
        emitter._listeners = {}
    if event not in emitter._listeners:
        emitter._listeners[event] = []
    if callback not in emitter._listeners[event]:
        emitter._listeners[event].append(callback)

def unregister_event(emitter, event, callback):
    if hasattr(emitter, '_listeners') and isinstance(emitter._listeners, dict) and event in emitter._listeners:
        if callback in emitter._listeners[event]:
            emitter._listeners[event].remove(callback)
