from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message

DESCRIPTOR: _descriptor.FileDescriptor

class MedalInfo(_message.Message):
    __slots__ = ("color", "color_border", "color_end", "color_start", "int2", "int4", "name", "roomid", "target_id")
    TARGET_ID_FIELD_NUMBER: _ClassVar[int]
    INT2_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    COLOR_FIELD_NUMBER: _ClassVar[int]
    COLOR_START_FIELD_NUMBER: _ClassVar[int]
    COLOR_END_FIELD_NUMBER: _ClassVar[int]
    COLOR_BORDER_FIELD_NUMBER: _ClassVar[int]
    ROOMID_FIELD_NUMBER: _ClassVar[int]
    INT4_FIELD_NUMBER: _ClassVar[int]
    target_id: int
    int2: int
    name: str
    color: int
    color_start: int
    color_end: int
    color_border: int
    roomid: int
    int4: int
    def __init__(self, target_id: int | None = ..., int2: int | None = ..., name: str | None = ..., color: int | None = ..., color_start: int | None = ..., color_end: int | None = ..., color_border: int | None = ..., roomid: int | None = ..., int4: int | None = ...) -> None: ...

class UMedalInfo(_message.Message):
    __slots__ = ("color", "color_border", "color_end", "color_start", "id", "int4", "level", "name", "ruid", "v2_medal_color_border", "v2_medal_color_end", "v2_medal_color_start", "v2_medal_level", "v2_medal_text")
    NAME_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    COLOR_START_FIELD_NUMBER: _ClassVar[int]
    COLOR_END_FIELD_NUMBER: _ClassVar[int]
    COLOR_BORDER_FIELD_NUMBER: _ClassVar[int]
    COLOR_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    RUID_FIELD_NUMBER: _ClassVar[int]
    INT4_FIELD_NUMBER: _ClassVar[int]
    V2_MEDAL_COLOR_START_FIELD_NUMBER: _ClassVar[int]
    V2_MEDAL_COLOR_END_FIELD_NUMBER: _ClassVar[int]
    V2_MEDAL_COLOR_BORDER_FIELD_NUMBER: _ClassVar[int]
    V2_MEDAL_TEXT_FIELD_NUMBER: _ClassVar[int]
    V2_MEDAL_LEVEL_FIELD_NUMBER: _ClassVar[int]
    name: str
    level: int
    color_start: int
    color_end: int
    color_border: int
    color: int
    id: int
    ruid: int
    int4: int
    v2_medal_color_start: str
    v2_medal_color_end: str
    v2_medal_color_border: str
    v2_medal_text: str
    v2_medal_level: str
    def __init__(self, name: str | None = ..., level: int | None = ..., color_start: int | None = ..., color_end: int | None = ..., color_border: int | None = ..., color: int | None = ..., id: int | None = ..., ruid: int | None = ..., int4: int | None = ..., v2_medal_color_start: str | None = ..., v2_medal_color_end: str | None = ..., v2_medal_color_border: str | None = ..., v2_medal_text: str | None = ..., v2_medal_level: str | None = ...) -> None: ...

class UserBase(_message.Message):
    __slots__ = ("face", "uname")
    UNAME_FIELD_NUMBER: _ClassVar[int]
    FACE_FIELD_NUMBER: _ClassVar[int]
    uname: str
    face: str
    def __init__(self, uname: str | None = ..., face: str | None = ...) -> None: ...

class UserInfo(_message.Message):
    __slots__ = ("base", "medal_info", "message1", "string1", "uid")
    class Message1(_message.Message):
        __slots__ = ("int1",)
        INT1_FIELD_NUMBER: _ClassVar[int]
        int1: int
        def __init__(self, int1: int | None = ...) -> None: ...
    UID_FIELD_NUMBER: _ClassVar[int]
    BASE_FIELD_NUMBER: _ClassVar[int]
    MEDAL_INFO_FIELD_NUMBER: _ClassVar[int]
    MESSAGE1_FIELD_NUMBER: _ClassVar[int]
    STRING1_FIELD_NUMBER: _ClassVar[int]
    uid: int
    base: UserBase
    medal_info: UMedalInfo
    message1: UserInfo.Message1
    string1: str
    def __init__(self, uid: int | None = ..., base: UserBase | _Mapping | None = ..., medal_info: UMedalInfo | _Mapping | None = ..., message1: UserInfo.Message1 | _Mapping | None = ..., string1: str | None = ...) -> None: ...

class ActivityMessage(_message.Message):
    __slots__ = ("icon", "msg", "type")
    ICON_FIELD_NUMBER: _ClassVar[int]
    MSG_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    icon: str
    msg: str
    type: int
    def __init__(self, icon: str | None = ..., msg: str | None = ..., type: int | None = ...) -> None: ...

class INTERACT_WORD_V2(_message.Message):
    __slots__ = ("activity_message", "int2", "int3", "medal_info", "msg_type", "roomid", "string1", "string2", "string4", "timestamp", "timestamp_millisecond", "uid", "uname", "user_info")
    UID_FIELD_NUMBER: _ClassVar[int]
    UNAME_FIELD_NUMBER: _ClassVar[int]
    STRING1_FIELD_NUMBER: _ClassVar[int]
    MSG_TYPE_FIELD_NUMBER: _ClassVar[int]
    ROOMID_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_MILLISECOND_FIELD_NUMBER: _ClassVar[int]
    MEDAL_INFO_FIELD_NUMBER: _ClassVar[int]
    STRING2_FIELD_NUMBER: _ClassVar[int]
    INT2_FIELD_NUMBER: _ClassVar[int]
    INT3_FIELD_NUMBER: _ClassVar[int]
    STRING4_FIELD_NUMBER: _ClassVar[int]
    USER_INFO_FIELD_NUMBER: _ClassVar[int]
    ACTIVITY_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    uid: int
    uname: str
    string1: str
    msg_type: int
    roomid: int
    timestamp: int
    timestamp_millisecond: int
    medal_info: MedalInfo
    string2: str
    int2: int
    int3: int
    string4: str
    user_info: UserInfo
    activity_message: ActivityMessage
    def __init__(self, uid: int | None = ..., uname: str | None = ..., string1: str | None = ..., msg_type: int | None = ..., roomid: int | None = ..., timestamp: int | None = ..., timestamp_millisecond: int | None = ..., medal_info: MedalInfo | _Mapping | None = ..., string2: str | None = ..., int2: int | None = ..., int3: int | None = ..., string4: str | None = ..., user_info: UserInfo | _Mapping | None = ..., activity_message: ActivityMessage | _Mapping | None = ...) -> None: ...
