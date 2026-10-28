from fastapi import APIRouter, Depends
from sqlalchemy import case
from sqlalchemy.orm import Session

from ...db.models import Item, User
from ...db.serializers import item_dict
from ...modules.items.service import review_item
from ..deps import admin_required, get_db
from ..schemas import ReviewRequest

router = APIRouter()


@router.get("/admin/items")
def admin_items(user=Depends(admin_required), db: Session = Depends(get_db)):
    pending_first = case((Item.pub_status == "PENDING", 0), else_=1)
    rows = (
        db.query(Item, User.name)
        .join(User, User.id == Item.owner_id)
        .order_by(pending_first, Item.id.desc())
        .all()
    )
    return {"items": [item_dict(i, owner_name=n) for i, n in rows]}


@router.post("/items/{item_id}/review")
def review_item_route(item_id: int, body: ReviewRequest, user=Depends(admin_required), db: Session = Depends(get_db)):
    review_item(db, user.id, item_id, body.decision)
    return {"message": "审核已保存", "reload": True}
