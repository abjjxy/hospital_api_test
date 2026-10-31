# conftest.py（项目根目录）
"""
全局 conftest：命令行参数、全局 fixture、pytest 钩子。

作用域说明（很重要）
--------------------
conftest.py 只对**它所在目录及其子目录**生效。
因此：
* 本文件里定义的 fixture → 整个项目都能用
* testcases/conftest.py 里的 fixture → 只在 testcases/ 目录下能用

加载顺序陷阱
------------
conftest.py 在 pytest_configure 之前就被 import，
所以**不要在本文件顶层 import config.settings 的常量**，
否则环境参数 --env 还没生效，配置会被锁死成默认环境。
本文件里的项目模块 import 全部放在函数内部。
"""

from __future__ import annotations

import os
import platform
from pathlib import Path

import pytest

# ==========================================================================
# 一、自定义命令行参数
# ==========================================================================
def pytest_addoption(parser):
    parser.addoption(
        "--env",
        action="store",
        default="dev",
        choices=["dev", "test", "prod"],
        help="运行环境：dev / test / prod（默认 dev）",
    )


def pytest_configure(config):
    """
    参数解析完成后立即执行：
    把 --env 写进环境变量，让 config.settings 在用例收集前就能读到正确环境。
    """
    env = config.getoption("--env")
    os.environ["HOSPITAL_ENV"] = env

    # 这里也可以动态注册 marker（markers 已经在 pytest.ini 里声明，此处仅作示例）
    # config.addinivalue_line("markers", "demo: 示例标记")

    from common.logger import get_logger

    get_logger("session").info("=" * 70)
    get_logger("session").info("测试开始 | 环境=%s | Python=%s | 平台=%s",
                               env, platform.python_version(), platform.system())
    get_logger("session").info("=" * 70)


# ==========================================================================
# 二、全局 fixture
# ==========================================================================

# ---------------------------------------------------------------- 配置
@pytest.fixture(scope="session")
def env_config():
    """当前环境的配置对象（EnvConfig）。用例里读地址、账号都从这里取。"""
    from config.settings import get_settings

    return get_settings()


# ---------------------------------------------------------------- HTTP
@pytest.fixture(scope="session")
def http(env_config):
    """
    全局唯一 HTTP 客户端（session 作用域）。

    yield 之前是 setup，yield 之后是 teardown —— 用例跑完自动关闭连接池。
    """
    from common.http_request import HttpRequest

    client = HttpRequest()
    yield client
    client.close()


# ---------------------------------------------------------------- 接口对象
@pytest.fixture(scope="session")
def staff_api(http):
    from apis.staff_api import StaffApi

    return StaffApi(http)


@pytest.fixture(scope="session")
def dept_api(http):
    from apis.dept_api import DeptApi

    return DeptApi(http)


@pytest.fixture(scope="session")
def registration_api(http):
    from apis.registration_api import RegistrationApi

    return RegistrationApi(http)


# ---------------------------------------------------------------- 鉴权
@pytest.fixture(scope="session")
def admin_token(staff_api, env_config):
    """
    管理员 token，整个测试会话只登录一次。

    依赖链：admin_token → staff_api → http → env_config
    用 `pytest --setup-show` 可以看到完整的创建顺序。
    """
    return staff_api.login_and_get_token(env_config.admin_user, env_config.admin_pwd)


@pytest.fixture(scope="session")
def auth_headers(admin_token):
    """带鉴权信息的请求头。所有需要登录态的用例注入它即可。"""
    return {"Authorization": f"Bearer {admin_token}"}


# ---------------------------------------------------------------- 业务层
@pytest.fixture(scope="session")
def registration_service(staff_api, dept_api, registration_api):
    from services.registration_service import RegistrationService

    return RegistrationService(staff_api, dept_api, registration_api)


# ---------------------------------------------------------------- 用例日志
@pytest.fixture(autouse=True)
def case_logger(request):
    """
    autouse=True：每条用例自动执行，无需在参数里声明。
    用于打印用例开始/结束分隔线，方便看日志。
    """
    from common.logger import get_logger

    log = get_logger("case")
    log.info("-" * 20 + f" START {request.node.nodeid} " + "-" * 20)
    yield
    log.info("-" * 20 + f" END   {request.node.nodeid} " + "-" * 20)


# ==========================================================================
# 三、pytest 钩子
# ==========================================================================
def pytest_collection_modifyitems(config, items):
    """
    用例收集完成后的钩子：把 smoke 用例排到最前面执行。

    实际项目里这个钩子常用于：
    * 打乱/重排执行顺序
    * 按 marker 自动给用例加 skip
    * 剔除不需要执行的用例
    """
    smoke = [item for item in items if "smoke" in item.keywords]
    others = [item for item in items if "smoke" not in item.keywords]
    items[:] = smoke + others


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    """
    用例失败时自动把「最后一次请求/响应」挂到 allure 报告上。

    wrapper=True 是 pytest 8.4+ 的写法（替代已弃用的 hookwrapper=True）：
    必须 return report，否则测试结果会丢失。
    """
    report = yield

    if report.failed:
        _attach_failure_detail(item, report)

    return report


def _attach_failure_detail(item, report):
    """把失败详情 + 最后一次 HTTP 交互写入 allure 报告。"""
    try:
        import allure
    except ImportError:
        return

    try:
        allure.attach(
            str(report.longrepr),
            name=f"失败详情（{report.when}）",
            attachment_type=allure.attachment_type.TEXT,
        )

        client = item.funcargs.get("http") if hasattr(item, "funcargs") else None
        if client is not None:
            if client.last_request_info:
                allure.attach(
                    client.last_request_info,
                    name="最后一次请求",
                    attachment_type=allure.attachment_type.TEXT,
                )
            if client.last_response_info:
                allure.attach(
                    client.last_response_info,
                    name="最后一次响应",
                    attachment_type=allure.attachment_type.TEXT,
                )
    except Exception:  # noqa: BLE001 - 报告增强不能反过来影响测试结果
        pass


def pytest_sessionfinish(session, exitstatus):
    """会话结束时写 allure 的 environment.properties（报告首页展示的环境信息）。"""
    alluredir = session.config.getoption("--alluredir", default=None)
    if not alluredir:
        return

    from config.settings import get_settings

    settings = get_settings()
    target = Path(alluredir if isinstance(alluredir, str) else alluredir[0])
    target.mkdir(parents=True, exist_ok=True)

    lines = [
        f"ENV={settings.name}",
        f"BASE_URL={settings.base_url}",
        f"Python={platform.python_version()}",
        f"Platform={platform.platform()}",
        f"pytest={pytest.__version__}",
    ]
    (target / "environment.properties").write_text("\n".join(lines), encoding="utf-8")


# ==========================================================================
# 四、参考：动态参数化钩子（当前用例不需要，留作练习）
# ==========================================================================
# 如果你的测试数据是「按用例名分文件存放」的，用这个钩子批量生成用例，
# 比在每个用例上写 @pytest.mark.parametrize 更灵活：
#
# def pytest_generate_tests(metafunc):
#     if "dynamic_case" in metafunc.fixturenames:
#         from common.data_loader import load_csv
#         cases = load_csv("booking_data.csv")
#         metafunc.parametrize("dynamic_case", cases, ids=[c["case_name"] for c in cases])