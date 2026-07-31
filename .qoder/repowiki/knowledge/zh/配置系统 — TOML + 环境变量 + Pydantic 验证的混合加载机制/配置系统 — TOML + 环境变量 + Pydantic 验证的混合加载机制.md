---
kind: configuration_system
name: 配置系统 — TOML + 环境变量 + Pydantic 验证的混合加载机制
category: configuration_system
scope:
    - '**'
source_files:
    - config.toml
    - main.py
    - utils/tools.py
    - live_streams/config.py
    - pyproject.toml
---

## 1. 使用的系统与框架
- **TOML 配置文件**：使用 Python 标准库 `tomllib`（Python 3.11+）解析 `config.toml`。
- **环境变量**：通过 `python-dotenv` 的 `load_dotenv()` 加载 `.env`，并通过 `os.getenv()` 读取运行时变量。
- **Pydantic v2**：用于对配置进行类型校验与结构化（`BaseModel`、`TypeAdapter`）。
- **自定义单例 ConfigManage**：在 `utils/tools.py` 中实现全局配置管理器，支持按路径/环境变量加载 TOML 并合并传入的 kwargs。

## 2. 核心文件与位置
- `config.toml`：项目根级 TOML 配置入口，当前仅包含 `live_room_id = []`。
- `main.py`：应用启动入口，负责加载 `.env`、读取 `LIVE_ROOM_ID` 环境变量、初始化日志路径 `LOG_PATH`，并并行启动多个 `BLiveClient`。
- `utils/tools.py`：集中实现 `ConfigManage` 单例类、WBI 签名缓存、字符串列表安全转换等工具函数。
- `live_streams/config.py`：定义 `Config` Pydantic 模型（cookie、保存方式、数据分析开关等），作为插件级配置结构。
- `pyproject.toml`：声明依赖（`python-dotenv`、`loguru`、`pydantic`、`tomllib` 等）及开发工具链。

## 3. 架构与设计决策
- **分层加载顺序**：
  1. `main.py` 调用 `load_dotenv()` 加载 `.env`。
  2. 从 `os.getenv("LIVE_ROOM_ID")` 获取房间号列表，若未设置直接抛出 `KeyError`。
  3. `ConfigManage` 默认从 `CONFIG_FILE` 环境变量指定的路径或 `config.toml` 加载 TOML，再与构造时传入的 `kwargs` 合并。
  4. 插件可通过 `ConfigManage.get_config(Config, names)` 获取经过 Pydantic 校验的配置片段。
- **单例模式**：`ConfigManage` 使用 `__new__` 保证全局唯一实例，避免重复解析配置文件。
- **类型安全**：所有配置值通过 `TypeAdapter(config).validate_python(...)` 进行 Pydantic 校验，确保字段类型正确。
- **错误处理**：配置文件不存在、TOML 解析失败或意外异常均记录日志并抛出对应异常，便于快速定位问题。
- **扩展性**：通过 `names` 参数支持嵌套配置读取，方便多插件共享同一份 TOML。

## 4. 约定与约束
- **环境变量命名约定**：
  - `LIVE_ROOM_ID`：必填，格式为 Python 列表字符串如 `"[1, 2, 3]"`，由 `convert_str_to_list` 安全解析。
  - `CONFIG_FILE`：可选，指定 TOML 配置文件路径；未设置则回退到 `config.toml`。
  - `COOKIE`：可选，用于 WBI 签名时的 Cookie 注入。
  - `LOG_PATH`：可选，指定日志输出目录；未设置时使用当前工作目录。
- **TOML 配置结构**：目前仅支持顶层键 `live_room_id`，未来可通过 `ConfigManage.get_config` 扩展嵌套结构。
- **配置更新**：支持通过 `ConfigManage.update(new_configs)` 动态合并新配置，但不会写回磁盘。
- **严格校验**：`LIVE_ROOM_ID` 必须为合法 Python 列表，否则抛出异常阻止启动。
- **日志配置**：通过 `loguru` 在启动时移除默认处理器并添加文件与 stdout 两个输出源，级别分别为 DEBUG 和 INFO。

## 5. 与其他模块的交互
- `main.py` 通过 `Handler.append_func` 装饰器注册弹幕消息回调，这些回调依赖 `models` 中的 Pydantic 模型。
- `live_streams/config.Config` 被 `ConfigManage.get_config` 用于校验插件配置，确保 cookie、保存策略等字段类型正确。
- `utils.tools.convert_str_to_list` 被 `main.py` 用于将环境变量中的字符串列表转换为 Python 列表，供房间 ID 解析使用。