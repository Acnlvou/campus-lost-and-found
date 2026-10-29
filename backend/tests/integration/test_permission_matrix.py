"""权限矩阵的集成测试。

把"哪类角色能访问哪些接口"整理成矩阵统一断言，
避免逐个接口写用例时遗漏某个角色的越权路径。
"""

import pytest

from conftest import API

PUBLISH_BODY = {
    "kind": "FOUND",
    "title": "权限矩阵用招领信息",
    "category": "数码设备",
    "location": "图书馆",
    "event_time": "2026-10-09T12:00",
    "description": "用于验证角色控制的信息描述，长度满足要求。",
}

ROLES = ("anonymous", "user", "admin")


def login_as(make_client, role: str):
    if role == "anonymous":
        return make_client()
    return make_client(login="admin" if role == "admin" else "alice")


READ_MATRIX = [
    (f"{API}/items", {"anonymous": 200, "user": 200, "admin": 200}),
    (f"{API}/health", {"anonymous": 200, "user": 200, "admin": 200}),
    (f"{API}/session", {"anonymous": 200, "user": 200, "admin": 200}),
    (f"{API}/mine", {"anonymous": 401, "user": 200, "admin": 200}),
    (f"{API}/applications", {"anonymous": 401, "user": 200, "admin": 200}),
    (f"{API}/admin/items", {"anonymous": 401, "user": 403, "admin": 200}),
]


@pytest.mark.parametrize(("path", "expected"), READ_MATRIX)
@pytest.mark.parametrize("role", ROLES)
class TestReadPermissions:
    def test_status_code_matches_matrix(self, make_client, path, expected, role):
        visitor = login_as(make_client, role)
        assert visitor.get(path).status_code == expected[role]


DENIED_COMBINATIONS = [
    (path, role, code)
    for path, expected in READ_MATRIX
    for role, code in expected.items()
    if code >= 400
]


@pytest.mark.parametrize(("path", "role", "status"), DENIED_COMBINATIONS)
def test_denied_responses_only_expose_error_message(make_client, path, role, status):
    response = login_as(make_client, role).get(path)
    assert response.status_code == status
    body = response.json()
    assert list(body) == ["error"]
    assert body["error"]


class TestPublishPermissions:
    @pytest.mark.parametrize(
        ("role", "status"), [("anonymous", 401), ("user", 201), ("admin", 201)]
    )
    def test_only_logged_in_users_may_publish(self, make_client, role, status):
        visitor = login_as(make_client, role)
        assert visitor.post(f"{API}/items", json=PUBLISH_BODY).status_code == status

    def test_anonymous_publish_creates_nothing(self, make_client, db):
        from app.db.models import Item

        assert login_as(make_client, "anonymous").post(f"{API}/items", json=PUBLISH_BODY).status_code == 401
        assert db.query(Item).count() == 0


class TestItemReviewPermissions:
    @pytest.mark.parametrize(
        ("role", "status"), [("anonymous", 401), ("user", 403), ("admin", 200)]
    )
    def test_only_admin_may_review_items(self, make_client, item_factory, role, status):
        item = item_factory(pub_status="PENDING")
        visitor = login_as(make_client, role)
        assert visitor.post(f"{API}/items/{item.id}/review", json={"decision": "approve"}).status_code == status

    def test_forbidden_review_does_not_change_state(self, make_client, item_factory, db):
        from app.db.models import Item

        item = item_factory(pub_status="PENDING")
        login_as(make_client, "user").post(f"{API}/items/{item.id}/review", json={"decision": "approve"})
        db.expire_all()
        assert db.get(Item, item.id).pub_status == "PENDING"


class TestClaimReviewPermissions:
    @pytest.mark.parametrize(
        ("role", "status"), [("anonymous", 401), ("user", 200), ("admin", 403)]
    )
    def test_only_owner_may_review_claims(self, make_client, users, item_factory, role, status):
        item = item_factory(pub_status="APPROVED", owner_id=users["alice"].id)
        bob = make_client(login="bob")
        claim_id = bob.post(f"{API}/items/{item.id}/claims", json={"note": "耳机背面有蓝色贴纸。"}).json()["id"]

        # "user" 角色固定为 alice，即该物品的发布者
        visitor = login_as(make_client, role)
        response = visitor.post(f"{API}/claims/{claim_id}/review", json={"decision": "approve"})
        assert response.status_code == status
