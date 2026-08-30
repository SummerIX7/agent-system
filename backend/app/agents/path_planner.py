import json

from app.agents.base import BaseAgent
from app.core.career_tracks import get_career_track_from_input


PATH_TEMPLATES = {
    "operator": [
        {
            "title": "安全规范与机床基础",
            "topics": ["安全操作规范", "5S现场管理", "设备日常点检", "机床启停与急停"],
            "estimated_hours": 4,
            "difficulty": "beginner",
        },
        {
            "title": "加工流程、工件装夹与校正",
            "topics": ["加工流程认知", "工件装夹与校正", "基准选择", "坐标方向与简单找正"],
            "estimated_hours": 6,
            "difficulty": "beginner",
        },
        {
            "title": "量具使用与尺寸检测",
            "topics": ["量具使用", "卡尺/千分尺使用", "简单尺寸检测", "测量记录与合格判断"],
            "estimated_hours": 5,
            "difficulty": "beginner",
        },
        {
            "title": "刀具更换与切削液管理",
            "topics": ["刀具更换流程", "刀具装卸操作", "切削液配比与管理", "刀具磨损与断刀识别"],
            "estimated_hours": 5,
            "difficulty": "beginner",
        },
        {
            "title": "程序识读、异常识别与综合实践",
            "topics": ["G代码基础识读", "程序运行前检查", "常见加工缺陷识别", "常见报警处理", "综合操作流程"],
            "estimated_hours": 8,
            "difficulty": "intermediate",
        },
    ],
    "setup_tech": [
        {
            "title": "安全复盘与调机准备",
            "topics": ["安全操作规范", "设备日常点检", "程序空运行与单段执行"],
            "estimated_hours": 6,
            "difficulty": "beginner",
        },
        {
            "title": "装夹定位、夹具与对刀",
            "topics": ["夹具定位与夹紧", "工件装夹与校正", "多种对刀方法"],
            "estimated_hours": 8,
            "difficulty": "intermediate",
        },
        {
            "title": "刀具补偿与切削参数设置",
            "topics": ["刀具补偿设置(G41/G42/G43)", "刀具选择与管理", "切削参数优化"],
            "estimated_hours": 8,
            "difficulty": "intermediate",
        },
        {
            "title": "首件检验与尺寸调整",
            "topics": ["首件检验流程", "尺寸超差分析与调整", "加工精度控制"],
            "estimated_hours": 6,
            "difficulty": "intermediate",
        },
        {
            "title": "换型调试、报警与综合排障",
            "topics": ["换型调试流程", "常见报警处理", "程序空运行与单段执行", "综合调机复盘"],
            "estimated_hours": 8,
            "difficulty": "advanced",
        },
    ],
    "programmer": [
        {
            "title": "工艺基础与程序安全",
            "topics": ["加工工艺规程设计", "安全操作规程", "程序运行前检查"],
            "estimated_hours": 8,
            "difficulty": "intermediate",
        },
        {
            "title": "G/M代码与手工编程",
            "topics": ["G代码/M代码编程", "坐标系与工件零点", "刀具补偿设置(G41/G42/G43)"],
            "estimated_hours": 10,
            "difficulty": "intermediate",
        },
        {
            "title": "CAD/CAM基础流程",
            "topics": ["CAD/CAM软件应用(UG/Mastercam)", "CAM基础流程", "后处理定制基础"],
            "estimated_hours": 10,
            "difficulty": "advanced",
        },
        {
            "title": "刀路优化、仿真与防撞",
            "topics": ["刀具路径优化策略", "加工仿真与碰撞检查", "切削参数优化"],
            "estimated_hours": 10,
            "difficulty": "advanced",
        },
        {
            "title": "宏程序、多轴与工艺标准化",
            "topics": ["B类宏程序编程", "四轴/五轴编程", "后处理定制", "工艺标准化与文档"],
            "estimated_hours": 12,
            "difficulty": "expert",
        },
    ],
}

DIFFICULTY_ORDER = ["beginner", "intermediate", "advanced", "expert"]


class PathPlannerAgent(BaseAgent):
    """路径规划 Agent：根据学情分析生成个性化学习路径"""

    def _floor_difficulty(self, template_difficulty: str, learner_difficulty: str) -> str:
        """按学习者画像给阶段难度兜底，避免高阶岗位被错误降到过低难度。"""
        if template_difficulty not in DIFFICULTY_ORDER:
            return learner_difficulty if learner_difficulty in DIFFICULTY_ORDER else "beginner"
        if learner_difficulty not in DIFFICULTY_ORDER:
            return template_difficulty
        return DIFFICULTY_ORDER[max(
            DIFFICULTY_ORDER.index(template_difficulty),
            DIFFICULTY_ORDER.index(learner_difficulty),
        )]

    def _build_template_path(self, profile: dict, topic: str) -> dict:
        track = get_career_track_from_input(profile or {})
        template = PATH_TEMPLATES.get(track.code, PATH_TEMPLATES["operator"])
        learner_difficulty = profile.get("recommended_difficulty") or profile.get("overall_level") or "beginner"

        path = []
        for idx, stage in enumerate(template, start=1):
            path.append({
                "stage": idx,
                "title": stage["title"],
                "topics": stage["topics"],
                "estimated_hours": stage["estimated_hours"],
                "difficulty": self._floor_difficulty(stage["difficulty"], learner_difficulty),
                "prerequisites": [] if idx == 1 else [template[idx - 2]["title"]],
                "resources_type": ["lecture", "guide", "project"],
                "completed": False,
                "basic_test_passed": False,
                "advanced_test_passed": False,
                "has_resources": True,
            })

        return {
            "path": path,
            "total_estimated_hours": sum(stage["estimated_hours"] for stage in template),
            "current_stage": 1,
            "career_track": track.code,
            "career_track_name": track.name,
            "recommended_order": "必须按 stage 1 → 5 顺序学习；在学习资源页完成当前节点后，下一节点才解锁。",
            "planning_topic": topic,
        }

    async def plan_path(self, profile: dict, topic: str) -> dict:
        """生成学习路径"""
        return self._build_template_path(profile or {}, topic)

    async def adjust_path(self, path: dict, feedback: dict) -> dict:
        """根据用户反馈调整学习路径

        注意：此方法基于单条反馈做 LLM 驱动的路径结构调整，
        与 orchestrator.adjust_learning_path() 的滑动窗口规则策略互补。
        """
        correctness = feedback.get("correctness", 0)
        current_stage = path.get("current_stage", 1)

        if correctness < 0.6:
            prompt = f"""学习者近期正确率为 {correctness:.0%}（偏低），当前在第 {current_stage} 阶段。请调整学习路径：
1. 在第 {current_stage} 阶段前插入基础知识补充阶段
2. 降低第 {current_stage} 阶段的难度

当前路径：{json.dumps(path, ensure_ascii=False)}

输出调整后的 JSON 路径。只输出 JSON。"""
        elif correctness > 0.9:
            prompt = f"""学习者近期正确率为 {correctness:.0%}（优秀），当前在第 {current_stage} 阶段。请调整学习路径：
1. 将第 {current_stage} 阶段标记为已完成
2. 跳过已覆盖的基础内容，推进到下一阶段

当前路径：{json.dumps(path, ensure_ascii=False)}

输出调整后的 JSON 路径。只输出 JSON。"""
        else:
            return path  # 无需调整

        response = await self.call_llm(prompt)
        try:
            adjusted = json.loads(response.strip().strip("```json").strip("```"))
        except json.JSONDecodeError:
            adjusted = path
        return adjusted

    async def run(self, profile: dict = None, topic: str = "", path: dict = None, feedback: dict = None, **kwargs) -> dict:
        if path and feedback:
            return await self.adjust_path(path, feedback)
        return await self.plan_path(profile or {}, topic)
