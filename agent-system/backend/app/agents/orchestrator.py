from app.agents.base import BaseAgent


class DecisionOrchestrator(BaseAgent):
    """决策调度 Agent：根据用户答题反馈实时调整学习路径"""

    async def handle_feedback(self, state: dict, user_answer: dict) -> dict:
        """处理学习者答题反馈，动态调整策略"""
        correctness = user_answer.get("correctness", 0)
        topic = user_answer.get("topic", "")

        if correctness < 0.6:
            state["decision_log"] = state.get("decision_log", []) + [
                f"正确率{correctness:.0%}<60%，触发降维解释"
            ]
            state["topic"] = f"{topic} 基础概念"
            state["difficulty"] = self._downgrade_difficulty(state.get("difficulty", "beginner"))

        elif correctness > 0.9:
            state["decision_log"] = state.get("decision_log", []) + [
                f"正确率{correctness:.0%}>90%，触发进阶挑战"
            ]
            state["topic"] = f"{topic} 高级应用"
            state["difficulty"] = self._upgrade_difficulty(state.get("difficulty", "beginner"))

        state["feedback_history"] = state.get("feedback_history", []) + [user_answer]
        return state

    async def decide_next(self, state: dict) -> str:
        """决策：辩论通过则完成，否则打回重新生成"""
        debate_results = state.get("debate_results", {})
        retry_count = state.get("retry_count", 0)

        # 检查是否所有资源都辩论通过
        all_passed = all(
            r.get("passed", False) for r in debate_results.values()
        )

        if all_passed:
            state["decision_log"] = state.get("decision_log", []) + ["所有资源辩论通过"]
            return "complete"

        if retry_count >= 3:
            state["decision_log"] = state.get("decision_log", []) + ["达到最大重试次数，强制完成"]
            return "complete"

        state["retry_count"] = retry_count + 1
        state["decision_log"] = state.get("decision_log", []) + [
            f"辩论未通过(第{state['retry_count']}次)，打回重新生成"
        ]
        return "retry"

    async def adjust_learning_path(self, path: dict, feedback_history: list) -> dict:
        """根据答题历史调整学习路径"""
        if not feedback_history:
            return path

        # 计算近期正确率
        recent = feedback_history[-5:]
        avg_correctness = sum(f.get("correctness", 0) for f in recent) / len(recent)

        if avg_correctness < 0.6:
            # 插入基础补充阶段
            current = path.get("current_stage", 1)
            for stage in path.get("path", []):
                if stage.get("stage") == current:
                    stage["difficulty"] = "beginner"
                    stage["title"] = f"{stage['title']}（基础巩固）"
                    break
        elif avg_correctness > 0.9:
            # 标记当前阶段完成，推进到下一阶段
            current = path.get("current_stage", 1)
            for stage in path.get("path", []):
                if stage.get("stage") == current:
                    stage["completed"] = True
                    break
            path["current_stage"] = current + 1

        return path

    def _downgrade_difficulty(self, current: str) -> str:
        levels = ["beginner", "intermediate", "advanced", "expert"]
        idx = levels.index(current) if current in levels else 0
        return levels[max(0, idx - 1)]

    def _upgrade_difficulty(self, current: str) -> str:
        levels = ["beginner", "intermediate", "advanced", "expert"]
        idx = levels.index(current) if current in levels else 0
        return levels[min(len(levels) - 1, idx + 1)]

    async def run(self, state: dict = None, user_answer: dict = None, **kwargs) -> dict:
        if state and user_answer:
            return await self.handle_feedback(state, user_answer)
        return state or {}
