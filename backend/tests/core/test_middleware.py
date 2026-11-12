"""HTTP 中间件与全局异常映射的测试（覆盖 app/main.py）。

CSRF 校验、请求体积上限、安全响应头和统一错误体是全局行为，
这里逐项验证，避免"某个接口写对了、另一个接口漏了"的情况。
"""

import re

import pytest

from conftest import API, PASSWORD

CSRF_PATTERN = re.compile(r"^[0-9a-f]{48}$")


class TestCsrfProtection:
    def test_get_issues_token_in_header_and_cookie(self, client):
        response = client.raw.get(f"{API}/session")
        assert response.status_code == 200
        assert CSRF_PATTERN.match(response.headers["X-CSRF-Token"])
        assert response.cookies.get("session")

    def test_write_without_token_is_rejected(self, client):
        response = client.raw.post(f"{API}/login", json={"username": "alice", "password": PASSWORD})
        assert response.status_code == 400
        assert response.json() == {"error": "页面验证失效，请刷新后重试。"}

    def test_write_with_wrong_token_is_rejected(self, client, users):
        client.raw.get(f"{API}/session")
        response = client.raw.post(
            f"{API}/login",
            json={"username": "alice", "password": PASSWORD},
            headers={"X-CSRF-Token": "0" * 48},
        )
        assert response.status_code == 400
        assert response.json()["error"] == "页面验证失效，请刷新后重试。"

    def test_write_with_matching_token_passes(self, client, users):
        token = client.raw.get(f"{API}/session").headers["X-CSRF-Token"]
        response = client.raw.post(
            f"{API}/login",
            json={"username": "alice", "password": PASSWORD},
            headers={"X-CSRF-Token": token},
        )
        assert response.status_code == 200
        assert response.json()["message"] == "登录成功"

    def test_safe_methods_do_not_need_token(self, client):
        for path in ("/health", "/items", "/session"):
            assert client.raw.get(API + path).status_code == 200

    def test_token_rotates_after_login(self, client, users):
        before = client.raw.get(f"{API}/session").headers["X-CSRF-Token"]
        response = client.post(f"{API}/login", json={"username": "alice", "password": PASSWORD})
        after = response.headers["X-CSRF-Token"]
        assert after and after != before
        assert CSRF_PATTERN.match(after)

    def test_login_session_carries_the_new_token(self, client, users):
        login = client.post(f"{API}/login", json={"username": "alice", "password": PASSWORD})
        token = login.headers["X-CSRF-Token"]
        assert client.me()["csrf"] == token

    def test_old_token_is_useless_after_logout(self, client, users):
        client.login("alice")
        stale = client.csrf
        assert client.logout().status_code == 200
        response = client.raw.post(
            f"{API}/items",
            json={
                "kind": "FOUND",
                "title": "登出后的发布尝试",
                "category": "其他",
                "location": "图书馆",
                "event_time": "2026-10-09T12:00",
                "description": "登出后应当无法继续写操作。",
            },
            headers={"X-CSRF-Token": stale},
        )
        assert response.status_code == 400
        assert response.json()["error"] == "页面验证失效，请刷新后重试。"


class TestRequestSizeLimit:
    def test_oversized_body_is_rejected_before_parsing(self, client):
        payload = b'{"pad":"' + b"x" * 20_000 + b'"}'
        response = client.raw.post(
            f"{API}/login", content=payload, headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 413
        assert response.json() == {"error": "请求内容过长。"}

    def test_body_within_limit_is_accepted(self, client, users):
        assert client.post(f"{API}/login", json={"username": "alice", "password": PASSWORD}).status_code == 200


class TestSecurityHeaders:
    @pytest.mark.parametrize(
        ("header", "expected"),
        [
            ("X-Content-Type-Options", "nosniff"),
            ("X-Frame-Options", "DENY"),
            ("Cache-Control", "no-store"),
        ],
    )
    def test_hardening_headers_are_present(self, client, header, expected):
        assert client.raw.get(f"{API}/session").headers[header] == expected

    def test_content_security_policy_is_restrictive(self, client):
        csp = client.raw.get(f"{API}/session").headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "object-src 'none'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "unsafe-eval" not in csp

    def test_headers_also_present_on_error_responses(self, client):
        response = client.raw.get(f"{API}/items/999999")
        assert response.status_code == 404
        assert response.headers["X-Frame-Options"] == "DENY"


class TestGlobalErrorHandling:
    def test_unknown_api_path_returns_json_404(self, client):
        response = client.raw.get(f"{API}/definitely-not-a-route")
        assert response.status_code == 404
        assert response.json() == {"error": "页面或信息不存在。"}

    def test_business_error_is_mapped_to_its_status(self, client):
        response = client.raw.get(f"{API}/mine")
        assert response.status_code == 401
        assert response.json() == {"error": "请先登录。"}

    def test_validation_error_unwraps_pydantic_prefix(self, client, users):
        client.login("alice")
        response = client.post(
            f"{API}/items",
            json={
                "kind": "FOUND",
                "title": "图书馆捡到耳机",
                "category": "数码",
                "location": "图书馆",
                "event_time": "2026-10-09T12:00",
                "description": "白色充电盒，拾得于二楼。",
            },
        )
        assert response.status_code == 400
        body = response.json()
        assert body == {"error": "信息类型或类别无效。"}
        assert "Value error" not in body["error"]

    def test_malformed_json_body_returns_400(self, client, users):
        client.login("alice")
        response = client.raw.post(
            f"{API}/items",
            content=b"{not json",
            headers={"Content-Type": "application/json", "X-CSRF-Token": client.csrf},
        )
        assert response.status_code == 400
        assert "error" in response.json()
