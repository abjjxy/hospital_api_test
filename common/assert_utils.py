# common/assert_utils.py
"""
断言封装。

为什么不用裸 assert？
---------------------
裸 assert 失败时 pytest 只能告诉你 "assert 500 == 200"，
而这些封装会把「请求方法、URL、实际响应体」一起打进失败信息，
排查问题时不用再去翻日志。

约定：断言失败统一抛 AssertionError，用例中可用 pytest.raises 捕获。
"""

from __future__ import annotations

from typing import Any


def assert_status(resp, expected: int = 200, message: str = "") -> None:
    """断言 HTTP 状态码。"""
    actual = getattr(resp, "status_code", None)
    assert actual == expected, (
        f"{message or 'HTTP 状态码不符'} | 期望={expected} 实际={actual} "
        f"| url={getattr(resp, 'url', '?')} | 响应={_text(resp)}"
    )


def assert_business_code(body: Any, expected: int = 200, message: str = "") -> Any:
    """
    断言业务返回码（本项目约定 code=200 为成功）。

    :return: 原样返回 body，方便链式调用
    """
    assert isinstance(body, dict), f"{message or '响应不是 JSON 对象'} | 实际={body!r}"
    actual = body.get("code")
    assert actual == expected, (
        f"{message or '业务 code 不符'} | 期望={expected} 实际={actual} | 完整响应={body}"
    )
    return body


def assert_fields(body: dict, expected: dict, message: str = "") -> None:
    """
    断言响应体中指定字段的值。

        assert_fields(data, {"deptId": 1, "needBook": 0})
    """
    for key, value in expected.items():
        actual = body.get(key)
        assert actual == value, f"{message or '字段值不符'} | 字段={key} 期望={value!r} 实际={actual!r}"


def assert_not_empty(value: Any, field_name: str = "字段") -> Any:
    """断言字段非空（None / "" / [] / {} 都算空）。"""
    assert value not in (None, "", [], {}), f"{field_name} 不能为空，实际={value!r}"
    return value


def assert_in(item: Any, container: Any, field_name: str = "值") -> Any:
    """断言 item 在 container 中，用于枚举类字段。"""
    assert item in container, f"{field_name}={item!r} 不在允许范围 {container!r}"
    return item


def _text(resp, limit: int = 1000) -> str:
    try:
        text = resp.text
    except Exception:  # noqa: BLE001 - 响应对象可能不完整
        return repr(resp)
    return text if len(text) <= limit else f"{text[:limit]}..."