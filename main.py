import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

load_dotenv(verbose=True)

from utils.tools import ConfigManage
from live_streams.config import Config
from live_streams import BLiveClient


async def main():
    async with BLiveClient(room_id=config.live_room_id.pop()) as live:
        await live.start()
        # await live.room_status()
        while True:
            await asyncio.sleep(60)


if __name__ == '__main__':
    config = ConfigManage().get_config(Config)
    log_path = Path(os.getenv('LOG_PATH') or Path.cwd())
    logger.remove()
    logger.add(log_path / f"{os.path.basename(__file__).split('.')[0]}.log", level="DEBUG")
    logger.add(sys.stdout, level="INFO")
    asyncio.run(main())
