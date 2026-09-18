# Blive-Bot

BiliBili 直播间机器人 —— 通过 WebSocket 直连 B 站直播间，实时接收并处理弹幕、礼物、醒目留言等消息。直播协议客户端完全自研，不依赖第三方直播库。

## ✨ 特性

- **自研协议客户端**：连接生命周期、认证、心跳、消息收发与解析（brotli 解压、包头解析、正文分发）全部自己实现
- **装饰器式消息处理**：`@Handler.append_func(MsgType.DanmakuMessage)` 一行注册回调，新增消息处理零侵入
- **丰富的消息类型**：弹幕、礼物、点赞、SuperChat、观看人数、进场消息（InteractWordV2，protobuf 反序列化）等
- **多房间并发**：为每个房间创建独立的 `BLiveClient`，asyncio 事件循环统一调度
- **WBI 签名**：自动获取并缓存 WBI 密钥
- **全异步架构**：Python 3.12+ / pydantic v2 / loguru / APScheduler

## 📦 支持的消息类型

| MsgType | 说明 |
| --- | --- |
| `DanmakuMessage` | 弹幕 |
| `GiftMessage` | 礼物 |
| `LikeUpdateMessage` / `LikeClickMessage` | 点赞 |
| `WatchedChangeMessage` | 观看人数 |
| `SuperChatMessage` | 醒目留言（SuperChat） |
| `LoginNoticeMessage` | 登录 / 日志通知 |
| `InteractWordV2Message` | 进场 / 关注等互动消息（protobuf） |

## 🚀 快速开始

环境要求：Python 3.12+、[uv](https://docs.astral.sh/uv/)

```bash
git clone https://github.com/laowumdzz/Blive-Bot.git
cd Blive-Bot
uv sync
```

在项目根目录创建 `.env`：

```dotenv
LIVE_ROOM_ID=[21452505]   # 必填，监听的直播间 ID 列表
COOKIE=...                # 可选，config.toml 中 use_cookie_login=true 时使用
LOG_PATH=logs             # 可选，日志目录，默认当前工作目录
```

运行：

```bash
uv run python main.py
```

## 🧱 项目结构

```
main.py                 入口：加载配置、注册回调、启动事件循环
live_streams/           直播核心
├── __init__.py         BLiveClient：WebSocket 客户端（连接/认证/心跳/解析）
├── handler.py          Handler：消息分发器（CMD → 模型 → 回调）
├── models.py           Pydantic 消息模型（MsgType 运行时自动生成）
├── config.py           配置模型、CMD 说明、API 常量
├── enum.py             协议枚举（ProtoVer / Operation / AuthReplyCode）
└── exception.py        AuthError 认证异常
utils/                  工具
├── tools.py            WBI 签名、配置管理、字符串转换
└── InteractWordV2.py   protoc 生成的 protobuf 代码
tests/                  测试与独立脚本
```

## 🧪 开发

```bash
uv run ruff check .      # 代码检查
uv run pyrefly check     # 类型检查
uv run pytest tests/     # 单元测试
```

## 📄 License

[AGPL-3.0](LICENSE)
