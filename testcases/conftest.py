# testcases/conftest.py
"""
用例目录级 conftest：只对 testcases/ 及其子目录生效。

这里放「测试数据 / 业务前置数据」相关的 fixture；
通用的 http、token、api 对象都在根目录 conftest.py 里。
"""

from __future__ import annotations

import pytest

from common.data_loader import load_csv


# ==========================================================================
# 一、业务前置数据（session 级，整个会话只请求一次）
# ==========================================================================
@pytest.fixture(scope="session")
def dept_id(dept_api, auth_headers, env_config):
    """
    目标科室 id。

    session 作用域 + 依赖 auth_headers，所以整个会话只会真实请求一次科室列表。
    这里之所以还写 env_config，是为了保证「环境配置先就绪」，也方便你断点观察依赖链。
    """
    return dept_api.get_dept_id_by_name(env_config.target_dept_name, headers=auth_headers)


@pytest.fixture(scope="session")
def dept_map(dept_api, auth_headers):
    """{科室名称: 科室id}，需要跨科室的用例可以用它。"""
    return dept_api.get_dept_map(headers=auth_headers)


# ==========================================================================
# 二、报文工厂 fixture（factory as fixture）
# ==========================================================================
@pytest.fixture
def reg_payload(registration_api, dept_id):
    """
    返回一个「函数」，用例里可以按需覆盖任意字段：

        payload = reg_payload()                    # 默认报文
        payload = reg_payload(name="张三", amount=30)

    工厂式 fixture 比直接返回 dict 灵活得多，尤其适合数据驱动。
    """

    def _make(**overrides) -> dict:
        return registration_api.default_payload(dept_id, **overrides)

    return _make


# ==========================================================================
# 三、数据驱动数据源
# ==========================================================================
@pytest.fixture(scope="session")
def booking_cases() -> list[dict]:
    """读取 data/booking_data.csv。"""
    return load_csv("booking_data.csv")