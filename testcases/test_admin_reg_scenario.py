# testcases/test_admin_reg_scenario.py
"""
场景级用例：管理员登录 → 查询科室列表 → 创建挂号单。

与改造前的区别
--------------
* URL、请求体、取 token 的逻辑全部下沉到 apis/ 和 services/
* 登录态由 admin_token fixture 提供（session 级，只登录一次）
* 每一步用 allure.step 包裹，报告里能看到完整的业务步骤
* 用例本身只保留「流程 + 断言」
"""

from __future__ import annotations

import allure
import pytest

from common.assert_utils import assert_business_code, assert_status, assert_not_empty

pytestmark = [pytest.mark.smoke, pytest.mark.regression]


@allure.feature("挂号管理")
@allure.story("管理员挂号全流程")
@allure.title("管理员登录 → 查询科室 → 创建挂号单")
def test_admin_create_registration_scene(
    registration_service,
    env_config,
):
    # ====================== 步骤1：管理员登录 ======================
    with allure.step("步骤1：管理员登录 POST /staff/login"):
        token = registration_service.login(env_config.admin_user, env_config.admin_pwd)
        assert_not_empty(token, "登录 token")
        headers = {"Authorization": f"Bearer {token}"}

    # ====================== 步骤2：获取科室列表 ======================
    with allure.step(f"步骤2：按名称查找科室【{env_config.target_dept_name}】"):
        dept_id = registration_service.find_dept_id(env_config.target_dept_name, headers)
        assert_not_empty(dept_id, "科室 id")

    # ====================== 步骤3：创建挂号单 ======================
    with allure.step("步骤3：创建挂号单 POST /registration/createRegistration"):
        result = registration_service.create_registration(dept_id, headers)

        assert_business_code(result, 200, "创建挂号失败")
        # TODO: 若接口返回了挂号单 id 等字段，可在此补断言，例如：
        #       assert_not_empty(result["data"]["id"], "挂号单 id")

    allure.attach(str(result), name="挂号接口返回", attachment_type=allure.attachment_type.JSON)
    print(f"✅ 整条管理员挂号场景执行完成！返回：{result}")


@allure.feature("挂号管理")
@allure.story("管理员挂号全流程")
@allure.title("使用默认报文工厂创建挂号单")
def test_admin_create_registration_with_factory(registration_service, auth_headers, reg_payload):
    """
    演示「报文工厂 fixture」的用法：只覆盖关心的字段。

    这条用例同时演示了 pytest 的复用思想 —— 登录、找科室全由 fixture 完成，
    用例体只有 3 行。
    """
    dept_id = reg_payload()["deptId"]          # 工厂里已经注入了 dept_id
    payload = reg_payload(amount=20)           # 只改金额

    resp = registration_service.registration_api.create(payload, headers=auth_headers)
    result = resp.json()

    assert_status(resp, 200)
    assert_business_code(result, 200, "创建挂号失败")

    assert dept_id is not None, "报文中的 deptId 不应该为空"