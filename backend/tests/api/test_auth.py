"""登录、登出与会话接口的测试（覆盖 app/api/routes/auth.py）。

除状态码外，重点验证：会话切换是否干净、csrf 是否随之轮换、
密码散列是否绝不外泄。
"""

import re

import pytest

from conftest import API, PASSWORD


class TestLogin:
    def test_success_returns_redirect_and_sets_session(self, client, users):
        response = client.post(f"{API}/login", json={"username": "alice", "password": PASSWORD})
        assert response.status_code == 200
        assert response.json() == {"message": "登录成功", "redirect": "/"}
        session = client.me()
        assert session["user"]["username"] == "alice"
        assert session["is_admin"] is False

    def test_admin_login_exposes_is_admin(self, client, users):
        client.login("admin")
        assert client.me()["is_admin"] is True

    def test_username_surrounding_spaces_are_tolerated(self, client, users):
        response = client.post(f"{API}/login", json={"username": "  alice  ", "password": PASSWORD})
        assert response.status_code == 200
        assert client.me()["user"]["username"] == "alice"

    def test_password_is_not_trimmed(self, client, users):
        response = client.post(f"{API}/login", json={"username": "alice", "password": f" {PASSWORD} "})
        assert response.status_code == 401

    @pytest.mark.parametrize(
        "payload",
        [
            {"username": "alice", "password": "wrong-password"},
            {"username": "nobody", "password": PASSWORD},
            {"username": "Alice", "password": PASSWORD},
            {"username": "", "password": PASSWORD},
            {"username": "alice"},
            {},
        ],
    )
    def test_invalid_credentials_are_rejected(self, client, users, payload):
        response = client.post(f"{API}/login", json=payload)
        assert response.status_code in (400, 401)
        assert "error" in response.json()

    def test_wrong_password_message_does_not_leak_account_existence(self, client, users):
        wrong_password = client.post(f"{API}/login", json={"username": "alice", "password": "nope"}).json()
        unknown_user = client.post(f"{API}/login", json={"username": "ghost", "password": "nope"}).json()
        assert wrong_password == unknown_user == {"error": "账号或密码错误。"}

    def test_second_login_switches_account_cleanly(self, client, users):
        client.login("alice")
        admin_token = client.csrf
        client.login("bob")
        assert client.me()["user"]["username"] == "bob"
        assert client.me()["is_admin"] is False
        assert client.csrf != admin_token


class TestSessionInfo:
    def test_anonymous_session_exposes_frontend_bootstrap_data(self, client):
        body = client.me()
        assert body["user"] is None
        assert body["is_admin"] is False
        assert body["allow_self"] is False
        assert len(body["categories"]) == 5
        assert body["labels"]["OPEN"] == "待认领"
        assert body["version"].startswith("v")

    def test_csrf_field_matches_response_header(self, client):
        response = client.get(f"{API}/session")
        assert response.json()["csrf"] == response.headers["X-CSRF-Token"]
        assert re.fullmatch(r"[0-9a-f]{48}", response.json()["csrf"])

    def test_logged_in_session_returns_public_profile_only(self, client, users):
        client.login("alice")
        user = client.me()["user"]
        assert user == {"id": users["alice"].id, "username": "alice", "name": "林同学", "role": "user"}
        assert "password_hash" not in str(client.me())


class TestLogout:
    def test_logout_clears_session(self, client, users):
        client.login("alice")
        response = client.logout()
        assert response.status_code == 200
        assert response.json() == {"redirect": "/"}
        assert client.me()["user"] is None

    def test_logout_requires_login(self, client):
        response = client.raw.post(
            f"{API}/logout",
            headers={"X-CSRF-Token": client.raw.get(f"{API}/session").headers["X-CSRF-Token"]},
        )
        assert response.status_code == 401
        assert response.json() == {"error": "请先登录。"}

    def test_protected_endpoint_rejects_after_logout(self, client, users):
        client.login("alice")
        assert client.get(f"{API}/mine").status_code == 200
        client.logout()
        assert client.get(f"{API}/mine").status_code == 401

    def test_second_logout_is_rejected(self, client, users):
        client.login("alice")
        assert client.logout().status_code == 200
        assert client.logout().status_code == 401
