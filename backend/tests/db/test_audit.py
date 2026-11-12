"""审计工具与时间戳的测试（覆盖 app/db/audit.py）。"""

from datetime import datetime

from app.db.audit import audit, now
from app.db.models import Audit


class TestNow:
    def test_returns_iso8601_with_timezone(self):
        stamp = now()
        parsed = datetime.fromisoformat(stamp)
        assert parsed.tzinfo is not None
        assert parsed.utcoffset() is not None

    def test_uses_second_precision(self):
        # 秒级精度便于 SQLite 字符串排序，也避免毫秒带来的比较歧义
        assert "." not in now()
        assert len(now()) >= 19

    def test_is_monotonic_enough_for_ordering(self):
        first = now()
        second = now()
        assert first <= second


class TestAudit:
    def test_appends_row_without_committing(self, db, users):
        audit(db, users["alice"].id, "ITEM_PUBLISH", None, "图书馆捡到无线耳机")
        # audit() 只把记录加入会话，由调用方统一提交，保证与业务写入同一事务
        assert [row.action for row in db.new if isinstance(row, Audit)] == ["ITEM_PUBLISH"]
        db.commit()
        assert db.query(Audit).count() == 1
        row = db.query(Audit).one()
        assert row.action == "ITEM_PUBLISH"
        assert row.detail == "图书馆捡到无线耳机"
        assert row.actor_id == users["alice"].id
        assert row.created_at

    def test_multiple_entries_keep_insertion_order(self, db, users):
        audit(db, users["alice"].id, "ITEM_PUBLISH", None, "第一条")
        audit(db, users["admin"].id, "ITEM_APPROVE", None, "第二条")
        db.commit()
        actions = [row.action for row in db.query(Audit).order_by(Audit.id).all()]
        assert actions == ["ITEM_PUBLISH", "ITEM_APPROVE"]

    def test_rollback_discards_pending_entry(self, db, users):
        audit(db, users["alice"].id, "ITEM_PUBLISH", None, "将被回滚")
        db.rollback()
        assert db.query(Audit).count() == 0
