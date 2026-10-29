from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...core.errors import BusinessError
from ...db.models import Audit, Claim, Item, User
from ...db.serializers import audit_dict, claim_dict, item_dict
from ...modules.items.service import list_locations, publish_item, query_items
from ..deps import current_user, get_db, login_required
from ..schemas import PublishRequest

router = APIRouter()

# 审核请求体模型
class ItemReviewBody(BaseModel):
    decision: str
    review_reason: str | None = None


@router.get("/items")
def list_items(
    q: str = Query(""),
    kind: str = Query(""),
    category: str = Query(""),
    location: str = Query(""),
    status: str = Query(""),
    db: Session = Depends(get_db),
):
    items = query_items(db, q=q, kind=kind, category=category, location=location, status=status)
    locations = list_locations(db)
    return {"items": items, "locations": locations}


@router.post("/items", status_code=201)
def publish(body: PublishRequest, user=Depends(login_required), db: Session = Depends(get_db)):
    item_id = publish_item(db, user.id, body.kind, body.title, body.category, body.location, body.event_time, body.description)
    # ✅ 修改这里，追加 notice=pending 参数
    return {"id": item_id, "redirect": f"/items/{item_id}?notice=pending"}


@router.post("/items/{item_id}/review")
def review_item(
    item_id: int,
    body: ItemReviewBody,
    user=Depends(login_required),
    db: Session = Depends(get_db)
):
    # 只有管理员才能审核
    if user.role != "admin":
        raise BusinessError("无审核权限", 403)

    item = db.query(Item).filter(Item.id == item_id).first()
    if item is None:
        raise BusinessError("物品不存在", 404)

    if body.decision == "approve":
        item.pub_status = "APPROVED"
        item.review_reason = None
    elif body.decision == "reject":
        item.pub_status = "REJECTED"
        item.review_reason = body.review_reason
    else:
        raise BusinessError("decision只能是 approve / reject", 400)

    db.commit()
    return {"ok": True}


@router.get("/items/{item_id}")
def detail(item_id: int, user=Depends(current_user), db: Session = Depends(get_db)):
    row = db.query(Item, User.name).join(User, User.id == Item.owner_id).filter(Item.id == item_id).first()
    if row is None:
        raise BusinessError("信息不存在。", 404)
    item, owner_name = row
    owner = user is not None and user.id == item.owner_id
    is_admin = user is not None and user.role == "admin"
    if item.pub_status != "APPROVED" and not owner and not is_admin:
        raise BusinessError("信息不存在。", 404)

    claims, history = [], []
    if user is not None:
        claims_query = (
            db.query(Claim, User.name)
            .join(User, User.id == Claim.applicant_id)
            .filter(Claim.item_id == item_id)
        )
        if not owner:
            claims_query = claims_query.filter(Claim.applicant_id == user.id)
        claims = [claim_dict(c, applicant_name=n) for c, n in claims_query.order_by(Claim.id.desc()).all()]
        if owner:
            history = [audit_dict(a) for a in db.query(Audit).filter(Audit.item_id == item_id).order_by(Audit.id.desc()).all()]

    return {
        "item": item_dict(item, owner_name),
        "owner": owner,
        "is_admin": is_admin,
        "claims": claims,
        "history": history,
    }


@router.get("/mine")
def mine(user=Depends(login_required), db: Session = Depends(get_db)):
    items = db.query(Item).filter(Item.owner_id == user.id).order_by(Item.id.desc()).all()
    return {"items": [item_dict(i) for i in items]}
