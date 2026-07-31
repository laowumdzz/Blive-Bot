---
kind: build_system
name: Python 构建与依赖管理（uv + pyproject.toml）
category: build_system
scope:
    - '**'
source_files:
    - pyproject.toml
    - uv.lock
    - .python-version
---

本项目采用基于 **uv** 的现代 Python 包管理与构建系统，所有构建、依赖解析、虚拟环境及代码质量工具均通过 `pyproject.toml` 统一声明，无传统 Makefile 或 Dockerfile。

### 1. 使用的系统与工具
- **包管理器与构建后端**：`uv`（由 `uv.lock` 和 `pyproject.toml` 中的 `[tool.uv.index]` 确认），用于依赖安装、锁定与虚拟环境管理。
- **Python 版本约束**：`.python-version` 固定为 `3.12`，`pyproject.toml` 中 `requires-python = ">=3.12"` 共同保证运行时一致性。
- **代码质量工具**：`ruff`（lint + format）、`pyright`（类型检查），均在 `pyproject.toml` 的 `[tool.ruff]` 与 `[tool.pyright]` 中集中配置。
- **开发依赖分组**：通过 `dependency-groups.dev` 声明 `pyright` 与 `ruff`，与生产依赖隔离。

### 2. 核心文件与职责
- `pyproject.toml`：项目元数据（name=`blive-bot`、version=`0.1.0`）、运行时依赖、dev 依赖、Ruff/Pyright 配置、自定义 PyPI 源（清华镜像）。
- `uv.lock`：精确锁定的依赖树，包含每个包的 hash、wheel 列表与来源，确保可重现构建。
- `.python-version`：强制指定 Python 3.12。

### 3. 架构与约定
- **单一配置文件驱动**：所有构建相关设置集中在 `pyproject.toml`，遵循 PEP 621 标准格式。
- **平台条件依赖**：`uvloop>=0.22.1 ; sys_platform == 'linux'` 仅在 Linux 平台安装，体现对运行环境的精细控制。
- **私有索引源**：通过 `[[tool.uv.index]]` 将默认源指向 `https://pypi.tuna.tsinghua.edu.cn/simple`，加速国内依赖下载。
- **虚拟环境路径约定**：`pyright` 配置中 `venvPath = "."`、`venv = ".venv"`，表明使用项目根目录下 `.venv` 作为虚拟环境。

### 4. 约定与约束
- **Python 版本下限**：必须使用 Python ≥3.12（由 `requires-python` 与 `.python-version` 双重约束）。
- **依赖锁定**：所有依赖版本由 `uv.lock` 锁定，禁止未锁定依赖进入生产环境。
- **代码风格强制**：Ruff 启用 F/W/E/I/UP/ASYNC/C4/T10/T20/PYI/PT/Q/TID/RUF 等规则集，行宽限制 120，换行符强制 LF。
- **类型检查模式**：Pyright 以 `standard` 模式运行，针对 `./tests` 和 `./` 两个 root 分别配置执行环境。
- **包发布元数据**：`[package.metadata]` 显式列出 `requires-dist`，与 `dependencies` 保持一致，便于生成标准 metadata。
- **无容器化/CI 脚本**：仓库中未发现 Dockerfile、Makefile、GitHub Actions 等 CI/CD 配置，构建流程完全依赖 uv 命令行工具。