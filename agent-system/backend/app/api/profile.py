import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.models.database import get_db
from app.models.schemas import LearnerProfileInput, LearnerProfile
from app.models.learner import Learner
from app.models.approval_log import ApprovalLog
from app.models.user import User
from app.agents.diagnosis import DiagnosisAgent
from app.core.career_tracks import get_career_track_from_input
from app.core.store import update_session, get_session, get_all_sessions

router = APIRouter(prefix="/api/profile", tags=["学习者画像"])

diagnosis_agent = DiagnosisAgent()


def _sanitize_knowledge_points(kps: list) -> list:
    """确保所有知识点的 score 字段为有效数值"""
    sanitized = []
    for kp in (kps or []):
        if not isinstance(kp, dict):
            continue
        sanitized.append({
            **kp,
            "score": _sanitize_score(kp.get("score", 0)),
            "confidence": max(0.0, min(1.0, float(kp.get("confidence", 0.5) or 0.5))),
        })
    return sanitized


def _sanitize_score(score) -> float:
    """确保分数为 0-100 的有效数值"""
    try:
        s = float(score)
    except (TypeError, ValueError):
        return 0.0
    if s != s:  # NaN check
        return 0.0
    return max(0.0, min(100.0, s))


def _level_from_score(score: float) -> str:
    """根据分数推算难度等级（用于 reassess 时更新 knowledge_points 的 level）"""
    s = _sanitize_score(score)
    if s >= 85:
        return "expert"
    if s >= 70:
        return "advanced"
    if s >= 40:
        return "intermediate"
    return "beginner"


def _filter_knowledge_points_by_track(knowledge_points: list, track_code: str) -> list:
    """
    只保留当前职业方向的技能知识点，过滤其他方向的。

    维度锚定逻辑：以 track.self_assessment_skills 为标准维度列表，
    命中的项保留其 score/level/confidence；缺失的项补零分占位。
    顺序按 self_assessment_skills 排列，保证雷达图维度稳定。
    匹配不到任何项时不再回退保留全部（那会导致选方向一却出现方向二/三的点）。
    """
    from app.core.career_tracks import get_career_track
    track = get_career_track(track_code)
    if not track or not track.self_assessment_skills:
        # 没有标准维度列表时，无法锚定，原样返回（已消毒）
        return _sanitize_knowledge_points(knowledge_points)

    def _norm(s: str) -> str:
        return (s or "").lower().replace(" ", "").replace("（", "(").replace("）", ")")

    allowed_skills = track.self_assessment_skills
    norm_allowed = [_norm(s) for s in allowed_skills]

    # 构建 name -> kp 索引（归一化 key）
    kp_by_norm = {}
    for kp in (knowledge_points or []):
        if not isinstance(kp, dict):
            continue
        kp_by_norm[_norm(kp.get("name", ""))] = kp

    aligned = []
    for raw_skill, norm_skill in zip(allowed_skills, norm_allowed):
        matched_kp = kp_by_norm.get(norm_skill)
        if matched_kp is None:
            # 子串包含兜底
            for nk, kp in kp_by_norm.items():
                if norm_skill and (norm_skill in nk or nk in norm_skill):
                    matched_kp = kp
                    break
        if matched_kp is not None:
            aligned.append({
                "name": raw_skill,  # 统一用标准名
                "level": matched_kp.get("level", "beginner"),
                "score": _sanitize_score(matched_kp.get("score", 0)),
                "confidence": max(0.0, min(1.0, float(matched_kp.get("confidence", 0.5) or 0.5))),
            })
        else:
            aligned.append({
                "name": raw_skill,
                "level": "beginner",
                "score": 0.0,
                "confidence": 0.3,
            })
    return aligned


@router.post("/", response_model=LearnerProfile)
async def create_profile(
    profile_input: LearnerProfileInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """提交学习者画像，触发学情诊断（需登录）"""
    # 1. 检查是否已有画像，有则更新
    stmt = select(Learner).where(Learner.user_id == current_user.id)
    result = await db.execute(stmt)
    existing_learner = result.scalar_one_or_none()

    # 2. 调用诊断 Agent
    try:
        diag_result = await diagnosis_agent.run(profile_input.model_dump())
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=f"LLM 服务不可用: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"诊断失败: {e}")

    profile_data = diag_result.get("profile", {})
    # 按职业方向过滤知识点，只保留当前方向的技能
    track_code = profile_input.career_track or profile_data.get("career_track", "operator")
    profile_data["knowledge_points"] = _filter_knowledge_points_by_track(
        profile_data.get("knowledge_points", []), track_code
    )
    session_id = f"user-{current_user.id}"

    if existing_learner:
        # 更新已有画像
        existing_learner.education_background = profile_input.education_background
        existing_learner.major = profile_input.major
        existing_learner.work_experience_years = profile_input.work_experience_years
        existing_learner.self_assessment = profile_input.self_assessment
        existing_learner.learning_style = profile_input.learning_style
        existing_learner.goals = profile_input.goals
        # 写入诊断结果
        existing_learner.knowledge_points = profile_data.get("knowledge_points", [])
        existing_learner.blind_spots = profile_data.get("blind_spots", [])
        existing_learner.overall_level = profile_data.get("overall_level", "beginner")
        existing_learner.recommended_difficulty = profile_data.get("recommended_difficulty", "beginner")
        learner = existing_learner
    else:
        # 创建新画像
        learner = Learner(
            user_id=current_user.id,
            education_background=profile_input.education_background,
            major=profile_input.major,
            work_experience_years=profile_input.work_experience_years,
            self_assessment=profile_input.self_assessment,
            learning_style=profile_input.learning_style,
            goals=profile_input.goals,
            # 写入诊断结果
            knowledge_points=profile_data.get("knowledge_points", []),
            blind_spots=profile_data.get("blind_spots", []),
            overall_level=profile_data.get("overall_level", "beginner"),
            recommended_difficulty=profile_data.get("recommended_difficulty", "beginner"),
        )
        db.add(learner)

    await db.flush()

    # 3. 存入内存 store（用于 WebSocket 等实时功能）
    update_session(session_id, {
        "learner_id": learner.id,
        "profile": {
            **profile_input.model_dump(),
            "id": learner.id,
            "session_id": session_id,
            "knowledge_points": profile_data.get("knowledge_points", []),
            "blind_spots": profile_data.get("blind_spots", []),
            "overall_level": profile_data.get("overall_level", "beginner"),
            "recommended_difficulty": profile_data.get("recommended_difficulty", "beginner"),
        },
    })

    # 4. 返回结果
    return LearnerProfile(
        id=learner.id,
        session_id=session_id,
        education_background=profile_input.education_background,
        major=profile_input.major,
        work_experience_years=profile_input.work_experience_years,
        self_assessment=profile_input.self_assessment,
        learning_style=profile_input.learning_style,
        goals=profile_input.goals,
        knowledge_points=[
            {"name": kp.get("name", ""), "level": kp.get("level", "beginner"),
             "score": kp.get("score", 0), "confidence": kp.get("confidence", 0)}
            for kp in profile_data.get("knowledge_points", [])
        ],
        blind_spots=profile_data.get("blind_spots", []),
        overall_level=profile_data.get("overall_level", "beginner"),
        recommended_difficulty=profile_data.get("recommended_difficulty", "beginner"),
    )


@router.get("/me", response_model=LearnerProfile)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的画像（需登录）"""
    stmt = select(Learner).where(Learner.user_id == current_user.id)
    result = await db.execute(stmt)
    learner = result.scalar_one_or_none()

    if not learner:
        raise HTTPException(status_code=404, detail="尚未创建学习者画像")

    # 优先从数据库读取诊断结果，并消毒分数
    knowledge_points = _sanitize_knowledge_points(learner.knowledge_points or [])
    blind_spots = learner.blind_spots or []
    overall_level = learner.overall_level or "beginner"
    recommended_difficulty = learner.recommended_difficulty or "beginner"

    # 如果数据库没有诊断结果，从 store 降级读取
    if not knowledge_points:
        for session in get_all_sessions():
            if session.get("profile", {}).get("id") == learner.id:
                p = session["profile"]
                knowledge_points = p.get("knowledge_points", [])
                blind_spots = p.get("blind_spots", [])
                overall_level = p.get("overall_level", "beginner")
                recommended_difficulty = p.get("recommended_difficulty", "beginner")
                break

    return LearnerProfile(
        id=learner.id,
        session_id=f"user-{current_user.id}",
        education_background=learner.education_background,
        major=learner.major,
        work_experience_years=learner.work_experience_years,
        self_assessment=learner.self_assessment or {},
        learning_style=learner.learning_style or "practice",
        goals=learner.goals or [],
        knowledge_points=knowledge_points,
        blind_spots=blind_spots,
        overall_level=overall_level,
        recommended_difficulty=recommended_difficulty,
        learning_path=learner.learning_path or None,
        machine_approval_status=learner.machine_approval_status or "none",
    )


@router.post("/apply-machine")
async def apply_machine_usage(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """学员申请机台使用权限"""
    # 查找学员画像
    stmt = select(Learner).where(Learner.user_id == current_user.id)
    result = await db.execute(stmt)
    learner = result.scalar_one_or_none()

    if not learner:
        raise HTTPException(status_code=404, detail="请先完成学习者画像")

    if learner.machine_approval_status == "pending":
        raise HTTPException(status_code=400, detail="已有审批中的申请，请耐心等待")

    if learner.machine_approval_status == "approved":
        raise HTTPException(status_code=400, detail="机台使用权限已批准，无需重复申请")

    # 更新状态为 pending
    learner.machine_approval_status = "pending"

    # 记录申请日志
    log = ApprovalLog(
        learner_id=learner.id,
        action="submit",
        operator_id=current_user.id,
        reason=None,
    )
    db.add(log)
    await db.flush()

    return {
        "message": "申请已提交，请等待管理员审批",
        "status": "pending",
    }


@router.post("/reassess", response_model=LearnerProfile)
async def reassess_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """基于客观学习数据重新诊断学习者画像（完成全部节点后调用）"""
    # 1. 获取 Learner 记录
    stmt = select(Learner).where(Learner.user_id == current_user.id)
    result = await db.execute(stmt)
    learner = result.scalar_one_or_none()
    if not learner:
        raise HTTPException(status_code=404, detail="请先创建学习者画像")

    # 2. 聚合客观学习数据
    session_id = f"user-{current_user.id}"
    session = get_session(session_id)

    # 学习路径完成情况
    learning_path = learner.learning_path or {}
    path_stages = learning_path.get("path", [])
    completed_nodes = [
        s.get("title", "") for s in path_stages
        if s.get("completed") or s.get("advanced_test_passed")
    ]
    node_details = [
        {"title": s.get("title", ""), "difficulty": s.get("difficulty", "beginner"),
         "completed": s.get("completed", False) or s.get("advanced_test_passed", False)}
        for s in path_stages
    ]

    # 练习成绩
    practice_results = session.get("practice_results", [])
    if isinstance(practice_results, str):
        try:
            practice_results = json.loads(practice_results)
        except Exception:
            practice_results = []
    practice_summary = []
    for pr in (practice_results or [])[-10:]:
        practice_summary.append({
            "level": pr.get("level", ""),
            "stage": pr.get("stage"),
            "score": pr.get("score", 0),
            "correct_count": pr.get("correct_count", 0),
            "question_count": pr.get("question_count", 0),
        })

    # 知识图谱掌握度
    kg = learner.kg_progress or {}
    kg_stats = kg.get("stats", {}) if isinstance(kg, dict) else {}
    kg_percentage = kg_stats.get("percentage", 0) if isinstance(kg_stats, dict) else 0

    # 构建知识点评分（从练习结果和 KG 进度推算）
    # 重要：reassess 时必须保留首次诊断的维度名，只更新 score/level，避免雷达图变形
    kp_list = learner.knowledge_points or []
    updated_kps = []
    for kp in kp_list:
        name = kp.get("name", "")
        old_score = kp.get("score", 0)
        # 若 KG 中有该知识点，用 KG 分数；否则保留旧分数
        new_score = old_score
        node_scores = kg.get("node_scores", {}) if isinstance(kg, dict) else {}
        for nid, ns in node_scores.items():
            if isinstance(ns, dict) and name and name in str(ns.get("matched_name", "")):
                new_score = max(old_score, ns.get("score", 0))
                break
        # 根据 new_score 重新推算 level（confidence 保留原值）
        updated_kps.append({
            **kp,
            "score": _sanitize_score(new_score),
            "level": _level_from_score(new_score),
        })

    # 3. 构建诊断 Agent 输入（混合原始画像 + 客观学习数据）
    input_data = {
        "education_background": learner.education_background or "",
        "major": learner.major or "",
        "work_experience_years": learner.work_experience_years or 0,
        "career_track": learner.career_track or learning_path.get("career_track", "operator"),
        "learning_style": learner.learning_style or "practice",
        "goals": learner.goals or [],
        # 用客观学习数据替换自评
        "self_assessment": _build_objective_assessment(updated_kps, practice_summary, completed_nodes),
        "learning_context": {
            "completed_nodes": completed_nodes,
            "total_nodes": len(path_stages),
            "node_details": node_details,
            "practice_summary": practice_summary,
            "kg_mastery_percentage": kg_percentage,
            "updated_knowledge_points": updated_kps,
        },
    }

    # 4. 调用诊断 Agent —— 仅用于评估 blind_spots / overall_level / recommended_difficulty
    #    knowledge_points 不采用 LLM 输出，直接用 updated_kps（保留原维度名，只更新数值）
    try:
        diag_result = await diagnosis_agent.run(input_data)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=f"LLM 服务不可用: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重新诊断失败: {e}")

    profile_data = diag_result.get("profile", {})

    # 5. 更新 Learner 记录
    #    知识点维度锚定：直接用 updated_kps，保证与首次诊断维度完全一致
    learner.knowledge_points = updated_kps
    learner.blind_spots = profile_data.get("blind_spots", learner.blind_spots or [])
    learner.overall_level = profile_data.get("overall_level", learner.overall_level)
    learner.recommended_difficulty = profile_data.get("recommended_difficulty", learner.recommended_difficulty)
    await db.flush()

    # 6. 更新 session store
    update_session(session_id, {
        "profile": {
            "id": learner.id,
            "session_id": session_id,
            "education_background": learner.education_background,
            "major": learner.major,
            "work_experience_years": learner.work_experience_years,
            "self_assessment": learner.self_assessment or {},
            "learning_style": learner.learning_style,
            "goals": learner.goals or [],
            "knowledge_points": updated_kps,
            "blind_spots": profile_data.get("blind_spots", []),
            "overall_level": profile_data.get("overall_level", "beginner"),
            "recommended_difficulty": profile_data.get("recommended_difficulty", "beginner"),
        },
    })

    return LearnerProfile(
        id=learner.id,
        session_id=session_id,
        education_background=learner.education_background,
        major=learner.major,
        work_experience_years=learner.work_experience_years,
        self_assessment=learner.self_assessment or {},
        learning_style=learner.learning_style or "practice",
        goals=learner.goals or [],
        knowledge_points=[{
            "name": kp.get("name", ""), "level": kp.get("level", "beginner"),
            "score": kp.get("score", 0), "confidence": kp.get("confidence", 0),
        } for kp in updated_kps],
        blind_spots=profile_data.get("blind_spots", []),
        overall_level=profile_data.get("overall_level", "beginner"),
        recommended_difficulty=profile_data.get("recommended_difficulty", "beginner"),
    )


def _build_objective_assessment(
    knowledge_points: list,
    practice_summary: list,
    completed_nodes: list,
) -> dict:
    """根据客观学习数据构建技能自评，替代用户手动填写的自评"""
    assessment = {}
    for kp in knowledge_points:
        name = kp.get("name", "")
        score = kp.get("score", 0)
        if score >= 80:
            assessment[name] = "精通"
        elif score >= 60:
            assessment[name] = "熟练"
        elif score >= 30:
            assessment[name] = "了解基础"
        else:
            assessment[name] = "不了解"
    # 补充已完成的节点标题
    for node in completed_nodes:
        if node and node not in assessment:
            assessment[node] = "熟练"
    return assessment
