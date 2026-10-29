"""配置常量的单元测试（覆盖 app/core/config.py）。"""

from pathlib import Path

from app.core import config


class TestCategories:
    def test_are_unique_and_fixed_size(self):
        assert isinstance(config.CATEGORIES, tuple)
        assert len(config.CATEGORIES) == 5
        assert len(set(config.CATEGORIES)) == 5

    def test_match_frontend_contract(self):
        assert config.CATEGORIES == ("数码设备", "证件卡片", "学习用品", "生活用品", "其他")


class TestLabels:
    def test_cover_every_persisted_state(self):
        statuses = {"OPEN", "CLAIMED", "PENDING", "APPROVED", "REJECTED", "CLOSED"}
        kinds = {"LOST", "FOUND"}
        assert statuses | kinds <= set(config.LABELS)
        assert all(isinstance(value, str) and value for value in config.LABELS.values())


class TestSelfClaimPolicy:
    def test_self_claim_is_disabled(self):
        # REQ-004：禁止用户认领自己发布的招领信息
        assert config.ALLOW_SELF_CLAIM is False


class TestPaths:
    def test_database_defaults_into_backend_runtime_dir(self):
        assert config.DEFAULT_DATABASE_URL.startswith("sqlite:///")
        assert "/backend/data/runtime/" in config.DEFAULT_DATABASE_URL.replace("\\", "/")
        assert config.RUNTIME_DIR == config.BACKEND_DIR / "data" / "runtime"
        assert isinstance(config.ROOT_DIR, Path)
        assert config.ROOT_DIR == config.BACKEND_DIR.parent

    def test_runtime_dir_is_created_on_import(self):
        assert config.RUNTIME_DIR.is_dir()


class TestSettings:
    def test_test_environment_overrides_are_applied(self):
        # conftest 在导入前注入了隔离库，说明设置确实读取了环境变量
        assert "campus-api-tests-" in config.settings.database_url
        assert config.settings.seed is False
        assert config.settings.secret_key == "pytest-only-secret-key"

    def test_api_prefix_and_origins(self):
        assert config.settings.api_prefix == "/api"
        assert config.settings.frontend_origins == ["http://localhost:5173"]

    def test_version_string_is_present(self):
        assert config.VERSION.startswith("v")
