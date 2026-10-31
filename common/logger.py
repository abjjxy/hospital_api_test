# common/logger.py
"""
统一日志入口。

- 控制台 + 文件双输出
- 文件统一落在 reports/logs/test.log
- 全局只初始化一次（重复 import 不会重复挂 handler）
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# 项目根目录（common/ 的上一级）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "reports" / "logs"
LOG_FILE = LOG_DIR / "test.log"

_LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)-20s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def _configure() -> None:
    global _configured
    if _configured:
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Windows 控制台默认 GBK，中文日志会乱码，这里统一改成 UTF-8
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover - 非标准输出流时忽略
        pass

    root = logging.getLogger("hospital")
    root.setLevel(logging.DEBUG)
    root.propagate = False  # 不再交给 pytest / 第三方重复输出

    console = logging.StreamHandler(stream=sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
    root.addHandler(console)

    file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
    root.addHandler(file_handler)

    _configured = True


def get_logger(name: str = "hospital") -> logging.Logger:
    """
    获取 logger。

    :param name: 子模块名，例如 "http" / "case"，最终名字为 hospital.http
    """
    _configure()
    full_name = name if name.startswith("hospital") else f"hospital.{name}"
    return logging.getLogger(full_name)