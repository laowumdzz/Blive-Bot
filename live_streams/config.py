from pydantic import BaseModel


class Config(BaseModel):
    live_room_id: list[int] = None
    """需要监听的直播间ID"""
    use_login: bool = False
    """是否使用Cookie登录"""
    data_analysis: bool = False
    """是否启用数据分析,未启用消息存储时只能分析单场直播"""
    live_room_history_save: bool = False
    """是否启用消息存储,可以分析长期数据"""
    save_history_analysis: bool = False
    """保存以往分析结果,使长期数据分析更准确"""
    save_data_method: int = 0
    """保存消息方式,0为数据库保存,1为本地JSON文件保存"""
    cookie: str = None
    """COOKIE"""


CMD_TO_INFO = {
    "DANMU_MSG": "弹幕",
    "DM_INTERACTION": "连续弹幕消息",
    "INTERACT_WORD": "进场或关注消息",
    "GUARD_BUY": "上舰通知",
    "USER_TOAST_MSG": "用户庆祝消息",
    "SUPER_CHAT_MESSAGE": "醒目留言",
    "SEND_GIFT": "送礼",
    "GIFT_STAR_PROCESS": "礼物星球点亮",
    "COMBO_SEND": "礼物连击",
    "NOTICE_MSG": "通知消息",
    "LOG_IN_NOTICE": "日志",
    "PREPARING": "主播准备中",
    "ROOM_REAL_TIME_MESSAGE_UPDATE": "主播信息更新",
    "ONLINE_RANK_V2": "直播间高能榜",
    "ONLINE_RANK_COUNT": "直播间高能用户数量",
    "ONLINE_RANK_TOP3": "用户到达直播间高能榜前三名的消息",
    "POPULAR_RANK_CHANGED": "直播间在人气榜的排名改变",
    "LIKE_INFO_V3_CLICK": "直播间用户点赞",
    "LIKE_INFO_V3_UPDATE": "直播间点赞数",
    "POPULARITY_RED_POCKET_START": "直播间发红包弹幕",
    "POPULARITY_RED_POCKET_NEW": "直播间红包",
    "POPULARITY_RED_POCKET_WINNER_LIST": "直播间抢到红包的用户",
    "WATCHED_CHANGE": "直播间看过人数",
    "ENTRY_EFFECT": "用户进场特效",
    "AREA_RANK_CHANGED": "直播间在所属分区的排名改变",
    "COMMON_NOTICE_DANMAKU": "直播间在所属分区排名提升的祝福",
    "ROOM_CHANGE": "直播间信息更改",
    "WIDGET_BANNER": "顶部横幅",
    "STOP_LIVE_ROOM_LIST": "下播的直播间",
    "PLAY_TOGETHER": "未知消息",
    "PK_BATTLE_PROCESS": "PK进程",
}
