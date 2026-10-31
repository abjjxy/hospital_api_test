# common/exceptions.py
"""框架自定义异常。"""

from __future__ import annotations


class ApiError(Exception):
    """
    接口层异常：HTTP 状态码异常、业务 code 不符合预期、或接口数据缺失。

    用例中可以这样断言异常场景：

        with pytest.raises(ApiError):
            dept_api.get_dept_id_by_name("不存在的科室")
    """

    def __init__(self, message: str, *, status_code: int | None = None, body=None):
        self.status_code = status_code
        self.body = body

        detail = message
        if status_code is not None:
            detail += f" | HTTP={status_code}"
        if body is not None:
            detail += f" | body={body}"
        super().__init__(detail)