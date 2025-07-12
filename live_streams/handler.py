"""消息解析模块"""
import asyncio
from typing import Optional, Union
from loguru import logger

from .models import *

__all__ = (
    "Handler",
)

IGNORED_CMDS = {
    'COMBO_SEND',
    'ENTRY_EFFECT',
    'HOT_RANK_CHANGED',
    'HOT_RANK_CHANGED_V2',
    'LIVE',
    'LIVE_INTERACTIVE_GAME',
    'NOTICE_MSG',
    'ONLINE_RANK_COUNT',
    'ONLINE_RANK_TOP3',
    'ONLINE_RANK_V2',
    'PK_BATTLE_END',
    'PK_BATTLE_FINAL_PROCESS',
    'PK_BATTLE_PROCESS',
    'PK_BATTLE_PROCESS_NEW',
    'PK_BATTLE_SETTLE',
    'PK_BATTLE_SETTLE_USER',
    'PK_BATTLE_SETTLE_V2',
    'PREPARING',
    'ROOM_REAL_TIME_MESSAGE_UPDATE',
    'STOP_LIVE_ROOM_LIST',
    'SUPER_CHAT_MESSAGE_JPN',
    'WIDGET_BANNER',
    "RANK_CHANGED_V2",
    "ONLINE_RANK_V3",
    "COMMON_NOTICE_DANMAKU",
    "PK_BATTLE_PUNISH_END",
}
"""常见可忽略的cmd"""

_msg_type = Union[
    type[DanmakuMessage],
    type[GeneralMessage],
    type[GiftMessage],
    type[GuardBuyMessage],
    type[SuperChatMessage],
    type[SuperChatDeleteMessage],
    type[LoginNoticeMessage],
    type[WatchedChangeMessage],
    type[LikeClickMessage],
    type[LikeUpdateMessage],
    type[InteractWordMessage],
    type[InteractWordV2Message],
]
logged_unknown_cmds = set()


class Handler:
    """
    直播消息处理器, 带消息分发和消息类型转换.
    请使用append_func装饰器装饰解析函数, 并标注需要注入的消息类型, 如:
    @Handler.append_func(DanmakuMessage)
    async def _(model):
    """

    _CMD_MODEL_DICT: dict[str, Optional[_msg_type]] = {
        # 收到弹幕
        "DANMU_MSG": DanmakuMessage,
        # 有人送礼
        "SEND_GIFT": GiftMessage,
        # 有人上舰
        "GUARD_BUY": GuardBuyMessage,
        # 醒目留言
        "SUPER_CHAT_MESSAGE": SuperChatMessage,
        # 删除醒目留言
        "SUPER_CHAT_MESSAGE_DELETE": SuperChatDeleteMessage,
        # 入场消息
        "INTERACT_WORD": InteractWordMessage,
        "INTERACT_WORD_V2": InteractWordV2Message,
        # 日志消息
        "LOG_IN_NOTICE": LoginNoticeMessage,
        # 观看人数
        "WATCHED_CHANGE": WatchedChangeMessage,
        # 用户点赞
        "LIKE_INFO_V3_CLICK": LikeClickMessage,
        # 点赞数量
        "LIKE_INFO_V3_UPDATE": LikeUpdateMessage,
        # 用户庆祝消息
        "USER_TOAST_MSG": UserToastMessage,
    }
    """cmd -> 处理回调"""
    # 忽略其他常见cmd
    for cmd in IGNORED_CMDS:
        _CMD_MODEL_DICT[cmd] = None
    del cmd

    @classmethod
    async def handle(cls, room_id: int, message: dict):
        cmd = message.get("cmd", "")
        pos = cmd.find(":")
        if pos != -1:
            cmd = cmd[:pos]

        model_type = cls._CMD_MODEL_DICT.get(cmd)
        if model_type is not None and getattr(model_type, "_func", False):
            logger.debug(f"running function {type[model_type]}")
            model = model_type.from_command(message)
            model.room_id = room_id
            await asyncio.gather(*(fun(model) for fun in model._func))

        if cmd not in cls._CMD_MODEL_DICT:
            # 只有第一次遇到未知cmd时打日志, 第二次使用通用消息模板解析
            if cmd not in logged_unknown_cmds:
                logged_unknown_cmds.add(cmd)
                print(f"[{room_id}] | 遇见未知CMD:{cmd} | 原始消息:{message}")
            else:
                cls._CMD_MODEL_DICT[cmd] = GeneralMessage
                print(f"[{room_id}] | 未解析CMD:{cmd} | 使用通用消息模板解析")

    @classmethod
    def append_func(cls, *msg_types: _msg_type):
        def decorator(func):
            for msg_type in msg_types:
                if getattr(msg_type, "_func", None) is None:
                    msg_type._func = []
                msg_type._func.append(func)

        return decorator
