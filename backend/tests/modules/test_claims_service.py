"""认领申请与审核服务的测试（覆盖 app/modules/claims/service.py）。

这里的规则最密集：公开状态、物品类型、本人认领（REQ-004）、重复申请、
仅发布者可审核、确认后自动关闭其他待处理申请。逐条验证。
"""

import pytest

from app.core.config import ALLOW_SELF_CLAIM
from app.core.errors import BusinessError
from app.db.models import Audit, Claim
from app.modules.claims.service import review_claim, submit_claim

NOTE = "耳机为白色，充电盒背面有蓝色贴纸。"


def assert_error(exc_info, status: int, message: str) -> None:
    assert exc_info.value.status == status
    assert exc_info.value.message == message


@pytest.fixture
def found_item(item_factory):
    return item_factory(kind="FOUND", pub_status="APPROVED", status="OPEN")


class TestSubmitClaim:
    def test_creates_pending_claim(self, db, found_item, users):
        claim_id = submit_claim(db, users["bob"].id, found_item.id, NOTE)
        claim = db.get(Claim, claim_id)
        assert claim.status == "PENDING"
        assert claim.applicant_id == users["bob"].id
        assert claim.item_id == found_item.id
        assert claim.note == NOTE

    def test_records_audit_entry(self, db, found_item, users):
        claim_id = submit_claim(db, users["bob"].id, found_item.id, NOTE)
        entry = db.query(Audit).filter(Audit.action == "CLAIM_SUBMIT").one()
        assert entry.item_id == found_item.id
        assert entry.actor_id == users["bob"].id
        assert entry.detail == f"申请 {claim_id}"

    def test_note_is_stripped(self, db, found_item, users):
        claim_id = submit_claim(db, users["bob"].id, found_item.id, "  耳机背面有蓝色贴纸。  ")
        assert db.get(Claim, claim_id).note == "耳机背面有蓝色贴纸。"

    def test_missing_item_raises_404(self, db, users):
        with pytest.raises(BusinessError) as exc_info:
            submit_claim(db, users["bob"].id, 999_999, NOTE)
        assert_error(exc_info, 404, "信息不存在。")

    @pytest.mark.parametrize("pub_status", ["PENDING", "REJECTED"])
    def test_unpublished_item_cannot_be_claimed(self, db, users, item_factory, pub_status):
        item = item_factory(pub_status=pub_status)
        with pytest.raises(BusinessError) as exc_info:
            submit_claim(db, users["bob"].id, item.id, NOTE)
        assert_error(exc_info, 409, "该信息尚未公开，不能认领。")

    def test_lost_item_cannot_be_claimed(self, db, users, item_factory):
        item = item_factory(kind="LOST")
        with pytest.raises(BusinessError) as exc_info:
            submit_claim(db, users["bob"].id, item.id, NOTE)
        assert_error(exc_info, 409, "该信息当前不接受认领。")

    def test_claimed_item_cannot_be_claimed_again(self, db, users, item_factory):
        item = item_factory(kind="FOUND", status="CLAIMED")
        with pytest.raises(BusinessError) as exc_info:
            submit_claim(db, users["bob"].id, item.id, NOTE)
        assert_error(exc_info, 409, "该信息当前不接受认领。")

    @pytest.mark.skipif(ALLOW_SELF_CLAIM, reason="当前配置允许本人认领")
    def test_owner_cannot_claim_own_item(self, db, found_item, users):
        # REQ-004：禁止用户认领自己发布的信息
        with pytest.raises(BusinessError) as exc_info:
            submit_claim(db, users["alice"].id, found_item.id, NOTE)
        assert_error(exc_info, 403, "不能认领本人发布的物品。")

    def test_duplicate_claim_is_rejected(self, db, found_item, users):
        submit_claim(db, users["bob"].id, found_item.id, NOTE)
        with pytest.raises(BusinessError) as exc_info:
            submit_claim(db, users["bob"].id, found_item.id, "再次申请同一物品。")
        assert_error(exc_info, 409, "你已经申请过此物品，请查看申请记录。")
        assert db.query(Claim).count() == 1

    def test_different_users_may_claim_the_same_item(self, db, found_item, users):
        submit_claim(db, users["bob"].id, found_item.id, NOTE)
        submit_claim(db, users["carol"].id, found_item.id, NOTE)
        assert db.query(Claim).filter(Claim.item_id == found_item.id).count() == 2

    def test_failed_claim_leaves_no_audit_trail(self, db, found_item, users):
        with pytest.raises(BusinessError):
            submit_claim(db, users["alice"].id, found_item.id, NOTE)
        assert db.query(Audit).count() == 0

    @pytest.mark.parametrize("note", ["1234", "说" * 501])
    def test_note_outside_length_range_is_rejected(self, db, found_item, users, note):
        with pytest.raises(BusinessError) as exc_info:
            submit_claim(db, users["bob"].id, found_item.id, note)
        assert_error(exc_info, 400, "认领说明须为 5 至 500 个字符。")

    def test_note_of_only_spaces_is_rejected(self, db, found_item, users):
        with pytest.raises(BusinessError) as exc_info:
            submit_claim(db, users["bob"].id, found_item.id, "     ")
        assert_error(exc_info, 400, "认领说明须为 5 至 500 个字符。")

    def test_non_string_note_is_rejected(self, db, found_item, users):
        with pytest.raises(BusinessError) as exc_info:
            submit_claim(db, users["bob"].id, found_item.id, None)
        assert_error(exc_info, 400, "认领说明须为 5 至 500 个字符。")

    @pytest.mark.parametrize("note", ["12345", "说" * 500])
    def test_note_boundaries_are_accepted(self, db, found_item, users, note):
        assert submit_claim(db, users["bob"].id, found_item.id, note)


class TestReviewClaimApprove:
    def test_approve_marks_item_claimed(self, db, found_item, users, claim_factory):
        claim = claim_factory(item_id=found_item.id, applicant_id=users["bob"].id)
        review_claim(db, users["alice"].id, claim.id, "approve")
        db.refresh(found_item)
        db.refresh(claim)
        assert found_item.status == "CLAIMED"
        assert claim.status == "APPROVED"

    def test_approve_closes_other_pending_claims(self, db, found_item, users, claim_factory):
        approved = claim_factory(item_id=found_item.id, applicant_id=users["bob"].id)
        other = claim_factory(item_id=found_item.id, applicant_id=users["carol"].id)
        review_claim(db, users["alice"].id, approved.id, "approve")
        db.refresh(other)
        assert other.status == "CLOSED"

    def test_approve_keeps_rejected_claims_untouched(self, db, found_item, users, claim_factory):
        approved = claim_factory(item_id=found_item.id, applicant_id=users["bob"].id)
        rejected = claim_factory(item_id=found_item.id, applicant_id=users["carol"].id, status="REJECTED")
        review_claim(db, users["alice"].id, approved.id, "approve")
        db.refresh(rejected)
        assert rejected.status == "REJECTED"

    def test_approve_records_audit_entry(self, db, found_item, users, claim_factory):
        claim = claim_factory(item_id=found_item.id, applicant_id=users["bob"].id)
        review_claim(db, users["alice"].id, claim.id, "approve")
        entry = db.query(Audit).filter(Audit.action == "CLAIM_APPROVE").one()
        assert entry.item_id == found_item.id
        assert entry.actor_id == users["alice"].id
        assert str(claim.id) in entry.detail

    def test_updated_at_moves_forward(self, db, found_item, users, claim_factory):
        claim = claim_factory(item_id=found_item.id, applicant_id=users["bob"].id, updated_at="2020-01-01T00:00:00+08:00")
        review_claim(db, users["alice"].id, claim.id, "approve")
        db.refresh(claim)
        assert claim.updated_at > "2020-01-01T00:00:00+08:00"


class TestReviewClaimReject:
    def test_reject_keeps_item_open(self, db, found_item, users, claim_factory):
        claim = claim_factory(item_id=found_item.id, applicant_id=users["bob"].id)
        review_claim(db, users["alice"].id, claim.id, "reject")
        db.refresh(found_item)
        db.refresh(claim)
        assert claim.status == "REJECTED"
        assert found_item.status == "OPEN"

    def test_reject_does_not_touch_other_claims(self, db, found_item, users, claim_factory):
        rejected = claim_factory(item_id=found_item.id, applicant_id=users["bob"].id)
        other = claim_factory(item_id=found_item.id, applicant_id=users["carol"].id)
        review_claim(db, users["alice"].id, rejected.id, "reject")
        db.refresh(other)
        assert other.status == "PENDING"

    def test_other_user_can_still_claim_after_rejection(self, db, found_item, users, claim_factory):
        claim = claim_factory(item_id=found_item.id, applicant_id=users["bob"].id)
        review_claim(db, users["alice"].id, claim.id, "reject")
        assert submit_claim(db, users["carol"].id, found_item.id, NOTE)


class TestReviewClaimPermissions:
    @pytest.mark.parametrize("actor", ["bob", "carol", "admin"])
    def test_only_owner_may_review(self, db, found_item, users, claim_factory, actor):
        claim = claim_factory(item_id=found_item.id, applicant_id=users["bob"].id)
        with pytest.raises(BusinessError) as exc_info:
            review_claim(db, users[actor].id, claim.id, "approve")
        assert_error(exc_info, 403, "只有发布者可以审核。")
        db.refresh(claim)
        assert claim.status == "PENDING"

    def test_missing_claim_raises_404(self, db, users):
        with pytest.raises(BusinessError) as exc_info:
            review_claim(db, users["alice"].id, 999_999, "approve")
        assert_error(exc_info, 404, "申请不存在。")

    @pytest.mark.parametrize("decision", ["APPROVE", "ok", ""])
    def test_invalid_decision_raises_400(self, db, found_item, users, claim_factory, decision):
        claim = claim_factory(item_id=found_item.id, applicant_id=users["bob"].id)
        with pytest.raises(BusinessError) as exc_info:
            review_claim(db, users["alice"].id, claim.id, decision)
        assert_error(exc_info, 400, "审核操作无效。")


class TestReviewClaimStateMachine:
    @pytest.mark.parametrize("status", ["APPROVED", "REJECTED", "CLOSED"])
    def test_non_pending_claim_cannot_be_reviewed(self, db, found_item, users, claim_factory, status):
        claim = claim_factory(item_id=found_item.id, applicant_id=users["bob"].id, status=status)
        with pytest.raises(BusinessError) as exc_info:
            review_claim(db, users["alice"].id, claim.id, "approve")
        assert_error(exc_info, 409, "申请或物品状态已变化，请刷新。")

    def test_pending_claim_on_claimed_item_cannot_be_approved(self, db, users, item_factory, claim_factory):
        item = item_factory(kind="FOUND", status="CLAIMED")
        claim = claim_factory(item_id=item.id, applicant_id=users["bob"].id)
        with pytest.raises(BusinessError) as exc_info:
            review_claim(db, users["alice"].id, claim.id, "approve")
        assert_error(exc_info, 409, "申请或物品状态已变化，请刷新。")

    def test_second_approval_cannot_overwrite_the_first(self, db, found_item, users, claim_factory):
        first = claim_factory(item_id=found_item.id, applicant_id=users["bob"].id)
        review_claim(db, users["alice"].id, first.id, "approve")
        second = claim_factory(item_id=found_item.id, applicant_id=users["carol"].id)
        with pytest.raises(BusinessError):
            review_claim(db, users["alice"].id, second.id, "approve")
        db.refresh(found_item)
        assert found_item.status == "CLAIMED"
        assert db.query(Claim).filter(Claim.status == "APPROVED").count() == 1
