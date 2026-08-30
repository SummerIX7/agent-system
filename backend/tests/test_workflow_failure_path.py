"""工作流失败路径集成测试：审核不通过 → 注入反馈重新生成 → 超限降级。

用 MOCK 模式驱动完整 LangGraph（builder.py 装配版），把 corrective_review
替换为受控失败源，验证主工作流的重试与降级行为。覆盖此前测试盲区中
"review 未过 → retry → 降级" 的端到端分支。
"""
import os

# 必须在导入任何 app 模块前设置环境变量
os.environ["MOCK_MODE"] = "true"
os.environ["ENABLE_KNOWLEDGE_BASE"] = "false"

import pytest
from unittest.mock import patch

from app.core.config import get_settings
from app.mock.llm import MockLLM


@pytest.fixture(scope="module", autouse=True)
def force_mock_environment():
    """强制 MOCK 环境：无论单独运行本文件还是全量运行，都不触达真实 LLM。"""
    get_settings.cache_clear()
    import app.knowledge.embedder as embedder_mod
    embedder_mod.get_embeddings.cache_clear()
    settings = get_settings()
    assert settings.MOCK_MODE is True, "测试前提失败：MOCK_MODE 未生效"
    assert settings.ENABLE_KNOWLEDGE_BASE is False

    # 单例 Agent 可能在此前测试中已用真实 LLM 客户端构造，统一替换为 Mock
    from app.graph import workflow as wf
    for agent in (wf.diagnosis_agent, wf.path_planner, wf.generation_agent,
                  wf.question_generator, wf.review_agent):
        agent.llm = MockLLM()
    yield


def _learner_input() -> dict:
    return {
        "education": "本科",
        "major": "机械工程",
        "experience_years": 1,
        "skill_self_assessment": {"数控编程": "不了解"},
        "career_track": "operator",
    }


async def _fail_review(content: str, topic: str) -> dict:
    return {
        "passed": False, "score": 0.55,
        "issues": ["测试注入：事实性错误示例"],
        "suggestions": [],
        "final_content": content,
        "correction_applied": False,
    }


async def _pass_review(content: str, topic: str) -> dict:
    return {
        "passed": True, "score": 0.93,
        "issues": [],
        "suggestions": [],
        "final_content": f"{content}【已修正】",
        "correction_applied": True,
    }


@pytest.mark.asyncio
async def test_review_failure_retries_then_degrades(monkeypatch):
    """持续不通过 → 重试 3 轮（每轮注入上一轮反馈）→ 超限降级 + 质量提醒横幅"""
    from app.graph.nodes import review_agent
    from app.graph.workflow import run_workflow

    monkeypatch.setattr(review_agent, "corrective_review", _fail_review)

    result = await run_workflow(
        _learner_input(), topic="数控车床对刀", session_id="test-degrade-path",
    )

    # 重试计数达到上限
    assert result["retry_count"] == 3

    # 三轮审核日志，且均触发重新生成
    review_logs = [line for line in result["decision_log"] if "审核纠偏 第" in line]
    assert len(review_logs) == 3
    assert all("需重试" in line for line in review_logs)

    # 第 2、3 轮生成时注入了上一轮审核反馈
    injected = [line for line in result["decision_log"] if "注入上一轮反馈" in line]
    assert len(injected) == 2

    # 全部内容被标记降级
    review_results = result["review_results"]
    assert review_results, "应存在审核结果"
    assert all(r.get("degraded") is True for r in review_results.values())

    # 降级内容附带质量提醒横幅
    lecture = next(r for r in result["final_resources"]
                   if r.get("type") == "lecture" and r.get("stage") == 1)
    assert "质量提醒" in lecture["content"]

    # 降级资源保留未通过的审核标记
    assert lecture["review_passed"] is False


@pytest.mark.asyncio
async def test_review_failure_then_pass_completes_without_degrade(monkeypatch):
    """第 1 轮不通过、第 2 轮通过 → 只重试一次，正常完成且无降级横幅"""
    from app.graph.nodes import review_agent
    from app.graph.workflow import run_workflow

    calls = {"n": 0}

    async def fail_then_pass(content: str, topic: str) -> dict:
        calls["n"] += 1
        # 第 1 轮 3 类内容不通过，第 2 轮起通过
        return await (_fail_review(content, topic) if calls["n"] <= 3 else _pass_review(content, topic))

    monkeypatch.setattr(review_agent, "corrective_review", fail_then_pass)

    result = await run_workflow(
        _learner_input(), topic="数控机床坐标系", session_id="test-retry-pass-path",
    )

    # 只重试一轮即通过
    assert result["retry_count"] == 1

    # 决策日志先"需重试"后"全部通过"
    review_logs = [line for line in result["decision_log"] if "审核纠偏 第" in line]
    assert any("需重试" in line for line in review_logs)
    assert any("全部通过" in line for line in review_logs)

    # 无内容被降级
    review_results = result["review_results"]
    assert all(not r.get("degraded", False) for r in review_results.values())

    # 采纳修正后的内容，且不带质量提醒
    lecture = next(r for r in result["final_resources"]
                   if r.get("type") == "lecture" and r.get("stage") == 1)
    assert lecture["content"].endswith("【已修正】")
    assert "质量提醒" not in lecture["content"]
    assert lecture["review_passed"] is True
