# common/data_loader.py
"""
测试数据加载。所有数据文件统一放在 data/ 目录下。

支持 CSV / JSON / YAML，返回 list[dict] 或 dict，可直接喂给
@pytest.mark.parametrize，也是做数据驱动最常用的入口。
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

# 项目根目录下的 data/
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _resolve(filename: str | Path) -> Path:
    path = Path(filename)
    return path if path.is_absolute() else DATA_DIR / path


def load_csv(filename: str | Path, *, encoding: str = "utf-8-sig") -> list[dict]:
    """
    读取 CSV，返回 list[dict]（第一行为表头）。

    utf-8-sig 兼容 Excel 保存时带 BOM 的情况。

        cases = load_csv("booking_data.csv")
        @pytest.mark.parametrize("case", cases, ids=lambda c: c["case_name"])
    """
    path = _resolve(filename)
    if not path.exists():
        raise FileNotFoundError(f"数据文件不存在: {path}")

    with path.open("r", encoding=encoding, newline="") as f:
        return list(csv.DictReader(f))


def load_json(filename: str | Path, *, encoding: str = "utf-8") -> Any:
    path = _resolve(filename)
    if not path.exists():
        raise FileNotFoundError(f"数据文件不存在: {path}")
    with path.open("r", encoding=encoding) as f:
        return json.load(f)


def load_yaml(filename: str | Path, *, encoding: str = "utf-8") -> Any:
    """
    读取 YAML。需要安装 PyYAML（已写入 requirements.txt）。
    """
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise ImportError("读取 YAML 需要安装 PyYAML: pip install PyYAML") from exc

    path = _resolve(filename)
    if not path.exists():
        raise FileNotFoundError(f"数据文件不存在: {path}")
    with path.open("r", encoding=encoding) as f:
        return yaml.safe_load(f)


def case_ids(cases: list[dict], key: str = "case_name") -> list[str]:
    """为 parameterize 生成可读的用例 id。"""
    ids = []
    for index, case in enumerate(cases, start=1):
        ids.append(str(case.get(key) or f"case_{index}"))
    return ids