"""
Redis 存储层测试
验证会话生命周期、WebSocket 消息队列、频率限制
"""
import pytest
from unittest.mock import patch, MagicMock

from app.core.store import (
    get_session, update_session, add_resource,
    add_feedback, add_agent_log, get_all_sessions,
    add_conversation_message, get_conversation_history,
    push_ws_message, pop_ws_messages,
    check_rate_limit, check_redis_health,
    redis_is_available,
)


@pytest.fixture(autouse=True)
def _clean_redis_test_keys():
    """Redis 在线时清理本模块测试 key：数据会跨测试运行残留（内存降级模式无此问题）。"""
    if redis_is_available():
        from app.core.store._client import _get_redis
        r = _get_redis()
        for pattern in ("session:test_*", "ws:test_*", "ratelimit:test*"):
            keys = list(r.scan_iter(pattern))
            if keys:
                r.delete(*keys)
    yield


class TestSessionLifecycle:
    """会话生命周期测试"""

    def test_create_session(self):
        """测试创建新会话"""
        session = get_session("test_user_001")

        assert session["session_id"] == "test_user_001"
        assert session["learner_id"] == ""
        assert session["profile"] == {}
        assert session["resources"] == []
        assert session["feedback"] == []
        assert session["agent_logs"] == []
        assert "created_at" in session

    def test_update_session(self):
        """测试更新会话数据"""
        get_session("test_user_002")
        update_session("test_user_002", {
            "learner_id": "learner_1",
            "profile": {"level": "beginner", "domain": "cnc"},
        })

        session = get_session("test_user_002")
        assert session["learner_id"] == "learner_1"
        assert session["profile"]["level"] == "beginner"

    def test_add_resource(self):
        """测试添加资源"""
        get_session("test_user_003")
        add_resource("test_user_003", {"type": "lecture", "title": "G代码入门"})
        add_resource("test_user_003", {"type": "guide", "title": "数控车床操作"})

        session = get_session("test_user_003")
        assert len(session["resources"]) == 2
        assert session["resources"][0]["type"] == "lecture"
        assert session["resources"][1]["type"] == "guide"
        assert "created_at" in session["resources"][0]

    def test_add_feedback(self):
        """测试添加反馈"""
        get_session("test_user_004")
        add_feedback("test_user_004", {"question_id": "q1", "is_correct": True})
        add_feedback("test_user_004", {"question_id": "q2", "is_correct": False})

        session = get_session("test_user_004")
        assert len(session["feedback"]) == 2
        assert session["feedback"][0]["is_correct"] is True
        assert session["feedback"][1]["is_correct"] is False

    def test_add_agent_log(self):
        """测试添加 Agent 日志"""
        get_session("test_user_005")
        add_agent_log("test_user_005", {"agent": "diagnosis", "status": "completed"})
        add_agent_log("test_user_005", {"agent": "generation", "status": "running"})

        session = get_session("test_user_005")
        assert len(session["agent_logs"]) == 2
        assert session["agent_logs"][0]["agent"] == "diagnosis"
        assert "timestamp" in session["agent_logs"][0]

    def test_conversation_history_append_and_truncate(self):
        """对话记忆：追加有序、超长截断最旧、limit 生效"""
        sid = "test_conv_001"
        get_session(sid)
        for i in range(25):
            role = "learner" if i % 2 == 0 else "agent"
            add_conversation_message(sid, role, f"消息-{i}")

        history = get_conversation_history(sid)
        assert len(history) == 20  # CONVERSATION_HISTORY_MAX
        assert history[0]["content"] == "消息-5"  # 最旧的 5 条已被截断
        assert history[-1]["content"] == "消息-24"
        assert history[-1]["role"] == "learner"
        assert "ts" in history[0]

        recent = get_conversation_history(sid, limit=3)
        assert [m["content"] for m in recent] == ["消息-22", "消息-23", "消息-24"]

    def test_conversation_history_empty_session(self):
        """无对话记录的会话返回空列表而非报错"""
        assert get_conversation_history("test_conv_none") == []

    def test_get_all_sessions(self):
        """测试获取所有会话"""
        get_session("test_user_006")
        get_session("test_user_007")

        sessions = get_all_sessions()
        session_ids = [s["session_id"] for s in sessions]

        assert "test_user_006" in session_ids
        assert "test_user_007" in session_ids


class TestWebSocketQueue:
    """WebSocket 消息队列测试"""

    def test_push_and_pop_messages(self):
        """测试推送和取消息"""
        push_ws_message("test_user_008", {"type": "status", "msg": "Agent 开始诊断"})
        push_ws_message("test_user_008", {"type": "status", "msg": "诊断完成"})
        push_ws_message("test_user_008", {"type": "progress", "value": 100})

        messages = pop_ws_messages("test_user_008")
        assert len(messages) == 3
        assert messages[0]["msg"] == "Agent 开始诊断"
        assert messages[1]["msg"] == "诊断完成"
        assert messages[2]["value"] == 100

    def test_pop_clears_queue(self):
        """测试取消息后队列清空"""
        push_ws_message("test_user_009", {"type": "status", "msg": "test"})
        pop_ws_messages("test_user_009")

        # 再次 pop 应为空
        messages = pop_ws_messages("test_user_009")
        assert len(messages) == 0

    def test_pop_empty_queue(self):
        """测试从空队列取消息"""
        messages = pop_ws_messages("nonexistent_user")
        assert len(messages) == 0


class TestRateLimit:
    """频率限制测试"""

    def test_rate_limit_allows_within_limit(self):
        """测试限制内允许通过"""
        key = "test:rate_limit_1"

        # 连续请求 max_requests 次应该通过
        for i in range(30):
            assert check_rate_limit(key, max_requests=30) is True

    def test_rate_limit_blocks_over_limit(self):
        """测试超过限制被阻止"""
        key = "test:rate_limit_2"

        # 先用完配额
        for i in range(30):
            check_rate_limit(key, max_requests=30)

        # 第 31 次应该被阻止
        assert check_rate_limit(key, max_requests=30) is False

    def test_rate_limit_different_keys(self):
        """测试不同 key 独立计数"""
        # 两个不同的 key 应该独立计数
        for i in range(30):
            assert check_rate_limit("test:key_a", max_requests=30) is True
            assert check_rate_limit("test:key_b", max_requests=30) is True

        # 都达到限制后应该被阻止
        assert check_rate_limit("test:key_a", max_requests=30) is False
        assert check_rate_limit("test:key_b", max_requests=30) is False


class TestRedisHealth:
    """Redis 健康检查测试"""

    def test_check_redis_health(self):
        """测试 Redis 健康检查"""
        health = check_redis_health()

        assert "status" in health
        assert health["status"] in ("healthy", "degraded", "unhealthy")

        if health["status"] == "healthy":
            assert "backend" in health
            assert health["backend"] == "redis"
        elif health["status"] == "degraded":
            assert "backend" in health
            assert health["backend"] == "memory"

    def test_redis_is_available(self):
        """测试 Redis 可用性检查"""
        # 这个测试依赖于实际的 Redis 连接
        # 在没有 Redis 的环境中应该返回 False
        result = redis_is_available()
        assert isinstance(result, bool)


class TestSerialization:
    """序列化测试"""

    def test_serialize_complex_data(self):
        """测试复杂数据序列化"""
        session = get_session("test_user_010")
        update_session("test_user_010", {
            "profile": {
                "name": "测试用户",
                "knowledge_points": [
                    {"name": "G代码", "score": 85, "level": "intermediate"},
                    {"name": "切削参数", "score": 70, "level": "beginner"},
                ],
                "goals": ["学习数控编程", "掌握G代码"],
            },
        })

        # 重新获取，验证数据完整性
        session = get_session("test_user_010")
        assert session["profile"]["name"] == "测试用户"
        assert len(session["profile"]["knowledge_points"]) == 2
        assert session["profile"]["knowledge_points"][0]["score"] == 85
        assert len(session["profile"]["goals"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
