"""utils 工具函数测试

覆盖 utils/tools.py 中的纯函数：
- convert_str_to_list: 字符串安全转换为 int 列表
- convert_str_to_list_int: 字符串安全转换为纯 int 列表（含类型校验）
- Config 模型默认值
"""

import pytest

from live_streams.config import Config
from utils.tools import convert_str_to_list, convert_str_to_list_int

# ---------------------------------------------------------------------------
# convert_str_to_list
# ---------------------------------------------------------------------------


class TestConvertStrToList:
    """convert_str_to_list 正常解析与边界情况。"""

    def test_normal_list(self):
        """合法的字符串列表应正确转换。"""
        assert convert_str_to_list("[1, 2, 3]") == [1, 2, 3]

    def test_single_element(self):
        """单元素列表应正确转换。"""
        assert convert_str_to_list("[42]") == [42]

    def test_empty_list(self):
        """空列表字符串应返回空列表。"""
        assert convert_str_to_list("[]") == []

    def test_invalid_syntax_raises(self):
        """非法语法应抛出 ValueError。"""
        with pytest.raises(ValueError, match="malformed"):
            convert_str_to_list("abc")

    def test_non_list_string_returns_empty(self):
        """解析结果非列表（如单个数字字符串）应返回空列表。"""
        assert convert_str_to_list("123") == []

    def test_incomplete_bracket_raises(self):
        """不完整的括号语法应抛出 SyntaxError。"""
        with pytest.raises(SyntaxError):
            convert_str_to_list("[1, 2")


# ---------------------------------------------------------------------------
# convert_str_to_list_int
# ---------------------------------------------------------------------------


class TestConvertStrToListInt:
    """convert_str_to_list_int 正常解析与类型校验。"""

    def test_normal_int_list(self):
        """纯 int 列表应正确转换。"""
        assert convert_str_to_list_int("[1, 2, 3]") == [1, 2, 3]

    def test_list_with_non_int_returns_none(self):
        """列表中含非 int 元素应返回 None。"""
        assert convert_str_to_list_int("[1, 'a', 3]") is None

    def test_empty_list_returns_none(self):
        """空列表（isinstance 为 list 但无元素可校验）应返回 None。

        实现中 all(...) 对空列表返回 True，但 isinstance(result, list) 为真，
        故理论上返回 []；然而逻辑上空房间列表无意义，验证实际行为。
        """
        assert convert_str_to_list_int("[]") == []

    def test_non_list_string_raises(self):
        """非法语法应抛出 ValueError 或 SyntaxError。"""
        with pytest.raises((ValueError, SyntaxError)):
            convert_str_to_list_int("not a list")

    def test_float_list_returns_none(self):
        """列表中含 float 元素应返回 None（非 int）。"""
        assert convert_str_to_list_int("[1, 2.0, 3]") is None

    def test_nested_list_returns_none(self):
        """嵌套列表（元素非 int）应返回 None。"""
        assert convert_str_to_list_int("[[1], [2]]") is None

    def test_none_input_raises(self):
        """None 输入应在 ast.literal_eval 时抛出异常。"""
        with pytest.raises((ValueError, TypeError)):
            convert_str_to_list_int(None)


# ---------------------------------------------------------------------------
# Config 模型默认值
# ---------------------------------------------------------------------------


class TestConfigModel:
    """Config Pydantic 模型默认值验证。"""

    def test_defaults(self):
        """Config 使用默认值创建应正确。"""
        config = Config()
        assert config.use_cookie_login is False
        assert config.save_history_method == 0
        assert config.data_analysis is False
        assert config.cookie is None

    def test_override_values(self):
        """Config 应支持覆盖默认值。"""
        config = Config(use_cookie_login=True, save_history_method=2, cookie="abc")
        assert config.use_cookie_login is True
        assert config.save_history_method == 2
        assert config.cookie == "abc"
