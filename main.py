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

room_task: dict[int, BLiveClient]


async def main():
    global room_task
    room_task = {rid: BLiveClient(room_id=rid) for rid in config.live_room_id}
    try:
        while True:
            for room_id, client in room_task.items():
                logger.debug(f"[{room_id}] | 检测状态")
                await client.auto_room_monitor()
                await asyncio.sleep(30)
    except asyncio.CancelledError:
        logger.info("正在关闭程序")
    finally:
        for room_id, client in room_task.items():
            await client.stop_and_close()


if __name__ == '__main__':
    config = ConfigManage().get_config(Config)
    log_path = Path(os.getenv('LOG_PATH') or Path.cwd())
    logger.remove()
    logger.add(log_path / f"{os.path.basename(__file__).split('.')[0]}.log", level="DEBUG")
    logger.add(sys.stdout, level="INFO")
    asyncio.run(main())
