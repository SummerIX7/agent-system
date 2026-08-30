from app.agents.base import BaseAgent


class DecisionOrchestrator(BaseAgent):
    """决策调度 Agent：根据学习者答题反馈实时调整学习路径"""

    async def decide_next(self, state: dict) -> str:
        """决策：审核通过则完成，超过最大重试次数则降级完成，否则打回重新生成"""
        MAX_RETRIES = 3
        review_results = state.get("review_results", {})
        retry_count = state.get("retry_count", 0)

        # 检查是否所有资源都审核通过
        all_passed = all(
            r.get("passed", False) for r in review_results.values()
        )
        has_degraded = any(
            r.get("degraded", False) for r in review_results.values()
        )

        if all_passed:
            state["decision_log"] = state.get("decision_log", []) + ["所有资源审核通过"]
            return "complete"

        if has_degraded or retry_count >= MAX_RETRIES:
            # 超过最大重试次数，走降级流程而非强制通过
            state["decision_log"] = state.get("decision_log", []) + [
                f"达到最大重试次数({MAX_RETRIES})，内容未通过质量审核，进入降级完成"
            ]
            return "complete"

        state["retry_count"] = retry_count + 1
        state["decision_log"] = state.get("decision_log", []) + [
            f"辩论未通过(第{state['retry_count']}次)，打回重新生成"
        ]
        return "retry"

    async def adjust_learning_path(self, path: dict, feedback_history: list) -> dict:
        """根据答题历史调整学习路径（返回新对象，不修改原对象）"""
        if not feedback_history:
            return path

        # 计算近期正确率
        recent = feedback_history[-5:]
        avg_correctness = sum(f.get("correctness", 0) for f in recent) / len(recent)

        # 工作在新的副本上，避免 in-place 修改导致调用方的比较总是相等
        import copy
        adjusted = copy.deepcopy(path)
        changed = False

        if avg_correctness < 0.6:
            # 插入基础补充阶段
            current = adjusted.get("current_stage", 1)
            for stage in adjusted.get("path", []):
                if stage.get("stage") == current:
                    stage["difficulty"] = "beginner"
                    stage["title"] = f"{stage['title']}（基础巩固）"
                    changed = True
                    break
        elif avg_correctness > 0.9:
            # 标记当前阶段完成，推进到下一阶段
            current = adjusted.get("current_stage", 1)
            for stage in adjusted.get("path", []):
                if stage.get("stage") == current:
                    stage["completed"] = True
                    changed = True
                    break
            adjusted["current_stage"] = current + 1
            changed = True

        return adjusted if changed else path

    def _downgrade_difficulty(self, current: str) -> str:
        levels = ["beginner", "intermediate", "advanced", "expert"]
        idx = levels.index(current) if current in levels else 0
        return levels[max(0, idx - 1)]

    def _upgrade_difficulty(self, current: str) -> str:
        levels = ["beginner", "intermediate", "advanced", "expert"]
        idx = levels.index(current) if current in levels else 0
        return levels[min(len(levels) - 1, idx + 1)]

    async def run(self, state: dict = None, **kwargs) -> dict:
        """基类接口：返回当前状态（实际调度通过 decide_next 和 adjust_learning_path）"""
        return state or {}
