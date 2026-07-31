"""BLive客户端"""
import asyncio
from datetime import datetime
import json
import os
import struct
import time
from typing import Any, ClassVar, NamedTuple

import aiofiles
import aiohttp
import brotli
from loguru import logger
import websockets

from utils import TEMP_PATH, ConfigManage, SignedParams

from . import models
from .config import DANMUINFO_URL, Config
from .enum import AuthReplyCode, Operation, ProtoVer
from .exception import AuthError
from .handler import Handler
from .models import MsgType

__all__ = (
    "BLiveClient",
    "Handler",
    "MsgType",
    "models",
)

HEADER_STRUCT = struct.Struct(">I2H2I")


class HeaderTuple(NamedTuple):
    pack_len: int
    """整个消息的长度"""

    raw_header_size: int
    """原始消息头的长度"""

    ver: int
    """
    ========协议版本========
    数据包协议版本        含义
    0                  数据包有效负载为未压缩的JSON格式数据
    1                  客户端心跳包，或服务器心跳回应(带有人气值)
    3                  数据包有效负载为通过br压缩后的JSON格式数据(之前是zlib)
    """

    operation: int
    """
    ==================操作类型==================
    数据包类型    发送方      名称             含义
    2           Client     心跳             不发送心跳包，50-60秒后服务器会强制断开连接
    3           Server     心跳回应          有效负载为直播间人气值
    5           Server     通知             有效负载为礼物、弹幕、公告等内容数据
    7           Client     认证(加入房间)     客户端成功建立连接后发送的第一个数据包
    8           Server     认证成功回应       服务器接受认证包后回应的第一个数据包
    """

    seq_id: int
    """序列ID"""


class BLiveClient:
    headers: ClassVar[dict] = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0",
        "Referer": "https://www.bilibili.com/",
        "Origin": "http://www.bilibili.com",
    }

    def __init__(
            self,
            room_id: int | None = None,
            user_id: int | None = None,
            session_: aiohttp.ClientSession | None = None,
            handler_: Handler = Handler(),
    ):
        if not (room_id or user_id):
            raise KeyError("房间ID和UID必须输入一个")
        self._config = ConfigManage.get_config(Config)
        if self._config.use_cookie_login:
            self.headers["Cookie"] = os.getenv("COOKIE")
        self.room_id = room_id
        self.user_id = user_id
        self._msg_hander: Handler = handler_
        self._own_session = False
        if not session_:
            self._own_session = True
            session_ = aiohttp.ClientSession(headers=self.headers)
        self._message_task: set[asyncio.Task] = set()
        self._session: aiohttp.ClientSession | None = session_
        self._ws: websockets.ClientConnection | None = None
        self._Heartbeat_Task: asyncio.Task | None = None
        self._Main_Task: asyncio.Task | None = None
        self.program_status: bool = False
        self.live_status: bool = False
        self._msg_seq: int = 0
        """消息关联ID递增计数器，用于日志追踪单条消息的处理路径"""

    async def get_uri_port(self) -> tuple[set[str], bytes]:
        """
        获取直播间流URI,以及编码后的认证令牌
        :return: tuple(set(直播间wss流URIs), 编码后的认证令牌)
        :raise KeyError: 未找到该直播间或已被风控
        """
        params = await SignedParams.get_end_result(params={"type": 0, "id": self.room_id, "web_location": "444.8"})
        await SignedParams.close()
        try:
            if self._session is None:
                raise RuntimeError("session未初始化")
            async with self._session.get(DANMUINFO_URL, params=params) as response:
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
            uris = {
                f"wss://{d['host']}:{d['wss_port']}/sub" for d in data["host_list"]}
        except KeyError:
            logger.error(f"[{self.room_id}] 未找到该直播间或已被风控")
            raise
        else:
            return uris, json.dumps(auth).encode()

    async def start(self):
        """启动WebSocket连接并处理消息循环"""
        if not self.room_id:
            await self.get_room_id()
        params = await self.get_uri_port()

        async def run():
            try:
                self.program_status = True
                async with websockets.connect(params[0].pop()) as self._ws:
                    await self.on_open(params[1])
                    logger.info(f"[{self.room_id}] 开启直播监听")
                    while True:
                        response = await self._ws.recv(decode=False)
                        task = asyncio.create_task(self._on_message(response))
                        self._message_task.add(task)
                        task.add_done_callback(self._on_message_task_done)
            except asyncio.CancelledError:
                logger.info(f"[{self.room_id}] 正在关闭直播监听")
            except websockets.exceptions.ConnectionClosedError as e:
                logger.opt(exception=e).error(f"[{self.room_id}] 连接意外关闭")
            finally:
                if self._Heartbeat_Task is not None:
                    self._Heartbeat_Task.cancel()
                    try:
                        await asyncio.wait_for(self._Heartbeat_Task, timeout=5.0)
                    except TimeoutError:
                        logger.warning(f"[{self.room_id}] 心跳任务取消超时")
                    except asyncio.CancelledError:
                        pass
                    self._Heartbeat_Task = None
                if self._ws:
                    await self._ws.close()
                    self._ws = None

        if params:
            self._Main_Task = asyncio.create_task(run())
            self.program_status = True

    async def _send_packet(self, packet_type: int, payload: bytes) -> None:
        """
        发送数据包
        :param packet_type: 数据包类型
        :param payload: 数据包
        :return: None
        """
        header = struct.pack(">IHHII", 16 + len(payload),
                             16, 1, packet_type, 1)
        """
        偏移量	长度	类型	    含义
        0	    4	uint32	封包总大小(头部大小+正文大小)
        4	    2	uint16	头部大小(一般为0x0010, 16字节)
        6	    2	uint16	协议版本:
            0.普通包正文不使用压缩, 1.心跳及认证包正文不使用压缩,
            2.普通包正文使用zlib压缩, 3.普通包正文使用brotli压缩,
            解压为一个带头部的协议0普通包
        8	    4	uint32	操作码(封包类型)
        12	    4	uint32	sequence, 每次发包时向上递增
        16      -   bytes[] 数据主体
        """

        if self._ws is None:
            raise RuntimeError("WebSocket连接未建立")
        await self._ws.send(header + payload)

    async def on_open(self, encode_auth: bytes) -> None:
        """建立连接后发送认证包和心跳包"""
        logger.debug("发送认证包")
        await self._send_packet(7, encode_auth)

        async def run():
            """每隔30秒发送一次心跳包"""
            while True:
                logger.debug(f"[{self.room_id}] 发送心跳包")
                payload = struct.pack(">I", 520)
                await self._send_packet(2, payload)
                await asyncio.sleep(30)

        self._Heartbeat_Task = asyncio.create_task(run())

    def _on_message_task_done(self, task: asyncio.Task) -> None:
        """消息处理任务完成回调，记录未捕获异常并清理任务引用"""
        self._message_task.discard(task)
        if not task.cancelled():
            exc = task.exception()
            if exc is not None:
                logger.opt(exception=exc).error(
                    f"[{self.room_id}] 消息处理任务异常退出: "
                    f"{type(exc).__name__}: {exc}"
                )

    async def _on_message(self, payload: bytes, msg_id: int | None = None) -> None:
        """
        处理接收到的消息
        :param payload: 普通数据包
        :param msg_id: 消息关联ID，用于日志追踪。为None时自动生成递增序号
        :return: None
        """
        if msg_id is None:
            self._msg_seq += 1
            msg_id = self._msg_seq
        offset = 0
        body: bytes
        header = HeaderTuple(*HEADER_STRUCT.unpack_from(payload))
        logger.debug(
            f"[{self.room_id}] [msg:{msg_id}] 收到消息 operation={header.operation}")
        try:
            match header.operation:
                case Operation.SEND_MSG_REPLY:
                    while True:
                        body = payload[offset +
                                       header.raw_header_size: offset + header.pack_len]
                        await self._parse_message(header, body, msg_id)
                        offset += header.pack_len
                        if offset >= len(payload):
                            break
                        header = HeaderTuple(
                            *HEADER_STRUCT.unpack_from(payload, offset))
                case Operation.HEARTBEAT_REPLY:
                    message = payload[offset + header.raw_header_size:]
                    heartbeat_values = [
                        int.from_bytes(message[i:i + 4])
                        for i in range(0, len(message), 4)
                    ]
                    logger.debug(
                        f"[{self.room_id}] [msg:{msg_id}] 心跳回应: {heartbeat_values}"
                    )
                case Operation.AUTH_REPLY:
                    message = payload[offset + header.raw_header_size:]
                    decode_body = json.loads(message.decode())
                    if decode_body["code"] != AuthReplyCode.OK:
                        logger.error(f"[{self.room_id}] [msg:{msg_id}] 认证失败 | code:{decode_body['code']}")
                        raise AuthError(
                            f"auth reply error, code={decode_body['code']}, body={decode_body}")
                    logger.debug(f"[{self.room_id}] [msg:{msg_id}] 认证回应: {decode_body}")
        except struct.error:
            logger.error(
                f"[{self.room_id}] [msg:{msg_id}] parsing header failed offset={offset} payload={payload}")

    async def _parse_message(self, header: HeaderTuple, payload: bytes, msg_id: int) -> None:
        decode_body: dict
        match header.ver:
            case ProtoVer.BROTLI:
                await self._on_message(
                    await asyncio.to_thread(brotli.decompress, payload), msg_id)
            case ProtoVer.NORMAL:
                if len(payload) != 0:
                    decode_body = json.loads(payload.decode())
                    if self.room_id is None:
                        raise RuntimeError("room_id未设置")
                    cmd = decode_body.get("cmd", "")
                    logger.debug(
                        f"[{self.room_id}] [msg:{msg_id}] 解析消息 cmd={cmd}")
                    await self._msg_hander.handle(self.room_id, decode_body, msg_id)
                    if self._config.save_history_method == 2:
                        await asyncio.create_task(self._write_file(decode_body))

    async def _write_file(self, data: dict) -> bool:
        file_path = TEMP_PATH / "bililive" / f"{self.room_id}.json"
        data["add_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            if file_path.exists():
                async with aiofiles.open(file_path, "r+", encoding="utf-8") as file:
                    content = await file.read()
                    old_data: list[dict] = json.loads(
                        content) if content else []
                    old_data.append(data)
                    await file.seek(0)
                    await file.truncate()
                    await file.write(json.dumps(old_data, ensure_ascii=False, indent=4))
            else:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                async with aiofiles.open(file_path, "w", encoding="utf-8") as file:
                    await file.write(json.dumps([data], ensure_ascii=False, indent=4))
            return True
        except Exception as e:
            logger.warning(f"[{self.room_id}] 文件写入错误. {type(e).__name__}: {e}")
            return False

    async def get_room_id(self) -> None:
        params = await SignedParams.get_end_result(self.user_id)
        if self._session is None:
            raise RuntimeError("session未初始化")
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
        if self._session is None:
            raise RuntimeError("session未初始化")
        await self._session.close()
        await self.stop()

    async def stop(self):
        if self._Main_Task is not None:
            try:
                self._Main_Task.cancel()
                await asyncio.wait_for(self._Main_Task, timeout=5.0)
            except TimeoutError:
                logger.warning("主任务取消超时")
            except asyncio.CancelledError:
                pass
            self._Main_Task = None
        self.program_status = False

    async def close(self):
        if self._session and self._own_session:
            await self._session.close()
            self._session = None

    async def send_msg(self, message: str, reply_mid: int = 0, reply_uname: str = ""):
        """
        发送弹幕
        :param message: 需要发送的消息
        :param reply_mid: 需要@时提供的用户mid
        :param reply_uname: 需要@时提供的用户名字
        :return: None
        """
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
        if self._session is None:
            raise RuntimeError("session未初始化")
        async with self._session.post("https://api.live.bilibili.com/msg/send", data=data) as response:
            response.raise_for_status()
            data: dict = await response.json()
        match data["code"]:
            case 0:
                logger.success(
                    f"[{self.room_id}] | 成功发送消息: {data['msg'] if data.get('msg') else message}")
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
                logger.warning(
                    f"未知错误code:{data['code']}, 消息:{data['message']}")

    async def _get_cookie_csrf(self) -> str:
        cookie = self.headers["Cookie"]
        csrf = cookie[cookie.find("bili_jct"):]
        return csrf[9:csrf.find(";")]

    async def _get_login_mid(self) -> int:
        try:
            if self._session is None:
                raise RuntimeError("session未初始化")
            async with self._session.get("https://api.bilibili.com/x/space/myinfo") as response:
                response.raise_for_status()
                data = await response.json()
            return data["data"]["mid"]
        except KeyError:
            logger.warning(f"[{self.room_id}] 获取登录用户UID失败,使用游客登录")
            return 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop_and_close()
        if exc_type is asyncio.CancelledError:
            return True
        return None
