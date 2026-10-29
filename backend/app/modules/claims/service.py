from sqlalchemy.orm import Session

from ...core.config import ALLOW_SELF_CLAIM
from ...core.errors import BusinessError
from ...db.audit import audit, now
from ...db.models import Claim, Item


def submit_claim(db: Session, user_id, item_id, note):
    if not isinstance(note, str) or not 5 <= len(note.strip()) <= 500:
        raise BusinessError("认领说明须为 5 至 500 个字符。")
    try:
        item = db.get(Item, item_id)
        if item is None:
            raise BusinessError("信息不存在。", 404)
        if item.pub_status != "APPROVED":
            raise BusinessError("该信息尚未公开，不能认领。", 409)
        if item.kind != "FOUND" or item.status != "OPEN":
            raise BusinessError("该信息当前不接受认领。", 409)
        if not ALLOW_SELF_CLAIM and item.owner_id == user_id:
            raise BusinessError("不能认领本人发布的物品。", 403)
        if db.query(Claim.id).filter(Claim.item_id == item_id, Claim.applicant_id == user_id).first():
            raise BusinessError("你已经申请过此物品，请查看申请记录。", 409)
        stamp = now()
        claim = Claim(
            item_id=item_id,
            applicant_id=user_id,
            note=note.strip(),
            status="PENDING",
            created_at=stamp,
            updated_at=stamp,
        )
        db.add(claim)
        db.flush()
        audit(db, user_id, "CLAIM_SUBMIT", item_id, f"申请 {claim.id}")
        db.commit()
        return claim.id
    except Exception:
        db.rollback()
        raise


def review_claim(db: Session, user_id, claim_id, decision):
    if decision not in ("approve", "reject"):
        raise BusinessError("审核操作无效。")
    try:
        claim = db.get(Claim, claim_id)
        if claim is None:
            raise BusinessError("申请不存在。", 404)
        item = db.get(Item, claim.item_id)
        if item is None:
            raise BusinessError("申请不存在。", 404)
        if item.owner_id != user_id:
            raise BusinessError("只有发布者可以审核。", 403)
        if claim.status != "PENDING" or item.status != "OPEN":
            raise BusinessError("申请或物品状态已变化，请刷新。", 409)
        stamp = now()
        if decision == "approve":
            result = db.query(Item).filter(Item.id == claim.item_id, Item.status == "OPEN").update(
                {"status": "CLAIMED"}, synchronize_session=False
            )
            if result != 1:
                raise BusinessError("该物品已经完成认领。", 409)
            claim.status = "APPROVED"
            claim.updated_at = stamp
            db.query(Claim).filter(
                Claim.item_id == claim.item_id,
                Claim.id != claim_id,
                Claim.status == "PENDING",
            ).update({"status": "CLOSED", "updated_at": stamp}, synchronize_session=False)
        else:
            claim.status = "REJECTED"
            claim.updated_at = stamp
        audit(db, user_id, "CLAIM_" + decision.upper(), claim.item_id, f"申请 {claim_id}；其他待处理申请在确认后自动关闭")
        db.commit()
    except Exception:
        db.rollback()
        raise
