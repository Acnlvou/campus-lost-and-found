"""响应序列化函数的测试（覆盖 app/db/serializers.py）。

序列化层决定"哪些字段能出网"，因此这里同时验证字段集合与敏感字段隔离。
"""

from app.db.audit import now
from app.db.models import Audit, Claim, Item
from app.db.serializers import audit_dict, claim_dict, item_dict, user_dict

ITEM_KEYS = {
    "id",
    "owner_id",
    "kind",
    "title",
    "category",
    "location",
    "event_time",
    "description",
    "status",
    "pub_status",
    "created_at",
    "review_reason",
}

CLAIM_KEYS = {"id", "item_id", "applicant_id", "note", "status", "created_at", "updated_at"}

AUDIT_KEYS = {"id", "actor_id", "action", "item_id", "detail", "created_at"}


class TestUserDict:
    def test_exposes_only_public_fields(self, db, users):
        data = user_dict(users["alice"])
        assert set(data) == {"id", "username", "name", "role"}

    def test_never_leaks_password_hash(self, db, users):
        data = user_dict(users["alice"])
        assert "password_hash" not in data
        assert "password" not in str(data).lower()


class TestItemDict:
    def test_base_fields(self, db, item_factory):
        item = item_factory()
        data = item_dict(item)
        assert set(data) == ITEM_KEYS
        assert data["id"] == item.id
        assert data["pub_status"] == "APPROVED"

    def test_owner_name_is_optional(self, db, item_factory):
        item = item_factory()
        assert "owner_name" not in item_dict(item)
        assert item_dict(item, owner_name="林同学")["owner_name"] == "林同学"

    def test_review_reason_is_exposed_for_rejected_items(self, db, item_factory):
        item = item_factory(pub_status="REJECTED", review_reason="描述不完整")
        assert item_dict(item)["review_reason"] == "描述不完整"


class TestClaimDict:
    def test_base_fields(self, db, item_factory, claim_factory):
        item = item_factory()
        claim = claim_factory(item_id=item.id)
        assert set(claim_dict(claim)) == CLAIM_KEYS

    def test_optional_joins(self, db, item_factory, claim_factory):
        item = item_factory()
        claim = claim_factory(item_id=item.id)
        data = claim_dict(claim, applicant_name="陈同学", title=item.title, location=item.location)
        assert data["applicant_name"] == "陈同学"
        assert data["title"] == item.title
        assert data["location"] == item.location

    def test_optional_fields_absent_by_default(self, db, item_factory, claim_factory):
        claim = claim_factory(item_id=item_factory().id)
        data = claim_dict(claim)
        assert {"applicant_name", "title", "location"}.isdisjoint(data)


class TestAuditDict:
    def test_maps_every_column(self, db, users):
        row = Audit(actor_id=users["admin"].id, action="ITEM_APPROVE", item_id=None, detail="审核通过", created_at=now())
        db.add(row)
        db.commit()
        data = audit_dict(row)
        assert set(data) == AUDIT_KEYS
        assert data["action"] == "ITEM_APPROVE"
        assert data["actor_id"] == users["admin"].id
