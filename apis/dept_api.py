# apis/dept_api.py
"""科室相关接口。"""

from __future__ import annotations

from apis.base_api import BaseApi
from common.exceptions import ApiError


class DeptApi(BaseApi):
    prefix = "/dept"

    def select_all(self, headers: dict | None = None, **kwargs):
        """
        查询全部科室。

        TODO: 若真实路径不是 /dept/selectAll，改这里的 "selectAll"。
        """
        return self.http.send("GET", self.url("selectAll"), headers=headers, **kwargs)

    def get_all(self, headers: dict | None = None) -> list[dict]:
        """返回科室列表 data。"""
        body = self.http.send_json("GET", self.url("selectAll"), headers=headers)
        self.ensure_business_ok(body, message="查询科室列表失败")
        data = body.get("data")
        if not isinstance(data, list):
            raise ApiError("科室列表 data 不是数组，请检查响应结构", body=body)
        return data

    def get_dept_map(self, headers: dict | None = None) -> dict[str, int]:
        """
        返回 {科室名称: 科室id}，供用例按名称取 id。

        TODO: 确认 id 字段名 —— 常见为 id / deptId / departmentId。
        """
        dept_map: dict[str, int] = {}
        for item in self.get_all(headers=headers):
            name = item.get("name")
            dept_id = item.get("id")      # TODO id 字段名以真实响应为准
            if name is not None and dept_id is not None:
                dept_map[name] = dept_id
        return dept_map

    def get_dept_id_by_name(self, dept_name: str, headers: dict | None = None) -> int:
        """
        按科室名称取 id，找不到抛 ApiError（可用 pytest.raises 断言）。
        """
        dept_map = self.get_dept_map(headers=headers)
        if dept_name not in dept_map:
            raise ApiError(
                f"仓库中没有名称【{dept_name}】的科室，现有科室: {list(dept_map)}"
            )
        return dept_map[dept_name]