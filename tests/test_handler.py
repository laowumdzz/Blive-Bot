"""Handler 消息分发逻辑测试

验证 MsgType 枚举重构后的消息路由正确性，覆盖：
- MsgType 枚举与 MessageInterface 子类的一致性
- _CMD_MODEL_DICT 路由表映射
- _func 字典键类型与 MsgType 的一致性
- Handler.handle() 消息分发与回调触发
- CMD 后缀截断、忽略 CMD、未知 CMD 的边界情况
"""

import asyncio
from typing import ClassVar

from loguru import logger
import pytest

from live_streams.handler import IGNORED_CMDS, Handler, _func
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
            _run(Handler.handle(ROOM_ID, {
                "cmd": "WATCHED_CHANGE",
                "data": {"num": 100, "text_small": "100", "text_large": "100人看过"},
            }))

            # 异常消息的回调不应被调用，正常消息的回调应被调用
            assert len(received) == 1
            assert received[0].num == 100
            # 应有解析失败的警告日志
            assert any("消息解析失败" in msg for msg in log_messages)
        finally:
            logger.remove(handler_id)
