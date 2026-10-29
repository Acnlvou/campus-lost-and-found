from datetime import datetime

from sqlalchemy.orm import Session

from .models import Audit


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def audit(db: Session, actor, action, item_id, detail) -> None:
    db.add(Audit(actor_id=actor, action=action, item_id=item_id, detail=detail, created_at=now()))
