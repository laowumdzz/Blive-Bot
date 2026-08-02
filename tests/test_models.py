"""消息模型 from_command() 解析测试

覆盖各消息模型 from_command() 的正常解析与异常场景，重点验证：
- InteractWordV2Message: protobuf 反序列化、face 字段来源（修复硬编码缺陷）、异常输入
- GiftMessage: 字段映射完整性、缺失字段异常
- DanmakuMessage: 勋章信息存在/缺失两种结构
- 其余核心模型: 正常解析路径的字段正确性
"""

import base64

from google.protobuf.message import DecodeError
import pytest

from live_streams.models import (
    DanmakuMessage,
    GeneralMessage,
    GiftMessage,
    GuardBuyMessage,
    InteractWordMessage,
    InteractWordV2Message,
    LikeClickMessage,
    LikeUpdateMessage,
    LoginNoticeMessage,
    SuperChatDeleteMessage,
    SuperChatMessage,
    UserToastMessage,
    WatchedChangeMessage,
)
import utils.InteractWordV2 as InteractWordV2


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


def _gift_data(**overrides) -> dict:
    """构造完整的 SEND_GIFT data 字段，可用 overrides 覆盖个别字段。"""
    data = {
        "giftName": "辣条",
        "num": 10,
        "uname": "送礼用户",
        "face": "https://example.com/face.png",
        "guard_level": 3,
        "uid": 67890,
        "timestamp": 1700000000,
        "giftId": 1,
        "giftType": 0,
        "action": "喂食",
        "price": 100,
        "rnd": "rnd-abc",
        "coin_type": "silver",
        "total_coin": 1000,
        "tid": "tid-001",
    }
    data.update(overrides)
    return data


def _danmaku_info(with_medal: bool = True) -> list:
    """构造 DANMU_MSG 的 info 数组。"""
    info0 = [0, 1, 25, 16777215, 1700000000, 12345, 0, "crc32", 0, 0, 0, 0, 0, "", "", {}]
    info2 = [67890, "弹幕用户", 0, 0, 0, 10000, 1, ""]
    info3 = [5, "粉丝牌", "主播名", 111, 255, 0] if with_medal else []
    info4 = [20, 0, 1, ">50000"]
    info5 = ["旧头衔", "新头衔"]
    return [info0, "Hello", info2, info3, info4, info5, "", 0]


# ---------------------------------------------------------------------------
# GiftMessage
# ---------------------------------------------------------------------------


class TestGiftMessageFromCommand:
    """GiftMessage.from_command() 正常解析与异常场景。"""

    def test_normal_parse(self):
        """完整数据应正确映射到全部字段。"""
        msg = GiftMessage.from_command({"cmd": "SEND_GIFT", "data": _gift_data()})

        assert msg.gift_name == "辣条"
        assert msg.num == 10
        assert msg.uname == "送礼用户"
        assert msg.face == "https://example.com/face.png"
        assert msg.guard_level == 3
        assert msg.uid == 67890
        assert msg.timestamp == 1700000000
        assert msg.gift_id == 1
        assert msg.gift_type == 0
        assert msg.action == "喂食"
        assert msg.price == 100
        assert msg.rnd == "rnd-abc"
        assert msg.coin_type == "silver"
        assert msg.total_coin == 1000
        assert msg.tid == "tid-001"

    def test_missing_data_raises_keyerror(self):
        """缺失 data 键应抛出 KeyError。"""
        with pytest.raises(KeyError):
            GiftMessage.from_command({"cmd": "SEND_GIFT"})

    @pytest.mark.parametrize(
        "field",
        [
            "giftName",
            "num",
            "uid",
            "face",
            "coin_type",
            "total_coin",
        ],
    )
    def test_missing_required_field_raises_keyerror(self, field):
        """缺失任意必填字段应抛出 KeyError。"""
        data = _gift_data()
        del data[field]
        with pytest.raises(KeyError):
            GiftMessage.from_command({"cmd": "SEND_GIFT", "data": data})


# ---------------------------------------------------------------------------
# InteractWordV2Message
# ---------------------------------------------------------------------------


class TestInteractWordV2MessageFromCommand:
    """InteractWordV2Message.from_command() 正常解析与异常场景。"""

    def test_normal_parse(self):
        """protobuf 应正确反序列化，face 来自 user_info.base.face 而非硬编码。"""
        raw_msg = {"cmd": "INTERACT_WORD_V2", "data": {"pb": _encode_interact_word_v2()}}
        msg = InteractWordV2Message.from_command(raw_msg)

        assert msg.uid == 12345
        assert msg.uname == "测试用户"
        assert msg.msg_type == 1
        assert msg.face == "https://example.com/face.jpg"

    def test_face_reflects_protobuf_value(self):
        """face 字段应反映 protobuf 中的实际头像 URL，而非固定值。"""
        custom_face = "https://i0.hdslb.com/bfs/face/abc.jpg"
        raw_msg = {"data": {"pb": _encode_interact_word_v2(face=custom_face)}}
        msg = InteractWordV2Message.from_command(raw_msg)
        assert msg.face == custom_face

    def test_face_defaults_to_empty_when_unset(self):
        """protobuf 未设置 user_info.base.face 时，face 应为空字符串（proto3 默认值）。"""
        pb = InteractWordV2.INTERACT_WORD_V2(uid=1, uname="无名", msg_type=2)
        encoded = base64.b64encode(pb.SerializeToString()).decode()
        msg = InteractWordV2Message.from_command({"data": {"pb": encoded}})
        assert msg.face == ""

    def test_missing_data_raises_keyerror(self):
        """缺失 data 键应抛出 KeyError。"""
        with pytest.raises(KeyError):
            InteractWordV2Message.from_command({"cmd": "INTERACT_WORD_V2"})

    def test_missing_pb_raises_keyerror(self):
        """data 中缺失 pb 键应抛出 KeyError。"""
        with pytest.raises(KeyError):
            InteractWordV2Message.from_command({"cmd": "INTERACT_WORD_V2", "data": {}})

    def test_invalid_protobuf_raises_decodeerror(self):
        """无效的 protobuf 字节流应抛出 DecodeError。"""
        bad_encoded = base64.b64encode(b"\xff").decode()
        with pytest.raises(DecodeError):
            InteractWordV2Message.from_command({"data": {"pb": bad_encoded}})


# ---------------------------------------------------------------------------
# DanmakuMessage
# ---------------------------------------------------------------------------


class TestDanmakuMessageFromCommand:
    """DanmakuMessage.from_command() 正常解析，覆盖勋章存在/缺失两种结构。"""

    def test_parse_with_medal(self):
        """勋章存在时应正确解析勋章相关字段。"""
        msg = DanmakuMessage.from_command({"info": _danmaku_info(with_medal=True)})

        assert msg.mode == 1
        assert msg.font_size == 25
        assert msg.color == 16777215
        assert msg.msg == "Hello"
        assert msg.uid == 67890
        assert msg.uname == "弹幕用户"
        assert msg.medal_level == 5
        assert msg.medal_name == "粉丝牌"
        assert msg.runame == "主播名"
        assert msg.medal_room_id == 111
        assert msg.mcolor == 255
        assert msg.special_medal == 0
        assert msg.privilege_type == 0

    def test_parse_without_medal(self):
        """勋章为空数组时应使用默认值，不抛出异常。"""
        msg = DanmakuMessage.from_command({"info": _danmaku_info(with_medal=False)})

        assert msg.msg == "Hello"
        assert msg.medal_level == 0
        assert msg.medal_name == ""
        assert msg.runame == ""
        assert msg.medal_room_id == 0
        assert msg.mcolor == 0
        assert msg.special_medal == 0

    def test_full_field_mapping(self):
        """验证 DanmakuMessage 所有字段都被正确映射。"""
        msg = DanmakuMessage.from_command({"info": _danmaku_info(with_medal=True)})

        # info[0] 派生字段
        assert msg.timestamp == 1700000000
        assert msg.rnd == 12345
        assert msg.uid_crc32 == "crc32"
        assert msg.msg_type == 0
        assert msg.bubble == 0
        assert msg.dm_type == 0
        assert msg.emoticon_options == ""
        assert msg.voice_config == ""
        assert msg.mode_info == {}

        # info[2] 派生字段
        assert msg.admin == 0
        assert msg.vip == 0
        assert msg.svip == 0
        assert msg.urank == 10000
        assert msg.mobile_verify == 1
        assert msg.uname_color == ""

        # info[4] 派生字段（用户等级）
        assert msg.user_level == 20
        assert msg.ulevel_color == 1
        assert msg.ulevel_rank == ">50000"

        # info[5] 派生字段（头衔）
        assert msg.old_title == "旧头衔"
        assert msg.title == "新头衔"

    def test_room_id_defaults_to_none(self):
        """from_command 未设置 room_id 时应为 None。"""
        msg = DanmakuMessage.from_command({"info": _danmaku_info()})
        assert msg.room_id is None

    def test_missing_info_raises_keyerror(self):
        """缺失 info 键应抛出 KeyError。"""
        with pytest.raises(KeyError):
            DanmakuMessage.from_command({})


# ---------------------------------------------------------------------------
# DanmakuMessage 属性
# ---------------------------------------------------------------------------


class TestDanmakuMessageProperties:
    """DanmakuMessage.emoticon_options_dict / voice_config_dict 属性。"""

    def test_emoticon_options_dict_from_dict(self):
        """emoticon_options 为 dict 时应直接返回。"""
        data = {"bulge_display": 0, "emoticon_unique": "official_13"}
        msg = DanmakuMessage(emoticon_options=data)
        assert msg.emoticon_options_dict == data

    def test_emoticon_options_dict_from_json_string(self):
        """emoticon_options 为 JSON 字符串时应解析为 dict。"""
        msg = DanmakuMessage(emoticon_options='{"key": "value"}')
        assert msg.emoticon_options_dict == {"key": "value"}

    def test_emoticon_options_dict_invalid_json(self):
        """emoticon_options 为无效 JSON 时应返回空 dict。"""
        msg = DanmakuMessage(emoticon_options="not json")
        assert msg.emoticon_options_dict == {}

    def test_emoticon_options_dict_none(self):
        """emoticon_options 为 None 时应返回空 dict。"""
        msg = DanmakuMessage(emoticon_options=None)
        assert msg.emoticon_options_dict == {}

    def test_voice_config_dict_from_dict(self):
        """voice_config 为 dict 时应直接返回。"""
        data = {"voice_url": "https://example.com/voice.wav", "text": "你好"}
        msg = DanmakuMessage(voice_config=data)
        assert msg.voice_config_dict == data

    def test_voice_config_dict_from_json_string(self):
        """voice_config 为 JSON 字符串时应解析为 dict。"""
        msg = DanmakuMessage(voice_config='{"text": "你好"}')
        assert msg.voice_config_dict == {"text": "你好"}

    def test_voice_config_dict_invalid_json(self):
        """voice_config 为无效 JSON 时应返回空 dict。"""
        msg = DanmakuMessage(voice_config="{invalid")
        assert msg.voice_config_dict == {}

    def test_voice_config_dict_none(self):
        """voice_config 为 None 时应返回空 dict。"""
        msg = DanmakuMessage(voice_config=None)
        assert msg.voice_config_dict == {}


# ---------------------------------------------------------------------------
# 其余核心模型正常解析
# ---------------------------------------------------------------------------


class TestOtherModelsFromCommand:
    """其余核心模型 from_command() 正常解析的字段正确性。"""

    def test_general_message(self):
        msg = GeneralMessage.from_command({"data": {"key": "value"}})
        assert msg.raw_message == {"key": "value"}

    def test_login_notice_message(self):
        msg = LoginNoticeMessage.from_command({"data": {"notice_msg": "请登录"}})
        assert msg.message == "请登录"

    def test_watched_change_message(self):
        msg = WatchedChangeMessage.from_command({"data": {"num": 999, "text_small": "999", "text_large": "999人看过"}})
        assert msg.num == 999
        assert msg.text_small == "999"
        assert msg.text_large == "999人看过"

    def test_guard_buy_message(self):
        data = {
            "uid": 111,
            "username": "舰长用户",
            "guard_level": 3,
            "num": 1,
            "price": 138000,
            "gift_id": 1003,
            "gift_name": "舰长",
            "start_time": 1700000000,
            "end_time": 1700000000,
        }
        msg = GuardBuyMessage.from_command({"data": data})
        assert msg.uid == 111
        assert msg.username == "舰长用户"
        assert msg.guard_level == 3
        assert msg.gift_name == "舰长"
        assert msg.start_time == msg.end_time == 1700000000

    def test_super_chat_message(self):
        data = {
            "price": 30,
            "message": "醒目留言内容",
            "message_trans": "",
            "start_time": 1700000000,
            "end_time": 1700000060,
            "time": 60,
            "id": 42,
            "gift": {"gift_id": 7, "gift_name": "醒目留言"},
            "uid": 222,
            "user_info": {
                "uname": "SC用户",
                "face": "https://example.com/sc.jpg",
                "guard_level": 0,
                "user_level": 30,
            },
            "background_bottom_color": "#000",
            "background_color": "#111",
            "background_icon": "icon",
            "background_image": "https://example.com/bg.jpg",
            "background_price_color": "#222",
        }
        msg = SuperChatMessage.from_command({"data": data})
        assert msg.price == 30
        assert msg.message == "醒目留言内容"
        assert msg.id == 42
        assert msg.gift_id == 7
        assert msg.gift_name == "醒目留言"
        assert msg.uid == 222
        assert msg.uname == "SC用户"
        assert msg.face == "https://example.com/sc.jpg"
        assert msg.guard_level == 0
        assert msg.user_level == 30

    def test_super_chat_delete_message(self):
        msg = SuperChatDeleteMessage.from_command({"data": {"ids": [1, 2, 3]}})
        assert msg.ids == [1, 2, 3]

    def test_like_click_message(self):
        data = {
            "uname": "点赞用户",
            "uinfo": {"uid": 333, "base": {"face": "https://example.com/like.jpg"}},
            "like_text": "点赞了",
        }
        msg = LikeClickMessage.from_command({"data": data})
        assert msg.uid == 333
        assert msg.uname == "点赞用户"
        assert msg.face == "https://example.com/like.jpg"
        assert msg.like_text == "点赞了"

    def test_like_update_message(self):
        msg = LikeUpdateMessage.from_command({"data": {"click_count": 88}})
        assert msg.click_count == 88

    def test_user_toast_message(self):
        data = {
            "anchor_show": True,
            "color": "#fff",
            "gift_id": 1003,
            "guard_level": 3,
            "num": 1,
            "price": 138000,
            "role_name": "舰长",
            "toast_msg": "恭喜成为舰长",
            "uid": 444,
            "unit": "月",
            "username": "上舰用户",
        }
        msg = UserToastMessage.from_command({"data": data})
        assert msg.uid == 444
        assert msg.username == "上舰用户"
        assert msg.guard_level == 3
        assert msg.role_name == "舰长"
        assert msg.toast_msg == "恭喜成为舰长"
        assert msg.anchor_show is True

    def test_interact_word_message(self):
        data = {
            "uname": "进场用户",
            "uid": 555,
            "uinfo": {"base": {"face": "https://example.com/enter.jpg"}},
            "msg_type": 1,
        }
        msg = InteractWordMessage.from_command({"data": data})
        assert msg.uid == 555
        assert msg.uname == "进场用户"
        assert msg.face == "https://example.com/enter.jpg"
        assert msg.msg_type == 1
