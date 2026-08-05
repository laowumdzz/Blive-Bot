import ast
from functools import reduce
from hashlib import md5
import json
import os
from pathlib import Path
import re
import tempfile
import time
import tomllib
from typing import Any, ClassVar, Self
import urllib.parse

import aiofiles
import aiohttp
from loguru import logger
import msgpack
from pydantic import BaseModel, TypeAdapter

TEMP_PATH = Path(tempfile.gettempdir()) / "BiliBili"
"""临时文件路径"""
WBI_TEMP_FILE = TEMP_PATH / "WbiSignature.pkl"
TEMP_PATH.mkdir(parents=True, exist_ok=True)


class SignedKeyData(BaseModel):
    img_key: str = ""
    sub_key: str = ""
    WbiKeys_update_timestamp: int = 0
    WbiKeys_update_count: int = 0
    WbiKeys_get_count: int = 0
    access_id: str = ""
    access_id_update_timestamp: int = 0
    access_id_update_count: int = 0
    access_id_get_count: int = 0


class SignedParamsManager:
    """
    签名类, 调用get_end_result函数即可, 利用序列化库msgpack缓存img_key和sub_key和access_id,避免反复获取触发风控
    """

    _temp_data: ClassVar[SignedKeyData] = SignedKeyData()
    flushed_time: int = 2 * 86400
    # fmt: off
    mixinKeyEncTab: ClassVar[list[int]] = [
        46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
        33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
        61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
        36, 20, 34, 44, 52
    ]
    headers: ClassVar[dict] = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/151.0.0.0 Safari/537.36 Edg/151.0.0.0",
        "Referer": "https://www.bilibili.com/",
        "Origin": "http://www.bilibili.com",
    }
    _session: ClassVar[aiohttp.ClientSession | None] = None

    @classmethod
    async def get_end_result(
            cls,
            mid: int | None = None,
            params: dict[str, Any] | None = None,
            compulsion: bool = False,
            use_webid: bool = False,
            use_cookie: bool = False,
    ) -> dict:
        """
        获取最后的结果
        :param mid: 用户UID, params和mid必填其中之一
        :param params: 自定义参数, 不输入则使用默认自带参数
        :param compulsion: 是否强制刷新数据库缓存
        :param use_webid: 是否使用w_webid,能不用就不用,如果过不了鉴权就可以启用
        :param use_cookie: 是否使用Cookie获取WBI,为True从系统环境变量获取COOKIE
        :return: 加密完成后的dict[params]
        """
        if not (mid or params):
            logger.error("Missing required parameter: either 'mid' or 'params' must be provided")
            raise KeyError("params和mid必填其中之一")
        if use_cookie:
            if cookie := os.getenv("COOKIE", None):
                cls.headers["Cookie"] = cookie
            else:
                logger.warning("未找到Cookie")
        default_params = {
            "mid": mid,
            "web_location": "444.8"
        }
        await cls._read_data()
        if not getattr(cls, "_session", None):
            cls._session = aiohttp.ClientSession(headers=cls.headers)
        if use_webid:
            if mid is None:
                raise KeyError("use_webid需要提供mid参数")
            default_params["w_webid"] = await cls._getAccessId(mid, compulsion)
        params = params or default_params
        logger.debug(f"签名参数: {params}")
        keys = await cls._getWbiKeys(compulsion)
        await cls._save_data()
        return cls._encWbi(params, *keys)

    @classmethod
    async def _getWbiKeys(cls, compulsion: bool) -> tuple[str, str]:
        """
        获取最新的 img_key 和 sub_key

        :param compulsion: 是否强制刷新
        :return: img_key, sub_key
        """
        if (int(time.time()) - (cls._temp_data.WbiKeys_update_timestamp + cls.flushed_time)) >= 0 or compulsion:
            if cls._session is None:
                raise RuntimeError("session未初始化")
            async with cls._session.get("https://api.bilibili.com/x/web-interface/nav") as response:
                response.raise_for_status()
                nav_data = await response.json()
            img_key = nav_data["data"]["wbi_img"]["img_url"].rsplit("/", 1)[1].split(".")[0]
            sub_key = nav_data["data"]["wbi_img"]["sub_url"].rsplit("/", 1)[1].split(".")[0]
            cls._temp_data.img_key = img_key
            cls._temp_data.sub_key = sub_key
            cls._temp_data.WbiKeys_update_timestamp = int(time.time())
            cls._temp_data.WbiKeys_update_count += 1
        else:
            cls._temp_data.WbiKeys_get_count += 1
        return cls._temp_data.img_key, cls._temp_data.sub_key

    @classmethod
    async def _getAccessId(cls, mid: int, compulsion: bool) -> str:
        """
        获取access_id

        :param compulsion: 是否强制刷新
        :return: access_id: str
        """
        if (int(time.time()) - (cls._temp_data.access_id_update_timestamp + cls.flushed_time)) >= 0 or compulsion:
            if cls._session is None:
                raise RuntimeError("session未初始化")
            try:
                async with cls._session.get(f"https://space.bilibili.com/{mid}/dynamic") as response:
                    response.raise_for_status()
                    match = re.search(r"<script id=\"__RENDER_DATA__\" type=\"application/json\">(.*?)</script>",
                                      await response.text(), re.S)
                    if match is None:
                        logger.warning("没有找到RENDER_DATA")
                        return ""
                    text = match.group(1)
            except AttributeError:
                logger.error("没有找到属性")
                return ""
            accessid = json.loads(urllib.parse.unquote(text))["access_id"]
            cls._temp_data.access_id = accessid
            cls._temp_data.access_id_update_timestamp = int(time.time())
            cls._temp_data.access_id_update_count += 1
        else:
            cls._temp_data.access_id_get_count += 1
        return cls._temp_data.access_id

    @classmethod
    def _getMixinKey(cls, orig: str) -> str:
        """
        对 imgKey 和 subKey 进行字符顺序打乱编码
        :param orig: img_key+sub_key
        :return: 打乱后的字符
        """
        return reduce(lambda s, i: s + orig[i], cls.mixinKeyEncTab, "")[:32]

    @classmethod
    def _encWbi(cls, params: dict, img_key: str, sub_key: str) -> dict:
        """
        为请求参数进行 wbi 签名
        :param params: 参数列表
        :param img_key: 通过分解img_url获取
        :param sub_key: 通过分解sub_url获取
        :return: params原有参数及加密后的w_rid值
        """
        mixin_key = cls._getMixinKey(img_key + sub_key)
        params["wts"] = round(time.time())  # 添加 wts 字段
        params = dict(sorted(params.items()))  # 按照 key 重排参数
        # 过滤 value 中的 "!'()*" 字符
        params = {
            k: "".join(filter(lambda x: x not in "!'()*", str(v)))
            for k, v in params.items()
        }
        query = urllib.parse.urlencode(params)  # 序列化参数
        params["w_rid"] = md5((query + mixin_key).encode()).hexdigest()  # 计算 w_rid并赋值给w_rid
        return params

    @classmethod
    async def close(cls):
        if getattr(cls, "_session", None):
            await cls._session.close()
            cls._session = None

    @classmethod
    async def _save_data(cls):
        async with aiofiles.open(WBI_TEMP_FILE, "wb") as f:
            data_bytes = msgpack.packb(cls._temp_data.model_dump())
            if isinstance(data_bytes, bytes):
                await f.write(data_bytes)
        logger.success("保存缓存数据成功")

    @classmethod
    async def _read_data(cls):
        if WBI_TEMP_FILE.exists():
            try:
                async with aiofiles.open(WBI_TEMP_FILE, "rb") as f:
                    cls._temp_data = SignedKeyData.model_validate(msgpack.unpackb(await f.read()))
                    logger.debug("缓存数据加载成功")
                    logger.debug(str({"Wbi更新次数": cls._temp_data.WbiKeys_update_count,
                                      "Wbi获取缓存次数": cls._temp_data.WbiKeys_get_count,
                                      "AccessId更新次数": cls._temp_data.access_id_update_count,
                                      "AccessId获取缓存次数": cls._temp_data.access_id_get_count}))
            except Exception as e:
                logger.opt(exception=e).error("缓存数据损坏,取消加载缓存")


class ConfigManage:
    _instance: Self | None = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self, file: str | os.PathLike[str] | None = None, **kwargs):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self.configs: dict[str, Any] = {}
        if file is None:
            env_file = os.getenv("CONFIG_FILE")
            file = env_file if env_file else Path(__file__).parent.parent / "config.toml"

        try:
            with open(file, "rb") as f:
                self.configs = tomllib.load(f)
                self.configs.update(kwargs)
            logger.success("配置文件成功加载")
        except FileNotFoundError:
            logger.error("配置文件路径未知, 不加载")
        except tomllib.TOMLDecodeError as e:
            logger.opt(exception=e).error("配置文件解码失败，不进行加载")
        except Exception as e:
            logger.opt(exception=e).error("配置文件加载失败，未知错误，不进行加载")

    def get(self, key: str, default: Any | None = None) -> Any:
        return self.configs.get(key, default)

    def update(self, new_configs: dict[str, Any]):
        self.configs.update(new_configs)
        logger.success("配置更新成功!")

    @classmethod
    def get_config[C: BaseModel](cls, config: type[C], names: list[str] | None = None) -> C:
        """从全局配置获取当前插件需要的配置项"""
        if cls._instance is None:
            cls._instance = cls()
        _config = cls.get_all_config()
        if names:
            for name in names:
                _config = _config[name]
        return TypeAdapter(config).validate_python(_config)

    @classmethod
    def get_all_config(cls) -> dict[str, Any]:
        """获取包含所有配置的字典"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance.configs


def convert_str_to_list(v: str) -> list[Any]:
    """
    将字符串类型列表安全转换成Python对象
    :param v: 字符串列表,如'[1, 2, 3]'
    :return: Python列表对象
    """
    try:
        result = ast.literal_eval(v)
        if isinstance(result, list):
            return result
    except (ValueError, SyntaxError):
        logger.error("LIVE_ROOM_ID must be a valid list, e.g., '[1, 2, 3]'")
        raise
    return []
