"""登录鉴权服务的测试（覆盖 app/modules/auth/service.py）。"""

import pytest

from app.core.errors import BusinessError
from app.modules.auth.service import authenticate


class TestAuthenticate:
    def test_returns_user_for_correct_credentials(self, db, users):
        user = authenticate(db, "alice", "Campus123!")
        assert user.id == users["alice"].id
        assert user.username == "alice"
        assert user.role == "user"

    def test_admin_can_authenticate(self, db, users):
        assert authenticate(db, "admin", "Campus123!").role == "admin"

    def test_wrong_password_raises_401(self, db, users):
        with pytest.raises(BusinessError) as exc_info:
            authenticate(db, "alice", "campus123!")
        assert exc_info.value.status == 401
        assert exc_info.value.message == "账号或密码错误。"

    def test_unknown_username_raises_401(self, db, users):
        with pytest.raises(BusinessError) as exc_info:
            authenticate(db, "nobody", "Campus123!")
        assert exc_info.value.status == 401
        assert exc_info.value.message == "账号或密码错误。"

    def test_error_message_does_not_reveal_which_field_is_wrong(self, db, users):
        with pytest.raises(BusinessError) as unknown:
            authenticate(db, "nobody", "Campus123!")
        with pytest.raises(BusinessError) as wrong_password:
            authenticate(db, "alice", "wrong")
        assert unknown.value.message == wrong_password.value.message

    def test_username_is_case_sensitive(self, db, users):
        with pytest.raises(BusinessError):
            authenticate(db, "Alice", "Campus123!")

    def test_empty_database_rejects_everything(self, db):
        with pytest.raises(BusinessError):
            authenticate(db, "alice", "Campus123!")

    def test_empty_password_is_rejected(self, db, users):
        with pytest.raises(BusinessError):
            authenticate(db, "alice", "")
