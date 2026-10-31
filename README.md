# hospital_api_test

基于 pytest + requests + allure 的接口自动化测试框架。

---

## 一、目录结构

```
hospital_api_test/
├── conftest.py                 # 根级：命令行参数、全局 fixture、pytest 钩子
├── pytest.ini                  # pytest 配置（marker、日志、allure、导入路径）
├── requirements.txt            # 依赖清单
├── run.py                      # 程序化执行入口（CI 用）
│
├── config/
│   └── settings.py             # 多环境配置（dev / test / prod）
│
├── common/                     # 与业务无关的基础设施
│   ├── logger.py               # 统一日志
│   ├── http_request.py         # HTTP 封装（超时 / 重试 / 日志 / 脱敏）
│   ├── assert_utils.py         # 断言封装
│   ├── data_loader.py          # CSV / JSON / YAML 读取
│   └── exceptions.py           # 自定义异常 ApiError
│
├── apis/                       # 接口对象层：一个接口模块一个类
│   ├── base_api.py
│   ├── staff_api.py            # /staff/*
│   ├── dept_api.py             # /dept/*
│   └── registration_api.py     # /registration/*
│
├── services/                   # 业务层：多接口组合成业务动作
│   └── registration_service.py
│
├── data/                       # 测试数据
│   ├── booking_data.csv        # 挂号数据驱动用例集
│   └── users.yaml              # 账号数据集
│
├── testcases/
│   ├── conftest.py             # 目录级 fixture（dept_id / reg_payload / CSV 数据）
│   ├── test_admin_reg_scenario.py   # 场景级用例
│   └── test_registration_api.py     # 接口级 + 数据驱动 + 异常场景
│
└── reports/                    # 输出（勿提交 git）
    ├── allure-results/
    └── logs/
```

### 分层职责

| 层 | 职责 | 改需求时动哪里 |
|---|---|---|
| `testcases/` | 业务流程 + 断言 | 业务规则变化 |
| `services/` | 组合多个接口 | 业务流程变化 |
| `apis/` | 单个接口的 URL / 参数 | 接口路径、参数名变化 |
| `common/` | 与业务无关的通用能力 | 框架能力增强 |
| `config/` | 环境与账号 | 换环境 |

**核心原则：用例里不出现 URL 字符串、不出现 requests 调用、不出现 token 拼接。**

---

## 二、快速开始

```bash
pip install -r requirements.txt

# 跑全部用例（默认 dev 环境）
pytest

# 指定环境
pytest --env=test

# 只跑冒烟
pytest -m smoke

# 只跑异常场景
pytest -m negative

# 用例名过滤
pytest -k "挂号"

# 查看 fixture 依赖链（学习 fixture 强烈推荐）
pytest --setup-show

# 列出所有可用 fixture
pytest --fixtures

# 只跑上次失败的
pytest --lf

# 最慢的 10 条用例
pytest --durations=10

# 并行执行（需 pytest-xdist）
pytest -n auto

# 失败重跑 2 次（需 pytest-rerunfailures）
pytest --reruns 2
```

生成 allure 报告：

```bash
pytest
allure serve reports/allure-results
# 或生成静态报告
allure generate reports/allure-results -o reports/allure-report --clean
```

---

## 三、待补充的真实接口信息（TODO 清单）

搜索整个项目里的 `TODO`，共以下几处：

| 文件 | 需要确认的内容 |
|---|---|
| [config/settings.py](config/settings.py) | test / prod 环境的地址、账号、科室名 |
| [apis/staff_api.py](apis/staff_api.py) | 登录路径、token 在响应中的字段名（`data.token`？`data.accessToken`？）、登出接口是否存在 |
| [apis/dept_api.py](apis/dept_api.py) | 科室列表路径、科室 id 字段名（`id` / `deptId`） |
| [apis/registration_api.py](apis/registration_api.py) | 创建挂号路径、`DEFAULT_PAYLOAD` 各字段取值、`invoiceNo` 是否要求唯一、查询接口路径 |
| [testcases/test_registration_api.py](testcases/test_registration_api.py) | 未鉴权时的真实表现、创建接口返回的 data 结构 |
| [data/booking_data.csv](data/booking_data.csv) | 各异常数据的真实业务错误码（现在是占位的 500） |

### 建议补充顺序

1. **先跑通正常场景**：`pytest -m smoke --env=dev`
   —— 依次修 `settings.py` → `staff_api.py`（token 字段）→ `dept_api.py`（id 字段）→ `registration_api.py`（路径）
2. **再跑数据驱动**：`pytest testcases/test_registration_api.py -k 数据驱动`
   —— 对照真实响应修 CSV 里的 `expect_code`
3. **最后修异常场景**：把 `test_create_registration_without_token` 里的断言改成真实行为

---

## 四、框架关键设计说明

### 1. 环境切换（`--env`）

`conftest.py` 的 `pytest_addoption` 注册参数 → `pytest_configure` 解析后写入 `HOSPITAL_ENV`
→ `config.settings.get_settings()` 读取。

**注意**：不要在 conftest.py 顶层 import `config.settings` 的常量 ——
conftest 加载早于 `pytest_configure`，会把环境锁死成 dev。

### 2. fixture 依赖链

```
env_config
   └── http
        ├── staff_api ──┐
        ├── dept_api ───┼── registration_service
        └── registration_api
              └── admin_token → auth_headers
                    └── dept_id → reg_payload
```

- `scope="session"`：整个测试会话只执行一次（登录、查科室）
- `scope="function"`：每条用例都重新执行（`reg_payload` 工厂）
- `yield` 之前是 setup，之后是 teardown（见 `http` fixture）

用 `pytest --setup-show` 可以直观看到创建/销毁顺序。

### 3. 失败自动取证

`conftest.py` 的 `pytest_runtest_makereport` 钩子在用例失败时，
自动把最后的请求报文、响应报文、断言堆栈挂到 allure 报告上，无需在用例里写任何代码。

### 4. 日志

- 控制台：`pytest.ini` 的 `log_cli`
- 文件：`reports/logs/pytest.log`（pytest 自身日志）+ `reports/logs/test.log`（框架日志）
- 敏感字段（password / token / authorization）在日志和报告中自动打码

---

## 五、练习路线（按需继续扩展）

当前框架已覆盖：fixture 体系、conftest 分层、参数化、数据驱动、marker、自定义命令行参数、
核心钩子、allure 集成、日志、断言封装、接口分层。

可以继续练习的方向：

1. **`pytest_generate_tests` 动态参数化** —— 见根 conftest.py 末尾的注释模板
2. **`monkeypatch` 打桩** —— 模拟第三方接口/支付回调
3. **并发数据隔离** —— `-n auto` 并行时如何保证测试数据不冲突（建议用 `tmp_path_factory` 生成唯一标识）
4. **CI 集成** —— GitHub Actions / Jenkins 里执行 `python run.py --env=test -m smoke`
5. **接口契约校验** —— 用 Pydantic 校验响应结构，而不仅是断言 code

---

## 六、CI/CD 集成

### 6.1 三个概念

| 术语 | 含义 |
|---|---|
| **CI**（持续集成） | 每次提交代码，机器自动拉代码 → 装依赖 → 跑测试，尽早发现改坏了什么 |
| **CD**（持续交付） | 测试通过后自动准备好可发布产物，**由人点按钮**发布 |
| **CD**（持续部署） | 测试通过后**直接自动**发布，无人干预 |

一条流水线永远由这五段组成：

```
① 触发器 → ② 准备环境 → ③ 执行任务 → ④ 产出报告/产物 → ⑤ 门禁 & 通知
```

### 6.2 本项目已配置的流水线

文件：[.github/workflows/api-test.yml](.github/workflows/api-test.yml)

| 环节 | 配置 |
|---|---|
| ① 触发 | push 到 main、提 PR、每天北京时间 02:00 定时、仓库网页手动触发 |
| ② 环境 | GitHub 提供的 `ubuntu-latest` + Python 3.12（每次都是干净系统） |
| ③ 执行 | `pytest --env=dev` |
| ④ 产物 | `reports/allure-results` 原始数据 + `allure-report` HTML + 运行日志，保留 7 天 |
| ⑤ 门禁 | 需在仓库 Settings → Branches 中开启（见 6.4） |

### 6.3 第一次跑通

```bash
cd hospital_api_test

git init
git add .
git commit -m "init: pytest 接口自动化框架"
git branch -M main
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
```

> `.gitignore` 已排除 `reports/`、`__pycache__/`、`.pytest_cache/`，不会把产物提交上去。

推送后打开仓库的 **Actions** 标签页即可看到流水线实时日志；
每次运行产生的 allure 报告，可以在该次 Run 页面底部的 **Artifacts** 里下载。

### 6.4 配置质量门禁（红灯禁止合并）

仓库 **Settings → Branches → Add branch protection rule**：

1. Branch name pattern 填 `main`
2. 勾选 **Require status checks to pass before merging**
3. 搜索并选中 `api-test`

之后任何 PR 只要接口测试失败，就无法合并。

### 6.5 在 README 加状态徽章

```markdown
![API Test](https://github.com/<你的用户名>/<仓库名>/actions/workflows/api-test.yml/badge.svg)
```

### 6.6 常用调参

| 需求 | 做法 |
|---|---|
| 只跑冒烟 | 把 step 改成 `pytest --env=dev -m smoke` |
| 换环境地址 | 仓库 Settings → Secrets 加 `BASE_URL`，step 里用 `env: BASE_URL: ${{ secrets.BASE_URL }}` |
| 并行加速 | `pip install pytest-xdist` 后加 `-n auto` |
| 失败重跑 | `pytest --reruns 2`（需 pytest-rerunfailures） |
| 失败告警 | 在 job 末尾加 `if: failure()` 的 curl，推送到企业微信/钉钉机器人 |

### 6.7 上 CI 前必须注意的两件事

1. **测试数据污染**：用例会在服务端真实创建挂号单。CI 每天定时跑，数据会不断累积。上线前应改用独立测试环境，或在 teardown 中调用删除接口清理。
2. **保持基线为绿**：已知的服务端缺陷用 `@pytest.mark.xfail` 记录（见 [data/booking_data.csv](data/booking_data.csv) 的 `mark` 列），不要让它长期让流水线变红 —— 否则「红灯」就失去信号价值了。