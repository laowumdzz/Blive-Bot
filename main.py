import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

load_dotenv(verbose=True)

from live_streams import *
from utils import convert_str_to_list

MUSIC_KEYWORDS = {"点歌", "来一首", "来首", "放首", "点一首"}
room_task: dict[int, BLiveClient]
count: dict[str, int] = {
    "WatchNum": 0,
    "InteractWord": 0,
    "Danmaku": 0,
    "Share": 0,
}


@Handler.append_func(models.DanmakuMessage)
async def _(model: models.DanmakuMessage):  # TODO: 使用arclet-alconna代替匹配关键字
    count["Danmaku"] += 1
    print(
        f"[{model.room_id}] | {model.uname}: {model.msg} | 等级: {model.user_level} | 舰队类型: {model.privilege_type}")


@Handler.append_func(models.GiftMessage)
async def _(model: models.GiftMessage):
    print(
        f"[{model.room_id}] | {model.uname} 赠送{model.gift_name}x{model.num} | (CNYx{model.total_coin / 1000}元)")


@Handler.append_func(models.LikeUpdateMessage)
async def _(model: models.LikeUpdateMessage):
    print(f"[{model.room_id}] | 点赞量:{model.click_count}")


@Handler.append_func(models.WatchedChangeMessage)
async def _(model: models.WatchedChangeMessage):
    if model.num != count["WatchNum"]:
        print(f"[{model.room_id}] | 观看人数: {model.text_large}")
        count["WatchNum"] = model.num


@Handler.append_func(models.LikeClickMessage)
async def _(model: models.LikeClickMessage):
    print(f"[{model.room_id}] | 用户[{model.uname}]{model.like_text}")


@Handler.append_func(models.LoginNoticeMessage)
async def _(model: models.LoginNoticeMessage):
    print(f"[{model.room_id}] | 日志: {model.message}")


@Handler.append_func(models.SuperChatMessage)
async def _(model: models.SuperChatMessage):
    print(f"[{model.room_id}] | 醒目留言 ¥{model.price} | {model.uname}：{model.message}")


@Handler.append_func(models.GuardBuyMessage)
async def _(model: models.GuardBuyMessage):
    print(f"[{model.room_id}] | {model.username} 购买{model.gift_name}")


@Handler.append_func(models.InteractWordMessage, models.InteractWordV2Message)
async def _(model: models.InteractWordMessage | models.InteractWordV2Message):
    match model.msg_type:
        case 2:
            type_str = "关注直播间"
        case 3:
            count["Share"] += 1
            type_str = "分享直播间"
        case _:
            count["InteractWord"] += 1
            type_str = "进入直播间"
    print(
        f"[{model.room_id}] | 用户:[{model.uname}] {type_str} || InteractWord_count:{count['InteractWord']} | Danmaku_count:{count['Danmaku']}")


async def main():
    global room_task
    room_ids = convert_str_to_list(os.getenv("LIVE_ROOM_ID"))
    room_task = {room_id: BLiveClient(room_id=room_id) for room_id in room_ids}
    try:
        for client in room_task.values():
            await client.start()
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        logger.info("正在关闭程序")


if __name__ == '__main__':
    log_path = Path(os.getenv('LOG_PATH') or Path.cwd())
    logger.remove()
    logger.add(
        log_path / f"{os.path.basename(__file__).split('.')[0]}.log",
        level="DEBUG",
        enqueue=True,
        rotation="00:00",
    )
    logger.add(sys.stdout, level="INFO", enqueue=True)
    asyncio.run(main())
