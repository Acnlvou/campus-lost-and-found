from sqlalchemy.orm import Session

from ...core.errors import BusinessError
from ...core.security import verify_password
from ...db.models import User


def authenticate(db: Session, username, password):
    user = db.query(User).filter(User.username == username).first()
    if user is None or not verify_password(password, user.password_hash):
        raise BusinessError("账号或密码错误。", 401)
    return user
