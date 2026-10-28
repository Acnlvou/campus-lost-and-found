from sqlalchemy.orm import Session

from ..core.security import hash_password
from .audit import now
from .models import Item, User

_DEMO_USERS = (
    ("alice", "林同学", "user"),
    ("bob", "陈同学", "user"),
    ("carol", "周同学", "user"),
    ("admin", "管理员", "admin"),
)

_DEMO_ITEMS = (
    ("FOUND", "图书馆捡到无线耳机", "数码设备", "图书馆", "白色充电盒，拾得于二楼自习区。请在认领说明中描述型号和独特特征。"),
    ("FOUND", "教学楼拾得校园卡", "证件卡片", "第一教学楼", "蓝色卡套，信息已作隐私处理。请提供可核验的卡面特征。"),
    ("LOST", "寻找黑色保温杯", "生活用品", "体育馆", "晚间活动后遗失，杯盖带提手。拾到的同学可发布对应招领信息。"),
    ("FOUND", "食堂拾得笔记本", "学习用品", "第二食堂", "绿色封面，内页有课程笔记。请说明笔记内容或封面标记。"),
)


def seed(db: Session) -> None:
    if db.query(User).first() is not None:
        return
    for username, name, role in _DEMO_USERS:
        db.add(User(username=username, name=name, role=role, password_hash=hash_password("Campus123!")))
    db.flush()
    for kind, title, category, location, description in _DEMO_ITEMS:
        db.add(
            Item(
                owner_id=1,
                kind=kind,
                title=title,
                category=category,
                location=location,
                event_time="2026-10-09T12:00",
                description=description,
                status="OPEN",
                pub_status="APPROVED",
                created_at=now(),
            )
        )
    db.commit()
