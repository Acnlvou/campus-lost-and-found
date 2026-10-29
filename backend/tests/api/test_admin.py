"""管理员接口的测试（覆盖 app/api/routes/admin.py）。"""

import pytest

from conftest import API


class TestAdminItems:
    def test_anonymous_is_rejected(self, client):
        response = client.get(f"{API}/admin/items")
        assert response.status_code == 401
        assert response.json() == {"error": "请先登录。"}

    @pytest.mark.parametrize("username", ["alice", "bob", "carol"])
    def test_normal_user_is_forbidden(self, client, make_client, username):
        visitor = make_client(login=username)
        response = visitor.get(f"{API}/admin/items")
        assert response.status_code == 403
        assert response.json() == {"error": "需要管理员权限。"}

    def test_admin_sees_every_publication_state(self, client, make_client, item_factory):
        item_factory(title="待审核", pub_status="PENDING")
        item_factory(title="已通过", pub_status="APPROVED")
        item_factory(title="已拒绝", pub_status="REJECTED")
        admin = make_client(login="admin")
        statuses = {row["pub_status"] for row in admin.get(f"{API}/admin/items").json()["items"]}
        assert statuses == {"PENDING", "APPROVED", "REJECTED"}

    def test_pending_items_are_listed_first(self, client, make_client, item_factory):
        item_factory(title="已通过一", pub_status="APPROVED")
        item_factory(title="待审核", pub_status="PENDING")
        item_factory(title="已通过二", pub_status="APPROVED")
        admin = make_client(login="admin")
        titles = [row["title"] for row in admin.get(f"{API}/admin/items").json()["items"]]
        assert titles == ["待审核", "已通过二", "已通过一"]

    def test_includes_owner_name(self, client, make_client, item_factory):
        item_factory()
        admin = make_client(login="admin")
        assert admin.get(f"{API}/admin/items").json()["items"][0]["owner_name"] == "林同学"

    def test_empty_database_returns_empty_list(self, client, make_client):
        admin = make_client(login="admin")
        assert admin.get(f"{API}/admin/items").json() == {"items": []}


class TestDuplicateReviewRoute:
    """admin.py 与 items.py 注册了相同的 POST /items/{id}/review。

    APIRouter 按注册顺序解析，items 路由先注册，因此 admin.py 中的
    review_item_route（依赖 admin_required、调用 service.review_item）不可达。
    这组用例用于固定"谁在生效"这一事实，避免后续重构时静默改变行为。
    """

    def test_rejection_message_comes_from_items_handler(self, client, make_client, item_factory):
        # admin_required 的文案是"需要管理员权限。"，items 实现是"无审核权限"
        item = item_factory(pub_status="PENDING")
        alice = make_client(login="alice")
        response = alice.post(f"{API}/items/{item.id}/review", json={"decision": "approve"})
        assert response.status_code == 403
        assert response.json() == {"error": "无审核权限"}

    def test_admin_handler_fields_are_not_honored(self, client, make_client, item_factory):
        """admin.py 的 ReviewRequest 只接受 decision；items.py 还接受 review_reason。

        既然实际生效的是 items.py，带 review_reason 的请求应当被接受。
        """
        item = item_factory(pub_status="PENDING")
        admin = make_client(login="admin")
        response = admin.post(
            f"{API}/items/{item.id}/review",
            json={"decision": "reject", "review_reason": "信息不完整"},
        )
        assert response.status_code == 200
        assert admin.get(f"{API}/items/{item.id}").json()["item"]["review_reason"] == "信息不完整"
