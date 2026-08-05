"""Handler 消息分发逻辑测试

验证 MsgType 枚举重构后的消息路由正确性，覆盖：
- MsgType 枚举与 MessageInterface 子类的一致性
- _CMD_MODEL_DICT 路由表映射
- _func 字典键类型与 MsgType 的一致性
- Handler.handle() 消息分发与回调触发
- CMD 后缀截断、忽略 CMD、未知 CMD 的边界情况
"""

import asyncio
import base64
from typing import ClassVar

from loguru import logger
import pytest

from live_streams.handler import IGNORED_CMDS, Handler, _func, logged_unknown_cmds
from live_streams.models import (
    DanmakuMessage,
    GiftMessage,
    GuardBuyMessage,
    InteractWordMessage,
    InteractWordV2Message,
    LikeClickMessage,
    LikeUpdateMessage,
    LoginNoticeMessage,
    MessageInterface,
    MsgType,
    SuperChatDeleteMessage,
    SuperChatMessage,
    UserToastMessage,
    WatchedChangeMessage,
    _all_subclasses,
)
import utils.InteractWordV2 as InteractWordV2

ROOM_ID = 12345


# ---------------------------------------------------------------------------
# fixture: 隔离 _func 全局状态
# ---------------------------------------------------------------------------


@pytest.fixture
def clean_func():
    """保存并恢复 _func 状态，避免测试间互相污染。"""
    saved = {k: set(v) for k, v in _func.items()}
    yield
    for k in _func:
        _func[k].clear()
        _func[k].update(saved.get(k, set()))


def _run(coro):
    """同步执行异步协程。"""
    return asyncio.run(coro)


def _encode_interact_word_v2(
    uid: int = 12345,
    uname: str = "测试用户",
    msg_type: int = 1,
    face: str = "https://example.com/face.jpg",
) -> str:
    """构造 INTERACT_WORD_V2 protobuf 并返回 base64 编码字符串。"""
    pb = InteractWordV2.INTERACT_WORD_V2(
        uid=uid,
        uname=uname,
        msg_type=msg_type,
        user_info=InteractWordV2.UserInfo(base=InteractWordV2.UserBase(face=face)),
    )
    return base64.b64encode(pb.SerializeToString()).decode()


# ---------------------------------------------------------------------------
# MsgType 枚举完整性
# ---------------------------------------------------------------------------


class TestMsgTypeEnum:
    """MsgType 枚举应在运行时从所有 MessageInterface 子类自动生成。"""

    def test_contains_all_messageinterface_subclasses(self):
        """每个 MessageInterface 子类都应作为 MsgType 成员存在。"""
        for cls in _all_subclasses(MessageInterface):
            assert cls.__name__ in MsgType.__members__
            assert MsgType[cls.__name__].value is cls

    def test_enum_value_is_model_class(self):
        """MsgType 成员的 value 应为对应的模型类本身。"""
        assert MsgType.DanmakuMessage.value is DanmakuMessage
        assert MsgType.GiftMessage.value is GiftMessage
        assert MsgType.WatchedChangeMessage.value is WatchedChangeMessage

    def test_msgtype_lookup_by_model_class(self):
        """通过模型类查找 MsgType 成员应返回正确的枚举值（handle 依赖此行为）。"""
        assert MsgType(DanmakuMessage) is MsgType.DanmakuMessage
        assert MsgType(WatchedChangeMessage) is MsgType.WatchedChangeMessage


# ---------------------------------------------------------------------------
# _CMD_MODEL_DICT 路由表
# ---------------------------------------------------------------------------


class TestCMDModelDict:
    """_CMD_MODEL_DICT 是 CMD → 消息模型的核心路由表。"""

    EXPECTED_MAPPING: ClassVar[dict[str, type[MessageInterface]]] = {
        "DANMU_MSG": DanmakuMessage,
        "SEND_GIFT": GiftMessage,
        "GUARD_BUY": GuardBuyMessage,
        "SUPER_CHAT_MESSAGE": SuperChatMessage,
        "SUPER_CHAT_MESSAGE_DELETE": SuperChatDeleteMessage,
        "INTERACT_WORD": InteractWordMessage,
        "INTERACT_WORD_V2": InteractWordV2Message,
        "LOG_IN_NOTICE": LoginNoticeMessage,
        "WATCHED_CHANGE": WatchedChangeMessage,
        "LIKE_INFO_V3_CLICK": LikeClickMessage,
        "LIKE_INFO_V3_UPDATE": LikeUpdateMessage,
        "USER_TOAST_MSG": UserToastMessage,
    }

    def test_cmd_to_model_mapping(self):
        """每个已知 CMD 应映射到正确的消息模型类。"""
        for cmd, model in self.EXPECTED_MAPPING.items():
            assert Handler._CMD_MODEL_DICT[cmd] is model

    def test_ignored_cmds_mapped_to_none(self):
        """IGNORED_CMDS 中的 CMD 应映射到 None，表示不解析。"""
        for cmd in IGNORED_CMDS:
            assert cmd in Handler._CMD_MODEL_DICT
            assert Handler._CMD_MODEL_DICT[cmd] is None

    def test_all_mapped_models_exist_in_msgtype(self):
        """_CMD_MODEL_DICT 中非 None 的模型都应能通过 MsgType(model) 查找。"""
        for cmd, model in Handler._CMD_MODEL_DICT.items():
            if model is not None:
                msg_type = MsgType(model)
                assert msg_type.value is model


# ---------------------------------------------------------------------------
# _func 字典与 MsgType 键类型一致性
# ---------------------------------------------------------------------------


class TestFuncDictConsistency:
    """_func 字典的键应与 MsgType 枚举成员完全一致。"""

    def test_func_keys_match_msgtype_members(self):
        """_func 字典的键集合应与 MsgType 枚举成员集合相同。"""
        assert set(_func.keys()) == set(MsgType)

    def test_func_values_are_sets(self):
        """_func 每个值应为 set 类型（用于存放回调函数）。"""
        for callbacks in _func.values():
            assert isinstance(callbacks, set)

    def test_append_func_registers_in_func_dict(self, clean_func):
        """append_func 注册的回调应出现在 _func 对应 MsgType 键下。"""

        async def callback(model):
            pass

        Handler.append_func(MsgType.WatchedChangeMessage)(callback)
        assert callback in _func[MsgType.WatchedChangeMessage]

    def test_append_func_accepts_multiple_msgtypes(self, clean_func):
        """append_func 应支持同时为多个 MsgType 注册同一回调。"""

        async def callback(model):
            pass

        Handler.append_func(MsgType.InteractWordMessage, MsgType.InteractWordV2Message)(callback)
        assert callback in _func[MsgType.InteractWordMessage]
        assert callback in _func[MsgType.InteractWordV2Message]

    def test_func_dict_keys_are_msgtype_instances(self):
        """_func 字典的所有键都应是 MsgType 枚举实例。"""
        for key in _func:
            assert isinstance(key, MsgType)


# ---------------------------------------------------------------------------
# Handler.handle() 消息路由
# ---------------------------------------------------------------------------


class TestMessageRouting:
    """Handler.handle() 应正确解析消息并调用注册的回调。"""

    def test_routes_watched_change(self, clean_func):
        """WATCHED_CHANGE 应路由到 WatchedChangeMessage 回调。"""
        received: list[WatchedChangeMessage] = []

        @Handler.append_func(MsgType.WatchedChangeMessage)
        async def callback(model: WatchedChangeMessage):
            received.append(model)

        message = {
            "cmd": "WATCHED_CHANGE",
            "data": {"num": 100, "text_small": "100", "text_large": "100人看过"},
        }
        _run(Handler.handle(ROOM_ID, message))

        assert len(received) == 1
        assert received[0].num == 100
        assert received[0].room_id == ROOM_ID

    def test_routes_like_update(self, clean_func):
        """LIKE_INFO_V3_UPDATE 应路由到 LikeUpdateMessage 回调。"""
        received: list[LikeUpdateMessage] = []

        @Handler.append_func(MsgType.LikeUpdateMessage)
        async def callback(model: LikeUpdateMessage):
            received.append(model)

        message = {"cmd": "LIKE_INFO_V3_UPDATE", "data": {"click_count": 42}}
        _run(Handler.handle(ROOM_ID, message))

        assert len(received) == 1
        assert received[0].click_count == 42
        assert received[0].room_id == ROOM_ID

    def test_routes_super_chat_delete(self, clean_func):
        """SUPER_CHAT_MESSAGE_DELETE 应路由到 SuperChatDeleteMessage 回调。"""
        received: list[SuperChatDeleteMessage] = []

        @Handler.append_func(MsgType.SuperChatDeleteMessage)
        async def callback(model: SuperChatDeleteMessage):
            received.append(model)

        message = {"cmd": "SUPER_CHAT_MESSAGE_DELETE", "data": {"ids": [1, 2, 3]}}
        _run(Handler.handle(ROOM_ID, message))

        assert len(received) == 1
        assert received[0].ids == [1, 2, 3]

    def test_routes_login_notice(self, clean_func):
        """LOG_IN_NOTICE 应路由到 LoginNoticeMessage 回调。"""
        received: list[LoginNoticeMessage] = []

        @Handler.append_func(MsgType.LoginNoticeMessage)
        async def callback(model: LoginNoticeMessage):
            received.append(model)

        message = {"cmd": "LOG_IN_NOTICE", "data": {"notice_msg": "请登录"}}
        _run(Handler.handle(ROOM_ID, message))

        assert len(received) == 1
        assert received[0].message == "请登录"

    def test_multiple_callbacks_same_type(self, clean_func):
        """同一消息类型的多个回调都应被调用。"""
        calls: list[str] = []

        @Handler.append_func(MsgType.WatchedChangeMessage)
        async def cb1(model):
            calls.append("cb1")

        @Handler.append_func(MsgType.WatchedChangeMessage)
        async def cb2(model):
            calls.append("cb2")

        message = {
            "cmd": "WATCHED_CHANGE",
            "data": {"num": 1, "text_small": "1", "text_large": "1人看过"},
        }
        _run(Handler.handle(ROOM_ID, message))

        assert set(calls) == {"cb1", "cb2"}

    def test_cmd_with_colon_suffix(self, clean_func):
        """带冒号后缀的 CMD（如 WATCHED_CHANGE:xxx）应正确路由。"""
        received: list[WatchedChangeMessage] = []

        @Handler.append_func(MsgType.WatchedChangeMessage)
        async def callback(model: WatchedChangeMessage):
            received.append(model)

        message = {
            "cmd": "WATCHED_CHANGE:some_suffix",
            "data": {"num": 200, "text_small": "200", "text_large": "200人看过"},
        }
        _run(Handler.handle(ROOM_ID, message))

        assert len(received) == 1
        assert received[0].num == 200

    def test_callback_not_called_for_other_types(self, clean_func):
        """注册了 WatchedChangeMessage 回调时，LikeUpdateMessage 不应触发它。"""
        received: list = []

        @Handler.append_func(MsgType.WatchedChangeMessage)
        async def callback(model):
            received.append(model)

        message = {"cmd": "LIKE_INFO_V3_UPDATE", "data": {"click_count": 99}}
        _run(Handler.handle(ROOM_ID, message))

        assert len(received) == 0

    def test_routes_gift(self, clean_func):
        """SEND_GIFT 应路由到 GiftMessage 回调。"""
        received: list[GiftMessage] = []

        @Handler.append_func(MsgType.GiftMessage)
        async def callback(model: GiftMessage):
            received.append(model)

        message = {
            "cmd": "SEND_GIFT",
            "data": {
                "giftName": "辣条",
                "num": 5,
                "uname": "送礼用户",
                "face": "https://example.com/face.png",
                "guard_level": 0,
                "uid": 111,
                "timestamp": 1700000000,
                "giftId": 1,
                "giftType": 0,
                "action": "馈食",
                "price": 100,
                "rnd": "rnd-1",
                "coin_type": "silver",
                "total_coin": 500,
                "tid": "tid-1",
            },
        }
        _run(Handler.handle(ROOM_ID, message))

        assert len(received) == 1
        assert received[0].gift_name == "辣条"
        assert received[0].num == 5
        assert received[0].uid == 111
        assert received[0].room_id == ROOM_ID

    def test_routes_danmaku(self, clean_func):
        """DANMU_MSG 应路由到 DanmakuMessage 回调。"""
        received: list[DanmakuMessage] = []

        @Handler.append_func(MsgType.DanmakuMessage)
        async def callback(model: DanmakuMessage):
            received.append(model)

        info0 = [0, 1, 25, 16777215, 1700000000, 12345, 0, "crc", 0, 0, 0, 0, 0, "", "", {}]
        info2 = [222, "弹幕用户", 0, 0, 0, 10000, 0, ""]
        info3 = [5, "粉丝牌", "主播", 111, 255, 0]
        info4 = [20, 0, 1, ">50000"]
        info5 = ["旧头衔", "新头衔"]
        message = {"cmd": "DANMU_MSG", "info": [info0, "你好", info2, info3, info4, info5, "", 0]}
        _run(Handler.handle(ROOM_ID, message))

        assert len(received) == 1
        assert received[0].msg == "你好"
        assert received[0].uid == 222
        assert received[0].uname == "弹幕用户"

    def test_routes_interact_word(self, clean_func):
        """INTERACT_WORD 应路由到 InteractWordMessage 回调。"""
        received: list[InteractWordMessage] = []

        @Handler.append_func(MsgType.InteractWordMessage)
        async def callback(model: InteractWordMessage):
            received.append(model)

        message = {
            "cmd": "INTERACT_WORD",
            "data": {
                "uname": "进场用户",
                "uid": 333,
                "uinfo": {"base": {"face": "https://example.com/enter.jpg"}},
                "msg_type": 1,
            },
        }
        _run(Handler.handle(ROOM_ID, message))

        assert len(received) == 1
        assert received[0].uid == 333
        assert received[0].uname == "进场用户"
        assert received[0].msg_type == 1

    def test_routes_interact_word_v2(self, clean_func):
        """INTERACT_WORD_V2 应路由到 InteractWordV2Message 回调。"""
        received: list[InteractWordV2Message] = []

        @Handler.append_func(MsgType.InteractWordV2Message)
        async def callback(model: InteractWordV2Message):
            received.append(model)

        message = {"cmd": "INTERACT_WORD_V2", "data": {"pb": _encode_interact_word_v2(uid=999, uname="v2用户")}}
        _run(Handler.handle(ROOM_ID, message))

        assert len(received) == 1
        assert received[0].uid == 999
        assert received[0].uname == "v2用户"

    def test_routes_super_chat(self, clean_func):
        """SUPER_CHAT_MESSAGE 应路由到 SuperChatMessage 回调。"""
        received: list[SuperChatMessage] = []

        @Handler.append_func(MsgType.SuperChatMessage)
        async def callback(model: SuperChatMessage):
            received.append(model)

        message = {
            "cmd": "SUPER_CHAT_MESSAGE",
            "data": {
                "price": 50,
                "message": "醒目留言",
                "message_trans": "",
                "start_time": 1700000000,
                "end_time": 1700000060,
                "time": 60,
                "id": 7,
                "gift": {"gift_id": 7, "gift_name": "醒目留言"},
                "uid": 444,
                "user_info": {
                    "uname": "SC用户",
                    "face": "https://example.com/sc.jpg",
                    "guard_level": 0,
                    "user_level": 30,
                },
                "background_bottom_color": "#000",
                "background_color": "#111",
                "background_icon": "icon",
                "background_image": "",
                "background_price_color": "#222",
            },
        }
        _run(Handler.handle(ROOM_ID, message))

        assert len(received) == 1
        assert received[0].price == 50
        assert received[0].message == "醒目留言"
        assert received[0].uid == 444

    def test_routes_like_click(self, clean_func):
        """LIKE_INFO_V3_CLICK 应路由到 LikeClickMessage 回调。"""
        received: list[LikeClickMessage] = []

        @Handler.append_func(MsgType.LikeClickMessage)
        async def callback(model: LikeClickMessage):
            received.append(model)

        message = {
            "cmd": "LIKE_INFO_V3_CLICK",
            "data": {
                "uname": "点赞用户",
                "uinfo": {"uid": 555, "base": {"face": "https://example.com/like.jpg"}},
                "like_text": "点赞了",
            },
        }
        _run(Handler.handle(ROOM_ID, message))

        assert len(received) == 1
        assert received[0].uid == 555
        assert received[0].like_text == "点赞了"

    def test_routes_user_toast(self, clean_func):
        """USER_TOAST_MSG 应路由到 UserToastMessage 回调。"""
        received: list[UserToastMessage] = []

        @Handler.append_func(MsgType.UserToastMessage)
        async def callback(model: UserToastMessage):
            received.append(model)

        message = {
            "cmd": "USER_TOAST_MSG",
            "data": {
                "anchor_show": True,
                "color": "#fff",
                "gift_id": 1003,
                "guard_level": 3,
                "num": 1,
                "price": 138000,
                "role_name": "舰长",
                "toast_msg": "恭喜",
                "uid": 666,
                "unit": "月",
                "username": "上舰用户",
            },
        }
        _run(Handler.handle(ROOM_ID, message))

        assert len(received) == 1
        assert received[0].uid == 666
        assert received[0].role_name == "舰长"
        assert received[0].anchor_show is True

    def test_routes_guard_buy(self, clean_func):
        """GUARD_BUY 应路由到 GuardBuyMessage 回调。"""
        received: list[GuardBuyMessage] = []

        @Handler.append_func(MsgType.GuardBuyMessage)
        async def callback(model: GuardBuyMessage):
            received.append(model)

        message = {
            "cmd": "GUARD_BUY",
            "data": {
                "uid": 777,
                "username": "舰长用户",
                "guard_level": 3,
                "num": 1,
                "price": 138000,
                "gift_id": 1003,
                "gift_name": "舰长",
                "start_time": 1700000000,
                "end_time": 1700000000,
            },
        }
        _run(Handler.handle(ROOM_ID, message))

        assert len(received) == 1
        assert received[0].uid == 777
        assert received[0].gift_name == "舰长"
        assert received[0].guard_level == 3


# ---------------------------------------------------------------------------
# 忽略 CMD 和未知 CMD
# ---------------------------------------------------------------------------


class TestIgnoredAndUnknownCMDs:
    """忽略 CMD 和未知 CMD 不应触发回调。"""

    def test_ignored_cmd_no_callback(self, clean_func):
        """IGNORED_CMDS 中的 CMD 不应触发任何回调。"""
        received: list = []

        @Handler.append_func(MsgType.DanmakuMessage)
        async def callback(model):
            received.append(model)

        _run(Handler.handle(ROOM_ID, {"cmd": "COMBO_SEND", "data": {}}))
        assert len(received) == 0

    def test_unknown_cmd_no_callback(self, clean_func):
        """未知 CMD 不应触发回调，也不应崩溃。"""
        received: list = []

        @Handler.append_func(MsgType.DanmakuMessage)
        async def callback(model):
            received.append(model)

        _run(Handler.handle(ROOM_ID, {"cmd": "TOTALLY_UNKNOWN_CMD", "data": {}}))
        assert len(received) == 0

    def test_empty_cmd_no_crash(self, clean_func):
        """空 CMD 或缺失 CMD 不应导致崩溃。"""
        _run(Handler.handle(ROOM_ID, {"cmd": ""}))
        _run(Handler.handle(ROOM_ID, {}))


# ---------------------------------------------------------------------------
# from_command 解析异常处理
# ---------------------------------------------------------------------------


class TestFromCommandErrorHandling:
    """from_command 解析异常应被捕获并记录日志，而非终止处理。"""

    def test_keyerror_in_from_command_is_caught(self, clean_func):
        """from_command 抛出 KeyError 时应被捕获并记录警告，回调不应被调用。"""
        log_messages: list[str] = []

        def sink(message):
            log_messages.append(message.record["message"])

        handler_id = logger.add(sink, level="WARNING")
        try:
            received: list = []

            @Handler.append_func(MsgType.WatchedChangeMessage)
            async def callback(model):
                received.append(model)

            # WATCHED_CHANGE 的 from_command 需要 data 中有 num/text_small/text_large
            # 缺少这些字段会触发 KeyError
            message = {"cmd": "WATCHED_CHANGE", "data": {}}
            _run(Handler.handle(ROOM_ID, message))

            # 回调不应被调用
            assert len(received) == 0
            # 应记录包含解析失败信息的警告日志
            assert any("消息解析失败" in msg for msg in log_messages)
        finally:
            logger.remove(handler_id)

    def test_indexerror_in_from_command_is_caught(self, clean_func):
        """from_command 抛出 IndexError 时应被捕获并记录警告，回调不应被调用。"""
        log_messages: list[str] = []

        def sink(message):
            log_messages.append(message.record["message"])

        handler_id = logger.add(sink, level="WARNING")
        try:
            received: list = []

            @Handler.append_func(MsgType.DanmakuMessage)
            async def callback(model):
                received.append(model)

            # DANMU_MSG 的 from_command 需要 info 列表有足够的元素
            # info 为空列表会触发 IndexError
            message = {"cmd": "DANMU_MSG", "info": []}
            _run(Handler.handle(ROOM_ID, message))

            # 回调不应被调用
            assert len(received) == 0
            # 应记录包含解析失败信息的警告日志
            assert any("消息解析失败" in msg for msg in log_messages)
        finally:
            logger.remove(handler_id)

    def test_normal_message_still_works_after_error(self, clean_func):
        """解析异常后，后续正常消息仍应被正确处理。"""
        log_messages: list[str] = []

        def sink(message):
            log_messages.append(message.record["message"])

        handler_id = logger.add(sink, level="WARNING")
        try:
            received: list[WatchedChangeMessage] = []

            @Handler.append_func(MsgType.WatchedChangeMessage)
            async def callback(model: WatchedChangeMessage):
                received.append(model)

            # 先发送一条会触发 KeyError 的消息
            _run(Handler.handle(ROOM_ID, {"cmd": "WATCHED_CHANGE", "data": {}}))
            # 再发送一条正常消息
            _run(
                Handler.handle(
                    ROOM_ID,
                    {
                        "cmd": "WATCHED_CHANGE",
                        "data": {"num": 100, "text_small": "100", "text_large": "100人看过"},
                    },
                )
            )

            # 异常消息的回调不应被调用，正常消息的回调应被调用
            assert len(received) == 1
            assert received[0].num == 100
            # 应有解析失败的警告日志
            assert any("消息解析失败" in msg for msg in log_messages)
        finally:
            logger.remove(handler_id)


# ---------------------------------------------------------------------------
# 回调异常处理
# ---------------------------------------------------------------------------


class TestCallbackErrorHandling:
    """回调执行异常应被记录，且不影响其他回调。"""

    def test_callback_exception_logged_and_continued(self, clean_func):
        """一个回调抛出异常时，应记录 error 日志，其他回调仍正常执行。"""
        log_messages: list[str] = []

        def sink(message):
            log_messages.append(message.record["message"])

        handler_id = logger.add(sink, level="ERROR")
        try:
            received: list[WatchedChangeMessage] = []

            @Handler.append_func(MsgType.WatchedChangeMessage)
            async def failing_callback(model: WatchedChangeMessage):
                raise RuntimeError("回调执行失败")

            @Handler.append_func(MsgType.WatchedChangeMessage)
            async def normal_callback(model: WatchedChangeMessage):
                received.append(model)

            message = {
                "cmd": "WATCHED_CHANGE",
                "data": {"num": 50, "text_small": "50", "text_large": "50人看过"},
            }
            _run(Handler.handle(ROOM_ID, message))

            # 正常回调仍应被调用
            assert len(received) == 1
            assert received[0].num == 50
            # 应记录回调执行失败的 error 日志
            assert any("回调执行失败" in msg for msg in log_messages)
        finally:
            logger.remove(handler_id)


# ---------------------------------------------------------------------------
# 未知 CMD 去重日志
# ---------------------------------------------------------------------------


class TestUnknownCmdLogging:
    """未知 CMD 的“未知CMD”日志应只记录一次。"""

    def test_unknown_cmd_logged_once(self, clean_func):
        """同一未知 CMD 多次出现时，“未知CMD”日志只记录一次。"""
        unknown_cmd = "UNIQUE_TEST_CMD_LOGGED_ONCE"
        # 清理历史状态，确保该 CMD 尚未被记录
        logged_unknown_cmds.discard(unknown_cmd)

        log_messages: list[str] = []

        def sink(message):
            log_messages.append(message.record["message"])

        handler_id = logger.add(sink, level="WARNING")
        try:
            # 发送同一未知 CMD 两次
            _run(Handler.handle(ROOM_ID, {"cmd": unknown_cmd, "data": {}}))
            _run(Handler.handle(ROOM_ID, {"cmd": unknown_cmd, "data": {}}))

            # “未知CMD” 日志应只出现一次
            unknown_count = sum(1 for msg in log_messages if "未知CMD" in msg)
            assert unknown_count == 1
            # “未解析CMD” 日志应出现两次
            unresolved_count = sum(1 for msg in log_messages if "未解析CMD" in msg)
            assert unresolved_count == 2
        finally:
            logger.remove(handler_id)
            logged_unknown_cmds.discard(unknown_cmd)
