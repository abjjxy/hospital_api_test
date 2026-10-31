# common/http_request.py
"""
HTTP 请求封装（基于 requests.Session）。

相比最朴素的封装，这里补上了实际项目必备的几件事：
1. base_url 拼接：用例里只写相对路径，环境切换只改配置
2. 超时：避免网络异常时用例一直挂着
3. 重试：对 5xx / 连接错误自动重试（只对幂等请求有意义，这里是通用兜底）
4. 日志：请求/响应全量落盘，失败时排查问题不用再抓包
5. 敏感字段脱敏：password / token 不会明文进日志和 allure 报告
6. 保留最后一次请求/响应快照，供 conftest 的失败钩子自动挂到报告上
"""

from __future__ import annotations

import json as _json
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from common.exceptions import ApiError
from common.logger import get_logger
from config.settings import get_settings

log = get_logger("http")

# 日志/报告中需要打码的字段（小写匹配）
_SENSITIVE_KEYS = {"password", "pwd", "token", "authorization", "accesstoken", "refreshtoken"}

# 响应内容在日志里截断的长度
_PREVIEW_LIMIT = 2000


# ---------------------------------------------------------------- 工具函数
def _mask(obj: Any) -> Any:
    """递归脱敏：把敏感字段的值替换成 ***。"""
    if isinstance(obj, dict):
        return {
            k: ("***" if str(k).lower() in _SENSITIVE_KEYS else _mask(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_mask(item) for item in obj]
    return obj


def _preview(text: str, limit: int = _PREVIEW_LIMIT) -> str:
    """截断过长的响应体，避免日志被刷屏。"""
    text = text or ""
    return text if len(text) <= limit else f"{text[:limit]}...（已截断，共 {len(text)} 字符）"


# ---------------------------------------------------------------- 主体
class HttpRequest:
    """全局复用的 HTTP 客户端。在 conftest 中以 session 作用域注入。"""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: int | None = None,
        retries: int | None = None,
    ):
        settings = get_settings()
        self.base_url = (base_url or settings.base_url).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.timeout
        retries = retries if retries is not None else settings.retry

        self.session = requests.Session()

        # 重试策略：连接失败 / 5xx / 429 自动重试
        retry = Retry(
            total=retries,
            backoff_factor=0.5,                       # 0s, 0.5s, 1s ... 递增等待
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET", "HEAD", "OPTIONS", "PUT", "DELETE", "POST"}),
            raise_on_status=False,                    # 重试完仍失败就返回响应，交给用例断言
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # 最近一次请求/响应快照（失败钩子会读取它挂到 allure 报告上）
        self.last_request_info: str = ""
        self.last_response_info: str = ""

    # ------------------------------------------------------------ URL
    def build_url(self, path: str) -> str:
        """相对路径自动拼 base_url；已是完整 URL 则原样返回。"""
        if path.startswith(("http://", "https://")):
            return path
        return f"{self.base_url}/{path.lstrip('/')}"

    # ------------------------------------------------------------ 通用请求
    def send(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: Any = None,
        data: Any = None,
        headers: dict | None = None,
        files: Any = None,
        timeout: int | None = None,
        verify: bool | None = None,
        **kwargs,
    ) -> requests.Response:
        """
        发送请求并返回原始 Response。

        :param method:  GET / POST / PUT / DELETE ...
        :param path:    相对路径（如 "/staff/login"）或完整 URL
        :param params:  URL 查询参数
        :param json:    JSON 请求体
        :param data:    表单请求体
        :param headers: 请求头
        :param files:   文件上传
        :param timeout: 覆盖默认超时
        """
        method = method.upper()
        url = self.build_url(path)
        req_headers = dict(headers or {})
        req_timeout = timeout if timeout is not None else self.timeout

        self.last_request_info = (
            f"{method} {url}\n"
            f"headers: {_mask(req_headers)}\n"
            f"params: {_mask(params)}\n"
            f"body: {_json.dumps(_mask(json), ensure_ascii=False) if json is not None else None}\n"
            f"data: {_mask(data)}"
        )

        log.info("→ %s %s | params=%s | body=%s",
                 method, url, _mask(params),
                 _json.dumps(_mask(json), ensure_ascii=False) if json is not None else None)

        started = time.perf_counter()
        try:
            resp = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json,
                data=data,
                headers=req_headers,
                files=files,
                timeout=req_timeout,
                verify=verify,
                **kwargs,
            )
        except requests.RequestException as exc:
            elapsed = (time.perf_counter() - started) * 1000
            log.error("✗ %s %s | %.0fms | 请求异常: %s", method, url, elapsed, exc)
            self.last_response_info = f"请求异常: {exc!r}"
            raise

        elapsed = (time.perf_counter() - started) * 1000
        self.last_response_info = (
            f"HTTP {resp.status_code} | {elapsed:.0f}ms\n"
            f"headers: {dict(resp.headers)}\n"
            f"body: {_preview(resp.text)}"
        )

        log.info("← %s %s | %s | %.0fms | %s",
                 resp.status_code, url, method, elapsed, _preview(resp.text))
        return resp

    # ------------------------------------------------------------ 便捷方法
    def send_json(self, method: str, path: str, *, expect_status: int | None = None, **kwargs) -> dict:
        """
        发送请求并直接返回解析后的 JSON（dict / list）。

        响应不是合法 JSON 时抛 ApiError，避免用例里出现 "Expecting value: line 1" 这种
        难以定位的报错。
        """
        resp = self.send(method, path, **kwargs)

        if expect_status is not None and resp.status_code != expect_status:
            raise ApiError("HTTP 状态码不符合预期", status_code=resp.status_code, body=_preview(resp.text))

        try:
            return resp.json()
        except ValueError as exc:
            raise ApiError(
                f"响应不是合法 JSON: {exc}", status_code=resp.status_code, body=_preview(resp.text)
            ) from exc

    def get(self, path: str, **kwargs) -> requests.Response:
        return self.send("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        return self.send("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> requests.Response:
        return self.send("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self.send("DELETE", path, **kwargs)

    def close(self) -> None:
        self.session.close()