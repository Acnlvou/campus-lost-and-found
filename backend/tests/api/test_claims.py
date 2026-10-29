"""认领申请、审核与"我的申请"接口的测试（覆盖 app/api/routes/claims.py）。"""

import pytest

from conftest import API

NOTE = "耳机为白色，充电盒背面有蓝色贴纸。"


@pytest.fixture
def found_item(item_factory):
    """alice 发布的、已公开的招领信息。"""
    return item_factory(kind="FOUND", pub_status="APPROVED", status="OPEN")


def claim(client, item_id: int, note: str = NOTE):
    return client.post(f"{API}/items/{item_id}/claims", json={"note": note})


class TestSubmitClaimEndpoint:
    def test_anonymous_is_rejected(self, client, found_item):
        response = claim(client, found_item.id)
        assert response.status_code == 401
        assert response.json() == {"error": "请先登录。"}

    def test_success_returns_claim_id_and_redirect(self, client, make_client, found_item):
        bob = make_client(login="bob")
        response = claim(bob, found_item.id)
        assert response.status_code == 201
        body = response.json()
        assert body["id"] > 0
        assert body["redirect"] == f"/items/{found_item.id}"

    def test_owner_cannot_claim_own_item(self, client, found_item):
        # REQ-004：禁止本人认领
        client.login("alice")
        response = claim(client, found_item.id)
        assert response.status_code == 403
        assert response.json() == {"error": "不能认领本人发布的物品。"}

    def test_duplicate_claim_is_rejected(self, client, make_client, found_item):
        bob = make_client(login="bob")
        claim(bob, found_item.id)
        response = claim(bob, found_item.id)
        assert response.status_code == 409
        assert response.json() == {"error": "你已经申请过此物品，请查看申请记录。"}

    @pytest.mark.parametrize("note", ["1234", "说" * 501])
    def test_note_length_is_validated(self, client, make_client, found_item, note):
        bob = make_client(login="bob")
        response = claim(bob, found_item.id, note)
        assert response.status_code == 400
        # Field 的长度约束先于自定义校验器触发，此处提示由 Pydantic 给出
        assert "5" in response.json()["error"] or "500" in response.json()["error"]

    def test_blank_note_uses_chinese_message(self, client, make_client, found_item):
        bob = make_client(login="bob")
        response = claim(bob, found_item.id, "     ")
        assert response.status_code == 400
        assert response.json() == {"error": "认领说明须为 5 至 500 个字符。"}

    def test_missing_note_field_is_rejected(self, client, make_client, found_item):
        bob = make_client(login="bob")
        assert bob.post(f"{API}/items/{found_item.id}/claims", json={}).status_code == 400

    def test_lost_item_cannot_be_claimed(self, client, make_client, item_factory):
        item = item_factory(kind="LOST", pub_status="APPROVED")
        bob = make_client(login="bob")
        response = claim(bob, item.id)
        assert response.status_code == 409
        assert response.json() == {"error": "该信息当前不接受认领。"}

    def test_pending_item_cannot_be_claimed(self, client, make_client, item_factory):
        item = item_factory(pub_status="PENDING")
        bob = make_client(login="bob")
        response = claim(bob, item.id)
        assert response.status_code == 409
        assert response.json() == {"error": "该信息尚未公开，不能认领。"}

    def test_missing_item_returns_404(self, client, make_client):
        bob = make_client(login="bob")
        response = claim(bob, 999_999)
        assert response.status_code == 404
        assert response.json() == {"error": "信息不存在。"}


class TestReviewClaimEndpoint:
    def test_owner_approve_returns_reload_flag(self, client, make_client, found_item):
        bob = make_client(login="bob")
        claim_id = claim(bob, found_item.id).json()["id"]
        alice = make_client(login="alice")
        response = alice.post(f"{API}/claims/{claim_id}/review", json={"decision": "approve"})
        assert response.status_code == 200
        assert response.json() == {"message": "审核已保存", "reload": True}

    def test_owner_approve_updates_item_status(self, client, make_client, found_item):
        bob = make_client(login="bob")
        claim_id = claim(bob, found_item.id).json()["id"]
        alice = make_client(login="alice")
        alice.post(f"{API}/claims/{claim_id}/review", json={"decision": "approve"})
        assert alice.get(f"{API}/items/{found_item.id}").json()["item"]["status"] == "CLAIMED"

    @pytest.mark.parametrize("actor", ["bob", "carol", "admin"])
    def test_non_owner_cannot_review(self, client, make_client, found_item, actor):
        bob = make_client(login="bob")
        claim_id = claim(bob, found_item.id).json()["id"]
        visitor = make_client(login=actor)
        response = visitor.post(f"{API}/claims/{claim_id}/review", json={"decision": "approve"})
        assert response.status_code == 403
        assert response.json() == {"error": "只有发布者可以审核。"}

    @pytest.mark.parametrize("decision", ["APPROVE", "ok", ""])
    def test_invalid_decision_is_rejected(self, client, make_client, found_item, decision):
        bob = make_client(login="bob")
        claim_id = claim(bob, found_item.id).json()["id"]
        alice = make_client(login="alice")
        response = alice.post(f"{API}/claims/{claim_id}/review", json={"decision": decision})
        assert response.status_code == 400
        assert response.json() == {"error": "审核操作无效。"}

    def test_missing_claim_returns_404(self, client, make_client):
        alice = make_client(login="alice")
        response = alice.post(f"{API}/claims/999999/review", json={"decision": "approve"})
        assert response.status_code == 404
        assert response.json() == {"error": "申请不存在。"}

    def test_anonymous_cannot_review(self, client, make_client, found_item):
        bob = make_client(login="bob")
        claim_id = claim(bob, found_item.id).json()["id"]
        response = client.post(f"{API}/claims/{claim_id}/review", json={"decision": "approve"})
        assert response.status_code == 401


class TestApplications:
    def test_requires_login(self, client):
        response = client.get(f"{API}/applications")
        assert response.status_code == 401
        assert response.json() == {"error": "请先登录。"}

    def test_returns_own_claims_with_item_context(self, client, make_client, found_item):
        bob = make_client(login="bob")
        claim(bob, found_item.id)
        body = bob.get(f"{API}/applications").json()
        assert len(body["claims"]) == 1
        row = body["claims"][0]
        assert row["title"] == found_item.title
        assert row["location"] == found_item.location
        assert row["status"] == "PENDING"

    def test_excludes_other_users_claims(self, client, make_client, found_item):
        bob = make_client(login="bob")
        carol = make_client(login="carol")
        claim(bob, found_item.id)
        claim(carol, found_item.id)
        assert len(bob.get(f"{API}/applications").json()["claims"]) == 1

    def test_empty_for_user_without_claims(self, client, make_client):
        carol = make_client(login="carol")
        assert carol.get(f"{API}/applications").json() == {"claims": []}

    def test_newest_claim_is_listed_first(self, client, make_client, item_factory):
        bob = make_client(login="bob")
        first = item_factory(title="第一件物品")
        second = item_factory(title="第二件物品")
        claim(bob, first.id)
        claim(bob, second.id)
        titles = [row["title"] for row in bob.get(f"{API}/applications").json()["claims"]]
        assert titles == ["第二件物品", "第一件物品"]

    def test_status_reflects_review_result(self, client, make_client, found_item):
        bob = make_client(login="bob")
        claim_id = claim(bob, found_item.id).json()["id"]
        alice = make_client(login="alice")
        alice.post(f"{API}/claims/{claim_id}/review", json={"decision": "reject"})
        assert bob.get(f"{API}/applications").json()["claims"][0]["status"] == "REJECTED"
