# services/registration_service.py
"""
挂号业务层：把「登录 → 查科室 → 创建挂号单」这组接口组合成业务动作。

为什么需要 services 层？
------------------------
* 用例只关心「做什么业务」，不关心「调哪个接口、参数怎么拼」
* 接口路径变了只改 apis/，业务规则变了只改 services/，用例基本不动
"""

from __future__ import annotations

from apis.dept_api import DeptApi
from apis.registration_api import RegistrationApi
from apis.staff_api import StaffApi


class RegistrationService:
    def __init__(self, staff_api: StaffApi, dept_api: DeptApi, registration_api: RegistrationApi):
        self.staff_api = staff_api
        self.dept_api = dept_api
        self.registration_api = registration_api

    def login(self, username: str, password: str) -> str:
        """登录并返回 token。"""
        return self.staff_api.login_and_get_token(username, password)

    def find_dept_id(self, dept_name: str, headers: dict) -> int:
        """按名称取科室 id。"""
        return self.dept_api.get_dept_id_by_name(dept_name, headers=headers)

    def create_registration(self, dept_id: int, headers: dict, **overrides) -> dict:
        """
        创建挂号单并返回响应 JSON。

        :param dept_id:   科室 id
        :param headers:   鉴权头
        :param overrides: 覆盖默认报文的任意字段
        """
        payload = self.registration_api.default_payload(dept_id, **overrides)
        return self.registration_api.create(payload, headers=headers).json()

    # ---------------------------------------------------------------- 组合动作
    def create_for_dept_name(self, dept_name: str, headers: dict, **overrides) -> dict:
        """
        一步完成「按科室名称找 id → 创建挂号单」，适合只关心结果的用例。
        """
        dept_id = self.find_dept_id(dept_name, headers)
        return self.create_registration(dept_id, headers, **overrides)