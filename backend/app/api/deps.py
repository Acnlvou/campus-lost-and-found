from fastapi import Depends, Request
from sqlalchemy.orm import Session

from ..core.errors import BusinessError
from ..db.models import User
from ..db.session import get_db


def current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    return db.get(User, int(user_id))


def login_required(user=Depends(current_user)):
    if user is None:
        raise BusinessError("请先登录。", 401)
    return user


def admin_required(user=Depends(login_required)):
    if user.role != "admin":
        raise BusinessError("需要管理员权限。", 403)
    return user
