"""物品检索、详情、发布与审核接口的测试（覆盖 app/api/routes/items.py + claims 路由中的 mine）。

接口层关注：可见性（未公开信息不泄露）、权限（谁能看、谁能改）、
以及与 service 层一致的错误码与错误文案。
"""

import pytest

from conftest import API

PUBLISH_BODY = {
    "kind": "FOUND",
    "title": "图书馆捡到无线耳机",
    "category": "数码设备",
    "location": "图书馆",
    "event_time": "2026-10-09T12:00",
    "description": "白色充电盒，拾得于二楼自习区。",
}


def publish(client, **overrides):
    body = dict(PUBLISH_BODY)
    body.update(overrides)
    return client.post(f"{API}/items", json=body)


class TestListItems:
    def test_public_list_needs_no_login(self, client, item_factory):
        item_factory(title="公开的招领信息")
        response = client.get(f"{API}/items")
        assert response.status_code == 200
        body = response.json()
        assert [row["title"] for row in body["items"]] == ["公开的招领信息"]
        assert body["locations"] == ["图书馆"]

    def test_only_approved_items_are_returned(self, client, item_factory):
        item_factory(title="已通过", pub_status="APPROVED")
        item_factory(title="待审核", pub_status="PENDING")
        item_factory(title="已拒绝", pub_status="REJECTED")
        titles = [row["title"] for row in client.get(f"{API}/items").json()["items"]]
        assert titles == ["已通过"]

    def test_owner_name_is_exposed(self, client, item_factory):
        item_factory()
        assert client.get(f"{API}/items").json()["items"][0]["owner_name"] == "林同学"

    @pytest.mark.parametrize(
        ("params", "expected"),
        [
            ({"kind": "LOST"}, ["寻物信息"]),
            ({"category": "证件卡片"}, ["校园卡"]),
            ({"location": "食堂"}, ["食堂物品"]),
            ({"status": "CLAIMED"}, ["已认领物品"]),
            ({"q": "校园卡"}, ["校园卡"]),
        ],
    )
    def test_filters_are_passed_through(self, client, item_factory, params, expected):
        item_factory(title="招领信息", kind="FOUND", status="OPEN", location="图书馆", category="数码设备")
        item_factory(title="寻物信息", kind="LOST", status="OPEN", location="图书馆", category="数码设备")
        item_factory(title="校园卡", kind="FOUND", status="OPEN", location="图书馆", category="证件卡片")
        item_factory(title="食堂物品", kind="FOUND", status="OPEN", location="食堂", category="生活用品")
        item_factory(title="已认领物品", kind="FOUND", status="CLAIMED", location="图书馆", category="数码设备")
        titles = [row["title"] for row in client.get(f"{API}/items", params=params).json()["items"]]
        assert titles == expected

    @pytest.mark.parametrize("params", [{"kind": "OTHER"}, {"category": "电子产品"}, {"status": "PENDING"}])
    def test_invalid_filter_returns_400(self, client, params):
        response = client.get(f"{API}/items", params=params)
        assert response.status_code == 400
        assert response.json() == {"error": "筛选条件无效。"}

    def test_keyword_over_limit_returns_400(self, client):
        response = client.get(f"{API}/items", params={"q": "关" * 101})
        assert response.status_code == 400
        assert response.json() == {"error": "关键词不能超过 100 个字符。"}

    def test_empty_result_is_valid_response(self, client):
        body = client.get(f"{API}/items").json()
        assert body == {"items": [], "locations": []}


class TestPublish:
    def test_anonymous_cannot_publish(self, client):
        response = publish(client)
        assert response.status_code == 401
        assert response.json() == {"error": "请先登录。"}

    def test_success_returns_id_and_pending_notice(self, client, users):
        client.login("alice")
        response = publish(client)
        assert response.status_code == 201
        body = response.json()
        assert body["id"] > 0
        assert body["redirect"] == f"/items/{body['id']}?notice=pending"

    def test_new_item_is_pending_and_hidden_from_public_list(self, client, make_client, users):
        client.login("alice")
        item_id = publish(client).json()["id"]
        # 本人可见（含待审核状态），但未公开前不会出现在公共列表
        assert client.get(f"{API}/items/{item_id}").json()["item"]["pub_status"] == "PENDING"
        assert client.get(f"{API}/items").json()["items"] == []
        assert make_client().get(f"{API}/items/{item_id}").status_code == 404

    def test_invalid_fields_are_rejected_with_readable_message(self, client, users):
        client.login("alice")
        cases = [
            ({"title": "耳"}, "title 字段须为 2 至 60 个字符。"),
            ({"description": "太短"}, "description 字段须为 5 至 1000 个字符。"),
            ({"event_time": "2026-10-09 12:00"}, "事件时间格式无效。"),
            ({"kind": "OTHER"}, "信息类型或类别无效。"),
        ]
        for overrides, message in cases:
            response = publish(client, **overrides)
            assert response.status_code == 400, overrides
            assert response.json() == {"error": message}

    def test_missing_field_is_rejected(self, client, users):
        client.login("alice")
        body = {key: value for key, value in PUBLISH_BODY.items() if key != "location"}
        assert client.post(f"{API}/items", json=body).status_code == 400

    def test_published_item_appears_in_my_list(self, client, users):
        client.login("alice")
        item_id = publish(client).json()["id"]
        mine = client.get(f"{API}/mine").json()["items"]
        assert [row["id"] for row in mine] == [item_id]


class TestDetail:
    def test_missing_item_returns_404(self, client):
        response = client.get(f"{API}/items/999999")
        assert response.status_code == 404
        assert response.json() == {"error": "信息不存在。"}

    def test_non_numeric_id_returns_400(self, client):
        assert client.get(f"{API}/items/not-a-number").status_code == 400

    def test_approved_item_is_public(self, client, item_factory):
        item = item_factory()
        body = client.get(f"{API}/items/{item.id}").json()
        assert body["item"]["id"] == item.id
        assert body["owner"] is False
        assert body["is_admin"] is False
        assert body["claims"] == []
        assert body["history"] == []

    @pytest.mark.parametrize("viewer", [None, "bob"])
    def test_pending_item_is_hidden_from_others(self, client, make_client, item_factory, viewer):
        item = item_factory(pub_status="PENDING")
        visitor = make_client() if viewer is None else make_client(login=viewer)
        assert visitor.get(f"{API}/items/{item.id}").status_code == 404

    def test_owner_can_see_own_pending_item(self, client, users, item_factory):
        client.login("alice")
        item = item_factory(pub_status="PENDING")
        body = client.get(f"{API}/items/{item.id}").json()
        assert body["owner"] is True
        assert body["item"]["pub_status"] == "PENDING"

    def test_admin_can_see_pending_item(self, client, users, item_factory):
        client.login("admin")
        item = item_factory(pub_status="PENDING")
        body = client.get(f"{API}/items/{item.id}").json()
        assert body["is_admin"] is True
        assert body["owner"] is False


class TestDetailClaimsVisibility:
    def test_owner_sees_every_claim_with_applicant_name(self, client, users, item_factory, claim_factory):
        item = item_factory(pub_status="APPROVED")
        claim_factory(item_id=item.id, applicant_id=users["bob"].id)
        claim_factory(item_id=item.id, applicant_id=users["carol"].id)
        client.login("alice")
        claims = client.get(f"{API}/items/{item.id}").json()["claims"]
        assert {row["applicant_name"] for row in claims} == {"陈同学", "周同学"}

    def test_applicant_sees_only_own_claim(self, client, users, item_factory, claim_factory):
        item = item_factory(pub_status="APPROVED")
        claim_factory(item_id=item.id, applicant_id=users["bob"].id)
        claim_factory(item_id=item.id, applicant_id=users["carol"].id)
        client.login("bob")
        claims = client.get(f"{API}/items/{item.id}").json()["claims"]
        assert len(claims) == 1
        assert claims[0]["applicant_id"] == users["bob"].id

    def test_unrelated_user_sees_no_claims(self, client, users, item_factory, claim_factory):
        item = item_factory(pub_status="APPROVED")
        claim_factory(item_id=item.id, applicant_id=users["bob"].id)
        client.login("carol")
        assert client.get(f"{API}/items/{item.id}").json()["claims"] == []

    def test_history_is_only_visible_to_owner(self, client, make_client, db, users, item_factory):
        from app.db.audit import now
        from app.db.models import Audit

        item = item_factory(pub_status="APPROVED", owner_id=users["alice"].id)
        db.add(Audit(actor_id=users["alice"].id, action="ITEM_PUBLISH", item_id=item.id, detail=item.title, created_at=now()))
        db.commit()

        owner = make_client(login="alice")
        assert [row["action"] for row in owner.get(f"{API}/items/{item.id}").json()["history"]] == ["ITEM_PUBLISH"]

        other = make_client(login="bob")
        assert other.get(f"{API}/items/{item.id}").json()["history"] == []

    def test_publish_history_is_recorded_for_owner(self, client, users):
        client.login("alice")
        item_id = publish(client).json()["id"]
        history = client.get(f"{API}/items/{item_id}").json()["history"]
        assert [row["action"] for row in history] == ["ITEM_PUBLISH"]


class TestMine:
    def test_requires_login(self, client):
        response = client.get(f"{API}/mine")
        assert response.status_code == 401
        assert response.json() == {"error": "请先登录。"}

    def test_returns_only_own_items_including_pending(self, client, users, item_factory):
        item_factory(owner_id=users["alice"].id, title="我的待审核", pub_status="PENDING")
        item_factory(owner_id=users["bob"].id, title="别人的信息", pub_status="APPROVED")
        client.login("alice")
        titles = [row["title"] for row in client.get(f"{API}/mine").json()["items"]]
        assert titles == ["我的待审核"]

    def test_empty_for_new_user(self, client, users):
        client.login("carol")
        assert client.get(f"{API}/mine").json()["items"] == []


class TestReviewEndpoint:
    """POST /api/items/{id}/review

    注意：该路径被 items.py 与 admin.py 同时注册，路由按注册顺序解析，
    实际生效的是 items.py 中的内联实现（admin.py 中的同名路由不可达）。
    因此这里断言的是"实际生效"的行为，包括它与 service 层的差异。
    """

    def test_anonymous_is_rejected(self, client, item_factory):
        item = item_factory(pub_status="PENDING")
        response = client.post(f"{API}/items/{item.id}/review", json={"decision": "approve"})
        assert response.status_code == 401

    def test_normal_user_is_forbidden(self, client, users, item_factory):
        client.login("alice")
        item = item_factory(pub_status="PENDING", owner_id=users["bob"].id)
        response = client.post(f"{API}/items/{item.id}/review", json={"decision": "approve"})
        assert response.status_code == 403
        assert response.json() == {"error": "无审核权限"}

    def test_admin_can_approve(self, client, users, item_factory):
        client.login("admin")
        item = item_factory(pub_status="PENDING")
        response = client.post(f"{API}/items/{item.id}/review", json={"decision": "approve"})
        assert response.status_code == 200
        assert response.json() == {"ok": True}
        assert client.get(f"{API}/items/{item.id}").json()["item"]["pub_status"] == "APPROVED"

    def test_admin_can_reject_with_reason(self, client, users, item_factory):
        client.login("admin")
        item = item_factory(pub_status="PENDING")
        response = client.post(
            f"{API}/items/{item.id}/review",
            json={"decision": "reject", "review_reason": "描述缺少可核验特征"},
        )
        assert response.status_code == 200
        body = client.get(f"{API}/items/{item.id}").json()["item"]
        assert body["pub_status"] == "REJECTED"
        assert body["review_reason"] == "描述缺少可核验特征"

    def test_invalid_decision_is_rejected(self, client, users, item_factory):
        client.login("admin")
        item = item_factory(pub_status="PENDING")
        response = client.post(f"{API}/items/{item.id}/review", json={"decision": "maybe"})
        assert response.status_code == 400
        assert response.json() == {"error": "decision只能是 approve / reject"}

    def test_missing_item_returns_404(self, client, users):
        client.login("admin")
        response = client.post(f"{API}/items/999999/review", json={"decision": "approve"})
        assert response.status_code == 404
        assert response.json() == {"error": "物品不存在"}

    def test_missing_decision_field_is_rejected(self, client, users, item_factory):
        client.login("admin")
        item = item_factory(pub_status="PENDING")
        assert client.post(f"{API}/items/{item.id}/review", json={}).status_code == 400

    def test_re_review_is_allowed_by_this_handler(self, client, users, item_factory):
        """记录与 service.review_item 的差异：此实现缺少"仅待审核可审"的守卫。

        service 层对已审核信息会返回 409，而路由内联实现会直接覆盖状态。
        该用例把当前行为固定下来，一旦修复重复路由，应同步调整本用例。
        """
        client.login("admin")
        item = item_factory(pub_status="APPROVED")
        response = client.post(f"{API}/items/{item.id}/review", json={"decision": "reject"})
        assert response.status_code == 200
        assert client.get(f"{API}/items/{item.id}").json()["item"]["pub_status"] == "REJECTED"

    def test_review_does_not_write_audit_trail(self, client, users, item_factory, db):
        from app.db.models import Audit

        client.login("admin")
        item = item_factory(pub_status="PENDING")
        client.post(f"{API}/items/{item.id}/review", json={"decision": "approve"})
        assert db.query(Audit).filter(Audit.action == "ITEM_APPROVE").count() == 0
