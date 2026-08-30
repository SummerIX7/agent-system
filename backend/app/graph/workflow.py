"""``app.graph.workflow`` —— 向后兼容的门面（Facade）。

历史用法（保持有效）：
    from app.graph.workflow import (
        run_workflow, run_workflow_no_debate,
        build_workflow, build_workflow_no_debate,
        _broadcast,
        generate_resources_for_stage, _generate_and_cache_questions,
    )

实际实现按职责拆分到：
- ``app.graph.nodes``    每个 Agent 节点（analyze/plan_path/generate/review/gen_questions/decide/finalize）
- ``app.graph.builder``  LangGraph 装配与 run_workflow 入口

注意：本文件只做 re-export，不要在此重新实现任何节点/装配逻辑——
模块级重复定义会遮蔽下面的 import，导致 nodes/builder 的修改失效。
"""

from app.graph.builder import (
    build_workflow,
    build_workflow_no_debate,
    get_workflow,
    get_workflow_no_debate,
    run_workflow,
    run_workflow_no_debate,
)
from app.graph.nodes import (
    MAX_RETRIES,
    _broadcast,
    _generate_and_cache_questions,
    _prepare_stage_states,
    _save_node_trace,
    _stage_learning_topic,
    _validate_questions,
    analyze_node,
    decide_node,
    diagnosis_agent,
    finalize_node,
    finalize_node_no_debate,
    gen_questions_node,
    gen_questions_node_no_debate,
    generate_node,
    generate_resources_for_stage,
    generation_agent,
    orchestrator,
    path_planner,
    plan_path_node,
    question_generator,
    review_agent,
    review_correct_node,
)

__all__ = [
    # 入口
    "run_workflow", "run_workflow_no_debate",
    "build_workflow", "build_workflow_no_debate",
    "get_workflow", "get_workflow_no_debate",
    # 节点
    "analyze_node", "plan_path_node", "generate_node", "review_correct_node",
    "gen_questions_node", "gen_questions_node_no_debate",
    "decide_node", "finalize_node", "finalize_node_no_debate",
    # 共享函数
    "generate_resources_for_stage", "_generate_and_cache_questions",
    "_broadcast", "_save_node_trace", "_stage_learning_topic",
    "_prepare_stage_states", "_validate_questions",
    # 常量 & Agent 单例
    "MAX_RETRIES",
    "diagnosis_agent", "path_planner", "generation_agent",
    "review_agent", "question_generator", "orchestrator",
]
