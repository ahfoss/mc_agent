import capabilities.movement as um

async def handle_quit(agent, username, message):
    await agent.bot.chat("Goodbye!")
    agent.reconnect = False
    await agent.bot.close()


async def handle_dig_to_me(agent, username, message):
    player_loc = await agent.bot.find_player(username)
    if not player_loc:
        await agent.bot.chat(f"I can't see you, {username}! You might be too far away.")
        return

    await agent.bot.move_to(player_loc, range_val=1, can_dig=True)


async def handle_come_to_me(agent, username, message):
    if not agent.ready or not getattr(agent.bot, 'position', None):
        await agent.bot.chat("Hold on, I'm still spawning. Try again in a moment.")
        return

    player_loc = await agent.bot.find_player(username)
    if not player_loc:
        await agent.bot.chat(f"I can't see you, {username}! You might be too far away.")
        return

    agent.log(f"come_to_me target: {player_loc}")
    if not await um.pathfind_to_goal(agent, player_loc):
        await agent.bot.chat("I couldn't start moving yet. Please try again in a moment.")


async def handle_teleport_to_me(agent, username, message):
    safe_username = str(username).strip()
    await agent.bot.chat(f"/tp {safe_username}")


async def handle_tell_location(agent, username, message):
    pos = agent.bot.position
    if pos:
        x = round(pos.x, 1)
        y = round(pos.y, 1)
        z = round(pos.z, 1)
        await agent.bot.chat(f"My coordinates are X: {x}, Y: {y}, Z: {z}")
    else:
        await agent.bot.chat("I don't know my coordinates yet.")


def register_commands(registry):
    registry.register("quit", handle_quit)
    registry.register("dig to me", handle_dig_to_me)
    registry.register("come to me", handle_come_to_me)
    registry.register("teleport to me", handle_teleport_to_me)
    registry.register("tell location", handle_tell_location)
