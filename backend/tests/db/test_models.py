"""数据模型约束的测试（覆盖 app/db/models.py 与 app/db/session.py 的 PRAGMA）。

数据库层是业务规则的最后一道防线：即使接口被绕过，非法状态也不该落库。
"""

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.audit import now
from app.db.models import Audit, Claim, Item, User


@pytest.fixture
def owner(db, users):
    return users["alice"]


@pytest.fixture
def other(db, users):
    return users["bob"]


def item_params(owner_id: int, **overrides) -> dict:
    params = {
        "owner_id": owner_id,
        "kind": "FOUND",
        "title": "图书馆捡到无线耳机",
        "category": "数码设备",
        "location": "图书馆",
        "event_time": "2026-10-09T12:00",
        "description": "白色充电盒，拾得于二楼自习区。",
        "created_at": now(),
    }
    params.update(overrides)
    return params


def claim_params(item_id: int, applicant_id: int, **overrides) -> dict:
    stamp = now()
    params = {
        "item_id": item_id,
        "applicant_id": applicant_id,
        "note": "耳机背面有蓝色贴纸。",
        "created_at": stamp,
        "updated_at": stamp,
    }
    params.update(overrides)
    return params


class TestDefaults:
    def test_new_item_defaults_to_open_and_pending(self, db, owner):
        # 不显式传 status / pub_status，验证模型默认值
        item = Item(
            owner_id=owner.id,
            kind="FOUND",
            title="图书馆捡到无线耳机",
            category="数码设备",
            location="图书馆",
            event_time="2026-10-09T12:00",
            description="白色充电盒，拾得于二楼自习区。",
            created_at=now(),
        )
        db.add(item)
        db.flush()
        assert item.status == "OPEN"
        assert item.pub_status == "PENDING"

    def test_new_user_defaults_to_normal_role(self, db, password_hash):
        user = User(username="dave", name="邓同学", password_hash=password_hash)
        db.add(user)
        db.flush()
        assert user.role == "user"

    def test_new_claim_defaults_to_pending(self, db, owner, other):
        item = Item(**item_params(owner.id))
        db.add(item)
        db.flush()
        claim = Claim(item_id=item.id, applicant_id=other.id, note="耳机背面有蓝色贴纸。", created_at=now(), updated_at=now())
        db.add(claim)
        db.flush()
        assert claim.status == "PENDING"


class TestCheckConstraints:
    @pytest.mark.parametrize("role", ["superuser", "ADMIN", "", "guest"])
    def test_user_role_must_be_user_or_admin(self, db, password_hash, role):
        db.add(User(username="x", name="测试", role=role, password_hash=password_hash))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    @pytest.mark.parametrize("kind", ["OTHER", "found", "", "LOST_ITEM"])
    def test_item_kind_must_be_lost_or_found(self, db, owner, kind):
        db.add(Item(**item_params(owner.id, kind=kind)))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    @pytest.mark.parametrize("status", ["PENDING", "CLOSED", "open"])
    def test_item_status_only_allows_open_or_claimed(self, db, owner, status):
        db.add(Item(**item_params(owner.id, status=status)))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    @pytest.mark.parametrize("pub_status", ["OPEN", "PUBLISHED", "approved"])
    def test_item_pub_status_is_restricted(self, db, owner, pub_status):
        db.add(Item(**item_params(owner.id, pub_status=pub_status)))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    @pytest.mark.parametrize("status", ["DONE", "approved", "WAITING"])
    def test_claim_status_is_restricted(self, db, owner, other, status):
        item = Item(**item_params(owner.id))
        db.add(item)
        db.commit()
        db.add(Claim(**claim_params(item.id, other.id, status=status)))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


class TestForeignKeys:
    def test_item_owner_must_exist(self, db):
        db.add(Item(**item_params(999_999)))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_claim_item_must_exist(self, db, other):
        db.add(Claim(**claim_params(999_999, other.id)))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_user_with_items_cannot_be_deleted(self, db, owner):
        db.add(Item(**item_params(owner.id)))
        db.commit()
        db.delete(owner)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


class TestClaimUniqueness:
    def test_same_user_cannot_claim_same_item_twice(self, db, owner, other):
        item = Item(**item_params(owner.id))
        db.add(item)
        db.commit()
        db.add(Claim(**claim_params(item.id, other.id)))
        db.commit()
        db.add(Claim(**claim_params(item.id, other.id, note="第二次申请应当被拒绝。")))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_two_users_may_both_claim(self, db, owner, other, users):
        item = Item(**item_params(owner.id))
        db.add(item)
        db.commit()
        db.add_all([Claim(**claim_params(item.id, other.id)), Claim(**claim_params(item.id, users["carol"].id))])
        db.commit()
        assert db.query(Claim).filter(Claim.item_id == item.id).count() == 2

    def test_only_one_approved_claim_per_item(self, db, owner, other, users):
        item = Item(**item_params(owner.id))
        db.add(item)
        db.commit()
        db.add(Claim(**claim_params(item.id, other.id, status="APPROVED")))
        db.commit()
        db.add(Claim(**claim_params(item.id, users["carol"].id, status="APPROVED")))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_multiple_rejected_claims_are_allowed(self, db, owner, other, users):
        item = Item(**item_params(owner.id))
        db.add(item)
        db.commit()
        db.add_all(
            [
                Claim(**claim_params(item.id, other.id, status="REJECTED")),
                Claim(**claim_params(item.id, users["carol"].id, status="REJECTED")),
            ]
        )
        db.commit()
        assert db.query(Claim).filter(Claim.status == "REJECTED").count() == 2


class TestAuditModel:
    def test_actor_may_be_null_for_system_actions(self, db):
        db.add(Audit(actor_id=None, action="SYSTEM_TICK", item_id=None, detail="定时任务", created_at=now()))
        db.commit()
        assert db.query(Audit).count() == 1

    def test_action_and_detail_are_required(self, db):
        db.add(Audit(actor_id=None, action=None, detail="缺失动作", created_at=now()))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
