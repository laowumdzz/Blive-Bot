import ast
import asyncio
import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

load_dotenv()
scheduler = AsyncIOScheduler()


def convert_str_to_list(str_list) -> list[int] | None:
    try:
        result = ast.literal_eval(str_list)
        if isinstance(result, list):
            return result
        return None
    except (ValueError, SyntaxError, TypeError):
        return None


temp_path_str = os.getenv("TEMP_PATH", None)
TEMP_PATH = Path(temp_path_str) if temp_path_str else Path.cwd()

status_url = 'https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld?mid={}'
user_card = 'https://api.bilibili.com/x/web-interface/card?mid={}'
uid = convert_str_to_list(os.getenv('LIVE_ROOM_MID'))
if not uid:
    raise RuntimeError('没有指定UID')
status_urls = {status_url.format(x) for x in uid}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0',
    'Referer': 'https://www.bilibili.com/'
}


def qqyx(subject: str, message: str) -> None:
    email_addr = 'menboid@qq.com'
    email_pwd = 'zxkcqcnuanrachdd'

    if not email_addr or not email_pwd:
        raise ValueError("邮箱地址和密码不能为空")

    msg = EmailMessage()
    msg['subject'] = subject
    msg['From'] = email_addr
    msg['To'] = email_addr
    msg.set_content(message)

    try:
        with smtplib.SMTP_SSL("smtp.qq.com", 465, context=ssl.create_default_context()) as smtp:
            smtp.login(email_addr, email_pwd)
            smtp.send_message(msg)
        print("邮件发送成功")
    except smtplib.SMTPResponseException as e:
        print(f"SMTP错误代码：{e.smtp_code}, 错误信息：{e.smtp_error}")
    except smtplib.SMTPException as e:
        print(f"SMTP异常：{e}")
    except Exception as e:
        print(f"发送邮件时发生未知错误：{e}")


async def fetch(session, url) -> dict[str, Any]:
    async with session.get(url) as response:
        return await response.json()


@scheduler.scheduled_job('interval', seconds=6, misfire_grace_time=10, max_instances=2)
async def get_live_status():
    print("-" * 20)
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            results = await asyncio.gather(*(fetch(session, url) for url in status_urls), return_exceptions=True)
            for mid, info in zip(uid, results):
                if isinstance(info, dict):
                    path = TEMP_PATH / str(mid)
                    user_name = (await fetch(session, user_card.format(mid)))["data"]["card"]["name"]
                    print(f"[{user_name}]{'已开播' if path.exists() else '未开播'}")
                    if info['data']['liveStatus'] and not path.exists():
                        qqyx("开播提醒", f"[{user_name}]已开播")
                        path.touch()
                    if not info['data']['liveStatus'] and path.exists():
                        qqyx('下播提醒', f'[{user_name}]已下播')
                        path.unlink(missing_ok=True)
                else:
                    print(f"[{mid}]获取状态出错 e:{info}")
    except asyncio.CancelledError:
        pass


async def main():
    try:
        scheduler.start()
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        pass


if __name__ == '__main__':
    asyncio.run(main())
