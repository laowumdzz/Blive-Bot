import asyncio
import dataclasses
import json
import os
import pickle
import re
import threading
import time
import tomllib
import urllib.parse
from functools import reduce
from hashlib import md5
from pathlib import Path
from typing import Optional, Any, TypeVar, Union

import aiohttp
from loguru import logger
from pydantic import BaseModel, TypeAdapter

C = TypeVar("C", bound=BaseModel)
T = TypeVar("T")

path = {name: Path(os.getenv(name)) for name in {"LOG_PATH", "DATA_PATH", "TEMP_PATH", "RESOURCE_PATH"}}

LOG_PATH = path["LOG_PATH"]
"""日志路径"""
DATA_PATH = path["DATA_PATH"]
"""数据路径"""
TEMP_PATH = path["TEMP_PATH"]
"""临时文件路径"""
RESOURCE_PATH = path["RESOURCE_PATH"]
"""资源路径"""
WBI_TEMP_FILE = TEMP_PATH / "WbiSignature.pkl"

LOG_PATH.mkdir(parents=True, exist_ok=True)
DATA_PATH.mkdir(parents=True, exist_ok=True)
TEMP_PATH.mkdir(parents=True, exist_ok=True)
RESOURCE_PATH.mkdir(parents=True, exist_ok=True)


@dataclasses.dataclass
class SignedKeyData:
    img_key: str = ""
    sub_key: str = ""
    WbiKeys_update_timestamp: float = 0
    WbiKeys_update_count: int = 0
    WbiKeys_get_count: int = 0
    access_id: str = ""
    access_id_update_timestamp: float = 0
    access_id_update_count: int = 0
    access_id_get_count: int = 0


class Signedparams:
    """
    签名类, 调用get_end_result函数即可, 利用序列化库pickle缓存img_key和sub_key和access_id,避免反复获取影响性能
    """
    Data: SignedKeyData = SignedKeyData()
    flushed_time: int = 2 * 86000
    mixinKeyEncTab = [
        46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
        33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
        61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
        36, 20, 34, 44, 52
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
        "Referer": "https://www.bilibili.com/",
        "Origin": "http://www.bilibili.com",
        "Cookie": os.getenv("COOKIE")
    }
    _session: Optional[aiohttp.ClientSession] = None

    @classmethod
    async def get_end_result(
            cls,
            mid: Optional[int] = None,
            params: Optional[dict[str, Any]] = None,
            compulsion: bool = False,
            use_webid: bool = False
    ) -> dict:
        """
        获取最后的结果
        :param mid: 用户UID, params和mid必填其中之一
        :param params: 自定义参数, 不输入则使用默认自带参数
        :param compulsion: 是否强制刷新数据库缓存
        :param use_webid: 是否使用w_webid,能不用就不用,如果过不了鉴权就可以启用
        :return: 加密完成后的dict[params]
        """
        if not (mid or params):
            logger.error("No params or No mid")
            raise ValueError("params和mid必填其中之一")
        default_params = {
            "mid": mid,
            "web_location": "444.8"
        }
        cls._read_data()
        if not cls.headers.get("Cookie"):
            logger.error("No Cookie")
            raise KeyError("没有Cookie")
        if not cls._session:
            cls._session = aiohttp.ClientSession(headers=cls.headers)
        if use_webid:
            default_params["w_webid"] = await cls._access_id(mid, compulsion)
        params = params or default_params
        logger.debug(f"签名参数: {params}")
        keys = await cls._getWbiKeys(compulsion)
        await asyncio.to_thread(cls._save_data)
        return await cls._encWbi(params, *keys)

    @classmethod
    async def _getWbiKeys(cls, compulsion: bool) -> tuple[str, str]:
        """
        获取最新的 img_key 和 sub_key
        :return: img_key, sub_key
        """
        if (time.time() - (cls.Data.WbiKeys_update_timestamp + cls.flushed_time)) >= 0 or compulsion:
            async with cls._session.get('https://api.bilibili.com/x/web-interface/nav') as response:
                response.raise_for_status()
                nav_data = await response.json()
            img_key = nav_data["data"]["wbi_img"]["img_url"].rsplit("/", 1)[1].split(".")[0]
            sub_key = nav_data["data"]["wbi_img"]["sub_url"].rsplit("/", 1)[1].split(".")[0]
            cls.Data.img_key = img_key
            cls.Data.sub_key = sub_key
            cls.Data.WbiKeys_update_timestamp = time.time()
            cls.Data.WbiKeys_update_count += 1
        else:
            cls.Data.WbiKeys_get_count += 1
        return cls.Data.img_key, cls.Data.sub_key

    @classmethod
    async def _access_id(cls, mid: int, compulsion: bool) -> str:
        """
        获取access_id
        :return: access_id: str
        """
        if (time.time() - (cls.Data.WbiKeys_update_timestamp + cls.flushed_time)) >= 0 or compulsion:
            try:
                async with cls._session.get(f'https://space.bilibili.com/{mid}/dynamic') as response:
                    response.raise_for_status()
                    text = re.search(r"<script id=\"__RENDER_DATA__\" type=\"application/json\">(.*?)</script>",
                                     await response.text(), re.S).group(1)
            except AttributeError:
                logger.error("没有找到属性")
                return ""
            accessid = json.loads(urllib.parse.unquote(text))["access_id"]
            cls.Data.access_id = accessid
            cls.Data.access_id_update_timestamp = time.time()
            cls.Data.access_id_update_count += 1
        else:
            cls.Data.access_id_get_count += 1
        return cls.Data.access_id

    @classmethod
    async def _getMixinKey(cls, orig: str) -> str:
        """
        对 imgKey 和 subKey 进行字符顺序打乱编码
        :param orig: img_key+sub_key
        :return: 打乱后的字符
        """
        return reduce(lambda s, i: s + orig[i], cls.mixinKeyEncTab, "")[:32]

    @classmethod
    async def _encWbi(cls, params: dict, img_key: str, sub_key: str) -> dict:
        """
        为请求参数进行 wbi 签名
        :param params: 参数列表
        :param img_key: 通过分解img_url获取
        :param sub_key: 通过分解sub_url获取
        :return: params原有参数及加密后的w_rid值
        """
        mixin_key = await cls._getMixinKey(img_key + sub_key)
        params["wts"] = round(time.time())  # 添加 wts 字段
        params = dict(sorted(params.items()))  # 按照 key 重排参数
        # 过滤 value 中的 "!'()*" 字符
        params = {
            k: "".join(filter(lambda x: x not in "!'()*", str(v)))
            for k, v in params.items()
        }
        query = urllib.parse.urlencode(params)  # 序列化参数
        # noinspection PyTypeChecker
        params["w_rid"] = md5((query + mixin_key).encode()).hexdigest()  # 计算 w_rid并赋值给w_rid
        return params

    @classmethod
    async def close(cls):
        if cls._session:
            await cls._session.close()
            cls.session = None

    @classmethod
    def _save_data(cls):
        with open(WBI_TEMP_FILE, "wb") as f:
            # noinspection PyTypeChecker
            pickle.dump(cls.Data, f)

    @classmethod
    def _read_data(cls):
        if WBI_TEMP_FILE.exists():
            try:
                with open(WBI_TEMP_FILE, "rb") as f:
                    cls.Data = pickle.load(f)
                    logger.debug("缓存数据加载成功")
                    logger.debug(str({"WbiKeys_update_count": cls.Data.WbiKeys_update_count,
                                      "WbiKeys_get_count": cls.Data.WbiKeys_get_count,
                                      "access_id_update_count": cls.Data.access_id_update_count,
                                      "access_id_get_count": cls.Data.access_id_get_count}))
            except (pickle.PickleError, EOFError) as e:
                logger.error(f"缓存数据损坏: {e}")


class ConfigManage:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, file: Union[str, Path] = None, **kwargs):
        if self._initialized:
            return
        self._initialized = True

        if file is None:
            file = os.getenv("CONFIG_FILE") or Path(__file__).parent / "config.toml"
        file = Path(file) if isinstance(file, str) else file

        if not file.exists():
            raise FileNotFoundError("配置文件路径未知")
        try:
            with open(file, "rb") as f:
                self.configs: dict[str, Any] = tomllib.load(f)
                self.configs.update(kwargs)
            logger.success("Configfile loaded successfully!")
        except tomllib.TOMLDecodeError as e:
            logger.error(f"Failed to load config file: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while loading config file: {e}")
            raise

    def get(self, key: str, default: Any = None) -> Any:
        return self.configs.get(key, default)

    def update(self, new_configs: dict[str, Any]):
        self.configs.update(new_configs)
        logger.success("Config updated successfully!")

    def get_config(self, config: type[C], name: str = None) -> C:
        """从全局配置获取当前插件需要的配置项"""
        if name:
            return TypeAdapter(config).validate_python(self.configs[name])
        return TypeAdapter(config).validate_python(self.configs)

    def get_all_config(self) -> dict[str, Any]:
        """获取包含所有配置的字典"""
        return self.configs
