import capabilities.movement as um

def handle_quit(agent, username, message):
    agent.bot.chat("Goodbye!")
    agent.reconnect = False
    agent.bot.quit()

def handle_dig_to_me(agent, username, message):
    sender = agent.bot.players[username]
    if not sender or not sender.entity:
        agent.bot.chat(f"I can't see you, {username}! You might be too far away.")
        return

    player_loc = sender.entity.position
    if player_loc:
        agent.bot.move_to(player_loc, range_val=1, can_dig=True)


def handle_come_to_me(agent, username, message):
    if not agent.ready or not getattr(agent.bot, 'position', None):
        agent.bot.chat("Hold on, I'm still spawning. Try again in a moment.")
        return

    sender = agent.bot.players[username]
    if not sender or not sender.entity:
        agent.bot.chat(f"I can't see you, {username}! You might be too far away.")
        return

    player_loc = sender.entity.position
    if player_loc:
        agent.log(f"come_to_me target: {player_loc}")
        if not um.pathfind_to_goal(agent, player_loc):
            agent.bot.chat("I couldn't start moving yet. Please try again in a moment.")


def handle_teleport_to_me(agent, username, message):
    safe_username = str(username).strip()
    agent.bot.chat(f"/tp {safe_username}")


def register_commands(registry):
    registry.register("quit", handle_quit)
    registry.register("dig to me", handle_dig_to_me)
    registry.register("come to me", handle_come_to_me)
    registry.register("teleport to me", handle_teleport_to_me)
