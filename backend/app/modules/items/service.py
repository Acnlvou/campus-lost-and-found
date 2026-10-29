from sqlalchemy.orm import Session

from ...core.config import CATEGORIES
from ...core.errors import BusinessError
from ...db.audit import audit, now
from ...db.models import Item, User
from ...db.serializers import item_dict


def query_items(db: Session, q="", kind="", category="", location="", status=""):
    query = db.query(Item, User.name).join(User, User.id == Item.owner_id).filter(Item.pub_status == "APPROVED")

    q = (q or "").strip()
    if len(q) > 100:
        raise BusinessError("关键词不能超过 100 个字符。")
    if q:
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = "%" + escaped + "%"
        query = query.filter(
            (Item.title.like(pattern, escape="\\")) | (Item.description.like(pattern, escape="\\"))
        )

    for field, value, allowed in (
        ("category", category, CATEGORIES),
        ("kind", kind, ("LOST", "FOUND")),
        ("status", status, ("OPEN", "CLAIMED")),
    ):
        if value:
            if value not in allowed:
                raise BusinessError("筛选条件无效。")
            query = query.filter(getattr(Item, field) == value)

    location = (location or "").strip()
    if len(location) > 60:
        raise BusinessError("地点不能超过 60 个字符。")
    if location:
        query = query.filter(Item.location == location)

    rows = query.order_by(Item.id.desc()).all()
    return [item_dict(item, owner_name) for item, owner_name in rows]


def list_locations(db: Session):
    rows = db.query(Item.location).distinct().order_by(Item.location).all()
    return [row[0] for row in rows]


def publish_item(db: Session, user_id, kind, title, category, location, event_time, description):
    item = Item(
        owner_id=user_id,
        kind=kind,
        title=title,
        category=category,
        location=location,
        event_time=event_time,
        description=description,
        status="OPEN",
        pub_status="PENDING",
        created_at=now(),
    )
    try:
        db.add(item)
        db.flush()
        audit(db, user_id, "ITEM_PUBLISH", item.id, title)
        db.commit()
        return item.id
    except Exception:
        db.rollback()
        raise


def review_item(db: Session, user_id, item_id, decision):
    if decision not in ("approve", "reject"):
        raise BusinessError("审核操作无效。")
    try:
        item = db.get(Item, item_id)
        if item is None:
            raise BusinessError("信息不存在。", 404)
        if item.pub_status != "PENDING":
            raise BusinessError("该信息已审核，请刷新。", 409)
        item.pub_status = "APPROVED" if decision == "approve" else "REJECTED"
        audit(db, user_id, "ITEM_" + decision.upper(), item_id, item.title)
        db.commit()
    except Exception:
        db.rollback()
        raise
