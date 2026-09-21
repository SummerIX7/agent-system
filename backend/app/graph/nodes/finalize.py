"""最终输出节点：保存节点1已审核资源 + 全路径批量生成 + 节点练习缓存。"""

from __future__ import annotations

import asyncio
import logging

from app.graph.nodes._common import (
    _broadcast,
    _prepare_stage_states,
    _stage_learning_topic,
    generation_agent,
    make_token_broadcaster,
    question_generator,
    review_agent,
)
from app.graph.state import AgentState

logger = logging.getLogger(__name__)

_DEGRADED_WARNING = (
    "\n\n---\n"
    "> ️ **质量提醒**：本内容经多轮审核后仍未完全通过质量验证，可能存在不准确之处，仅供参考学习。\n"
    "> 建议结合权威资料交叉验证，或尝试更换学习主题以获得更高质量内容。\n"
)


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
        for content_type, review in review_results.items():
            content = review.get("final_content", "")
            final_resources.append({
                "type": content_type, "stage": 1,
                "content": content + _DEGRADED_WARNING if content else _DEGRADED_WARNING.strip(),
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

    # ── Step 2: 并行遍历 5 个节点，补齐全部资源与节点练习 ──
    if path_stages:
        if stage_one_saved:
            _broadcast(session_id, "知识生成 Agent", "running",
                       "节点1资源已完成审核，继续生成全路径试题...", 84)
        final_resources.extend(
            await _run_stage_generations(session_id, path_stages, profile, learning_path,
                                         skip_stage_one_resources=stage_one_saved)
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

    # 生成全路径资源与试题（并行）
    if path_stages:
        final_resources.extend(
            await _run_stage_generations(session_id, path_stages, profile, learning_path,
                                         skip_stage_one_resources=stage_one_saved)
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
# 共享函数：全路径并行生成 / 单节点资源 + 试题
# ──────────────────────────────────────────────

async def _run_stage_generations(
    session_id: str,
    path_stages: list,
    profile: dict,
    learning_path: dict,
    skip_stage_one_resources: bool,
) -> list:
    """并行生成所有节点的资源与节点练习（信号量限流，结果按节点顺序拼接）。

    - 并发度由 FINALIZE_CONCURRENCY 控制（默认 3），避免打满 LLM API 限额；
    - 节点间无数据依赖；单节点异常不影响其他节点（记日志后跳过）；
    - 进度广播按完成数计数，避免并行下百分比错乱；
    - 节点 1 资源已在图内审核完成时跳过其资源生成，但仍生成节点练习。
    """
    from app.core.config import get_settings
    concurrency = max(1, getattr(get_settings(), "FINALIZE_CONCURRENCY", 3))
    sem = asyncio.Semaphore(concurrency)
    total = len(path_stages)
    done = {"n": 0}

    async def run_one(idx: int, stage_data: dict) -> list:
        stage_num = int(stage_data.get("stage", idx))
        node_topic = _stage_learning_topic(stage_data)
        node_difficulty = stage_data.get("difficulty", "beginner")
        async with sem:
            stage_resources = []
            if not (stage_num == 1 and skip_stage_one_resources):
                stage_resources = await generate_resources_for_stage(
                    session_id, stage_num, profile, learning_path)
            await _generate_and_cache_questions(
                session_id, stage_num, node_topic, node_difficulty, profile, learning_path)
            done["n"] += 1
            _broadcast(session_id, "知识生成 Agent", "running",
                       f"已完成 {done['n']}/{total} 个节点的资源与试题生成",
                       min(96, 84 + done["n"] * 2))
            return stage_resources

    # gather 保持传入顺序，资源仍按节点顺序拼接
    results = await asyncio.gather(
        *(run_one(idx, sd) for idx, sd in enumerate(path_stages, start=1)),
        return_exceptions=True,
    )
    resources: list = []
    for idx, r in enumerate(results, start=1):
        if isinstance(r, Exception):
            logger.warning("节点%s 批量生成异常，已跳过: %s", idx, r)
            continue
        resources.extend(r)
    return resources


async def generate_resources_for_stage(
    session_id: str, stage: int, profile: dict, learning_path: dict,
    gen_agent=None, review_agent_inst=None,
) -> list:
    """
    为学习路径的指定节点生成 3 种资源（lecture/guide/project）+ 审核纠偏。
    返回该节点生成的资源列表。

    审核异常时不再静默放行：标记 review_passed=False + degraded=True，
    内容附带质量提醒文案（与 finalize Step 1 的降级处理一致）。
    """
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

    # 复用模块级单例（trace 埋点已用 ContextVar 做并发隔离，并行安全）
    gen_agent = gen_agent or generation_agent
    review_agent_inst = review_agent_inst or review_agent
    resources = []

    for ct in ("lecture", "guide", "project"):
        try:
            feed, flush = make_token_broadcaster(session_id, "知识生成 Agent", f"{stage}:{ct}")
            try:
                if ct == "lecture":
                    content = await gen_agent.generate_lecture_notes(full_topic, profile, track, on_token=feed)
                elif ct == "guide":
                    content = await gen_agent.generate_practical_guide(full_topic, profile, track, on_token=feed)
                else:
                    content = await gen_agent.generate_project_case(full_topic, profile, track, on_token=feed)
            finally:
                flush()

            try:
                review = await review_agent_inst.corrective_review(content, full_topic)
                final_content = review.get("final_content", content)
            except Exception as e:  # noqa: BLE001
                # 审核异常不再静默放行：标记降级并附质量提醒，让学习者明确知情
                logger.warning("节点%s %s 审核异常，标记为降级内容: %s", stage, ct, e)
                review = {"score": None, "passed": False, "degraded": True}
                final_content = content + _DEGRADED_WARNING

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

    q_agent = question_generator
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
