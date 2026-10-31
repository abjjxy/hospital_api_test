# apis/staff_api.py
"""员工（员工端登录）相关接口。"""

from __future__ import annotations

from apis.base_api import BaseApi
from common.exceptions import ApiError


class StaffApi(BaseApi):
    prefix = "/staff"

    # ------------------------------------------------------------------ 登录
    def login(self, username: str, password: str, **kwargs):
        """
        管理员/员工登录。

        TODO: 若真实登录接口路径不是 /staff/login，改这里的 "login"。
        """
        return self.http.send(
            "POST",
            self.url("login"),
            json={"username": username, "password": password},
            **kwargs,
        )

    def login_and_get_token(self, username: str, password: str) -> str:
        """
        登录并直接返回 token（供 session 级 fixture 使用）。
        登录失败直接抛 ApiError，避免后续用例拿到空 token 才报错。

        TODO: 确认 token 在响应里的真实位置。
              目前按 {"code":200,"data":{"token":"xxx"}} 处理。
              如果是 data.accessToken / data.access_token，改下面的取值。
        """
        body = self.http.send_json(
            "POST",
            self.url("login"),
            json={"username": username, "password": password},
        )
        self.ensure_business_ok(body, message="登录失败")

        data = body.get("data") or {}
        token = data.get("token")          # TODO 字段名以真实响应为准
        if not token:
            raise ApiError("登录成功但未取到 token，请检查响应结构", body=body)
        return token

    # ------------------------------------------------------------------ 登出
    def logout(self, headers: dict | None = None):
        """
        登出（session 级 fixture 的 teardown 可选调用）。

        TODO: 确认登出接口路径，如不需要可在 conftest 里注释掉。
        """
        return self.http.send("POST", self.url("logout"), headers=headers)