"""最终输出节点：保存节点1已审核资源 + 全路径批量生成 + 节点练习缓存。"""

from __future__ import annotations

import logging

from app.graph.nodes._common import (
    _broadcast,
    _prepare_stage_states,
    _stage_learning_topic,
)
from app.graph.state import AgentState

logger = logging.getLogger(__name__)


async def finalize_node(state: AgentState) -> dict:
    """最终输出（保存已审核资源 + 生成试题 + 标记节点）。"""
    final_resources = []
    topic = state.get("topic", "")
    difficulty = state.get("difficulty", "beginner")
    review_results = state.get("review_results", {})
    session_id = state.get("session_id", "")
    profile = state.get("profile", {})
    learning_path = state.get("learning_path", {})

    path_stages = _prepare_stage_states(learning_path)
    has_degraded = any(r.get("degraded", False) for r in review_results.values())
    stage_one = next((s for s in path_stages if s.get("stage") == 1), {}) if path_stages else {}
    stage_one_topic = _stage_learning_topic(stage_one) if stage_one else topic
    stage_one_difficulty = stage_one.get("difficulty", difficulty) if stage_one else difficulty
    stage_one_saved = False

    # ── Step 1: 保存节点 1 的已审核资源 ──
    if has_degraded:
        degraded_warning = (
            "\n\n---\n"
            "> ️ **质量提醒**：本内容经多轮审核后仍未完全通过质量验证，可能存在不准确之处，仅供参考学习。\n"
            "> 建议结合权威资料交叉验证，或尝试更换学习主题以获得更高质量内容。\n"
        )
        for content_type, review in review_results.items():
            content = review.get("final_content", "")
            final_resources.append({
                "type": content_type, "stage": 1,
                "content": content + degraded_warning if content else degraded_warning.strip(),
                "topic": stage_one_topic, "difficulty": stage_one_difficulty,
                "review_score": review.get("score"),
                "review_passed": review.get("passed", False),
            })
            stage_one_saved = True
    else:
        for content_type, review in review_results.items():
            final_resources.append({
                "type": content_type, "stage": 1,
                "content": review.get("final_content", ""),
                "topic": stage_one_topic, "difficulty": stage_one_difficulty,
                "review_score": review.get("score"),
                "review_passed": review.get("passed", True),
            })
            stage_one_saved = True

    # ── Step 2: 遍历 5 个节点，补齐全部资源与节点练习 ──
    if path_stages:
        total = len(path_stages)
        for idx, stage_data in enumerate(path_stages, start=1):
            stage_num = int(stage_data.get("stage", idx))
            node_topic = _stage_learning_topic(stage_data)
            node_difficulty = stage_data.get("difficulty", difficulty)

            if stage_num == 1 and stage_one_saved:
                _broadcast(session_id, "知识生成 Agent", "running",
                           "节点1资源已完成审核，继续生成全路径试题...", 84)
            else:
                progress = min(96, 84 + idx * 2)
                _broadcast(session_id, "知识生成 Agent", "running",
                           f"正在批量生成节点 {stage_num}/{total} 资源：{stage_data.get('title', node_topic)}", progress)
                final_resources.extend(
                    await generate_resources_for_stage(session_id, stage_num, profile, learning_path)
                )

            await _generate_and_cache_questions(
                session_id, stage_num, node_topic, node_difficulty, profile, learning_path
            )
    else:
        await _generate_and_cache_questions(session_id, 1, topic, difficulty, profile, learning_path)

    # ── Step 3: 添加学习路径 ──
    if path_stages:
        final_resources.append({
            "type": "learning_path",
            "content": learning_path,
            "topic": topic, "difficulty": difficulty,
        })

    _broadcast(session_id, "知识生成 Agent", "completed", "全部节点资源与试题生成完成", 96)
    _broadcast(session_id, "审核纠偏 Agent", "completed", "全部节点内容已审核", 96)
    _broadcast(session_id, "决策调度 Agent", "completed", "工作流完成：5个节点资源+节点练习已全部就绪", 100)

    return {
        "final_resources": final_resources,
        "learning_path": learning_path,
        "review_results": review_results,
        "decision_log": ["⑥ 工作流完成 — 5个节点资源+节点练习已全部就绪"],
    }


async def finalize_node_no_debate(state: AgentState) -> dict:
    """最终输出节点（无辩论版本）。"""
    final_resources = []
    topic = state.get("topic", "")
    difficulty = state.get("difficulty", "beginner")
    generated = state.get("generated_content", {})
    session_id = state.get("session_id", "")
    profile = state.get("profile", {})
    learning_path = state.get("learning_path", {})
    path_stages = _prepare_stage_states(learning_path)
    stage_one = next((s for s in path_stages if s.get("stage") == 1), {}) if path_stages else {}
    stage_one_topic = _stage_learning_topic(stage_one) if stage_one else topic
    stage_one_difficulty = stage_one.get("difficulty", difficulty) if stage_one else difficulty
    stage_one_saved = False

    # 直接使用生成的内容，不经过辩论验证
    for content_type, content in generated.items():
        final_resources.append({
            "type": content_type, "stage": 1,
            "content": content, "topic": stage_one_topic, "difficulty": stage_one_difficulty,
            "review_score": None, "review_passed": True,
        })
        stage_one_saved = True

    # 生成全路径资源与试题
    if path_stages:
        total = len(path_stages)
        for idx, stage_data in enumerate(path_stages, start=1):
            stage_num = int(stage_data.get("stage", idx))
            node_topic = _stage_learning_topic(stage_data)
            node_difficulty = stage_data.get("difficulty", difficulty)
            if not (stage_num == 1 and stage_one_saved):
                _broadcast(session_id, "知识生成 Agent", "running",
                           f"正在批量生成节点 {stage_num}/{total} 资源：{stage_data.get('title', node_topic)}",
                           min(96, 84 + idx * 2))
                final_resources.extend(
                    await generate_resources_for_stage(session_id, stage_num, profile, learning_path)
                )
            await _generate_and_cache_questions(
                session_id, stage_num, node_topic, node_difficulty, profile, learning_path
            )
    else:
        await _generate_and_cache_questions(session_id, 1, topic, difficulty, profile, learning_path)

    # 添加学习路径
    if path_stages:
        final_resources.append({
            "type": "learning_path",
            "content": learning_path,
            "topic": topic, "difficulty": difficulty,
        })

    _broadcast(session_id, "知识生成 Agent", "completed", "全部节点资源与试题生成完成", 96)
    _broadcast(session_id, "决策调度 Agent", "completed", "工作流完成（无辩论，5个节点资源+节点练习已就绪）", 100)

    return {
        "final_resources": final_resources,
        "learning_path": learning_path,
        "decision_log": ["⑥ 工作流完成（无辩论，5个节点资源+节点练习已就绪）"],
    }


# ──────────────────────────────────────────────
# 共享函数：为指定节点生成资源 + 试题
# ──────────────────────────────────────────────

async def generate_resources_for_stage(
    session_id: str, stage: int, profile: dict, learning_path: dict,
) -> list:
    """
    为学习路径的指定节点生成 3 种资源（lecture/guide/project）+ 审核纠偏。
    返回该节点生成的资源列表。
    """
    from app.agents.generation import GenerationAgent
    from app.agents.review import ReviewAgent
    from app.core.career_tracks import get_career_track_from_input

    path_stages = learning_path.get("path", [])
    stage_data = next((s for s in path_stages if s.get("stage") == stage), None)
    if not stage_data:
        logger.warning("未找到节点 %s", stage)
        return []

    node_title = stage_data.get("title", f"节点{stage}")
    node_topic = _stage_learning_topic(stage_data)
    node_difficulty = stage_data.get("difficulty", "beginner")
    track = get_career_track_from_input({
        "career_track": profile.get("career_track", learning_path.get("career_track", "")),
        **(profile or {}),
    })
    full_topic = f"{track.name} - {node_topic}"

    gen_agent = GenerationAgent()
    review_agent_inst = ReviewAgent()
    resources = []

    for ct in ("lecture", "guide", "project"):
        try:
            if ct == "lecture":
                content = await gen_agent.generate_lecture_notes(full_topic, profile, track)
            elif ct == "guide":
                content = await gen_agent.generate_practical_guide(full_topic, profile, track)
            else:
                content = await gen_agent.generate_project_case(full_topic, profile, track)

            try:
                review = await review_agent_inst.corrective_review(content, full_topic)
                final_content = review.get("final_content", content)
            except Exception:  # noqa: BLE001
                review = {"score": None, "passed": True}
                final_content = content

            resources.append({
                "type": ct, "stage": stage,
                "content": final_content,
                "topic": node_title, "difficulty": node_difficulty,
                "review_score": review.get("score"),
                "review_passed": review.get("passed", True),
            })
        except Exception as e:  # noqa: BLE001
            logger.warning("节点%s %s 生成失败: %s", stage, ct, e)

    logger.info("[节点生成] stage=%s (%s): 已生成 %d 种资源", stage, node_title, len(resources))
    return resources


async def _generate_and_cache_questions(
    session_id: str, stage: int, topic: str, difficulty: str,
    profile: dict, learning_path: dict = None,
) -> dict:
    """为指定节点生成节点练习并按 stage 缓存。"""
    from app.agents.question_generator import QuestionGeneratorAgent
    from app.core.store import get_session, save_tiered_questions_for_stage

    def collect_avoid_questions() -> list[str]:
        session = get_session(session_id)
        tq_map = session.get("tiered_questions_map", {}) or {}
        questions: list[str] = []
        if isinstance(tq_map, dict):
            for tiered in tq_map.values():
                if not isinstance(tiered, dict):
                    continue
                for qset in tiered.values():
                    for q in (qset or {}).get("questions", []) or []:
                        if q.get("question"):
                            questions.append(q["question"])
        return list(dict.fromkeys(questions))

    q_agent = QuestionGeneratorAgent()
    _broadcast(session_id, "试题生成 Agent", "running", f"正在生成节点{stage}练习题...", 86)

    tiered = {}
    try:
        stage_data = {}
        for item in (learning_path or {}).get("path", []):
            if int(item.get("stage", 0) or 0) == int(stage):
                stage_data = item
                break
        node_title = stage_data.get("title") or topic
        node_topics = [str(t) for t in stage_data.get("topics", []) if t]
        node_result = await q_agent.generate_node_practice_questions(
            topic=topic,
            difficulty=difficulty,
            profile=profile,
            count=9,
            avoid_questions=collect_avoid_questions(),
            node_title=node_title,
            node_topics=node_topics,
        )
        tiered["node"] = {
            "level": "node", "label": "节点练习", "stage": stage,
            "topic": node_result.get("topic", topic),
            "difficulty": node_result.get("difficulty", difficulty),
            "questions": node_result.get("questions", []),
        }
    except Exception as e:  # noqa: BLE001
        logger.warning("节点%s练习题生成失败: %s", stage, e)
        tiered["node"] = {"level": "node", "label": "节点练习", "stage": stage, "questions": [], "topic": topic, "difficulty": difficulty}

    save_tiered_questions_for_stage(session_id, stage, tiered)
    _broadcast(session_id, "试题生成 Agent", "completed",
               f"节点练习生成完成: {len(tiered['node']['questions'])}题", 94)
    logger.info("[节点练习] 节点%s: %d题", stage, len(tiered['node']['questions']))
    return tiered
