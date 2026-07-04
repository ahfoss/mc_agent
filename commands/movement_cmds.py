from javascript import require
import capabilities.movement as um

mineflayer_pathfinder = require("mineflayer-pathfinder")


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

    # Temporarily set to digging allowed
    mc_data = require('minecraft-data')(agent.bot.version)
    movements = mineflayer_pathfinder.Movements(agent.bot, mc_data)
    movements.canDig = True
    agent.bot.pathfinder.setMovements(movements)

    if player_loc:
        um.pathfind_to_goal(agent, player_loc)

    # Revert to bot's default digging setting
    movements = mineflayer_pathfinder.Movements(agent.bot, mc_data)
    movements.canDig = agent.can_dig
    agent.bot.pathfinder.setMovements(movements)


def handle_come_to_me(agent, username, message):
    if not agent.ready or not getattr(agent.bot, 'entity', None):
        agent.bot.chat("Hold on, I'm still spawning. Try again in a moment.")
        return

    sender = agent.bot.players[username]
    if not sender or not sender.entity:
        agent.bot.chat(f"I can't see you, {username}! You might be too far away.")
        return

    player_loc = sender.entity.position
    if player_loc:
        # Reinitialize movement settings before pathfinding.
        mc_data = require('minecraft-data')(agent.bot.version)
        movements = mineflayer_pathfinder.Movements(agent.bot, mc_data)
        movements.canDig = agent.can_dig
        agent.bot.pathfinder.setMovements(movements)

        location = {
            "x": float(player_loc.x),
            "y": float(player_loc.y),
            "z": float(player_loc.z),
        }
        agent.log(f"come_to_me target: {location}")
        if not um.pathfind_to_goal(agent, location):
            agent.bot.chat("I couldn't start moving yet. Please try again in a moment.")


def handle_teleport_to_me(agent, username, message):
    safe_username = str(username).strip()
    agent.bot.chat(f"/tp {safe_username}")


def register_commands(registry):
    registry.register("quit", handle_quit)
    registry.register("dig to me", handle_dig_to_me)
    registry.register("come to me", handle_come_to_me)
    registry.register("teleport to me", handle_teleport_to_me)
