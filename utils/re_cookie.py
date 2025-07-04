import asyncio
import binascii
import os
import re
import time
from html.parser import HTMLParser

from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA

from until.tools import Fetch

os.environ[
    "COOKIE"] = "buvid3=EAB5766E-112D-0398-D7F5-602E630367F431381infoc; b_nut=1707742728; buvid4=9F2F9816-5347-25DB-7BD0-EA4BF501F35A31381-024021212-ziyOgVVydBFlb6iBZh14bw%3D%3D; buvid_fp=afcc77854ce7d4917defdd9a7b04f047; PVID=1; enable_web_push=DISABLE; header_theme_version=CLOSE; home_feed_column=5; browser_resolution=1536-742; DedeUserID=479269916; DedeUserID__ckMd5=5ba75d3b3bd39722; hit-dyn-v2=1; SESSDATA=f4eb100d%2C1750486747%2C84275%2Ac1CjBBFTPrvd6xx5Q5BXyvQTUukA_qkCjjVj3CnA-qMYWIhsZkd2hJBHAMEDZj1veqLfwSVlVIWWZZQTRhZUtua0NhYmM2eDJHd2tyTGk1N3J5TVh6dWVyMWtBOWhOYUlsYmJ5eVNxT1AzMDZQSFdNM1BHcXZDN3RzbFFmVlpaM0hveU14WldLTWZ3IIEC; bili_jct=cbf6371691346105dc44aa61c74e49df; sid=4s9cvo1i; bp_t_offset_479269916=1014399420512337920; rpdid=|(k|k)J~mm)k0J'u~Jl|kuY~Y; bili_ticket=eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MzUyODA5NTAsImlhdCI6MTczNTAyMTY5MCwicGx0IjotMX0.WDbMtP4OfaPzkYZ7wLz5fwLpeZJKwuQkei9kB_y5rik; bili_ticket_expires=1735280890; CURRENT_FNVAL=4048; b_lsid=98810751E_193F7954029"


class MyHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.capture = False
        self.data = []

    def handle_starttag(self, tag, attrs):
        if tag == "div":
            for attr in attrs:
                if attr == ('id', '1-name'):
                    self.capture = True

    def handle_endtag(self, tag):
        if tag == "div" and self.capture:
            self.capture = False

    def handle_data(self, data):
        if self.capture:
            self.data.append(data)


def extract_content(html_content):
    parser = MyHTMLParser()
    parser.feed(html_content)
    return ''.join(parser.data)


def extract_bili_jct_value(input_string) -> str | None:
    """
    :param input_string: str
    :return: bili jct value
    """
    pattern = r"bili_jct=([0-9a-f]+)"
    match = re.search(pattern, input_string)
    if match:
        return match.group(1)
    else:
        return None


headers = {
    "cookie": os.getenv("COOKIE"),
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0',
    'Referer': 'https://www.bilibili.com/',
}


# noinspection PyTypeChecker
async def get_CorrespondPath():
    key = RSA.importKey('''-----BEGIN PUBLIC KEY-----
    MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDLgd2OAkcGVtoE3ThUREbio0Eg
    Uc/prcajMKXvkCKFCWhJYJcLkcM2DKKcSeFpD/j6Boy538YXnR6VhcuUJOhH2x71
    nzPjfdTcqMz7djHum0qSZA0AyCBDABUqCrfNgCiJ00Ra7GmRj+YCK1NJEuewlb40
    JNrRuoEUXpabUzGB8QIDAQAB
    -----END PUBLIC KEY-----''')
    ts = round(time.time() * 1000)
    cipher = PKCS1_OAEP.new(key, SHA256)
    encrypted = cipher.encrypt(f'refresh_{ts}'.encode())
    return binascii.b2a_hex(encrypted).decode()


async def test_refresh() -> bool | None:
    result: dict = await Fetch()("https://passport.bilibili.com/x/passport-login/web/cookie/info", headers=headers)
    if not result['code'] and not result['message']:
        return result['data']['refresh']
    elif result['code'] == -101:
        print("账号未登录")
    await Fetch.close_session()
    return None


async def get_refresh_csrf():
    correspondpath = await get_CorrespondPath()
    result = await Fetch()(f"https://www.bilibili.com/correspond/1/{correspondpath}", headers=headers)
    refresh_csrf = extract_content(result)
    return refresh_csrf


if __name__ == '__main__':
    asyncio.run(test_refresh())
