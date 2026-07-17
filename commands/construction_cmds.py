import behaviors.shelter as bs
import capabilities.construction as ucon
import behaviors.forage as bf
import behaviors.iron_mining as bim
import re

async def handle_build_shelter(agent, username, message):
    await bs.build_shelter(agent)


async def handle_furnish_shelter(agent, username, message):
    await bs.furnish_shelter1(agent)


async def handle_place_block(agent, username, message):
    # Check if a custom block was specified, e.g., "place block cobblestone"
    # Otherwise, default to "bedrock" to preserve original logic.
    parts = message.lower().split("place block")
    item_name = "bedrock"
    if len(parts) > 1:
        extracted = parts[1].strip()
        if extracted:
            item_name = extracted
            
    await ucon.place_block_on_ground_one_forward(agent, item_name)


async def handle_test(agent, username, message):
    parts = message.lower().split("test")
    test_case = parts[1].strip() if len(parts) > 1 and parts[1].strip() else "1"
    
    if test_case == "1":
        # Test Case 1: Window leakage verification
        ct_pos = agent.memory.retrieve("crafting_table_position")
        if not ct_pos:
            # Try to find a crafting table block in the world
            ct_pos = await agent.bot.find_block("crafting_table", max_distance=10)
            
        if not ct_pos:
            await agent.bot.chat("Test 1 failed: No crafting table found in memory or nearby.")
            return

        await agent.bot.chat("Running Hypothesis 1 test: Crafting window leakage...")
        try:
            res = await agent.bot.send_command("test_case_1", {
                "x": int(ct_pos.x),
                "y": int(ct_pos.y),
                "z": int(ct_pos.z)
            })
            await agent.bot.chat(f"SUCCESS: Equip holds {res['held_after_equip']}. After close it holds: {res['held_after_close']}")
        except Exception as e:
            await agent.bot.chat(f"FAILED to execute Test 1: {e}")

    elif test_case == "2":
        # Test Case 2: Air block placement verification
        await agent.bot.chat("Running Hypothesis 2 test: Block placement against air vs solid block...")
        
        # We will stand in place and attempt to place against the block below feet (solid)
        # and then against the air block above the feet (air)
        pos = agent.bot.position
        pos_solid = pos - (0, 1, 0) # block we are standing on (solid)
        pos_air = pos + (0, 1, 0) # block above our head (air)
        
        try:
            await agent.bot.chat(f"Test 2A: Placing against solid floor {pos_solid}...")
            res_solid = await agent.bot.send_command("test_case_2", {
                "x": int(pos_solid.x),
                "y": int(pos_solid.y),
                "z": int(pos_solid.z)
            })
            await agent.bot.chat(f"Result for solid: {res_solid['status']} (Error: {res_solid.get('error')})")
            
            await agent.bot.chat(f"Test 2B: Placing against air {pos_air}...")
            res_air = await agent.bot.send_command("test_case_2", {
                "x": int(pos_air.x),
                "y": int(pos_air.y),
                "z": int(pos_air.z)
            })
            await agent.bot.chat(f"Result for air: {res_air['status']} (Error: {res_air.get('error')})")
        except Exception as e:
            await agent.bot.chat(f"FAILED to execute Test 2: {e}")
    else:
        await agent.bot.chat("Unknown test case. Use 'test 1' or 'test 2'.")


async def handle_forage(agent, username, message):
    amount = 1
    match = re.search(r'\d+', message)
    if match:
        amount = int(match.group())
    await bf.forage_food(agent, amount)


async def handle_mine_iron(agent, username, message):
    await bim.mine_iron(agent)


def register_commands(registry):
    registry.register("build shelter", handle_build_shelter)
    registry.register("furnish shelter", handle_furnish_shelter)
    registry.register("place block", handle_place_block)
    registry.register("test", handle_test)
    registry.register("forage", handle_forage)
    registry.register("mine iron", handle_mine_iron)
