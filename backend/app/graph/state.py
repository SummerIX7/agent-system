import operator
from typing import Annotated, TypedDict


class AgentState(TypedDict, total=False):
    """LangGraph 工作流状态（6 Agent 架构）"""

    # 输入
    learner_input: dict          # 学习者输入信息
    topic: str                   # 当前主题

    # ① 学情分析
    profile: dict                # 学习者画像
    difficulty: str              # 难度等级

    # ② 路径规划
    learning_path: dict          # 学习路径 {path: [...], current_stage: 1}

    # ③ 知识生成
    generated_content: dict      # 生成的资源 {lecture/guide/project: content}

    # ③½ 审核纠偏（双视角审查+修正，合并了原预审+辩论）
    review_results: dict         # 审核结果 {type: {passed, score, issues, final_content, correction_applied}}

    # ⑤ 试题生成
    question_set: dict           # 试题集 {questions: [...]}

    # ⑥ 决策调度
    retry_count: int             # 重试次数
    next_action: str             # 下一步动作

    # 输出
    final_resources: list        # 最终通过审核的资源

    # 反馈循环
    feedback_history: list       # 答题反馈历史
    decision_log: Annotated[list, operator.add]  # 决策日志

    # 会话信息
    session_id: str              # 会话 ID
    learner_id: str              # 学习者 ID
    career_track: str            # 职业方向代码 (operator/setup_tech/programmer)
