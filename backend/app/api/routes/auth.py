from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ...core.config import ALLOW_SELF_CLAIM, CATEGORIES, LABELS, VERSION
from ...core.security import new_csrf
from ...db.serializers import user_dict
from ...modules.auth.service import authenticate
from ..deps import current_user, get_db, login_required
from ..schemas import LoginRequest

router = APIRouter()


@router.post("/login")
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = authenticate(db, body.username.strip(), body.password)
    request.session.clear()
    request.session["user_id"] = user.id
    request.session["csrf"] = new_csrf()
    return {"message": "登录成功", "redirect": "/"}


@router.post("/logout")
def logout(request: Request, user=Depends(login_required)):
    request.session.clear()
    return {"redirect": "/"}


@router.get("/session")
def session_info(request: Request, user=Depends(current_user)):
    return {
        "user": user_dict(user) if user else None,
        "csrf": request.session.get("csrf", ""),
        "is_admin": user is not None and user.role == "admin",
        "version": VERSION,
        "allow_self": ALLOW_SELF_CLAIM,
        "categories": list(CATEGORIES),
        "labels": LABELS,
    }
