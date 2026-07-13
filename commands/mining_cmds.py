import behaviors.mining as bm

async def handle_mine_line(agent, username, message):
    # Parse length if provided, e.g., "mine line 15"
    # Otherwise, default to 10 to match original logic.
    parts = message.lower().split("mine line")
    length = 10
    if len(parts) > 1:
        extracted = parts[1].strip()
        if extracted.isdigit():
            length = int(extracted)
            
    await bm.mine_line(agent, length)


def register_commands(registry):
    registry.register("mine line", handle_mine_line)
