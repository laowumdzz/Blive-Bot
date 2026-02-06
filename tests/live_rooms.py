import ast
import asyncio
from email.message import EmailMessage
from itertools import zip_longest
import os
from pathlib import Path
import smtplib
import ssl
from typing import Any

import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from loguru import logger

load_dotenv(verbose=True)
scheduler = AsyncIOScheduler()


def convert_str_to_list_int(v) -> list[int] | None:
    try:
        result = ast.literal_eval(v)
        if isinstance(result, list) and all(isinstance(i, int) for i in result):
            return result
    except (ValueError, SyntaxError):
        logger.error(
            "LIVE_ROOM_MID must be a valid list of integers, e.g., '[1, 2, 3]'")
        raise
    return None


ENV_TEMP_DIR = os.getenv("TEMP_PATH")
TEMP_PATH = Path(ENV_TEMP_DIR) if ENV_TEMP_DIR else Path.cwd() / "temp"
LIVE_STATUS_API = "https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld?mid={}"
USER_CARD_API = "https://api.live.bilibili.com/live_user/v1/Master/info?uid={}"
GLOBAL_SESSION: aiohttp.ClientSession | None = None
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 "
    "Safari/537.36 Edg/145.0.0.0",
    "Referer": "https://www.bilibili.com/",
}
CodeError = Exception


UIDS = convert_str_to_list_int(os.getenv("LIVE_ROOM_MID"))
if not UIDS:
    raise ValueError("没有指定UID, 请在.env文件中指定LIVE_ROOM_MID,示例:[uid1, uid2]")
live_status_urls = [LIVE_STATUS_API.format(uid) for uid in UIDS]
user_care_urls = [USER_CARD_API.format(uid) for uid in UIDS]


def qqyx(subject: str, message: str) -> None:
    email_addr = "menboid@qq.com"
    email_pwd = "zxkcqcnuanrachdd"

    if not email_addr or not email_pwd:
        raise ValueError("邮箱地址和密码不能为空")

    msg = EmailMessage()
    msg["subject"] = subject
    msg["From"] = email_addr
    msg["To"] = email_addr
    msg.set_content(message)

    try:
        with smtplib.SMTP_SSL("smtp.qq.com", 465, context=ssl.create_default_context()) as smtp:
            smtp.login(email_addr, email_pwd)
            smtp.send_message(msg)
        logger.success("成功发送邮件")
    except smtplib.SMTPResponseException as e:
        logger.warning(f"SMTP错误代码：{e.smtp_code}, 错误信息：{e.smtp_error}")
    except smtplib.SMTPException as e:
        logger.opt(exception=e).error("SMTP异常")
    except Exception as e:
        logger.opt(exception=e).error("未知错误")


async def fetch(session, url) -> dict[str, Any]:
    async with session.get(url) as response:
        response.raise_for_status()
        json_data = await response.json()
        if not json_data.get("code"):
            return json_data
        raise CodeError("风控校验失败")


async def fetch_all_data(session):
    """并发获取所有直播间和用户卡片数据"""
    status_tasks = [fetch(session, url) for url in live_status_urls]
    user_card_tasks = [fetch(session, url) for url in user_care_urls]
    status_results = await asyncio.gather(*status_tasks, return_exceptions=True)
    user_card_results = await asyncio.gather(*user_card_tasks, return_exceptions=True)
    user_card_results = [CodeError("1"), CodeError("2")]
    return status_results, user_card_results


@scheduler.scheduled_job("interval", seconds=5, max_instances=2)
async def get_live_status():
    if GLOBAL_SESSION is None:
        logger.error("全局 ClientSession 尚未初始化！")
        return
    try:
        status_results, user_card_results = await fetch_all_data(GLOBAL_SESSION)

        processed_status_results = []
        for i, result in enumerate(status_results):
            if isinstance(result, Exception):
                logger.opt(exception=result).error(
                    f"获取状态URL失败. UID: [{UIDS[i]}] | URL: {live_status_urls[i]}")
                processed_status_results.append(None)
            else:
                processed_status_results.append(result)

        processed_user_card_results = []
        for i, result in enumerate(user_card_results):
            if isinstance(result, Exception):
                logger.warning(f"获取用户名称失败,回退到使用UID显示. URL: {user_care_urls[i]} 错误原因: {type(result).__name__}: {result}")
                processed_user_card_results.append(None)
            else:
                processed_user_card_results.append(result)

        for uid, status_data, name_data in zip_longest(UIDS, processed_status_results, processed_user_card_results):
            if status_data is None:
                logger.warning(f"用户 {uid} 的数据不完整，已跳过处理。")
                continue
            path = TEMP_PATH / str(uid)
            user_name = name_data["data"]["info"]["uname"] if name_data else uid
            logger.info(f"{[user_name]}{'已开播' if path.exists() else '未开播'}")
            if status_data["data"]["liveStatus"] and not path.exists():
                qqyx("开播提醒", f"[{user_name}]已开播")
                path.touch()
            if not status_data["data"]["liveStatus"] and path.exists():
                qqyx("下播提醒", f"[{user_name}]已下播")
                path.unlink(missing_ok=True)
        logger.info("所有直播间检测完毕")
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.opt(exception=e).error("未知错误")


async def run():
    global GLOBAL_SESSION
    scheduler.start()
    logger.success("调度器已启动, 按[Ctrl+C]退出")
    if GLOBAL_SESSION is None:
        GLOBAL_SESSION = aiohttp.ClientSession(headers=HEADERS)
    try:
        await asyncio.Event().wait()
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("正在关闭调度器和会话...")
        scheduler.shutdown()
        if GLOBAL_SESSION is not None:
            await GLOBAL_SESSION.close()
            GLOBAL_SESSION = None
        logger.success("调度器和会话已关闭")


if __name__ == "__main__":
    try:
        import uvloop
        uvloop.run(run())
    except ModuleNotFoundError:
        asyncio.run(run())
