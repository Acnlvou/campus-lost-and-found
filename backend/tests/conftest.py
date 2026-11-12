"""pytest 全局配置与公共夹具。

设计要点：

1. 测试使用独立的临时 SQLite 数据库，绝不读写 ``data/runtime`` 下的开发库；
   由于 ``app.core.config.settings`` 在模块导入时即读取环境变量，所有
   ``CAMPUS_*`` 变量必须在导入 ``app`` 之前设置。
2. 应用使用会话 Cookie + CSRF 双校验，写请求必须携带与 ``session["csrf"]``
   一致的 ``X-CSRF-Token``。``ApiClient`` 把这一步封装掉，测试里只关心业务断言。
3. 每个用例执行前后清空全部业务表，保证用例相互独立、可单独运行、顺序无关。
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# --- 必须在导入 app 之前完成环境隔离 -------------------------------------------------
_TMP_DIR = Path(tempfile.mkdtemp(prefix="campus-api-tests-"))
os.environ["CAMPUS_DATABASE_URL"] = "sqlite:///" + (_TMP_DIR / "test.sqlite").as_posix()
os.environ["CAMPUS_SEED"] = "false"
os.environ["CAMPUS_SECRET_KEY"] = "pytest-only-secret-key"
os.environ["CAMPUS_FRONTEND_ORIGINS"] = '["http://localhost:5173"]'

from fastapi.testclient import TestClient  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.audit import now  # noqa: E402
from app.db.models import Audit, Claim, Item, User  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402

# 与前端、README 保持一致的常量
API = "/api"
PASSWORD = "Campus123!"
DEMO_USERS = (
    ("alice", "林同学", "user"),
    ("bob", "陈同学", "user"),
    ("carol", "周同学", "user"),
    ("admin", "管理员", "admin"),
)


class ApiClient:
    """带会话 Cookie 与自动 CSRF 处理的测试客户端。"""

    def __init__(self) -> None:
        self._client = TestClient(app)
        self.csrf = ""

    # -- 底层 ---------------------------------------------------------------
    @property
    def raw(self) -> TestClient:
        """绕过 CSRF 自动化，用于验证中间件本身的行为。"""
        return self._client

    def _refresh_csrf(self) -> None:
        response = self._client.get(f"{API}/session")
        self.csrf = response.headers.get("X-CSRF-Token", "")

    def request(self, method: str, url: str, **kwargs):
        method = method.upper()
        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            if not self.csrf:
                self._refresh_csrf()
            headers = dict(kwargs.pop("headers", None) or {})
            headers.setdefault("X-CSRF-Token", self.csrf)
            response = self._client.request(method, url, headers=headers, **kwargs)
        else:
            response = self._client.request(method, url, **kwargs)
        token = response.headers.get("X-CSRF-Token")
        if token is not None:
            # 登录、登出会轮换或清空令牌，这里跟随服务端最新值
            self.csrf = token
        return response

    def get(self, url: str, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs):
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs):
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs):
        return self.request("DELETE", url, **kwargs)

    # -- 业务便捷方法 -------------------------------------------------------
    def login(self, username: str, password: str = PASSWORD):
        self._refresh_csrf()
        response = self.post(f"{API}/login", json={"username": username, "password": password})
        assert response.status_code == 200, response.text
        return response

    def logout(self):
        return self.post(f"{API}/logout")

    def me(self) -> dict:
        response = self.get(f"{API}/session")
        assert response.status_code == 200, response.text
        return response.json()


# --- 数据库隔离 ---------------------------------------------------------------------
def _truncate_tables() -> None:
    with SessionLocal() as session:
        # 先删子表，避免外键约束冲突
        session.query(Audit).delete()
        session.query(Claim).delete()
        session.query(Item).delete()
        session.query(User).delete()
        session.commit()


@pytest.fixture(scope="session", autouse=True)
def _database_ready():
    """确认测试库指向临时文件，并清理本次会话的残留数据。"""
    assert str(engine.url).startswith("sqlite:///"), "测试必须运行在 SQLite 上"
    assert "campus-api-tests-" in str(engine.url), "测试库未指向临时目录，可能污染开发数据"
    _truncate_tables()
    yield


@pytest.fixture(autouse=True)
def clean_database():
    """每个用例前后清空业务表，保证用例独立可重跑。"""
    _truncate_tables()
    yield
    _truncate_tables()


# --- 常用夹具 -----------------------------------------------------------------------
@pytest.fixture(scope="session")
def password_hash() -> str:
    """PBKDF2 迭代次数较高，整个测试会话只计算一次。"""
    return hash_password(PASSWORD)


@pytest.fixture
def db(clean_database):
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def users(db, password_hash) -> dict[str, User]:
    """创建 alice / bob / carol（普通用户）与 admin（管理员）。"""
    created: dict[str, User] = {}
    for username, name, role in DEMO_USERS:
        user = User(username=username, name=name, role=role, password_hash=password_hash)
        db.add(user)
        created[username] = user
    db.commit()
    for user in created.values():
        db.refresh(user)
    return created


@pytest.fixture
def client() -> ApiClient:
    """匿名客户端；需要登录时调用 ``client.login("alice")``。"""
    return ApiClient()


@pytest.fixture
def make_client(users):
    """需要同时模拟多个用户时使用，每次调用返回独立会话的客户端。

    依赖 ``users`` 以保证演示账号已就绪，避免用例忘记请求用户夹具而登录失败。
    """

    def _make(**kwargs) -> ApiClient:
        instance = ApiClient()
        username = kwargs.get("login")
        if username:
            instance.login(username, kwargs.get("password", PASSWORD))
        return instance

    return _make


@pytest.fixture
def item_factory(db, users):
    """按需创建物品，字段默认值取一个合法的招领信息。"""

    def _create(**overrides) -> Item:
        params = {
            "owner_id": users["alice"].id,
            "kind": "FOUND",
            "title": "图书馆捡到无线耳机",
            "category": "数码设备",
            "location": "图书馆",
            "event_time": "2026-10-09T12:00",
            "description": "白色充电盒，拾得于二楼自习区。",
            "status": "OPEN",
            "pub_status": "APPROVED",
            "created_at": now(),
            "review_reason": None,
        }
        params.update(overrides)
        item = Item(**params)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    return _create


@pytest.fixture
def claim_factory(db, users):
    """按需创建认领申请。"""

    def _create(**overrides) -> Claim:
        stamp = now()
        params = {
            "item_id": 1,
            "applicant_id": users["bob"].id,
            "note": "耳机为白色，充电盒背面有贴纸。",
            "status": "PENDING",
            "created_at": stamp,
            "updated_at": stamp,
        }
        params.update(overrides)
        claim = Claim(**params)
        db.add(claim)
        db.commit()
        db.refresh(claim)
        return claim

    return _create
