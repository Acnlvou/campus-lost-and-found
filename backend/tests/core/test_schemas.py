"""请求模型字段校验的单元测试（覆盖 app/api/schemas.py）。

这些用例直接实例化 Pydantic 模型，不经过 HTTP，聚焦"字段约束"本身；
字段长度、枚举取值、时间格式的边界都在这里锁死。
"""

import pytest
from pydantic import ValidationError

from app.api.schemas import ClaimRequest, LoginRequest, PublishRequest, ReviewRequest
from app.core.config import CATEGORIES

VALID_PUBLISH = {
    "kind": "FOUND",
    "title": "图书馆捡到无线耳机",
    "category": "数码设备",
    "location": "图书馆二楼",
    "event_time": "2026-10-09T12:00",
    "description": "白色充电盒，拾得于二楼自习区。",
}


def publish_payload(**overrides) -> dict:
    payload = dict(VALID_PUBLISH)
    payload.update(overrides)
    return payload


def first_error_message(exc_info) -> str:
    return exc_info.value.errors()[0]["msg"]


class TestLoginRequest:
    def test_accepts_normal_credentials(self):
        body = LoginRequest(username="alice", password="Campus123!")
        assert body.username == "alice"
        assert body.password == "Campus123!"

    @pytest.mark.parametrize(
        "payload",
        [
            {"username": "", "password": "Campus123!"},
            {"username": "a" * 81, "password": "Campus123!"},
            {"username": "alice", "password": ""},
            {"username": "alice", "password": "p" * 129},
            {"username": "alice"},
            {"password": "Campus123!"},
        ],
    )
    def test_rejects_boundary_violations(self, payload):
        with pytest.raises(ValidationError):
            LoginRequest(**payload)

    def test_accepts_maximum_lengths(self):
        body = LoginRequest(username="u" * 80, password="p" * 128)
        assert len(body.username) == 80
        assert len(body.password) == 128


class TestPublishRequest:
    def test_accepts_valid_payload(self):
        body = PublishRequest(**VALID_PUBLISH)
        assert body.kind == "FOUND"
        assert body.category == "数码设备"

    def test_strips_surrounding_whitespace(self):
        body = PublishRequest(
            **publish_payload(title="  无线耳机  ", location="  图书馆  ", description="  白色充电盒，拾得于二楼。  ")
        )
        assert body.title == "无线耳机"
        assert body.location == "图书馆"
        assert body.description == "白色充电盒，拾得于二楼。"

    @pytest.mark.parametrize("kind", ["FOUND", "LOST"])
    def test_accepts_both_kinds(self, kind):
        assert PublishRequest(**publish_payload(kind=kind)).kind == kind

    @pytest.mark.parametrize("kind", ["found", "LOST ", "OTHER", "", "招领"])
    def test_rejects_invalid_kind(self, kind):
        with pytest.raises(ValidationError):
            PublishRequest(**publish_payload(kind=kind))

    @pytest.mark.parametrize("category", CATEGORIES)
    def test_accepts_every_configured_category(self, category):
        assert PublishRequest(**publish_payload(category=category)).category == category

    @pytest.mark.parametrize("category", ["数码", "电子产品", "", "其他物品"])
    def test_rejects_unknown_category(self, category):
        with pytest.raises(ValidationError):
            PublishRequest(**publish_payload(category=category))

    @pytest.mark.parametrize("title", ["耳", "耳" * 61, "  耳  "])
    def test_rejects_title_outside_2_to_60(self, title):
        with pytest.raises(ValidationError):
            PublishRequest(**publish_payload(title=title))

    @pytest.mark.parametrize("title", ["耳机", "耳" * 60])
    def test_accepts_title_boundaries(self, title):
        assert PublishRequest(**publish_payload(title=title)).title == title

    @pytest.mark.parametrize("location", ["图", "图" * 61])
    def test_rejects_location_outside_2_to_60(self, location):
        with pytest.raises(ValidationError):
            PublishRequest(**publish_payload(location=location))

    @pytest.mark.parametrize("location", ["图书馆", "图" * 60])
    def test_accepts_location_boundaries(self, location):
        assert PublishRequest(**publish_payload(location=location)).location == location

    @pytest.mark.parametrize("description", ["短文本", "文" * 1001])
    def test_rejects_description_outside_5_to_1000(self, description):
        with pytest.raises(ValidationError):
            PublishRequest(**publish_payload(description=description))

    @pytest.mark.parametrize("description", ["五个字符啊", "文" * 1000])
    def test_accepts_description_boundaries(self, description):
        assert PublishRequest(**publish_payload(description=description)).description == description

    @pytest.mark.parametrize(
        "event_time",
        ["2026-10-09 12:00", "2026-10-09T12:00:00", "2026/10/09T12:00", "", "2026-10-09"],
    )
    def test_rejects_bad_event_time_shape(self, event_time):
        with pytest.raises(ValidationError):
            PublishRequest(**publish_payload(event_time=event_time))

    @pytest.mark.parametrize("event_time", ["2026-13-01T12:00", "2026-02-30T08:30", "2026-10-09T25:00"])
    def test_rejects_impossible_calendar_values(self, event_time):
        with pytest.raises(ValidationError):
            PublishRequest(**publish_payload(event_time=event_time))

    def test_accepts_leap_day(self):
        assert PublishRequest(**publish_payload(event_time="2028-02-29T23:59")).event_time == "2028-02-29T23:59"

    def test_title_error_message_is_human_readable(self):
        with pytest.raises(ValidationError) as exc_info:
            PublishRequest(**publish_payload(title="耳"))
        assert first_error_message(exc_info) == "Value error, title 字段须为 2 至 60 个字符。"


class TestClaimRequest:
    @pytest.mark.parametrize("note", ["12345", "说" * 500])
    def test_accepts_note_boundaries(self, note):
        assert ClaimRequest(note=note).note == note

    @pytest.mark.parametrize("note", ["1234", "说" * 501, "   1234   "])
    def test_rejects_note_outside_5_to_500(self, note):
        with pytest.raises(ValidationError):
            ClaimRequest(note=note)

    def test_strips_note(self):
        assert ClaimRequest(note="  耳机背面有蓝色贴纸  ").note == "耳机背面有蓝色贴纸"


class TestReviewRequest:
    @pytest.mark.parametrize("decision", ["approve", "reject"])
    def test_accepts_supported_decisions(self, decision):
        assert ReviewRequest(decision=decision).decision == decision

    @pytest.mark.parametrize("decision", ["APPROVE", "ok", "", "通过"])
    def test_rejects_unsupported_decisions(self, decision):
        with pytest.raises(ValidationError):
            ReviewRequest(decision=decision)
