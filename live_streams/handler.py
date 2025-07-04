from typing import Optional, Any

from .models import *

__all__ = (
    "Handler",
)

IGNORED_CMDS = (
    'COMBO_SEND',
    'ENTRY_EFFECT',
    'HOT_RANK_CHANGED',
    'HOT_RANK_CHANGED_V2',
    'INTERACT_WORD',
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
)
"""常见可忽略的cmd"""

logged_unknown_cmds = set()

MUSIC_KEYWORDS = {"点歌", "来一首", "来首", "放首", "点一首"}


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


class Handler(HandlerInterface):
    """
    一个简单的消息处理器实现，带消息分发和消息类型转换。继承并重写_on_xxx方法即可实现自己的处理器
    """

    @staticmethod
    async def _on_danmaku(room_id: int, message: dict):
        """收到弹幕"""
        model: DanmakuMessage = DanmakuMessage.from_command(message["info"])
        music_match = match_keyword(model.msg, MUSIC_KEYWORDS)
        print(
            f"[{room_id}] | {model.uname}: {model.msg} | 匹配: {music_match} | 等级: {model.user_level} | 舰队类型: {model.privilege_type}")

    @staticmethod
    async def _on_gift(room_id: int, message: dict):
        """收到礼物"""
        model: GiftMessage = GiftMessage.from_command(message["data"])
        print(
            f"[{room_id}] | {model.uname} 赠送{model.gift_name}x{model.num}, ({model.coin_type}瓜子x{model.total_coin})")

    @staticmethod
    async def _on_buy_guard(room_id: int, message: dict):
        """有人上舰"""
        model: GuardBuyMessage = GuardBuyMessage.from_command(message["data"])
        print(f"[{room_id}] | {model.username} 购买{model.gift_name}")

    @staticmethod
    async def _on_super_chat(room_id: int, message: dict):
        """醒目留言"""
        model: SuperChatMessage = SuperChatMessage.from_command(message["data"])
        print(f"[{room_id}] | 醒目留言 ¥{model.price} | {model.uname}：{model.message}")

    @staticmethod
    async def _interact_word(room_id: int, message: dict):
        """入场消息回调"""
        model: GeneralMessage = GeneralMessage.from_command(message["data"])
        print(f"[{room_id}] | uname: {model.raw_message['data']['uname']}")

    @staticmethod
    async def _on_super_chat_delete(room_id: int, message: dict):
        """删除醒目留言"""
        # model = SuperChatDeleteMessage.from_command(message["data"])

    @staticmethod
    async def _on_notice_message(room_id: int, message: dict) -> None:
        """系统日志消息"""
        model: NoticeMessage = NoticeMessage.from_command(message["data"])
        print(f"[{room_id}] | 日志: {model.message}")

    @staticmethod
    async def _on_watched_change(room_id: int, message: dict):
        """观看过的人数"""
        model: WatchedChangeMessage = WatchedChangeMessage.from_command(message["data"])
        print(f"[{room_id}] | 观看人数: {model.text_large}")

    _CMD_CALLBACK_DICT: dict[str, Optional[Any]] = {
        # 收到弹幕
        "DANMU_MSG": _on_danmaku,
        # 有人送礼
        "SEND_GIFT": _on_gift,
        # 有人上舰
        "GUARD_BUY": _on_buy_guard,
        # 醒目留言
        "SUPER_CHAT_MESSAGE": _on_super_chat,
        # 删除醒目留言
        "SUPER_CHAT_MESSAGE_DELETE": _on_super_chat_delete,
        # 入场消息
        "INTERACT_WORD": _interact_word,
        # 日志消息
        "LOG_IN_NOTICE": _on_notice_message,
        # 观看人数
        "WATCHED_CHANGE": _on_watched_change,
    }
    """cmd -> 处理回调"""
    # 忽略其他常见cmd
    for cmd in IGNORED_CMDS:
        _CMD_CALLBACK_DICT[cmd] = None
    del cmd

    @classmethod
    async def handle(cls, room_id: int, message: dict):
        cmd = message.get("cmd", "")
        pos = cmd.find(":")
        if pos != -1:
            cmd = cmd[:pos]

        callback = cls._CMD_CALLBACK_DICT.get(cmd)
        if callback is not None:
            await callback(room_id, message)

        if cmd not in cls._CMD_CALLBACK_DICT:
            # 只有第一次遇到未知cmd时打日志
            if cmd not in logged_unknown_cmds:
                logged_unknown_cmds.add(cmd)
                print(f"[{room_id}] | 未知CMD:{cmd} | 原始消息:{message}")
