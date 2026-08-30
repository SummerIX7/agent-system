"""
E2E 主链路测试（MOCK 模式，SQLite 内存库）

覆盖用户核心操作链路：
1. 健康检查与监控
2. 职业方向/领域列表
3. 用户注册 → 登录 → 获取当前用户
4. 学习者画像创建与查询
5. 知识图谱（文件驱动，非 DB）
6. 错误处理与边界情况
"""

from __future__ import annotations

import pytest


# ══════════════════════════════════════════════════════════════
# 1. 健康检查 & 监控端点（无需鉴权）
# ══════════════════════════════════════════════════════════════

class TestHealth:
    """分层健康检查端点测试"""

    @pytest.mark.anyio
    async def test_root(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert "version" in data

    @pytest.mark.anyio
    async def test_livez(self, client):
        """存活探针：无任何依赖检测，进程能响应即 200"""
        resp = await client.get("/livez")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @pytest.mark.anyio
    async def test_readyz(self, client):
        """就绪探针：Mock 模式 + SQLite 时全部 healthy/degraded，不 503"""
        resp = await client.get("/readyz")
        # SQLite 内存库可用、Mock 模式跳过密钥检查、Redis 降级为 degraded
        data = resp.json()
        assert data["status"] == "ok"
        checks = data["checks"]
        assert "mysql" in checks
        assert "redis" in checks
        assert "llm_config" in checks
        assert checks["llm_config"]["mode"] == "mock"

    @pytest.mark.anyio
    async def test_health(self, client):
        """兼容旧版 /health 端点"""
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["mock_mode"] is True

    @pytest.mark.anyio
    async def test_mock_status(self, client):
        resp = await client.get("/mock-status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mock_mode"] is True

    @pytest.mark.anyio
    async def test_metrics(self, client):
        """Prometheus 文本格式指标端点"""
        resp = await client.get("/metrics")
        assert resp.status_code == 200
        body = resp.text
        assert "process_uptime_seconds" in body
        assert "http_requests_total" in body
        assert "llm_calls_total" in body


# ══════════════════════════════════════════════════════════════
# 2. 职业方向 & 领域（无需鉴权）
# ══════════════════════════════════════════════════════════════

class TestCareerTracks:
    """职业方向配置端点测试"""

    @pytest.mark.anyio
    async def test_list_career_tracks(self, client):
        resp = await client.get("/api/career-tracks")
        assert resp.status_code == 200
        tracks = resp.json()
        assert isinstance(tracks, list)
        assert len(tracks) == 3
        codes = [t["code"] for t in tracks]
        assert "operator" in codes
        assert "setup_tech" in codes
        assert "programmer" in codes

    @pytest.mark.anyio
    async def test_list_domains(self, client):
        resp = await client.get("/api/domains")
        assert resp.status_code == 200
        domains = resp.json()
        assert isinstance(domains, list)
        assert len(domains) == 3


# ══════════════════════════════════════════════════════════════
# 3. 用户认证流程
# ══════════════════════════════════════════════════════════════

class TestAuth:
    """注册 → 登录 → 获取用户信息"""

    @staticmethod
    def _uniq(prefix: str = "e2e") -> str:
        import os as _os
        return f"{prefix}_{_os.urandom(4).hex()}"

    @pytest.mark.anyio
    async def test_register(self, client):
        u = self._uniq("e2e_reg")
        resp = await client.post("/api/auth/register", json={
            "username": u,
            "password": "secure123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["username"] == u

    @pytest.mark.anyio
    async def test_register_duplicate(self, client):
        """重复注册应返回 400"""
        u = self._uniq("e2e_dup")
        # 先注册
        await client.post("/api/auth/register", json={
            "username": u,
            "password": "pass123",
        })
        # 再次注册同名
        resp = await client.post("/api/auth/register", json={
            "username": u,
            "password": "pass456",
        })
        assert resp.status_code == 400
        assert "已存在" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_login_success(self, client):
        """先注册再登录"""
        u = self._uniq("e2e_login")
        await client.post("/api/auth/register", json={
            "username": u,
            "password": "mypassword",
        })
        resp = await client.post("/api/auth/login", json={
            "username": u,
            "password": "mypassword",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["username"] == u

    @pytest.mark.anyio
    async def test_login_wrong_password(self, client):
        """错误密码应返回 401"""
        u = self._uniq("e2e_wp")
        await client.post("/api/auth/register", json={
            "username": u,
            "password": "correct",
        })
        resp = await client.post("/api/auth/login", json={
            "username": u,
            "password": "wrong_password",
        })
        assert resp.status_code == 401

    @pytest.mark.anyio
    async def test_get_me(self, client):
        """登录后获取用户信息"""
        u = self._uniq("e2e_me")
        # 注册 + 登录
        resp = await client.post("/api/auth/register", json={
            "username": u,
            "password": "test123",
        })
        token = resp.json()["access_token"]

        resp2 = await client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp2.status_code == 200
        data = resp2.json()
        assert data["username"] == u
        assert data["role"] == "learner"

    @pytest.mark.anyio
    async def test_get_me_no_token(self, client):
        """无 token 访问应返回 401"""
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401

    @pytest.mark.anyio
    async def test_get_me_invalid_token(self, client):
        """无效 token 应返回 401"""
        resp = await client.get("/api/auth/me", headers={
            "Authorization": "Bearer invalid_token_here",
        })
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════
# 4. 学习者画像（需鉴权 + Mock LLM）
# ══════════════════════════════════════════════════════════════

class TestProfile:
    """学习者画像创建与查询"""

    @pytest.fixture
    async def token(self, client):
        """创建测试用户并返回 token（每次用唯一用户名避免冲突）"""
        import os as _os
        username = f"e2e_profile_{_os.urandom(4).hex()}"
        resp = await client.post("/api/auth/register", json={
            "username": username,
            "password": "test123",
        })
        return resp.json()["access_token"]

    @pytest.mark.anyio
    async def test_create_profile(self, client, token):
        """创建学习者画像（Mock 模式：LLM 返回模拟诊断结果）"""
        resp = await client.post("/api/profile/", json={
            "education_background": "本科",
            "major": "机械工程",
            "work_experience_years": 2,
            "career_track": "operator",
            "self_assessment": {"机床操作": "了解基础"},
            "learning_style": "practice",
            "goals": ["学习数控操作"],
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["career_track"] == "operator"
        assert "session_id" in data
        assert "knowledge_points" in data

    @pytest.mark.anyio
    async def test_get_my_profile(self, client, token):
        """查询自己的画像（需先创建）"""
        # 先创建
        await client.post("/api/profile/", json={
            "education_background": "本科",
            "major": "机械工程",
            "work_experience_years": 2,
            "career_track": "operator",
            "self_assessment": {"机床操作": "了解基础"},
            "learning_style": "practice",
            "goals": ["学习数控操作"],
        }, headers={"Authorization": f"Bearer {token}"})

        resp = await client.get("/api/profile/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["career_track"] == "operator"

    @pytest.mark.anyio
    async def test_get_profile_without_create(self, client, token):
        """未创建画像时查询应返回 404"""
        resp = await client.get("/api/profile/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_create_profile_no_auth(self, client):
        """未登录创建画像应返回 401"""
        resp = await client.post("/api/profile/", json={
            "education_background": "本科",
            "major": "机械工程",
            "work_experience_years": 2,
            "career_track": "operator",
            "self_assessment": {},
            "learning_style": "practice",
            "goals": [],
        })
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════
# 5. 知识图谱（文件驱动，无需鉴权）
# ══════════════════════════════════════════════════════════════

class TestKnowledgeGraph:
    """知识图谱端点（基于 markdown 文件，不依赖 DB）"""

    @pytest.mark.anyio
    async def test_get_knowledge_graph(self, client):
        resp = await client.get("/api/knowledge-graph")
        assert resp.status_code == 200
        data = resp.json()
        # build_tree() 直接返回树结构 {name, id, children, total_leaves}
        assert "name" in data
        assert "children" in data
        assert "total_leaves" in data

    @pytest.mark.anyio
    async def test_get_knowledge_graph_graph(self, client):
        resp = await client.get("/api/knowledge-graph/graph")
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "links" in data

    @pytest.mark.anyio
    async def test_get_knowledge_graph_files(self, client):
        resp = await client.get("/api/knowledge-graph/files")
        assert resp.status_code == 200
        data = resp.json()
        assert "files" in data


# ══════════════════════════════════════════════════════════════
# 6. 错误处理 & 边界情况
# ══════════════════════════════════════════════════════════════

class TestErrors:
    """错误处理与边界情况"""

    @pytest.mark.anyio
    async def test_404_not_found(self, client):
        resp = await client.get("/nonexistent/route")
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_422_validation_error(self, client):
        """缺少必填字段时应返回 422"""
        resp = await client.post("/api/auth/register", json={
            "username": "test",
            # 缺少 password
        })
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_x_request_id_header(self, client):
        """每个响应都应包含 X-Request-Id 头"""
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "x-request-id" in resp.headers
        assert len(resp.headers["x-request-id"]) > 0

    @pytest.mark.anyio
    async def test_cors_headers(self, client):
        """预检请求应返回 CORS 头"""
        resp = await client.options("/", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        })
        assert resp.status_code in (200, 405)
        if resp.status_code == 200:
            assert "access-control-allow-origin" in resp.headers


# ══════════════════════════════════════════════════════════════
# 7. authenticated_user fixture 验证
# ══════════════════════════════════════════════════════════════

class TestAuthFixture:
    """验证 conftest 提供的 authenticated_user fixture"""

    @pytest.mark.anyio
    async def test_fixture_returns_valid_token(self, client, authenticated_user):
        token, user_id, username = authenticated_user
        assert token
        assert user_id
        assert username.startswith("e2e_test_")

        # token 有效
        resp = await client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 200
        assert resp.json()["username"] == username
