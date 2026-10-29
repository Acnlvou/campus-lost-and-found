"""种子数据的测试（覆盖 app/db/seed.py）。

种子数据是演示和联调的基础，必须可重复执行且不产生重复记录。
"""

from app.core.security import verify_password
from app.db.models import Item, User
from app.db.seed import _DEMO_ITEMS, _DEMO_USERS, seed


class TestSeedUsers:
    def test_creates_all_demo_accounts(self, db):
        seed(db)
        users = {user.username: user for user in db.query(User).all()}
        assert set(users) == {username for username, _, _ in _DEMO_USERS}
        assert users["admin"].role == "admin"
        assert all(users[name].role == "user" for name, _, role in _DEMO_USERS if role == "user")

    def test_demo_password_is_usable(self, db):
        seed(db)
        alice = db.query(User).filter(User.username == "alice").one()
        assert verify_password("Campus123!", alice.password_hash)
        assert not verify_password("wrong-password", alice.password_hash)

    def test_display_names_are_chinese(self, db):
        seed(db)
        names = {user.username: user.name for user in db.query(User).all()}
        assert names["alice"] == "林同学"
        assert names["admin"] == "管理员"


class TestSeedItems:
    def test_creates_published_demo_items(self, db):
        seed(db)
        items = db.query(Item).all()
        assert len(items) == len(_DEMO_ITEMS)
        assert all(item.pub_status == "APPROVED" for item in items)
        assert all(item.status == "OPEN" for item in items)

    def test_items_belong_to_alice(self, db):
        seed(db)
        alice = db.query(User).filter(User.username == "alice").one()
        assert {item.owner_id for item in db.query(Item).all()} == {alice.id}

    def test_covers_both_kinds_and_valid_categories(self, db):
        from app.core.config import CATEGORIES

        seed(db)
        items = db.query(Item).all()
        assert {item.kind for item in items} == {"FOUND", "LOST"}
        assert all(item.category in CATEGORIES for item in items)


class TestSeedIdempotency:
    def test_second_run_does_not_duplicate(self, db):
        seed(db)
        seed(db)
        assert db.query(User).count() == len(_DEMO_USERS)
        assert db.query(Item).count() == len(_DEMO_ITEMS)

    def test_does_nothing_when_users_already_exist(self, db, users):
        before = db.query(User).count()
        seed(db)
        assert db.query(User).count() == before
        assert db.query(Item).count() == 0
