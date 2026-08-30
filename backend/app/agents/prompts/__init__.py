"""``app.agents.prompts`` —— Agent 使用的 Prompt 模板集中管理。"""
from app.agents.prompts.question_prompts import (
    build_basic_prompt,
    build_comprehensive_prompt,
    build_node_practice_prompt,
)

__all__ = [
    "build_basic_prompt",
    "build_comprehensive_prompt",
    "build_node_practice_prompt",
]
