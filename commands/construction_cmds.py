import behaviors.shelter as bs
import capabilities.construction as ucon


def handle_build_shelter(agent, username, message):
    bs.build_shelter(agent)


def handle_furnish_shelter(agent, username, message):
    bs.furnish_shelter1(agent)


def handle_place_block(agent, username, message):
    # Check if a custom block was specified, e.g., "place block cobblestone"
    # Otherwise, default to "bedrock" to preserve original logic.
    parts = message.lower().split("place block")
    item_name = "bedrock"
    if len(parts) > 1:
        extracted = parts[1].strip()
        if extracted:
            item_name = extracted
            
    ucon.place_block_on_ground_one_forward(agent, item_name)


def register_commands(registry):
    registry.register("build shelter", handle_build_shelter)
    registry.register("furnish shelter", handle_furnish_shelter)
    registry.register("place block", handle_place_block)
