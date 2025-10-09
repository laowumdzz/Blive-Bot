from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class MedalInfo(_message.Message):
    __slots__ = ("target_id", "int2", "name", "color", "color_start", "color_end", "color_border", "roomid", "int4")
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
    def __init__(self, target_id: _Optional[int] = ..., int2: _Optional[int] = ..., name: _Optional[str] = ..., color: _Optional[int] = ..., color_start: _Optional[int] = ..., color_end: _Optional[int] = ..., color_border: _Optional[int] = ..., roomid: _Optional[int] = ..., int4: _Optional[int] = ...) -> None: ...

class UMedalInfo(_message.Message):
    __slots__ = ("name", "level", "color_start", "color_end", "color_border", "color", "id", "ruid", "int4", "v2_medal_color_start", "v2_medal_color_end", "v2_medal_color_border", "v2_medal_text", "v2_medal_level")
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
    def __init__(self, name: _Optional[str] = ..., level: _Optional[int] = ..., color_start: _Optional[int] = ..., color_end: _Optional[int] = ..., color_border: _Optional[int] = ..., color: _Optional[int] = ..., id: _Optional[int] = ..., ruid: _Optional[int] = ..., int4: _Optional[int] = ..., v2_medal_color_start: _Optional[str] = ..., v2_medal_color_end: _Optional[str] = ..., v2_medal_color_border: _Optional[str] = ..., v2_medal_text: _Optional[str] = ..., v2_medal_level: _Optional[str] = ...) -> None: ...

class UserBase(_message.Message):
    __slots__ = ("uname", "face")
    UNAME_FIELD_NUMBER: _ClassVar[int]
    FACE_FIELD_NUMBER: _ClassVar[int]
    uname: str
    face: str
    def __init__(self, uname: _Optional[str] = ..., face: _Optional[str] = ...) -> None: ...

class UserInfo(_message.Message):
    __slots__ = ("uid", "base", "medal_info", "message1", "string1")
    class Message1(_message.Message):
        __slots__ = ("int1",)
        INT1_FIELD_NUMBER: _ClassVar[int]
        int1: int
        def __init__(self, int1: _Optional[int] = ...) -> None: ...
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
    def __init__(self, uid: _Optional[int] = ..., base: _Optional[_Union[UserBase, _Mapping]] = ..., medal_info: _Optional[_Union[UMedalInfo, _Mapping]] = ..., message1: _Optional[_Union[UserInfo.Message1, _Mapping]] = ..., string1: _Optional[str] = ...) -> None: ...

class ActivityMessage(_message.Message):
    __slots__ = ("icon", "msg", "type")
    ICON_FIELD_NUMBER: _ClassVar[int]
    MSG_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    icon: str
    msg: str
    type: int
    def __init__(self, icon: _Optional[str] = ..., msg: _Optional[str] = ..., type: _Optional[int] = ...) -> None: ...

class INTERACT_WORD_V2(_message.Message):
    __slots__ = ("uid", "uname", "string1", "msg_type", "roomid", "timestamp", "timestamp_millisecond", "medal_info", "string2", "int2", "int3", "string4", "user_info", "activity_message")
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
    def __init__(self, uid: _Optional[int] = ..., uname: _Optional[str] = ..., string1: _Optional[str] = ..., msg_type: _Optional[int] = ..., roomid: _Optional[int] = ..., timestamp: _Optional[int] = ..., timestamp_millisecond: _Optional[int] = ..., medal_info: _Optional[_Union[MedalInfo, _Mapping]] = ..., string2: _Optional[str] = ..., int2: _Optional[int] = ..., int3: _Optional[int] = ..., string4: _Optional[str] = ..., user_info: _Optional[_Union[UserInfo, _Mapping]] = ..., activity_message: _Optional[_Union[ActivityMessage, _Mapping]] = ...) -> None: ...
