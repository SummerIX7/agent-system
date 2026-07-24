"""
独立知识谬误率验证模块
对生成内容抽样，逐知识点进行事实核查，不依赖 Agent 自评评分
"""

import json
import logging
import random
import re
from typing import List, Dict, Any

from app.agents.base import BaseAgent
from app.core.llm import get_verifier_llm

logger = logging.getLogger(__name__)

# 断言分层类别（用于分层抽样，避免只采样某一类）
_ASSERTION_CATEGORIES = ("数值型", "步骤型", "定义型")
_STEP_KEYWORDS = ("先", "然后", "接着", "步骤", "第一步", "第二步", "首先", "其次", "再", "最后", "依次")


class HallucinationChecker(BaseAgent):
    """
    独立谬误检测器
    不依赖 Judge 评分，直接通过 RAG 检索进行事实核查。
    默认使用跨模型的校验 LLM（VERIFIER_LLM_*），与生成模型解耦以降低自评偏差。
    """

    def __init__(self, llm=None):
        super().__init__(llm=llm or get_verifier_llm())

    async def check_content(self, content: str, topic: str) -> dict:
        """
        对内容中每个"断言"进行独立事实核查。

        流程：提取断言 → RAG 检索 → LLM 逐条比对 → 判定真/伪/无法验证

        返回：
            total_assertions: 总断言数
            errors: 错误断言数
            unverifiable: 无法验证断言数
            hallucination_rate: 谬误率 (0-1)
            details: 每条断言的判定详情
            method: 验证方法说明
        """
        # 1. 用 LLM 从 content 中提取可验证的"事实断言"
        assertions = await self._extract_assertions(content)

        if not assertions:
            return {
                "total_assertions": 0,
                "errors": 0,
                "unverifiable": 0,
                "unverifiable_rate": 0,
                "reliability_score": 0,
                "hallucination_rate": 0,
                "details": [],
                "method": "独立事实核查 — RAG 知识库逐条比对（跨模型 + 分层抽样）",
            }

        # 2. 分层抽样（定义型/数值型/步骤型按比例抽，合计上限 20）再逐条验证
        sample = self._stratified_sample(assertions, cap=20)
        results = []
        for assertion in sample:
            try:
                context = self.retrieve_context(assertion, k=3)
                verdict = await self._verify_assertion(assertion, context, topic)
                results.append(verdict)
            except Exception as e:
                logger.warning(f"断言验证失败: {assertion[:50]}... 错误: {e}")
                results.append({
                    "assertion": assertion,
                    "verdict": "无法验证",
                    "reason": f"验证过程出错: {str(e)}",
                })

        # 3. 统计
        total = len(results)
        errors = sum(1 for r in results if r.get("verdict") == "错误")
        unverifiable = sum(1 for r in results if r.get("verdict") == "无法验证")
        correct = sum(1 for r in results if r.get("verdict") == "正确")

        # 谬误率 = 错误断言数 / 总断言数（保持原语义）
        hallucination_rate = errors / total if total > 0 else 0
        # 无法验证率：过多"无法验证"往往意味着含糊表达，需计入惩罚
        unverifiable_rate = unverifiable / total if total > 0 else 0
        # 可信度评分：正确率再按无法验证率打折，避免含糊表达绕过检测
        reliability_score = (correct / total) * (1 - 0.5 * unverifiable_rate) if total > 0 else 0

        return {
            "total_assertions": total,
            "correct": correct,
            "errors": errors,
            "unverifiable": unverifiable,
            "unverifiable_rate": round(unverifiable_rate, 4),
            "reliability_score": round(reliability_score, 4),
            "hallucination_rate": round(hallucination_rate, 4),
            "hallucination_rate_percent": round(hallucination_rate * 100, 1),
            "details": results,
            "method": "独立事实核查 — RAG 知识库逐条比对（跨模型 + 分层抽样）",
        }

    @staticmethod
    def _classify_assertion(assertion: str) -> str:
        """启发式将断言分类为 数值型 / 步骤型 / 定义型"""
        # 数值型：含数字（含范围、单位）
        if re.search(r"\d", assertion):
            return "数值型"
        # 步骤型：含流程关键词
        if any(kw in assertion for kw in _STEP_KEYWORDS):
            return "步骤型"
        return "定义型"

    def _stratified_sample(self, assertions: List[str], cap: int = 20) -> List[str]:
        """分层抽样：按类别比例分配名额，各类内随机抽取，合计不超过 cap"""
        if len(assertions) <= cap:
            return list(assertions)

        # 按类别分组
        groups: Dict[str, List[str]] = {c: [] for c in _ASSERTION_CATEGORIES}
        for a in assertions:
            groups[self._classify_assertion(a)].append(a)

        total = len(assertions)
        sample: List[str] = []
        # 按比例分配名额（向下取整），各组内随机抽
        remainders = []
        for cat, items in groups.items():
            if not items:
                continue
            exact = cap * len(items) / total
            quota = int(exact)
            quota = min(quota, len(items))
            picked = random.sample(items, quota) if quota > 0 else []
            sample.extend(picked)
            leftover = [x for x in items if x not in picked]
            remainders.append((exact - quota, leftover))

        # 用小数余量从大到小补齐到 cap
        remainders.sort(key=lambda t: t[0], reverse=True)
        for _, leftover in remainders:
            if len(sample) >= cap:
                break
            random.shuffle(leftover)
            for x in leftover:
                if len(sample) >= cap:
                    break
                sample.append(x)

        return sample[:cap]

    async def _extract_assertions(self, content: str) -> List[str]:
        """
        从内容中提取可验证的"事实断言"列表
        排除观点性陈述、泛泛而谈的介绍、无争议的背景描述
        """
        prompt = f"""请从以下学习内容中提取所有可验证的"事实断言"。

每条断言必须是一个可以被"正确/错误/无法验证"判定的陈述句。
排除以下类型：
- 观点性陈述（如"XX是最好的方法"）
- 泛泛而谈的介绍（如"XX是一个重要的概念"）
- 无争议的背景描述（如"本节将介绍..."）
- 主观评价（如"简单易学"）

保留以下类型：
- 具体的技术定义（如"G01是直线插补指令"）
- 数值参数（如"切削速度通常为100-200m/min"）
- 操作步骤（如"先对刀再设定工件坐标系"）
- 概念关系（如"进给量与表面粗糙度成正比"）

内容：
{content[:3000]}

以 JSON 数组返回，只包含 assertion 字段：
[{{"assertion": "G代码G01是直线插补指令"}}, {{"assertion": "..."}}, ...]

只输出 JSON，不要其他文字。"""

        response = await self.call_llm(prompt)

        try:
            # 清理响应，提取 JSON
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            assertions_data = json.loads(cleaned)

            # 提取 assertion 字段
            if isinstance(assertions_data, list):
                return [item.get("assertion", "") if isinstance(item, dict) else str(item)
                        for item in assertions_data
                        if item.get("assertion") or isinstance(item, str)]
            return []
        except json.JSONDecodeError as e:
            logger.warning(f"断言提取 JSON 解析失败: {e}")
            # 尝试简单的句号分割作为降级方案
            sentences = [s.strip() for s in content.split("。") if len(s.strip()) > 10]
            return sentences[:10]

    async def _verify_assertion(self, assertion: str, context: str, topic: str = "") -> Dict[str, Any]:
        """
        对照知识库上下文验证单条断言
        判定规则：
        - "正确"：知识库明确支持该断言
        - "错误"：知识库明确与该断言矛盾
        - "无法验证"：知识库中没有相关信息
        """
        prompt = f"""请验证以下断言是否与知识库内容一致。

[断言]
{assertion}

[主题]
{topic}

[知识库参考]
{context[:2000]}

[判定规则]
- "正确"：知识库明确支持该断言，或断言与知识库内容一致
- "错误"：知识库明确与该断言矛盾，或断言包含明显的事实错误
- "无法验证"：知识库中没有相关信息，无法判断对错

[注意事项]
1. 只关注事实准确性，不评价表述风格
2. 如果断言的核心事实正确，但表述略有差异，仍应判定为"正确"
3. 如果知识库没有相关信息，判定为"无法验证"而非"错误"
4. 如果断言包含多个子断言，只有全部正确才判定为"正确"

以 JSON 返回：
{{"verdict": "正确/错误/无法验证", "reason": "判定理由", "confidence": 0-1}}

只输出 JSON，不要其他文字。"""

        response = await self.call_llm(prompt)

        try:
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            result = json.loads(cleaned)
            return {
                "assertion": assertion,
                "verdict": result.get("verdict", "无法验证"),
                "reason": result.get("reason", ""),
                "confidence": result.get("confidence", 0.5),
            }
        except json.JSONDecodeError:
            return {
                "assertion": assertion,
                "verdict": "无法验证",
                "reason": "验证响应解析失败",
                "confidence": 0,
            }


# 全局单例
_checker: HallucinationChecker | None = None


def get_checker() -> HallucinationChecker:
    """获取谬误检测器单例"""
    global _checker
    if _checker is None:
        _checker = HallucinationChecker()
    return _checker


async def compute_hallucination_rate(content: str, topic: str) -> dict:
    """
    计算内容的谬误率（便捷函数）

    Args:
        content: 待检查的内容
        topic: 内容主题

    Returns:
        包含 hallucination_rate 和详细信息的字典
    """
    checker = get_checker()
    return await checker.check_content(content, topic)
