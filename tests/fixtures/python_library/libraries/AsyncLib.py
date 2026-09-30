"""Async keyword (RF 6.1+)."""
import asyncio


async def wait_a_bit(seconds: float = 0.01) -> str:
    """Wait asynchronously."""
    await asyncio.sleep(seconds)
    return "ok"
