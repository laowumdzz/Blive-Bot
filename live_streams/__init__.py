import asyncio
import json
import os
import struct
import time
from datetime import datetime
from typing import Optional, Any

import aiofiles
import aiohttp
import brotli
import websockets
from loguru import logger

from utils.tools import Signedparams, TEMP_PATH
from .config import Config
from .enum import Operation, ProtoVer, AuthReplyCode
from .exception import AuthError
from .handler import HandlerInterface, Handler
from .models import HeaderTuple

GetRoomPlayInfo = "https://api.live.bilibili.com/xlive/web-room/v2/index/getRoomPlayInfo?room_id={}&protocol=0&platform=web"


class BLiveClient:
    HEADER_STRUCT = struct.Struct('>I2H2I')
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
        "Referer": "https://www.bilibili.com/",
        "Origin": "http://www.bilibili.com",
        "Cookie": os.getenv("COOKIE")
    }

    def __init__(
            self,
            room_id: int = None,
            user_id: int = None,
            session_: aiohttp.ClientSession = None,
            handler_: HandlerInterface = Handler(),
    ):
        self.room_id = room_id
        self.user_id = user_id
        if not (room_id or user_id):
            raise KeyError("not found room_id or user_id")
        self._msg_hander: HandlerInterface = handler_
        self.own_session = False
        if not session_:
            self.own_session = True
            session_ = aiohttp.ClientSession(headers=self.headers)
        self._session: Optional[aiohttp.ClientSession] = session_
        self._ws: Optional[websockets.ClientConnection] = None
        self._Heartbeat_Task: Optional[asyncio.Task] = None
        self._Main_Task: Optional[asyncio.Task] = None
        self.status: bool = False

    async def get_uri_port(self) -> Optional[tuple[set[str], bytes]]:
        """
        获取直播间流URI,以及编码后的认证令牌
        :return: tuple(set(直播间wss流URIs), 编码后的认证令牌)
        :raise KeyError: 未找到该直播间或已被风控
        """
        params = await Signedparams.get_end_result(params={"type": 0, "id": self.room_id, "web_location": "444.8"})
        await Signedparams.close()
        try:
            async with self._session.get("https://api.live.bilibili.com/xlive/web-room/v1/index/getDanmuInfo",
                                         params=params) as response:
                response.raise_for_status()
                data: dict[str, Any] = (await response.json())["data"]
            auth = {
                "uid": await self._get_login_mid(),
                "protover": 3,
                "platform": "web",
                "type": 2,
                "roomid": self.room_id,
                "key": data["token"]
            }
            uris = {f"wss://{d['host']}:{d['wss_port']}/sub" for d in data["host_list"]}
        except KeyError as e:
            logger.error(f"{e}: 未找到该直播间或已被风控")
            return None
        else:
            return uris, json.dumps(auth).encode()

    async def start(self):
        if not self.room_id:
            await self.get_room_id()  # 3546612229998826
        params = await self.get_uri_port()

        async def run():
            try:
                self.status = True
                async with websockets.connect(params[0].pop()) as self._ws:
                    await self.on_open(params[1])
                    while True:
                        response = await self._ws.recv()
                        await asyncio.create_task(self._on_message(response))
            except asyncio.CancelledError:
                logger.info("正在关闭直播监听")
            except websockets.exceptions.ConnectionClosedError as e:
                logger.error(f"连接意外关闭: {e}")
            finally:
                if self._Heartbeat_Task is not None:
                    self._Heartbeat_Task.cancel()

        if params:
            self._Main_Task = asyncio.create_task(run())
            self.status = True

    async def _send_packet(self, packet_type: int, payload: bytes):
        """
        发送数据包
        :param packet_type: 数据包类型
        :param payload: 数据包
        :return: None
        """
        header = struct.pack(">IHHII", 16 + len(payload), 16, 1, packet_type, 1)
        """
        偏移量	长度	类型	    含义
        0	    4	uint32	封包总大小(头部大小+正文大小)
        4	    2	uint16	头部大小(一般为0x0010，16字节)
        6	    2	uint16	协议版本: 0.普通包正文不使用压缩, 1.心跳及认证包正文不使用压缩, 2.普通包正文使用zlib压缩, 3.普通包正文使用brotli压缩,解压为一个带头部的协议0普通包
        8	    4	uint32	操作码(封包类型)
        12	    4	uint32	sequence, 每次发包时向上递增
        16      -   bytes[] 数据主体
        """

        await self._ws.send(header + payload)

    async def on_open(self, encode_auth: bytes):
        """建立连接后发送认证包和心跳包"""
        logger.info("发送认证包")
        await self._send_packet(7, encode_auth)

        async def run():
            """每隔30秒发送一次心跳包"""
            while True:
                logger.debug("发送心跳包")
                payload = struct.pack(">I", 520)
                await self._send_packet(2, payload)
                await asyncio.sleep(30)

        self._Heartbeat_Task = asyncio.create_task(run())

    async def _on_message(self, payload: bytes):
        """
        处理接收到的消息
        :param payload: 普通数据包
        :return: None
        """
        offset = 0
        body: bytes
        header = HeaderTuple(*self.HEADER_STRUCT.unpack_from(payload))
        try:
            match header.operation:
                case Operation.SEND_MSG_REPLY:
                    while True:
                        body = payload[offset + header.raw_header_size: offset + header.pack_len]
                        await self._parse_message(header, body)
                        offset += header.pack_len
                        if offset >= len(payload):
                            break
                        header = HeaderTuple(*self.HEADER_STRUCT.unpack_from(payload, offset))
                        logger.debug(f"当前偏移量:{offset}")
                case Operation.HEARTBEAT_REPLY:
                    message = payload[offset + header.raw_header_size:]
                    logger.debug(f"心跳回应: {[int.from_bytes(message[i:i + 4]) for i in range(0, len(message), 4)]}")
                case Operation.AUTH_REPLY:
                    message = payload[offset + header.raw_header_size:]
                    decode_body = json.loads(message.decode())
                    if decode_body['code'] != AuthReplyCode.OK:
                        raise AuthError(f"auth reply error, code={decode_body['code']}, body={decode_body}")
                    logger.info(f"认证回应: {decode_body}")
        except struct.error:
            logger.error(f'[{self.room_id}] parsing header failed offset={offset} payload={payload}')

    async def _parse_message(self, header: HeaderTuple, payload: bytes):
        decode_body: dict
        match header.ver:
            case ProtoVer.BROTLI:
                logger.debug("正文已被压缩,正在解压")
                await self._on_message(
                    await asyncio.to_thread(brotli.decompress, payload))
            case ProtoVer.NORMAL:
                if len(payload) != 0:
                    decode_body = json.loads(payload.decode())
                    await self._msg_hander.handle(self.room_id, decode_body)

    async def _write_file(self, data: dict) -> bool:
        if not isinstance(data, dict):
            raise TypeError("data must be a dict")
        file_path = TEMP_PATH / "bililive" / f"{self.room_id}.json"
        data["time_now"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            file_exists = file_path.exists()
            async with aiofiles.open(file_path, "a+" if file_exists else "w", encoding="utf-8") as file:
                if file_exists:
                    await file.seek(0)
                    last_char = await file.read(-1)
                    if last_char == "]":
                        await file.write(",\n" + json.dumps(data, ensure_ascii=False, indent=4))
                    else:
                        await file.seek(0)
                        await file.truncate()
                        await file.write(json.dumps([data], ensure_ascii=False, indent=4))
                else:
                    await file.write(json.dumps([data], ensure_ascii=False, indent=4))
            return True
        except Exception as e:
            logger.error(f"文件写入错误: {e}")
            return False

    async def get_room_id(self):
        params = await Signedparams.get_end_result(self.user_id)
        async with self._session.get("https://api.bilibili.com/x/space/wbi/acc/info", params=params) as response:
            response.raise_for_status()
            data: dict = (await response.json())["data"]
        if data["live_room"]["roomStatus"]:
            message = f"""\n
            ===== [{data["name"]}]直播间状态 =====
            开播状态: {"已开播" if data["live_room"]["liveStatus"] else "未开播"}
            直播链接: {data["live_room"]["url"]}
            直播ID: {data["live_room"]["roomid"]}
            轮播状态: {"轮播中" if data["live_room"]["roundStatus"] else "未轮播"}
            看过人数: {data["live_room"]["watched_show"]["num"]}
            ====================================
            """.strip()
            logger.info(message)
            if not data["live_room"]["liveStatus"]:
                logger.warning(f"[{data['name']}]当前未开播, 继续监听")
            self.room_id = int(data["live_room"]["roomid"])

    async def stop_and_close(self):
        await self._session.close()
        await self.stop()

    async def stop(self):
        if self._Heartbeat_Task is not None:
            self._Heartbeat_Task.cancel()
            try:
                await asyncio.wait_for(self._Heartbeat_Task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("心跳任务取消超时")
            except asyncio.CancelledError:
                pass
            self._Heartbeat_Task = None
        if self._Main_Task is not None:
            try:
                self._Main_Task.cancel()
                await asyncio.wait_for(self._Main_Task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("主任务取消超时")
            except asyncio.CancelledError:
                pass
            self._Main_Task = None
        if self._ws:
            await self._ws.close()
            self._ws = None
        self.status = False

    async def close(self):
        if self._session and self.own_session:
            await self._session.close()
            self._session = None

    async def auto_room_monitor(self):
        try:
            async with self._session.get(GetRoomPlayInfo.format(self.room_id)) as response:
                response.raise_for_status()
                data = (await response.json())["data"]
            if data["live_status"] and not self.status:
                logger.info(f"[{self.room_id}] | 直播开始,启动监听")
                await self.start()
            elif self.status:
                logger.info(f"[{self.room_id}] | 直播结束,关闭监听")
                await self.stop()
        except asyncio.CancelledError:
            logger.info("结束自动启停监控")
        except Exception as e:
            logger.error(f"检测直播间状态失败: {e}")

    async def send_msg(self, message: str, reply_mid: int = 0, reply_uname: str = ""):
        """发送弹幕"""
        data = {
            "roomid": self.room_id,
            "csrf": await self._get_cookie_csrf(),
            "msg": message,
            "rnd": round(time.time()),
            "fontsize": 25,
            "color": 16777215,
            "reply_mid": reply_mid,
            "reply_attr": 0,
            "reply_uname": reply_uname,
            "bubble": 0,
        }
        async with self._session.post("https://api.live.bilibili.com/msg/send", data=data) as response:
            response.raise_for_status()
            data: dict = await response.json()
        match data["code"]:
            case 0:
                logger.success(f"成功发送消息: {data['msg'] if data.get('msg') else message}")
            case -101:
                logger.warning("账号未登录")
            case -111:
                logger.warning("csrf校验失败")
            case -400:
                logger.warning("请求错误, 带有必须参数的信息")
            case 1003212:
                logger.warning("超出限制长度")
            case 10031:
                logger.warning("发送频率过快")
            case _:
                logger.warning(f"未知错误code:{data['code']}, 消息:{data['message']}")

    async def _get_cookie_csrf(self) -> str:
        cookie = self.headers['Cookie']
        csrf = cookie[cookie.find('bili_jct'):]
        return csrf[9:csrf.find(';')]

    async def _get_login_mid(self) -> int:
        async with self._session.get("https://api.bilibili.com/x/space/myinfo") as response:
            response.raise_for_status()
            data = await response.json()
        return data["data"]["mid"]

    async def loop_room_monitor(self):
        while True:
            await self.auto_room_monitor()
            await asyncio.sleep(30)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop_and_close()
        if exc_type is asyncio.CancelledError:
            return True
        return None
