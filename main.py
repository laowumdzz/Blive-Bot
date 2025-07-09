import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from loguru import logger

load_dotenv(verbose=True)

from utils.tools import ConfigManage
from live_streams.config import Config
from live_streams import BLiveClient, models, Handler

MUSIC_KEYWORDS = {"点歌", "来一首", "来首", "放首", "点一首"}
room_task: dict[int, BLiveClient]
count: dict[str, int] = {
    "WatchNum": 0,
    "InteractWord": 0,
    "Danmaku": 5,
}
client: BLiveClient


def match_keyword(input_string: str, keywords) -> Optional[str]:
    """
    匹配输入字符串中的第一个关键字(来自关键字数组)
    :param input_string: 要搜索的字符串
    :param keywords: 关键字列表
    :return: 匹配到的第一个关键字后的内容(不带后面的空格)，如果没有匹配则返回None
    """
    for keyword in keywords:
        start = input_string.find(keyword)
        if start != -1:
            end = start + len(keyword)
            if end < len(input_string):
                return input_string[end:].strip()
    return None


@Handler.append_func(models.DanmakuMessage)
async def _(model: models.DanmakuMessage):
    music_match = match_keyword(model.msg, MUSIC_KEYWORDS)
    print(
        f"[{model.room_id}] | {model.uname}: {model.msg} | 匹配: {music_match} | 等级: {model.user_level} | 舰队类型: {model.privilege_type}")
    count["Danmaku"] += 1


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
            type_str = "分享直播间"
        case _:
            count["InteractWord"] += 1
            type_str = "进入直播间"
    print(
        f"[{model.room_id}] | 用户:[{model.uname}] {type_str} || InteractWord_count:{count['InteractWord']} | Danmaku_count:{count['Danmaku']}")


async def main():
    global client
    # room_task = {rid: BLiveClient(room_id=rid) for rid in config.live_room_id}
    try:
        client = BLiveClient(room_id=config.live_room_id.pop())
        await client.start()
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        logger.info("正在关闭程序")


if __name__ == '__main__':
    log_path = Path(os.getenv('LOG_PATH') or Path.cwd())
    logger.remove()
    logger.add(log_path / f"{os.path.basename(__file__).split('.')[0]}.log", level="DEBUG")
    logger.add(sys.stdout, level="INFO")
    config = ConfigManage.get_config(Config)
    asyncio.run(main())
