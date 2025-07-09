import ast
import asyncio
import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

load_dotenv()


def convert_str_to_list(str_list) -> list[int] | None:
    try:
        result = ast.literal_eval(str_list)
        if isinstance(result, list):
            return result
        return None
    except (ValueError, SyntaxError, TypeError):
        return None


TEMP_PATH = Path(os.getenv("TEMP_PATH"))

status_url = 'https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld?mid={}'
user_card = 'https://api.bilibili.com/x/web-interface/card?mid={}'
uid = convert_str_to_list(os.getenv('LIVE_ROOM_MID'))
if not uid:
    raise RuntimeError('没有指定MID')
room_status_urls = [status_url.format(x) for x in uid]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0',
    'Referer': 'https://www.bilibili.com/'
}


def qqyx(subject: str, message: str) -> None:
    email_addr = 'menboid@qq.com'
    email_pass = 'zxkcqcnuanrachdd'

    if not email_addr or not email_pass:
        raise ValueError("邮箱地址和密码不能为空")
    if not message:
        raise ValueError("邮件内容不能为空")

    context = ssl.create_default_context()
    sender = email_addr
    receiver = email_addr
    subject = subject
    body = message

    msg = EmailMessage()
    msg['subject'] = subject
    msg['From'] = sender
    msg['To'] = receiver
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL("smtp.qq.com", 465, context=context) as smtp:
            smtp.login(email_addr, email_pass)
            smtp.send_message(msg)
        print("邮件发送成功")
    except smtplib.SMTPResponseException as e:
        print(f"SMTP错误代码：{e.smtp_code}, 错误信息：{e.smtp_error}")
    except smtplib.SMTPException as e:
        print(f"SMTP异常：{e}")
    except Exception as e:
        print(f"发送邮件时发生未知错误：{e}")


async def fetch(session, url):
    async with session.get(url, headers=headers) as response:
        return await response.json()


async def fetch_all(urls, loop):
    async with aiohttp.ClientSession(loop=loop) as session:
        results = await asyncio.gather(*[fetch(session, url) for url in urls], return_exceptions=True)
        return results


async def get_live_room_status():
    loop = asyncio.get_event_loop()
    results = await fetch_all(room_status_urls, loop)
    for mid, info in zip(uid, results):
        path = TEMP_PATH / str(mid)
        async with aiohttp.ClientSession() as session:
            user_name = (await fetch(session, user_card.format(mid)))["data"]["card"]["name"]
        print(f"{[user_name]}{'已开播' if path.exists() else '未开播'}")
        if info['data']['liveStatus'] and not path.exists():
            qqyx("开播提醒", f"[{user_name}]已开播")
            path.touch()
        if not info['data']['liveStatus'] and path.exists():
            os.remove(path)
            qqyx('下播提醒', f'[{user_name}]已下播')


async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(get_live_room_status, 'interval', seconds=5)
    scheduler.start()
    await asyncio.Event().wait()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
