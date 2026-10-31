# config/settings.py
"""
项目配置中心（多环境）。

设计说明
--------
1. 环境由命令行 `--env=dev|test|prod` 指定，默认 dev。
   `--env` 在根目录 conftest.py 的 pytest_configure 中被写入环境变量 HOSPITAL_ENV，
   所以用例收集阶段就已经能读到正确的环境配置。

2. 新代码统一使用 `get_settings()`（带缓存）或 conftest 里的 `env_config` fixture，
   不要在 conftest.py 顶层 import 本模块的常量 —— conftest 早于 pytest_configure 加载，
   会把配置锁死在默认环境。

3. 文件末尾的 BASE_URL / ADMIN_USER ... 常量是为了兼容旧写法而保留的，
   重构完成后可以删除。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict

# dataclass 是 Python 3.7+ 引入的标准库装饰器，帮你自动生成 __init__、__repr__、__eq__ 等方法。
@dataclass(frozen=True)
class EnvConfig:
    """单个环境的全部配置。"""

    name: str
    base_url: str

    # ---- 账号 ----
    admin_user: str
    admin_pwd: str

    # ---- 业务常量 ----
    target_dept_name: str

    # ---- HTTP 行为 ----
    timeout: int = 10          # 单次请求超时（秒）
    retry: int = 2             # 幂等请求失败重试次数

    # ---- 预留扩展位：需要新增的配置项直接往这里塞 ----
    extra: Dict[str, str] = field(default_factory=dict)


# ==========================================================================
# 环境配置表
# TODO ↓↓↓ test / prod 两个环境的地址、账号、科室名称尚为占位符，按需替换 ↓↓↓
# ==========================================================================
_ENVS: Dict[str, EnvConfig] = {
    "dev": EnvConfig(
        name="dev",
        base_url="http://101.43.51.98:10099",     # 对应 Postman 环境 hospital-dev
        admin_user="admin",
        admin_pwd="admin123456",
        target_dept_name="测试QA",
    ),
    "test": EnvConfig(
        name="test",
        base_url="http://127.0.0.1:8080",         # TODO 测试环境地址
        admin_user="admin",
        admin_pwd="admin123456",                  # TODO 测试环境密码
        target_dept_name="测试QA",                 # TODO 测试环境科室名称
    ),
    "prod": EnvConfig(
        name="prod",
        base_url="https://TODO-prod.example.com", # TODO 生产环境地址
        admin_user="TODO_PROD_USER",              # TODO 生产账号
        admin_pwd="TODO_PROD_PWD",                # TODO 生产密码
        target_dept_name="TODO_PROD_DEPT",        # TODO 生产科室
    ),
}

# 未指定 --env 时使用的默认环境
DEFAULT_ENV = "dev"

# --env 允许的取值
AVAILABLE_ENVS = tuple(_ENVS.keys())


def current_env() -> str:
    """返回当前生效的环境名（由根 conftest.py 写入环境变量）。"""
    return os.environ.get("HOSPITAL_ENV", DEFAULT_ENV).lower()


@lru_cache(maxsize=None)
def get_settings(env: str | None = None) -> EnvConfig:
    """获取指定环境的配置，默认取当前环境。结果会被缓存。"""
    name = (env or current_env()).lower()
    if name not in _ENVS:
        raise ValueError(f"未知环境: {name}，可选值: {AVAILABLE_ENVS}")
    return _ENVS[name]


# ==========================================================================
# 兼容旧代码：重构时可以先保留，全部迁移到 fixture 后删除下面四行。
# 注意：这些常量在 import 时立即求值，只有在 pytest_configure 之后被导入才是对的。
# ==========================================================================
BASE_URL = get_settings().base_url
ADMIN_USER = get_settings().admin_user
ADMIN_PWD = get_settings().admin_pwd
TARGET_DEPT_NAME = get_settings().target_dept_name