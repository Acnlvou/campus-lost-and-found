"""健康检查接口的测试（覆盖 app/api/routes/health.py）。"""

from app.core.config import VERSION
from conftest import API


class TestHealthCheck:
    def test_returns_ok_and_version(self, client):
        response = client.get(f"{API}/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "version": VERSION}

    def test_is_reachable_without_login(self, client):
        # 健康检查用于部署探活，必须免登录
        assert client.get(f"{API}/health").status_code == 200

    def test_is_not_shadowed_by_spa_fallback(self, client):
        # main.py 末尾注册了 /{full_path:path} 兜底路由，确认它没有覆盖 /api 前缀
        assert client.get(f"{API}/health").headers["content-type"].startswith("application/json")
