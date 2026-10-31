# run.py
"""
程序化执行入口。

适合：
* 在 CI（Jenkins / GitHub Actions）里用 `python run.py --env=test -m smoke` 调用
* 想在 python 调试器里单步跟踪 pytest 内部流程时

直接命令行 pytest 也是完全可以的，本文件只是把常用参数封装了一层。
"""

from __future__ import annotations

import argparse
import sys

import pytest

# Windows 控制台默认 GBK，中文提示会乱码，统一改成 UTF-8
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover
        pass


def build_args(argv: argparse.Namespace) -> list[str]:
    args = ["testcases", f"--env={argv.env}"]

    if argv.marker:
        args += ["-m", argv.marker]
    if argv.keyword:
        args += ["-k", argv.keyword]
    if argv.workers:
        args += ["-n", str(argv.workers)]
    if argv.reruns:
        args += ["--reruns", str(argv.reruns)]
    if argv.maxfail:
        args += ["--maxfail", str(argv.maxfail)]
    if argv.extend:
        args += argv.extend
    return args


def main() -> int:
    parser = argparse.ArgumentParser(description="hospital_api_test 执行入口")
    parser.add_argument("--env", default="dev", choices=["dev", "test", "prod"], help="运行环境")
    parser.add_argument("-m", "--marker", help="按 marker 过滤，如 smoke / negative")
    parser.add_argument("-k", "--keyword", help="按用例名关键字过滤")
    parser.add_argument("-n", "--workers", help="并行进程数，如 auto / 4（需 pytest-xdist）")
    parser.add_argument("--reruns", type=int, help="失败重跑次数（需 pytest-rerunfailures）")
    parser.add_argument("--maxfail", type=int, help="失败 N 条后停止")
    parser.add_argument("--extend", nargs=argparse.REMAINDER, help="透传给 pytest 的其余参数")
    argv = parser.parse_args()

    args = build_args(argv)
    print(f"[run.py] pytest {' '.join(args)}")
    return pytest.main(args)


if __name__ == "__main__":
    sys.exit(main())