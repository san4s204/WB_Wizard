# core/cleanup_job.py
import asyncio
import logging
from functools import partial
from core.cleanup import purge_old_data

async def purge_old_data_job():
    loop = asyncio.get_running_loop()
    stats = await loop.run_in_executor(None, partial(purge_old_data, months=6))
    logging.info(f"[CLEANUP] done: {stats}")
