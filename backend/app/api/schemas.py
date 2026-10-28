from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from ..core.config import CATEGORIES


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=128)


class PublishRequest(BaseModel):
    kind: str
    title: str
    category: str
    location: str
    event_time: str
    description: str

    @field_validator("kind")
    @classmethod
    def check_kind(cls, v):
        if v not in ("FOUND", "LOST"):
            raise ValueError("信息类型或类别无效。")
        return v

    @field_validator("category")
    @classmethod
    def check_category(cls, v):
        if v not in CATEGORIES:
            raise ValueError("信息类型或类别无效。")
        return v

    @field_validator("title")
    @classmethod
    def check_title(cls, v):
        if not 2 <= len(v.strip()) <= 60:
            raise ValueError("title 字段须为 2 至 60 个字符。")
        return v.strip()

    @field_validator("location")
    @classmethod
    def check_location(cls, v):
        if not 2 <= len(v.strip()) <= 60:
            raise ValueError("location 字段须为 2 至 60 个字符。")
        return v.strip()

    @field_validator("description")
    @classmethod
    def check_description(cls, v):
        if not 5 <= len(v.strip()) <= 1000:
            raise ValueError("description 字段须为 5 至 1000 个字符。")
        return v.strip()

    @field_validator("event_time")
    @classmethod
    def check_event_time(cls, v):
        if len(v) != 16:
            raise ValueError("事件时间格式无效。")
        try:
            datetime.strptime(v, "%Y-%m-%dT%H:%M")
        except ValueError:
            raise ValueError("事件时间格式无效。")
        return v


class ClaimRequest(BaseModel):
    note: str = Field(min_length=5, max_length=500)

    @field_validator("note")
    @classmethod
    def check_note(cls, v):
        if not 5 <= len(v.strip()) <= 500:
            raise ValueError("认领说明须为 5 至 500 个字符。")
        return v.strip()


class ReviewRequest(BaseModel):
    decision: str

    @field_validator("decision")
    @classmethod
    def check_decision(cls, v):
        if v not in ("approve", "reject"):
            raise ValueError("审核操作无效。")
        return v
