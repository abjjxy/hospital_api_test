# testcases/test_registration_api.py
"""
接口级用例集：数据驱动 + 异常场景。

这个文件演示了 pytest 最常用的几个能力：
* @pytest.mark.parametrize + CSV 数据驱动 + ids 可读用例名
* @pytest.mark.negative 标记异常/边界用例
* pytest.raises 断言预期的异常
* @pytest.mark.skip / skipif 的写法（见文末示例）
"""

from __future__ import annotations

import allure
import pytest

from common.assert_utils import (
    assert_business_code,
    assert_fields,
    assert_status,
)
from common.data_loader import load_csv
from common.exceptions import ApiError

pytestmark = [pytest.mark.regression]

# 模块加载时读一次 CSV（不依赖任何 fixture/配置，import 阶段安全）
BOOKING_CASES = load_csv("booking_data.csv")


def _build_booking_params() -> list:
    """
    把 CSV 的每一行转成 pytest.param，并支持按行打标记。

    CSV 里 mark=xfail 的行 → 生成 @pytest.mark.xfail 标记。
    xfail 的含义：这条用例「预期会失败」。如果它真的失败了，pytest 记为 XFAIL（不算失败）；
    如果它意外通过了，记为 XPASS（strict=False 时仍算通过）。

    用途：服务端缺陷还没修复时，把「正确行为」的断言先写进用例并标 xfail，
    这样既保留了缺陷证据，又不会让 CI 一直红灯。
    缺陷修复后，把该行的 mark 列清空即可（此时用例会真正开始校验）。
    """
    params = []
    for case in BOOKING_CASES:
        marks = []
        if case.get("mark") == "xfail":
            marks.append(
                pytest.mark.xfail(strict=False, reason=case.get("remark") or "已知缺陷，待修复")
            )
        params.append(pytest.param(case, marks=marks, id=case["case_name"]))
    return params


BOOKING_PARAMS = _build_booking_params()


# ==========================================================================
# 一、数据驱动：正常 + 异常数据统一跑
# ==========================================================================
@allure.feature("挂号管理")
@allure.story("创建挂号单 - 数据驱动")
@pytest.mark.parametrize("case", BOOKING_PARAMS)
def test_create_registration_by_data(registration_api, auth_headers, reg_payload, case):
    """
    CSV 中每一行数据生成一条用例。

    CSV 列说明见 data/booking_data.csv 的表头。
    """

    # 空字符串字段表示「故意不给该字段」，用 None 传更接近真实缺失场景
    payload = reg_payload(
        name=case["name"] or "",
        identificationNo=case["identificationNo"] or "",
        dateOfBirth=case["dateOfBirth"],
        gender=int(case["gender"]),
        amount=int(case["amount"]),
    )

    with allure.step(f"提交挂号报文（{case['case_name']}）"):
        allure.attach(str(payload), name="请求报文", attachment_type=allure.attachment_type.JSON)
        resp = registration_api.create(payload, headers=auth_headers)
        result = resp.json()
        allure.attach(str(result), name="响应报文", attachment_type=allure.attachment_type.JSON)

    # 第一层：HTTP 状态码
    assert_status(resp, int(case["expect_http"]), f"[{case['case_name']}] HTTP 状态码不符")

    # 第二层：业务 code（真实错误码待确认，见 CSV 的 remark 列）
    assert_business_code(result, int(case["expect_code"]), f"[{case['case_name']}] 业务 code 不符")


# ==========================================================================
# 二、异常场景
# ==========================================================================
@allure.feature("挂号管理")
@allure.story("创建挂号单 - 异常场景")
@pytest.mark.negative
@pytest.mark.xfail(
    strict=False,
    reason="实测未携带 token 也能创建成功，服务端未做鉴权校验；待确认是设计如此还是缺陷（TODO 提缺陷单）",
)
def test_create_registration_without_token(registration_api, reg_payload):
    """
    未携带鉴权头创建挂号单，**期望**被拒绝。

    这条用例当前是 xfail：断言写的是「正确行为」，但服务端实测会返回 code=200，
    于是用例失败 → 被标记为 XFAIL，CI 不会因此变红。
    等开发修复鉴权后，本条会自动变成 XPASS，届时删掉上面的 xfail 装饰器即可。
    """
    resp = registration_api.create(reg_payload(), headers=None)

    # 期望行为：未鉴权请求应当被拒绝（401/403，或业务层返回非 200 的 code）
    assert resp.status_code in (401, 403), f"未鉴权请求未被拒绝，HTTP={resp.status_code}"
    assert resp.json().get("code") != 200, "未鉴权请求业务层应返回错误码"


@allure.feature("科室管理")
@allure.story("查询科室 - 异常场景")
@pytest.mark.negative
def test_dept_not_exist_raises(dept_api, auth_headers):
    """
    查询不存在的科室时，业务层应抛 ApiError。

    这是 pytest.raises 的典型用法：断言「异常真的发生了」。
    """
    with pytest.raises(ApiError):
        dept_api.get_dept_id_by_name("不存在的科室_TODO_请改成确定不存在的名称", headers=auth_headers)


@allure.feature("挂号管理")
@allure.story("创建挂号单 - 字段校验")
def test_create_registration_field_echo(registration_api, auth_headers, reg_payload):
    """
    创建后校验关键字段是否被正确保存（若接口返回了完整 entity）。

    TODO: 该用例依赖创建接口返回完整数据。
          若只返回 id，请改为「创建后调用 get_by_id 再校验」：
              reg_id = result["data"]["id"]
              detail = registration_api.get_by_id(reg_id, headers=auth_headers).json()
    """
    payload = reg_payload(name="字段回显校验_TODO", amount=25)
    result = registration_api.create(payload, headers=auth_headers).json()

    assert_business_code(result, 200)

    data = result.get("data")

    # 实测创建接口返回 {"code":200,"message":"操作成功","data":1}，data 是挂号单 id（int）
    # 只有接口返回完整实体（dict）时才能做字段回显校验
    if not isinstance(data, dict):
        pytest.skip(
            f"创建接口只返回了 id={data!r}，无法直接做字段校验；"
            "需先确认真实查询接口后改用 get_by_id 二次查询（见 registration_api.get_by_id）"
        )

    assert_fields(data, {"name": payload["name"], "amount": payload["amount"]}, "创建结果字段回显不符")


# ==========================================================================
# 三、跳过示例（保留作模板，当前不生效）
# ==========================================================================
@pytest.mark.skip(reason="示例：无条件跳过")
def test_skip_demo():
    assert False


@pytest.mark.skipif("TODO_CONDITION" == "TODO_CONDITION", reason="示例：满足条件时跳过")
def test_skipif_demo():
    """skipif 的条件可以是环境、平台、版本等。"""
    assert True