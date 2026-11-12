"""端到端业务流程测试：发布 → 审核 → 认领 → 确认。

单个接口的用例只能证明"这一步没错"，集成用例负责证明"整条链路串起来没错"，
包括状态在多个模块间流转时的一致性（信息状态、申请状态、审计记录）。
"""

from conftest import API

PUBLISH_BODY = {
    "kind": "FOUND",
    "title": "图书馆捡到无线耳机",
    "category": "数码设备",
    "location": "图书馆",
    "event_time": "2026-10-09T12:00",
    "description": "白色充电盒，拾得于二楼自习区。",
}

NOTE_BOB = "耳机为白色，充电盒背面有蓝色贴纸。"
NOTE_CAROL = "失主是我，耳机左耳有轻微划痕，可以核对。"


def claim(client, item_id: int, note: str):
    return client.post(f"{API}/items/{item_id}/claims", json={"note": note})


class TestHappyPath:
    def test_publish_review_claim_approve(self, make_client):
        alice = make_client(login="alice")
        bob = make_client(login="bob")
        admin = make_client(login="admin")
        anonymous = make_client()

        # 1. 发布后进入待审核，公网不可见
        published = alice.post(f"{API}/items", json=PUBLISH_BODY)
        assert published.status_code == 201
        item_id = published.json()["id"]
        assert anonymous.get(f"{API}/items").json()["items"] == []

        # 2. 管理员在待审列表中看到它，并审核通过
        pending_titles = [row["title"] for row in admin.get(f"{API}/admin/items").json()["items"]]
        assert PUBLISH_BODY["title"] in pending_titles
        assert admin.post(f"{API}/items/{item_id}/review", json={"decision": "approve"}).status_code == 200

        # 3. 通过后出现在公共列表
        public = anonymous.get(f"{API}/items").json()["items"]
        assert [row["id"] for row in public] == [item_id]

        # 4. 其他用户提交认领申请
        assert claim(bob, item_id, NOTE_BOB).status_code == 201

        # 5. 发布者在详情页看到申请，并确认
        detail = alice.get(f"{API}/items/{item_id}").json()
        assert len(detail["claims"]) == 1
        claim_id = detail["claims"][0]["id"]
        assert alice.post(f"{API}/claims/{claim_id}/review", json={"decision": "approve"}).status_code == 200

        # 6. 物品变为已认领，申请变为已通过
        assert anonymous.get(f"{API}/items/{item_id}").json()["item"]["status"] == "CLAIMED"
        assert bob.get(f"{API}/applications").json()["claims"][0]["status"] == "APPROVED"

    def test_claimed_item_leaves_the_open_filter(self, make_client):
        alice = make_client(login="alice")
        bob = make_client(login="bob")
        admin = make_client(login="admin")
        item_id = alice.post(f"{API}/items", json=PUBLISH_BODY).json()["id"]
        admin.post(f"{API}/items/{item_id}/review", json={"decision": "approve"})
        claim_id = claim(bob, item_id, NOTE_BOB).json()["id"]
        alice.post(f"{API}/claims/{claim_id}/review", json={"decision": "approve"})

        assert [row["id"] for row in alice.get(f"{API}/items", params={"status": "OPEN"}).json()["items"]] == []
        assert [row["id"] for row in alice.get(f"{API}/items", params={"status": "CLAIMED"}).json()["items"]] == [item_id]


class TestMultiApplicantCompetition:
    def test_approving_one_claim_closes_the_others(self, make_client):
        alice = make_client(login="alice")
        bob = make_client(login="bob")
        carol = make_client(login="carol")
        admin = make_client(login="admin")

        item_id = alice.post(f"{API}/items", json=PUBLISH_BODY).json()["id"]
        admin.post(f"{API}/items/{item_id}/review", json={"decision": "approve"})
        bob_claim = claim(bob, item_id, NOTE_BOB).json()["id"]
        carol_claim = claim(carol, item_id, NOTE_CAROL).json()["id"]

        # 发布者能看到两份申请
        assert len(alice.get(f"{API}/items/{item_id}").json()["claims"]) == 2

        alice.post(f"{API}/claims/{bob_claim}/review", json={"decision": "approve"})

        statuses = {
            row["id"]: row["status"]
            for row in alice.get(f"{API}/items/{item_id}").json()["claims"]
        }
        assert statuses == {bob_claim: "APPROVED", carol_claim: "CLOSED"}

    def test_losing_applicant_sees_closed_status(self, make_client):
        alice = make_client(login="alice")
        bob = make_client(login="bob")
        carol = make_client(login="carol")
        admin = make_client(login="admin")

        item_id = alice.post(f"{API}/items", json=PUBLISH_BODY).json()["id"]
        admin.post(f"{API}/items/{item_id}/review", json={"decision": "approve"})
        bob_claim = claim(bob, item_id, NOTE_BOB).json()["id"]
        claim(carol, item_id, NOTE_CAROL)
        alice.post(f"{API}/claims/{bob_claim}/review", json={"decision": "approve"})

        mine = carol.get(f"{API}/applications").json()["claims"]
        assert [row["status"] for row in mine] == ["CLOSED"]

    def test_late_claim_is_rejected_after_item_is_taken(self, make_client):
        alice = make_client(login="alice")
        bob = make_client(login="bob")
        admin = make_client(login="admin")

        item_id = alice.post(f"{API}/items", json=PUBLISH_BODY).json()["id"]
        admin.post(f"{API}/items/{item_id}/review", json={"decision": "approve"})
        claim_id = claim(bob, item_id, NOTE_BOB).json()["id"]
        alice.post(f"{API}/claims/{claim_id}/review", json={"decision": "approve"})

        late = make_client(login="carol")
        response = claim(late, item_id, "我来晚了，也想认领。")
        assert response.status_code == 409
        assert response.json() == {"error": "该信息当前不接受认领。"}


class TestRejectionPath:
    def test_rejected_claim_keeps_item_open_for_others(self, make_client):
        alice = make_client(login="alice")
        bob = make_client(login="bob")
        carol = make_client(login="carol")
        admin = make_client(login="admin")

        item_id = alice.post(f"{API}/items", json=PUBLISH_BODY).json()["id"]
        admin.post(f"{API}/items/{item_id}/review", json={"decision": "approve"})
        bob_claim = claim(bob, item_id, NOTE_BOB).json()["id"]

        assert alice.post(f"{API}/claims/{bob_claim}/review", json={"decision": "reject"}).status_code == 200

        # 物品仍可被认领
        detail = alice.get(f"{API}/items/{item_id}").json()
        assert detail["item"]["status"] == "OPEN"
        assert claim(carol, item_id, NOTE_CAROL).status_code == 201

        # 被拒记录仍占用"同一用户只能申请一次"的唯一约束，bob 无法重复提交
        assert bob.get(f"{API}/applications").json()["claims"][0]["status"] == "REJECTED"
        again = claim(bob, item_id, "我再补充一些特征信息。")
        assert again.status_code == 409
        assert again.json() == {"error": "你已经申请过此物品，请查看申请记录。"}
    def test_rejected_item_is_hidden_and_cannot_be_claimed(self, make_client):
        alice = make_client(login="alice")
        bob = make_client(login="bob")
        admin = make_client(login="admin")
        anonymous = make_client()

        item_id = alice.post(f"{API}/items", json={**PUBLISH_BODY, "title": "描述不完整的信息"}).json()["id"]
        response = admin.post(
            f"{API}/items/{item_id}/review",
            json={"decision": "reject", "review_reason": "请补充可核验特征"},
        )
        assert response.status_code == 200

        assert anonymous.get(f"{API}/items/{item_id}").status_code == 404
        assert anonymous.get(f"{API}/items").json()["items"] == []
        assert claim(bob, item_id, NOTE_BOB).status_code == 409

        # 发布者仍能看到拒绝原因，便于修改后重新发布
        own = alice.get(f"{API}/items/{item_id}").json()["item"]
        assert own["pub_status"] == "REJECTED"
        assert own["review_reason"] == "请补充可核验特征"


class TestOwnershipRules:
    def test_owner_cannot_claim_own_publication(self, make_client):
        alice = make_client(login="alice")
        admin = make_client(login="admin")
        item_id = alice.post(f"{API}/items", json=PUBLISH_BODY).json()["id"]
        admin.post(f"{API}/items/{item_id}/review", json={"decision": "approve"})

        response = claim(alice, item_id, NOTE_BOB)
        assert response.status_code == 403
        assert response.json() == {"error": "不能认领本人发布的物品。"}

    def test_admin_cannot_review_claims_of_others_items(self, make_client):
        alice = make_client(login="alice")
        bob = make_client(login="bob")
        admin = make_client(login="admin")
        item_id = alice.post(f"{API}/items", json=PUBLISH_BODY).json()["id"]
        admin.post(f"{API}/items/{item_id}/review", json={"decision": "approve"})
        claim_id = claim(bob, item_id, NOTE_BOB).json()["id"]

        # 管理员可以审核"物品发布"，但不能代替发布者确认"认领申请"
        response = admin.post(f"{API}/claims/{claim_id}/review", json={"decision": "approve"})
        assert response.status_code == 403
        assert response.json() == {"error": "只有发布者可以审核。"}

    def test_other_users_cannot_see_pending_item_detail(self, make_client):
        alice = make_client(login="alice")
        bob = make_client(login="bob")
        item_id = alice.post(f"{API}/items", json=PUBLISH_BODY).json()["id"]

        assert bob.get(f"{API}/items/{item_id}").status_code == 404
        assert alice.get(f"{API}/items/{item_id}").status_code == 200


class TestAuditTrail:
    def test_flow_records_publish_and_claim_actions(self, make_client, db):
        from app.db.models import Audit

        alice = make_client(login="alice")
        bob = make_client(login="bob")
        admin = make_client(login="admin")
        item_id = alice.post(f"{API}/items", json=PUBLISH_BODY).json()["id"]
        admin.post(f"{API}/items/{item_id}/review", json={"decision": "approve"})
        claim_id = claim(bob, item_id, NOTE_BOB).json()["id"]
        alice.post(f"{API}/claims/{claim_id}/review", json={"decision": "approve"})

        actions = [row.action for row in db.query(Audit).order_by(Audit.id).all()]
        assert actions == ["ITEM_PUBLISH", "CLAIM_SUBMIT", "CLAIM_APPROVE"]

    def test_item_history_is_visible_to_owner_after_flow(self, make_client):
        alice = make_client(login="alice")
        bob = make_client(login="bob")
        admin = make_client(login="admin")
        item_id = alice.post(f"{API}/items", json=PUBLISH_BODY).json()["id"]
        admin.post(f"{API}/items/{item_id}/review", json={"decision": "approve"})
        claim_id = claim(bob, item_id, NOTE_BOB).json()["id"]
        alice.post(f"{API}/claims/{claim_id}/review", json={"decision": "approve"})

        history = alice.get(f"{API}/items/{item_id}").json()["history"]
        assert [row["action"] for row in history] == ["CLAIM_APPROVE", "CLAIM_SUBMIT", "ITEM_PUBLISH"]
