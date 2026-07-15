import math
from typing import Any
from core.memory import get_vec3
import capabilities.movement as um

async def mine_line(agent: Any, length: int) -> None:
    """
    Digs a straight line of given length, moving relative to current position.
    """
    Vec3Class = get_vec3()
    pos = agent.bot.position
    start_pos = Vec3Class(math.floor(pos.x), math.floor(pos.y), math.floor(pos.z))
    await agent.bot.dig(start_pos + (0, -1, 0))
    for i in range(length):
        target_ref = start_pos + (i, 0, 0)
        await agent.bot.dig(target_ref + (1, 0, 0))
        await um.move_absolute(agent, target_ref + (1.5, 0.0, 0.5))


async def burrow_one_block_down_positive_x(agent: Any) -> None:
    """
    Digs blocks in positive x and moves down by one block.
    """
    Vec3Class = get_vec3()
    pos = agent.bot.position
    start_pos = Vec3Class(math.floor(pos.x), math.floor(pos.y), math.floor(pos.z))
    agent.log(f"Burrow start. Bot position: {pos}, Floored: {start_pos}")

    agent.log(f"Digging upper block: {start_pos + (1, 1, 0)}")
    await agent.bot.dig(start_pos + (1, 1, 0))
    
    agent.log(f"Digging middle block: {start_pos + (1, 0, 0)}")
    await agent.bot.dig(start_pos + (1, 0, 0))
    
    agent.log(f"Digging lower block: {start_pos + (1, -1, 0)}")
    await agent.bot.dig(start_pos + (1, -1, 0))
    
    agent.log(f"Moving to step center: {start_pos + (1.5, -1.0, 0.5)}")
    await um.move_absolute(agent, start_pos + (1.5, -1.0, 0.5))


async def tunnel_forward(agent: Any, length: int, height: int = 2, direction: str = 'x', direction_sign: int = 1) -> None:
    """
    Digs out a tunnel of specified dimensions.
    """
    if height < 2 or height > 3:
        agent.log("Height must be 2 or 3. Defaulting to 2.")
        height = 2
        
    xcoord = 0
    zcoord = 0
    if direction == 'x':
        xcoord = 1 * direction_sign
    elif direction == 'z':
        zcoord = 1 * direction_sign
    else:
        raise RuntimeError("Invalid direction.")
        
    Vec3Class = get_vec3()
    pos = agent.bot.position
    start_pos = Vec3Class(math.floor(pos.x), math.floor(pos.y), math.floor(pos.z))
    
    for i in range(length):
        tx = start_pos.x + i * xcoord
        tz = start_pos.z + i * zcoord
        
        await agent.bot.dig(Vec3Class(tx + xcoord, start_pos.y, tz + zcoord))
        await agent.bot.dig(Vec3Class(tx + xcoord, start_pos.y + 1, tz + zcoord))
        if height == 3:
            await agent.bot.dig(Vec3Class(tx + xcoord, start_pos.y + 2, tz + zcoord))
        await um.move_absolute(agent, Vec3Class(tx + xcoord + 0.5, start_pos.y, tz + zcoord + 0.5))


async def dig_chamber(agent: Any, xdim: int, zdim: int) -> None:
    """
    Digs out a 3D rectangular chamber of size xdim by zdim (with height 3).
    """
    Vec3Class = get_vec3()
    
    pos = agent.bot.position
    start_pos = Vec3Class(math.floor(pos.x), math.floor(pos.y), math.floor(pos.z))

    # Dig starting column
    await agent.bot.dig(start_pos + (1, 0, 0))
    await agent.bot.dig(start_pos + (1, 1, 0))
    await agent.bot.dig(start_pos + (1, 2, 0))
    await um.move_relative_to_self(agent, 1, 0, 0)
    for z in range(zdim):
        await tunnel_forward(agent, xdim - 1, height=3, direction='x', direction_sign=1)
        if z == zdim - 1:
            return
        await um.move_relative_to_self(agent, 1 - xdim, 0, 0)
        await agent.bot.dig(start_pos + (1, 0, z + 1))
        await agent.bot.dig(start_pos + (1, 1, z + 1))
        await agent.bot.dig(start_pos + (1, 2, z + 1))
        await um.move_relative_to_self(agent, 0, 0, 1)


async def dig_staircase_down(agent: Any, depth: int) -> None:
    """
    Digs a staircase down for depth levels.
    """
    Vec3Class = get_vec3()
    pos = agent.bot.position
    start_pos = Vec3Class(math.floor(pos.x), math.floor(pos.y), math.floor(pos.z))
    
    for i in range(depth):
        step_x = start_pos.x + (i + 1)
        step_y = start_pos.y - (i + 1)
        step_z = start_pos.z
        
        agent.log(f"[STAIRCASE] Digging step {i+1}/{depth} at X={step_x}, Y={step_y}")
        
        await agent.bot.dig(Vec3Class(step_x, step_y + 2, step_z))
        await agent.bot.dig(Vec3Class(step_x, step_y + 1, step_z))
        await agent.bot.dig(Vec3Class(step_x, step_y, step_z))
        
        target_step = Vec3Class(step_x + 0.5, step_y, step_z + 0.5)
        try:
            await agent.bot.move_to(target_step, range_val=0)
        except Exception as e:
            agent.log(f"[STAIRCASE] Move to step {i+1} failed: {e}. Retrying dig and move.")
            await agent.bot.dig(Vec3Class(step_x, step_y + 2, step_z))
            await agent.bot.dig(Vec3Class(step_x, step_y + 1, step_z))
            await agent.bot.dig(Vec3Class(step_x, step_y, step_z))
            try:
                await agent.bot.move_to(target_step, range_val=0)
            except Exception:
                pass