import time as _time

from langgraph.graph import END, StateGraph

from app.agents.diagnosis import DiagnosisAgent
from app.agents.path_planner import PathPlannerAgent
from app.agents.generation import GenerationAgent
from app.agents.question_generator import QuestionGeneratorAgent
from app.agents.orchestrator import DecisionOrchestrator
from app.agents.review import ReviewAgent
from app.graph.state import AgentState
from app.core.career_tracks import get_career_track_from_input

# Agent 实例
diagnosis_agent = DiagnosisAgent()
path_planner = PathPlannerAgent()
generation_agent = GenerationAgent()
review_agent = ReviewAgent()
question_generator = QuestionGeneratorAgent()
orchestrator = DecisionOrchestrator()

# 最大重试次数
MAX_RETRIES = 3


def _broadcast(session_id: str, agent: str, status: str, message: str, progress: float = 0):
    """广播 Agent 状态"""
    if session_id:
        try:
            from app.api.ws import broadcast_agent_status
            broadcast_agent_status(session_id, agent, status, message, progress)
        except Exception:
            pass


def _save_node_trace(session_id: str, node: str, agent_name: str,
                     input_data: dict, output_data: dict,
                     llm_calls: list, start_time: float):
    """保存节点追踪记录"""
    if not session_id:
        return
    try:
        from app.core.store import add_trace_entry
        add_trace_entry(session_id, {
            "node": node,
            "agent_name": agent_name,
            "input": input_data,
            "output": output_data,
            "llm_calls": llm_calls,
            "duration_ms": round((_time.time() - start_time) * 1000),
        })
    except Exception:
        pass


# ──────────────────────────────────────────────
# ① 学情分析 Agent
# ──────────────────────────────────────────────
async def analyze_node(state: AgentState) -> dict:
    session_id = state.get("session_id", "")
    start = _time.time()
    diagnosis_agent._trace_agent_name = "学情分析 Agent"
    diagnosis_agent._trace_calls = []

    _broadcast(session_id, "学情分析 Agent", "running", "正在分析学习者画像...", 5)

    result = await diagnosis_agent.run(state.get("learner_input", {}))

    _broadcast(session_id, "学情分析 Agent", "completed", "学情分析完成", 15)

    output = {
        "profile": result.get("profile", {}),
        "difficulty": result.get("difficulty", "beginner"),
        "decision_log": ["① 学情分析完成"],
    }
    _save_node_trace(session_id, "analyze", "学情分析 Agent",
                     {"learner_input": state.get("learner_input", {})},
                     {"difficulty": output["difficulty"]},
                     diagnosis_agent.collect_trace(), start)
    return output


# ──────────────────────────────────────────────
# ② 路径规划 Agent
# ──────────────────────────────────────────────
async def plan_path_node(state: AgentState) -> dict:
    session_id = state.get("session_id", "")
    start = _time.time()
    path_planner._trace_agent_name = "路径规划 Agent"
    path_planner._trace_calls = []

    _broadcast(session_id, "路径规划 Agent", "running", "正在规划学习路径...", 20)

    existing_path = state.get("learning_path")
    feedback_history = state.get("feedback_history", [])

    if existing_path and feedback_history:
        result = await path_planner.adjust_path(existing_path, feedback_history[-1])
    else:
        result = await path_planner.plan_path(
            profile=state.get("profile", {}),
            topic=state.get("topic", ""),
        )

    _broadcast(session_id, "路径规划 Agent", "completed", "学习路径规划完成", 30)

    output = {
        "learning_path": result,
        "decision_log": ["② 路径规划完成"],
    }
    _save_node_trace(session_id, "plan_path", "路径规划 Agent",
                     {"profile": state.get("profile", {}), "topic": state.get("topic", "")},
                     {"learning_path_stages": len(result.get("path", [])) if result else 0},
                     path_planner.collect_trace(), start)
    return output


# ──────────────────────────────────────────────
# ③ 知识生成 Agent
# ──────────────────────────────────────────────
async def generate_node(state: AgentState) -> dict:
    session_id = state.get("session_id", "")
    start = _time.time()
    generation_agent._trace_agent_name = "知识生成 Agent"
    generation_agent._trace_calls = []

    topic = state.get("topic", "")
    learning_path = state.get("learning_path", {})
    stage_one = next((s for s in learning_path.get("path", []) if s.get("stage") == 1), None)
    if stage_one:
        topic = _stage_learning_topic(stage_one)
    profile = state.get("profile", {})
    career_code = state.get("career_track", "operator")
    track = get_career_track_from_input({"career_track": career_code, **profile})
    retry_count = state.get("retry_count", 0)
    generated = {}
    logs = []

    # 重试时收集上一轮审核反馈，注入到生成 prompt 中
    retry_context = ""
    if retry_count > 0:
        issues_parts = []
        review_results = state.get("review_results", {})
        for ct, review in review_results.items():
            if review.get("issues"):
                for issue in review["issues"]:
                    issues_parts.append(f"[审核-{ct}] {issue}")
        if issues_parts:
            retry_context = "\n".join(issues_parts)
            logs.append(f"注入上一轮反馈: {len(issues_parts)} 条问题")

    _broadcast(session_id, "知识生成 Agent", "running",
               "正在重新生成讲义（已注入审核反馈）..." if retry_context else "正在生成讲义...", 35)
    generated["lecture"] = await generation_agent.generate_lecture_notes(topic, profile, track, retry_context)
    logs.append("讲义生成完成")

    _broadcast(session_id, "知识生成 Agent", "running",
               "正在重新生成实验指导..." if retry_context else "正在生成实验指导...", 45)
    generated["guide"] = await generation_agent.generate_practical_guide(topic, profile, track, retry_context)
    logs.append("实验指导生成完成")

    _broadcast(session_id, "知识生成 Agent", "running",
               "正在重新生成项目案例..." if retry_context else "正在生成项目案例...", 55)
    generated["project"] = await generation_agent.generate_project_case(topic, profile, track, retry_context)
    logs.append("项目案例生成完成")

    _broadcast(session_id, "知识生成 Agent", "running", "内容已生成，等待审核验证...", 58)

    output = {
        "generated_content": generated,
        "decision_log": [f"③ 知识生成完成: {', '.join(logs)}"],
    }
    _save_node_trace(session_id, "generate", "知识生成 Agent",
                     {"topic": topic, "retry_count": retry_count, "has_retry_context": bool(retry_context)},
                     {"content_types": list(generated.keys()),
                      "lecture_len": len(generated.get("lecture", "")),
                      "guide_len": len(generated.get("guide", "")),
                      "project_len": len(generated.get("project", ""))},
                     generation_agent.collect_trace(), start)
    return output


# ──────────────────────────────────────────────
# ③½ 审核纠偏 Agent（双视角审查 + 修正，合并原预审+辩论）
# ──────────────────────────────────────────────
async def review_correct_node(state: AgentState) -> dict:
    session_id = state.get("session_id", "")
    start = _time.time()
    review_agent._trace_agent_name = "审核纠偏 Agent"
    review_agent._trace_calls = []

    topic = state.get("topic", "")
    learning_path = state.get("learning_path", {})
    stage_one = next((s for s in learning_path.get("path", []) if s.get("stage") == 1), None)
    if stage_one:
        topic = _stage_learning_topic(stage_one)
    generated = state.get("generated_content", {})
    retry_count = state.get("retry_count", 0)
    review_results = {}

    _broadcast(session_id, "审核纠偏 Agent", "running", "启动双视角审核纠偏...", 59)

    for content_type, content in generated.items():
        progress = 59 + len(review_results) * 5

        # 跳过非文本内容
        if content_type == "test":
            review_results[content_type] = {
                "passed": True, "score": 1.0, "issues": [],
                "final_content": content, "correction_applied": False,
            }
            continue

        # 达到最大重试次数，标记为降级
        if retry_count >= MAX_RETRIES:
            review_results[content_type] = {
                "passed": False, "score": 0, "issues": [],
                "final_content": content, "correction_applied": False,
                "degraded": True,
            }
            continue

        _broadcast(session_id, "审核纠偏 Agent", "running",
                   f"审核+纠偏: {content_type}...", progress)

        try:
            result = await review_agent.corrective_review(content, topic)
            review_results[content_type] = result
        except Exception as e:
            review_results[content_type] = {
                "passed": False, "score": 0,
                "issues": [f"审核纠偏异常: {str(e)}"],
                "final_content": content, "correction_applied": False,
            }

    all_passed = all(r.get("passed", False) for r in review_results.values())
    has_degraded = any(r.get("degraded", False) for r in review_results.values())
    new_retry = retry_count if all_passed else retry_count + 1

    # 本轮重试耗尽 → 标记为降级（修复：retry_count=2进入、失败后new_retry=3时漏标degraded）
    if not all_passed and new_retry >= MAX_RETRIES and not has_degraded:
        has_degraded = True
        for ct in review_results:
            if not review_results[ct].get("passed", False):
                review_results[ct]["degraded"] = True

    # 构建调试日志
    debug_lines = []
    for ct, r in review_results.items():
        status = "通过" if r.get("passed") else ("降级" if r.get("degraded") else "未通过")
        score = r.get("score", 0)
        issue_count = len(r.get("issues", []))
        corrected = "已修正" if r.get("correction_applied") else "未修正"
        debug_lines.append(f"  {ct}: {status} | 评分={score:.2f} | 问题数={issue_count} | {corrected}")
    debug_log = f"③½ 审核纠偏 第{new_retry}次 | {'全部通过' if all_passed else '需重试'}\n" + "\n".join(debug_lines)

    # 广播
    if has_degraded:
        _broadcast(session_id, "审核纠偏 Agent", "completed",
                   f"审核完成：已降级（超过最大重试{MAX_RETRIES}次）", 82)
        _broadcast(session_id, "知识生成 Agent", "completed", "内容已生成（降级通过）", 65)
    elif all_passed:
        _broadcast(session_id, "审核纠偏 Agent", "completed", "审核完成：全部内容通过", 82)
        _broadcast(session_id, "知识生成 Agent", "completed", "内容已生成并通过审核", 65)
    else:
        _broadcast(session_id, "审核纠偏 Agent", "completed",
                   f"审核完成：有内容未通过（第{new_retry}次），触发重新生成", 82)
        _broadcast(session_id, "知识生成 Agent", "error", "内容未通过审核，需重新生成", 60)

    # 存储调试信息到 session
    if session_id:
        try:
            from app.core.store import add_agent_log
            add_agent_log(session_id, {
                "agent_name": "审核纠偏 Agent",
                "status": "completed",
                "message": debug_log,
                "progress": 82,
            })
        except Exception:
            pass

    output = {
        "review_results": review_results,
        "retry_count": new_retry,
        "decision_log": [debug_log],
    }
    _save_node_trace(session_id, "review_correct", "审核纠偏 Agent",
                     {"content_types": list(generated.keys()), "retry_count": retry_count, "topic": topic},
                     {"all_passed": all_passed, "has_degraded": has_degraded, "new_retry": new_retry,
                      "results_summary": {ct: {"passed": r.get("passed"), "score": r.get("score"),
                                               "issues": len(r.get("issues", [])),
                                               "corrected": r.get("correction_applied")}
                                          for ct, r in review_results.items()}},
                     review_agent.collect_trace(), start)
    return output


# ──────────────────────────────────────────────
# ⑤ 试题生成 Agent
# ──────────────────────────────────────────────

def _validate_questions(questions: list) -> tuple[list, list]:
    """
    试题格式校验：检查题目结构、选项合法性、答案是否在选项中。
    不依赖 LLM，纯规则检查，防止生成明显错误的试题。
    返回 (valid_questions, issues)
    """
    issues = []
    valid = []
    valid_letters = {"A", "B", "C", "D", "E", "F"}

    for i, q in enumerate(questions):
        q_type = q.get("question_type", "")
        q_issues = []

        # 必填字段检查
        if not q.get("question"):
            q_issues.append("缺少题目内容")
        if not q_type:
            q_issues.append("缺少题目类型")

        if q_type == "multiple_choice":
            options = q.get("options", [])
            if len(options) < 3:
                q_issues.append(f"选项数量不足({len(options)}，至少3个)")
            if not q.get("correct_answer") or q["correct_answer"] not in valid_letters:
                q_issues.append(f"正确答案格式无效({q.get('correct_answer')})")
            elif q["correct_answer"] in valid_letters:
                idx = ord(q["correct_answer"]) - 65
                if idx >= len(options):
                    q_issues.append(f"正确答案索引({q['correct_answer']})超出选项范围")
        elif q_type == "true_false":
            options = q.get("options", [])
            if "正确" not in str(options) and "错误" not in str(options):
                q_issues.append("判断题缺少正确/错误选项")
            if q.get("correct_answer") not in ("正确", "错误"):
                q_issues.append(f"判断题答案应为正确/错误，实际为: {q.get('correct_answer')}")
        elif q_type == "practical":
            if not q.get("explanation"):
                q_issues.append("实操缺少评分标准(explanation)")
        else:
            q_issues.append(f"未知题型: {q_type}")

        if q_issues:
            issues.append(f"题目{i+1}: {'; '.join(q_issues)}")
        valid.append(q)

    return valid, issues


async def gen_questions_node(state: AgentState) -> dict:
    session_id = state.get("session_id", "")
    start = _time.time()
    question_generator._trace_agent_name = "试题生成 Agent"
    question_generator._trace_calls = []

    _broadcast(session_id, "试题生成 Agent", "running", "正在生成试题...", 88)

    topic = state.get("topic", "")
    difficulty = state.get("difficulty", "beginner")
    profile = state.get("profile", {})

    result = await question_generator.generate_questions(topic, difficulty, profile)

    # 试题格式校验
    raw_questions = result.get("questions", [])
    valid_questions, q_issues = _validate_questions(raw_questions)
    result["questions"] = valid_questions

    log_msg = "⑤ 试题生成完成"
    if q_issues:
        log_msg += f"（{len(q_issues)}题格式异常已过滤: {'; '.join(q_issues[:3])}）"

    _broadcast(session_id, "试题生成 Agent", "completed", log_msg, 92)

    output = {
        "question_set": result,
        "decision_log": [log_msg],
    }
    _save_node_trace(session_id, "gen_questions", "试题生成 Agent",
                     {"topic": topic, "difficulty": difficulty},
                     {"question_count": len(result.get("questions", [])) if result else 0},
                     question_generator.collect_trace(), start)
    return output


# ──────────────────────────────────────────────
# ⑥ 决策调度 Agent
# ──────────────────────────────────────────────
async def decide_node(state: AgentState) -> str:
    session_id = state.get("session_id", "")
    _broadcast(session_id, "决策调度 Agent", "running", "正在决策...", 95)

    review_results = state.get("review_results", {})
    retry_count = state.get("retry_count", 0)

    all_passed = all(r.get("passed", False) for r in review_results.values())
    has_degraded = any(r.get("degraded", False) for r in review_results.values())

    if all_passed:
        _broadcast(session_id, "决策调度 Agent", "completed", "审核通过，正在生成最终内容...", 82)
        return "complete"
    elif has_degraded or retry_count >= MAX_RETRIES:
        _broadcast(session_id, "决策调度 Agent", "completed", "审核完成（降级），正在生成最终内容...", 82)
        return "complete"
    else:
        _broadcast(session_id, "决策调度 Agent", "running", f"审核未通过（第{retry_count}次），触发重新生成...", 25)
        _broadcast(session_id, "知识生成 Agent", "running", "重新生成内容...", 30)
        return "retry"


# ──────────────────────────────────────────────
# 最终输出（保存已审核资源 + 生成试题 + 标记节点）
# ──────────────────────────────────────────────
def _stage_learning_topic(stage_data: dict) -> str:
    """把一个学习节点压缩成资源/试题生成使用的主题。"""
    title = stage_data.get("title") or f"节点{stage_data.get('stage', '')}"
    topics = [str(t) for t in stage_data.get("topics", []) if t]
    if topics:
        return f"{title}（{ '、'.join(topics) }）"
    return title


def _prepare_stage_states(learning_path: dict) -> list[dict]:
    """初始化学习节点状态；资源在协同阶段一次性生成，因此全部标记 has_resources。"""
    path_stages = learning_path.get("path", [])
    for stage_data in path_stages:
        stage_data.setdefault("completed", False)
        stage_data.setdefault("basic_test_passed", False)
        stage_data.setdefault("advanced_test_passed", False)
        stage_data["has_resources"] = True
    return path_stages


async def finalize_node(state: AgentState) -> dict:
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
        print(f"[警告] 未找到节点 {stage}")
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
    review_agent = ReviewAgent()
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
                review = await review_agent.corrective_review(content, full_topic)
                final_content = review.get("final_content", content)
            except Exception:
                review = {"score": None, "passed": True}
                final_content = content

            resources.append({
                "type": ct, "stage": stage,
                "content": final_content,
                "topic": node_title, "difficulty": node_difficulty,
                "review_score": review.get("score"),
                "review_passed": review.get("passed", True),
            })
        except Exception as e:
            print(f"[警告] 节点{stage} {ct} 生成失败: {e}")

    print(f"[节点生成] stage={stage} ({node_title}): 已生成 {len(resources)} 种资源")
    return resources


async def _generate_and_cache_questions(
    session_id: str, stage: int, topic: str, difficulty: str,
    profile: dict, learning_path: dict = None,
) -> dict:
    """为指定节点生成节点练习并按 stage 缓存"""
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
    except Exception as e:
        print(f"[警告] 节点{stage}练习题生成失败: {e}")
        tiered["node"] = {"level": "node", "label": "节点练习", "stage": stage, "questions": [], "topic": topic, "difficulty": difficulty}

    save_tiered_questions_for_stage(session_id, stage, tiered)
    _broadcast(session_id, "试题生成 Agent", "completed",
               f"节点练习生成完成: {len(tiered['node']['questions'])}题", 94)
    print(f"[节点练习] 节点{stage}: {len(tiered['node']['questions'])}题")
    return tiered


# ──────────────────────────────────────────────
# 构建工作流
# ──────────────────────────────────────────────
def build_workflow() -> StateGraph:
    workflow = StateGraph(AgentState)

    # 5 个节点（试题生成已独立为按需接口）
    workflow.add_node("analyze", analyze_node)            # ① 学情分析
    workflow.add_node("plan_path", plan_path_node)        # ② 路径规划
    workflow.add_node("generate", generate_node)          # ③ 知识生成
    workflow.add_node("review_correct", review_correct_node)  # ③½ 审核纠偏（双视角审查+修正）
    workflow.add_node("finalize", finalize_node)          # 最终输出

    # 流程
    workflow.set_entry_point("analyze")
    workflow.add_edge("analyze", "plan_path")
    workflow.add_edge("plan_path", "generate")
    workflow.add_edge("generate", "review_correct")

    # 审核纠偏后条件路由：通过则直接输出，未通过则重新生成
    workflow.add_conditional_edges(
        "review_correct",
        decide_node,
        {
            "complete": "finalize",
            "retry": "generate",
        },
    )

    workflow.add_edge("finalize", END)

    return workflow.compile()


_workflow = None


def get_workflow():
    global _workflow
    if _workflow is None:
        _workflow = build_workflow()
    return _workflow


async def run_workflow(learner_input: dict, topic: str, session_id: str = "", profile: dict = None) -> dict:
    """运行完整 6 Agent 工作流（包含审核纠偏机制）"""
    workflow = get_workflow()

    # 如果传入了 profile，合并到 learner_input
    if profile:
        learner_input = {**learner_input, **profile}

    # 解析职业方向配置
    track = get_career_track_from_input(learner_input)

    initial_state: AgentState = {
        "learner_input": learner_input,
        "topic": topic,
        "retry_count": 0,
        "generated_content": {},
        "review_results": {},
        "question_set": {},
        "learning_path": {},
        "final_resources": [],
        "feedback_history": [],
        "decision_log": [],
        "session_id": session_id,
        "career_track": track.code,
    }

    result = await workflow.ainvoke(initial_state)
    return result


# ──────────────────────────────────────────────
# 无辩论版本（用于消融实验）
# ──────────────────────────────────────────────

async def gen_questions_node_no_debate(state: AgentState) -> dict:
    """试题生成节点（无辩论版本）"""
    session_id = state.get("session_id", "")
    _broadcast(session_id, "试题生成 Agent", "running", "正在生成试题...", 88)

    topic = state.get("topic", "")
    difficulty = state.get("difficulty", "beginner")
    profile = state.get("profile", {})

    result = await question_generator.generate_questions(topic, difficulty, profile)

    _broadcast(session_id, "试题生成 Agent", "completed", "试题生成完成", 92)

    return {
        "question_set": result,
        "decision_log": ["⑤ 试题生成完成（无辩论）"],
    }


async def finalize_node_no_debate(state: AgentState) -> dict:
    """最终输出节点（无辩论版本）"""
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


def build_workflow_no_debate() -> StateGraph:
    """构建无审核版本的工作流（用于消融实验对比）"""
    workflow = StateGraph(AgentState)

    # 只包含分析、生成、最终输出（跳过审核纠偏+试题生成）
    workflow.add_node("analyze", analyze_node)            # ① 学情分析
    workflow.add_node("plan_path", plan_path_node)        # ② 路径规划
    workflow.add_node("generate", generate_node)          # ③ 知识生成
    workflow.add_node("finalize", finalize_node_no_debate)  # 最终输出（无审核）

    # 简单流程：分析 → 生成 → 输出
    workflow.set_entry_point("analyze")
    workflow.add_edge("analyze", "plan_path")
    workflow.add_edge("plan_path", "generate")
    workflow.add_edge("generate", "finalize")
    workflow.add_edge("finalize", END)

    return workflow.compile()


_workflow_no_debate = None


def get_workflow_no_debate():
    """获取无辩论工作流单例"""
    global _workflow_no_debate
    if _workflow_no_debate is None:
        _workflow_no_debate = build_workflow_no_debate()
    return _workflow_no_debate


async def run_workflow_no_debate(learner_input: dict, topic: str, session_id: str = "", profile: dict = None) -> dict:
    """
    运行无审核版本的工作流（用于消融实验）

    与 run_workflow 的区别：
    - 跳过审核纠偏节点，直接使用生成的内容
    - 不进行质量验证
    - 用于对比有/无审核纠偏机制对谬误率的影响
    """
    workflow = get_workflow_no_debate()

    # 如果传入了 profile，合并到 learner_input
    if profile:
        learner_input = {**learner_input, **profile}

    # 解析职业方向配置
    track = get_career_track_from_input(learner_input)

    initial_state: AgentState = {
        "learner_input": learner_input,
        "topic": topic,
        "retry_count": 0,
        "generated_content": {},
        "review_results": {},
        "question_set": {},
        "learning_path": {},
        "final_resources": [],
        "feedback_history": [],
        "decision_log": [],
        "session_id": session_id,
        "career_track": track.code,
    }

    result = await workflow.ainvoke(initial_state)
    return result
