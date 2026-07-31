---
kind: logging_system
name: 基于 Loguru 的日志系统
category: logging_system
scope:
    - '**'
source_files:
    - main.py
    - live_streams/__init__.py
    - utils/tools.py
    - tests/live_rooms.py
---

本项目使用 **loguru** 作为统一的日志框架，所有模块通过 `from loguru import logger` 直接导入全局 logger 实例进行记录。

### 日志初始化与输出配置
- 程序入口 `main.py` 在启动时统一配置日志：
  - 先调用 `logger.remove()` 清空默认 sink；
  - 添加文件 sink：输出到 `{脚本名}.log`，级别为 `DEBUG`，启用 `enqueue=True` 异步写入，并按天 `rotation="00:00"` 轮转；
  - 添加标准输出 sink：输出到 `sys.stdout`，级别为 `INFO`，同样启用 `enqueue=True`。
- 日志路径可通过环境变量 `LOG_PATH` 覆盖，默认写入当前工作目录。

### 日志级别使用规范
- `debug`：用于调试细节（如心跳包发送、认证流程、签名参数等）；
- `info`：关键业务流程节点（开启监听、认证成功、配置加载成功等）；
- `warning`：可恢复异常或边界情况（Cookie 缺失、请求频率限制、超时等）；
- `error`：严重错误（房间未找到、认证失败、配置文件损坏、解析异常等）；
- `success`：操作成功提示（消息发送成功、配置更新成功等）。

### 结构化字段约定
- 所有日志均包含 `[room_id]` 前缀标识直播间上下文；
- 异常通过 `logger.opt(exception=e).error(...)` 附加完整堆栈信息；
- 网络请求、认证、心跳等关键路径均有对应级别的日志埋点。

### 依赖与约束
- 仅依赖第三方库 `loguru`，无自定义日志封装类；
- 所有模块共享同一个全局 logger 实例，无需显式传递；
- 测试模块也遵循相同的日志使用方式。