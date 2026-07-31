---
kind: dependency_management
name: Python 依赖管理（uv + pyproject.toml）
category: dependency_management
scope:
    - '**'
source_files:
    - pyproject.toml
    - uv.lock
    - .python-version
---

本项目使用 Python 生态中的 **uv** 作为包管理器与依赖解析器，配合标准的 **PEP 621** 风格的 `pyproject.toml` 声明依赖，并通过 `uv.lock` 锁定精确版本以确保可重复构建。

**核心系统与工具链**
- 包管理器：`uv`（通过 `pyproject.toml` 中的 `[tool.uv]` 配置索引源）
- 依赖声明：`pyproject.toml` 的 `[project.dependencies]` 字段
- 锁定文件：`uv.lock`，记录每个包的完整哈希、wheel/sdist 来源及平台标记
- Python 版本约束：`.python-version` 固定为 `3.12`，`pyproject.toml` 中 `requires-python = ">=3.12"`

**依赖分类与结构**
- 运行时依赖：`pydantic`、`protobuf`、`apscheduler`、`aiofiles`、`aiohttp`、`python-dotenv`、`loguru`、`cryptography`、`brotli`、`websockets`，以及条件依赖 `uvloop>=0.22.1 ; sys_platform == 'linux'`
- 开发依赖：通过 `[dependency-groups] dev` 声明 `pyright` 和 `ruff`
- 私有/自定义索引：通过 `[[tool.uv.index]]` 将默认索引指向清华 PyPI 镜像 `https://pypi.tuna.tsinghua.edu.cn/simple`

**架构与约定**
- 所有第三方依赖以 `>=X.Y.Z` 的最小版本形式声明在 `pyproject.toml` 中，具体解析后的版本由 `uv.lock` 固化
- 平台相关依赖通过 PEP 508 环境标记（如 `sys_platform == 'linux'`）进行条件安装
- 项目自身作为虚拟包 `blive-bot` 出现在 `uv.lock` 中，source 标记为 `virtual = "."`，表示本地开发模式
- 无 vendoring 策略，依赖全部从远程索引下载；无 `requirements.txt`、`setup.py`、`poetry.lock` 等其他格式并存
- 类型检查与 lint 工具（pyright、ruff）的配置也集中在 `pyproject.toml` 中，与依赖声明统一管理