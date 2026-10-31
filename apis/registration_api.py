# apis/registration_api.py
"""挂号相关接口。"""

from __future__ import annotations

from typing import Any

from apis.base_api import BaseApi

# ==========================================================================
# 挂号单默认报文模板
# TODO ↓↓↓ 以下字段名与取值均来自 Postman 抓包，请对照真实接口文档确认 ↓↓↓
#      尤其注意：
#      - invoiceNo（发票号）若要求唯一，重复执行会冲突，建议改成动态生成
#      - attendanceDate / dateOfBirth 的格式是否为 yyyy-MM-dd
#      - settlementCatId / operatorId 的合法取值范围
# ==========================================================================
DEFAULT_PAYLOAD: dict[str, Any] = {
    "name": "mc",
    "identificationNo": "sm",
    "dateOfBirth": "2026-10-01",
    "gender": 0,
    "phoneNo": "",
    "homeAddress": "",
    "attendanceDate": "2019-07-07",
    "deptId": None,          # 由 default_payload 注入
    "skdId": None,
    "needBook": 0,
    "settlementCatId": 1,
    "amount": 15,
    "invoiceNo": 50637283,
    "operatorId": 1,
}


class RegistrationApi(BaseApi):
    prefix = "/registration"

    # ------------------------------------------------------------------ 创建
    def create(self, payload: dict, headers: dict | None = None, **kwargs):
        """
        创建挂号单。

        TODO: 若真实路径不是 /registration/createRegistration，改这里的字符串。
        """
        return self.http.send(
            "POST", self.url("createRegistration"), json=payload, headers=headers, **kwargs
        )

    def default_payload(self, dept_id: int | None = None, **overrides) -> dict:
        """
        生成一份默认报文，可用关键字参数覆盖任意字段：

            reg_api.default_payload(dept_id, name="张三", amount=30)
        """
        payload = dict(DEFAULT_PAYLOAD)
        if dept_id is not None:
            payload["deptId"] = dept_id
        payload.update(overrides)
        return payload

    # ------------------------------------------------------------------ 查询
    def get_by_id(self, reg_id, headers: dict | None = None, **kwargs):
        """
        根据 id 查询挂号单（若后续需要做「创建后校验」的用例）。

        TODO: 确认查询接口路径与参数名，不需要可删除本方法。
        """
        return self.http.send(
            "GET", self.url("selectById"), params={"id": reg_id}, headers=headers, **kwargs
        )