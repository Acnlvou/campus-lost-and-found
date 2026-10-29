"""物品检索、发布与审核服务的测试（覆盖 app/modules/items/service.py）。

这一层承载信息检索的具体规则：只返回已公开信息、关键词转义、
筛选值白名单、审核状态机。接口层只做参数搬运，因此规则必须在这里锁死。
"""

from datetime import datetime

import pytest

from app.core.errors import BusinessError
from app.db.models import Audit, Item
from app.modules.items.service import list_locations, publish_item, query_items, review_item

PUBLISH_ARGS = {
    "kind": "FOUND",
    "title": "图书馆捡到无线耳机",
    "category": "数码设备",
    "location": "图书馆",
    "event_time": "2026-10-09T12:00",
    "description": "白色充电盒，拾得于二楼自习区。",
}


def assert_error(exc_info, status: int, message: str) -> None:
    assert exc_info.value.status == status
    assert exc_info.value.message == message


class TestQueryItemsVisibility:
    def test_only_approved_items_are_listed(self, db, item_factory):
        item_factory(title="已通过的招领", pub_status="APPROVED")
        item_factory(title="待审核的招领", pub_status="PENDING")
        item_factory(title="被拒绝的招领", pub_status="REJECTED")
        titles = [row["title"] for row in query_items(db)]
        assert titles == ["已通过的招领"]

    def test_empty_database_returns_empty_list(self, db):
        assert query_items(db) == []

    def test_results_are_newest_first(self, db, item_factory):
        first = item_factory(title="第一条")
        second = item_factory(title="第二条")
        third = item_factory(title="第三条")
        ids = [row["id"] for row in query_items(db)]
        assert ids == [third.id, second.id, first.id]

    def test_owner_name_is_joined(self, db, users, item_factory):
        item_factory(owner_id=users["alice"].id)
        assert query_items(db)[0]["owner_name"] == "林同学"


class TestKeywordSearch:
    @pytest.mark.parametrize("keyword", ["耳机", "图书馆", "无线"])
    def test_matches_title(self, db, item_factory, keyword):
        item_factory(title="图书馆捡到无线耳机")
        item_factory(title="食堂拾得笔记本")
        assert [row["title"] for row in query_items(db, q=keyword)] == ["图书馆捡到无线耳机"]

    def test_matches_description(self, db, item_factory):
        item_factory(title="图书馆捡到无线耳机", description="白色充电盒，拾得于二楼自习区。")
        item_factory(title="食堂拾得笔记本", description="绿色封面，内页有课程笔记。")
        assert [row["title"] for row in query_items(db, q="充电盒")] == ["图书馆捡到无线耳机"]

    def test_blank_keyword_is_ignored(self, db, item_factory):
        item_factory(title="图书馆捡到无线耳机")
        assert len(query_items(db, q="   ")) == 1

    def test_no_match_returns_empty(self, db, item_factory):
        item_factory()
        assert query_items(db, q="不存在的物品") == []

    def test_percent_sign_is_treated_literally(self, db, item_factory):
        item_factory(title="100%纯棉T恤", description="洗衣房拾到，纯棉材质。")
        item_factory(title="普通水杯", description="教室拾到。")
        rows = query_items(db, q="%")
        assert [row["title"] for row in rows] == ["100%纯棉T恤"]

    def test_underscore_is_treated_literally(self, db, item_factory):
        item_factory(title="A_B测试物品", description="下划线命名的物品。")
        item_factory(title="AXB测试物品", description="普通命名的物品。")
        rows = query_items(db, q="_")
        assert [row["title"] for row in rows] == ["A_B测试物品"]

    def test_backslash_is_treated_literally(self, db, item_factory):
        item_factory(title=r"文件夹\资料", description="带有反斜杠的描述。")
        assert len(query_items(db, q="\\")) == 1

    def test_keyword_at_max_length_is_allowed(self, db, item_factory):
        item_factory()
        assert query_items(db, q="关" * 100) == []

    def test_keyword_over_limit_is_rejected(self, db):
        with pytest.raises(BusinessError) as exc_info:
            query_items(db, q="关" * 101)
        assert_error(exc_info, 400, "关键词不能超过 100 个字符。")


class TestFilters:
    def test_filter_by_kind(self, db, item_factory):
        item_factory(kind="FOUND", title="招领信息")
        item_factory(kind="LOST", title="寻物信息")
        assert [row["title"] for row in query_items(db, kind="LOST")] == ["寻物信息"]

    def test_filter_by_category(self, db, item_factory):
        item_factory(category="数码设备", title="耳机")
        item_factory(category="证件卡片", title="校园卡")
        assert [row["title"] for row in query_items(db, category="证件卡片")] == ["校园卡"]

    def test_filter_by_status(self, db, item_factory):
        item_factory(status="OPEN", title="待认领")
        item_factory(status="CLAIMED", title="已认领")
        assert [row["title"] for row in query_items(db, status="CLAIMED")] == ["已认领"]

    def test_filter_by_location_is_exact_match(self, db, item_factory):
        item_factory(location="图书馆", title="图书馆里的物品")
        item_factory(location="图书馆二楼", title="二楼自习区的物品")
        assert [row["title"] for row in query_items(db, location="图书馆")] == ["图书馆里的物品"]

    def test_filters_are_combined(self, db, item_factory):
        item_factory(kind="FOUND", category="数码设备", location="图书馆", title="目标物品")
        item_factory(kind="LOST", category="数码设备", location="图书馆", title="类型不符")
        item_factory(kind="FOUND", category="证件卡片", location="图书馆", title="类别不符")
        rows = query_items(db, kind="FOUND", category="数码设备", location="图书馆")
        assert [row["title"] for row in rows] == ["目标物品"]

    def test_empty_filter_values_are_ignored(self, db, item_factory):
        item_factory()
        assert len(query_items(db, kind="", category="", location="", status="")) == 1

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("kind", "FOUND2"),
            ("kind", "found"),
            ("category", "电子产品"),
            ("status", "PENDING"),
            ("status", "open"),
        ],
    )
    def test_invalid_filter_value_is_rejected(self, db, field, value):
        with pytest.raises(BusinessError) as exc_info:
            query_items(db, **{field: value})
        assert_error(exc_info, 400, "筛选条件无效。")

    def test_location_at_max_length_is_allowed(self, db, item_factory):
        item_factory()
        assert query_items(db, location="图" * 60) == []

    def test_location_over_limit_is_rejected(self, db):
        with pytest.raises(BusinessError) as exc_info:
            query_items(db, location="图" * 61)
        assert_error(exc_info, 400, "地点不能超过 60 个字符。")


class TestListLocations:
    def test_returns_distinct_sorted_locations(self, db, item_factory):
        item_factory(location="图书馆")
        item_factory(location="食堂")
        item_factory(location="图书馆")
        assert list_locations(db) == sorted({"图书馆", "食堂"})

    def test_includes_locations_of_unpublished_items(self, db, item_factory):
        # 当前实现按全表取值：筛选下拉框可选到尚无公开物品的地点
        item_factory(location="体育馆", pub_status="PENDING")
        assert list_locations(db) == ["体育馆"]

    def test_empty_database_returns_empty_list(self, db):
        assert list_locations(db) == []


class TestPublishItem:
    def test_creates_pending_open_item(self, db, users):
        item_id = publish_item(db, users["alice"].id, **PUBLISH_ARGS)
        item = db.get(Item, item_id)
        assert item.pub_status == "PENDING"
        assert item.status == "OPEN"
        assert item.owner_id == users["alice"].id
        assert item.review_reason is None

    def test_records_an_audit_entry(self, db, users):
        item_id = publish_item(db, users["alice"].id, **PUBLISH_ARGS)
        entry = db.query(Audit).filter(Audit.action == "ITEM_PUBLISH").one()
        assert entry.item_id == item_id
        assert entry.actor_id == users["alice"].id
        assert entry.detail == PUBLISH_ARGS["title"]

    def test_created_at_is_iso_timestamp(self, db, users):
        item = db.get(Item, publish_item(db, users["alice"].id, **PUBLISH_ARGS))
        assert datetime.fromisoformat(item.created_at).tzinfo is not None

    def test_published_item_is_invisible_until_approved(self, db, users):
        publish_item(db, users["alice"].id, **PUBLISH_ARGS)
        assert query_items(db) == []

    def test_supports_lost_items(self, db, users):
        item_id = publish_item(db, users["alice"].id, **{**PUBLISH_ARGS, "kind": "LOST"})
        assert db.get(Item, item_id).kind == "LOST"

    def test_each_publish_creates_a_separate_record(self, db, users):
        first = publish_item(db, users["alice"].id, **PUBLISH_ARGS)
        second = publish_item(db, users["alice"].id, **{**PUBLISH_ARGS, "title": "教学楼捡到校园卡"})
        assert first != second
        assert db.query(Item).count() == 2


class TestReviewItem:
    def test_approve_publishes_the_item(self, db, users, item_factory):
        item = item_factory(pub_status="PENDING")
        review_item(db, users["admin"].id, item.id, "approve")
        db.refresh(item)
        assert item.pub_status == "APPROVED"
        assert [row["id"] for row in query_items(db)] == [item.id]

    def test_reject_hides_the_item(self, db, users, item_factory):
        item = item_factory(pub_status="PENDING")
        review_item(db, users["admin"].id, item.id, "reject")
        db.refresh(item)
        assert item.pub_status == "REJECTED"
        assert query_items(db) == []

    @pytest.mark.parametrize(("decision", "action"), [("approve", "ITEM_APPROVE"), ("reject", "ITEM_REJECT")])
    def test_audit_action_names(self, db, users, item_factory, decision, action):
        item = item_factory(pub_status="PENDING")
        review_item(db, users["admin"].id, item.id, decision)
        entry = db.query(Audit).filter(Audit.action == action).one()
        assert entry.item_id == item.id
        assert entry.actor_id == users["admin"].id

    def test_missing_item_raises_404(self, db, users):
        with pytest.raises(BusinessError) as exc_info:
            review_item(db, users["admin"].id, 999_999, "approve")
        assert_error(exc_info, 404, "信息不存在。")

    @pytest.mark.parametrize("decision", ["APPROVE", "ok", "", None])
    def test_invalid_decision_raises_400(self, db, users, item_factory, decision):
        item = item_factory(pub_status="PENDING")
        with pytest.raises(BusinessError) as exc_info:
            review_item(db, users["admin"].id, item.id, decision)
        assert_error(exc_info, 400, "审核操作无效。")

    @pytest.mark.parametrize("current", ["APPROVED", "REJECTED"])
    def test_already_reviewed_item_raises_409(self, db, users, item_factory, current):
        item = item_factory(pub_status=current)
        with pytest.raises(BusinessError) as exc_info:
            review_item(db, users["admin"].id, item.id, "approve")
        assert_error(exc_info, 409, "该信息已审核，请刷新。")

    def test_failed_review_keeps_previous_state(self, db, users, item_factory):
        item = item_factory(pub_status="APPROVED")
        with pytest.raises(BusinessError):
            review_item(db, users["admin"].id, item.id, "reject")
        db.refresh(item)
        assert item.pub_status == "APPROVED"
        assert db.query(Audit).count() == 0

    def test_unknown_id_raises_404(self, db, users, item_factory):
        item_factory(pub_status="PENDING")
        with pytest.raises(BusinessError) as exc_info:
            review_item(db, users["admin"].id, 0, "approve")
        assert_error(exc_info, 404, "信息不存在。")
