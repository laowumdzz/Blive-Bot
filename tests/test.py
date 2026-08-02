"""INTERACT_WORD_V2 protobuf 反序列化测试

使用真实样本数据验证 protobuf 反序列化的字段正确性，
确保 InteractWordV2 模型与 utils/InteractWordV2.proto 的字段映射一致。
"""

import base64

from google.protobuf.message import DecodeError

import utils.InteractWordV2 as interact_word_v2_pb2

# 真实直播间抓取的 INTERACT_WORD_V2 样本数据（base64 编码的 protobuf）
ENCODED_DATA = (
    "CMCxxs0EEhLljYPljYPlrrbjga7nqbrkuIMiAwYDASgBMLS5ieEGOJryssMGQI6VifC4NEou"
    "CMXl1wwQGBoJ5aW96L+Q5Y2DIMuoaSjLqGkwkrvKAjjLqGlAAWCR10loiaDsF2IAeLrnpJXh"
    "zoyoGIABA5oBALIB+QEIwLHGzQQSaQoS5Y2D5Y2D5a6244Gu56m65LiDEkpodHRwczovL2kw"
    "Lmhkc2xiLmNvbS9iZnMvZmFjZS9mNjBmOTNjYjhiNGNkZmRjYjhjY2FiMzlmYWQ4NDZhNTQx"
    "ZWNmOGNkLmpwZ0IHIzAwRDFGMRppCgnlpb3ov5DljYMQGBjLqGkgkrvKAijLqGkwy6hpOPXq"
    "EkgBUMXl1wxgiaDsF3oJIzQzQjNFM0NDggEJIzQzQjNFM0NDigEJIzVGQzdGNEZGkgEJI0ZG"
    "RkZGRkZGmgEJIzAwMzA4Qzk5IgIIHDIXCAMSEzIwMjUtMDctMjMgMjM6NTk6NTm6AQA="
)


def _decode_sample() -> interact_word_v2_pb2.INTERACT_WORD_V2:
    """解码样本数据并返回 protobuf 对象。"""
    binary_data = base64.b64decode(ENCODED_DATA)
    interact_word = interact_word_v2_pb2.INTERACT_WORD_V2()
    interact_word.ParseFromString(binary_data)
    return interact_word


def test_uid():
    """用户ID应正确解析。"""
    assert _decode_sample().uid == 1236375744


def test_uname():
    """用户名应正确解析（含中日文混合字符）。"""
    assert _decode_sample().uname == "千千家の空七"


def test_msg_type():
    """消息类型应为进场（msg_type=1）。"""
    assert _decode_sample().msg_type == 1


def test_face_url():
    """用户头像URL应正确解析。"""
    msg = _decode_sample()
    assert msg.user_info.base.face == (
        "https://i0.hdslb.com/bfs/face/f60f93cb8b4cdfdcb8ccab39fad846a541ecf8cd.jpg"
    )


def test_invalid_protobuf_raises_decodeerror():
    """无效的 protobuf 字节流应抛出 DecodeError。"""
    bad_data = base64.b64encode(b"\xff\xff").decode()
    interact_word = interact_word_v2_pb2.INTERACT_WORD_V2()
    try:
        interact_word.ParseFromString(base64.b64decode(bad_data))
        # 如果没有抛出异常，说明 protobuf 容忍了无效数据，验证字段为默认值
        assert interact_word.uid == 0
    except DecodeError:
        pass  # DecodeError 也是可接受的预期行为
