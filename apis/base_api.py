# apis/base_api.py
"""接口基类：统一持有 HttpRequest 与接口前缀。"""

from __future__ import annotations

from common.exceptions import ApiError
from common.http_request import HttpRequest


class BaseApi:
    """
    所有接口类的父类。

    子类只需覆盖 `prefix`，方法里用 `self.url("xxx")` 得到相对路径。

        class StaffApi(BaseApi):
            prefix = "/staff"
    """

    # 接口路径前缀，子类覆盖
    prefix: str = ""

    def __init__(self, http: HttpRequest):
        self.http = http

    def url(self, path: str = "") -> str:
        """拼出带前缀的相对路径。"""
        if not path:
            return self.prefix
        return f"{self.prefix.rstrip('/')}/{path.lstrip('/')}"

    # ------------------------------------------------------------ 响应校验
    @staticmethod
    def ensure_http_ok(resp, expected: int = 200, message: str = "") -> None:
        """内部快速校验 HTTP 状态码，失败抛 ApiError。"""
        if resp.status_code != expected:
            raise ApiError(
                message or "HTTP 状态码不符合预期",
                status_code=resp.status_code,
                body=resp.text[:1000],
            )

    @staticmethod
    def ensure_business_ok(body: dict, expected: int = 200, message: str = "") -> dict:
        """内部快速校验业务 code，失败抛 ApiError。"""
        if not isinstance(body, dict):
            raise ApiError(message or "响应不是 JSON 对象", body=body)
        if body.get("code") != expected:
            raise ApiError(message or "业务 code 不符合预期", body=body)
        return body