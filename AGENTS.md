# AGENTS.md

Bilibili 直播间机器人，通过 WebSocket 连接 B 站直播间，接收并处理弹幕、礼物、醒目留言等实时消息。

## 模块边界

### `main.py`（入口）

- 通过 `python-dotenv` 加载 `.env` 环境变量
- 使用 `@Handler.append_func(MsgType.XxxMessage)` 装饰器注册各消息类型的处理回调
- 读取 `LIVE_ROOM_ID`，经 `convert_str_to_list` 解析为房间 ID 列表，为每个房间创建 `BLiveClient` 实例
- 配置 loguru 日志输出（文件 + 控制台），运行主事件循环

### `live_streams/`（直播核心模块）

| 文件 | 职责 |
|------|------|
| `__init__.py` | `BLiveClient` — WebSocket 客户端，管理连接生命周期、认证、心跳、消息收发与解析（brotli 解压、包头解析、正文分发） |
| `handler.py` | `Handler` — 消息分发器，`_CMD_MODEL_DICT` 将 CMD 映射到消息模型，`handle()` 解析并路由消息，`append_func()` 注册回调 |
| `models.py` | Pydantic 消息模型，继承 `MessageInterface`；每个模型通过 `from_command()` 解析原始数据；`MsgType` 枚举在运行时从所有子类自动生成 |
| `config.py` | `Config` 配置模型、CMD 说明映射、API URL 常量 |
| `enum.py` | 协议枚举：`ProtoVer`、`Operation`、`AuthReplyCode` |
| `exception.py` | `AuthError` 认证异常 |

### `utils/`（工具模块）

| 文件 | 职责 |
|------|------|
| `tools.py` | `SignedParams`（WBI 签名，pickle 缓存密钥）、`ConfigManage`（单例配置管理，读取 `config.toml`）、`convert_str_to_list` / `convert_str_to_list_int`（字符串列表安全转换）、`TEMP_PATH`（临时文件路径） |
| `InteractWordV2.py` / `.pyi` | protoc 自动生成的 protobuf 代码，用于 `InteractWordV2Message` 反序列化 |

### `tests/`（独立脚本）

- `test.py` — protobuf 反序列化快速验证
- `live_rooms.py` — 独立的开播状态监控脚本（APScheduler + 邮件通知），与主程序分离

## 环境变量

| 变量 | 必需 | 说明 |
|------|------|------|
| `LIVE_ROOM_ID` | 是 | 监听的直播间 ID 列表，格式如 `[21452505]` |
| `COOKIE` | 否 | B 站 Cookie 字符串，`config.toml` 中 `use_cookie_login=true` 时使用 |
| `LOG_PATH` | 否 | 日志文件输出目录，默认当前工作目录 |

## 运行与测试命令

```bash
# 运行主程序
uv run python main.py

# 代码检查
uv run ruff check .

# 类型检查
uv run pyright
```

## 核心变更风险区域

### `live_streams/handler.py` — 消息分发

- `_CMD_MODEL_DICT` 是 CMD → 消息模型的核心路由表，修改映射会影响所有消息的分发路径
- `handle()` 方法是消息处理的唯一入口，解析 CMD 并调用注册的回调函数
- `append_func()` 装饰器用于注册回调，改动注册逻辑会影响所有下游处理函数的执行

### `live_streams/models.py` — 消息模型

- `MsgType` 枚举在运行时从 `MessageInterface` 所有子类自动生成，增删模型会直接改变枚举值和所有 `@Handler.append_func` 注册
- `from_command()` 方法解析 B 站原始 JSON 数据，字段映射错误会导致静默数据丢失
