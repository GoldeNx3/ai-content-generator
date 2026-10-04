# Rola pliku: Start osobnego procesu workera i łagodne zatrzymanie SIGTERM.

import asyncio
import signal

from app.core.db import SessionLocal, engine
from app.core.logging import setup_logging
from app.workers.worker import Worker


async def main():
    setup_logging()
    worker = Worker(SessionLocal)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, worker.stopping.set)
    try:
        await worker.run()
    finally:
        await engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())
