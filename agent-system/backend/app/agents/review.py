import json
import re as _re

from app.agents.base import BaseAgent
from app.agents.tools import REVIEW_TOOLS


class ReviewAgent(BaseAgent):
    """内容审核纠偏 Agent：交叉验证生成内容的专业准确性"""

    def _parse_issues(self, response: str) -> list:
        """解析 LLM 返回的问题列表，兼容新旧格式"""
        cleaned = response.strip()
        # 去除 markdown 代码块
        for prefix in ["```json", "```"]:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

        try:
            result = json.loads(cleaned)
        except json.JSONDecodeError:
            # 尝试正则提取 JSON 数组
            match = _re.search(r'\[.*\]', cleaned, _re.DOTALL)
            if match:
                try:
                    result = json.loads(match.group(0))
                except json.JSONDecodeError:
                    return []
            else:
                return []

        # 统一格式：兼容旧格式（纯字符串列表）和新格式（对象列表）
        parsed = []
        for item in (result if isinstance(result, list) else []):
            if isinstance(item, str):
                parsed.append({"issue": item, "severity": "minor"})
            elif isinstance(item, dict):
                parsed.append({
                    "issue": item.get("issue", str(item)),
                    "severity": item.get("severity", "minor"),
                })
        return parsed

    def _merge_issues(self, issues_a: list, issues_b: list) -> list:
        """合并两个视角的问题，按内容去重，保留最高严重度"""
        severity_rank = {"critical": 3, "minor": 2, "suggestion": 1}
        merged = {}
        for item in issues_a + issues_b:
            key = item["issue"][:200]  # 用前200字符作为去重键（修复前80字符导致的同问题计两次）
            if key not in merged or severity_rank.get(item["severity"], 1) > severity_rank.get(merged[key]["severity"], 0):
                merged[key] = item
        return list(merged.values())

    def _severity_weighted_score(self, issues: list) -> float:
        """按问题严重度加权计算评分"""
        if not issues:
            return 1.0
        score = 1.0
        for item in issues:
            sev = item.get("severity", "minor")
            if sev == "critical":
                score -= 0.15
            elif sev == "minor":
                score -= 0.05
            else:  # suggestion
                score -= 0.02
        return max(0, score)

    def _robust_json_parse(self, response: str, default: dict) -> dict:
        """增强的 JSON 解析：正则提取 + 文本推断降级（与 judge.py 同级容错）"""
        cleaned = response.strip()

        # 1. 去除 markdown 代码块
        for prefix in ["```json", "```"]:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

        # 2. 尝试直接解析
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # 3. 正则提取第一个完整 JSON 对象或数组
        for pattern in [r'\{.*\}', r'\[.*\]']:
            match = _re.search(pattern, cleaned, _re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass

        # 4. 降级：返回默认值
        return default

    async def _generate_correction(self, content: str, topic: str,
                                   issues: list, context: str) -> str:
        """根据审核发现的问题，生成修正后的内容"""
        issues_text = "\n".join([
            f"{idx}. [{item['severity']}] {item['issue']}"
            for idx, item in enumerate(issues, 1)
        ])

        prompt = f"""你是一位内容修正专家。以下内容经双视角审核后发现若干问题，请逐一修正。

[参考资料（修正依据）]
{context if context else "（无可用参考资料，请基于专业知识修正）"}

[原始内容]
{content}

[审核发现的问题]
{issues_text}

[修正要求]
1. 逐条修正上述所有问题，确保修正后的内容与参考资料一致
2. 保持原有 Markdown 结构和风格
3. 如果某个问题不成立（质疑有误），保持原内容不变
4. 输出修正后的完整 Markdown 内容，不要遗漏任何章节

请输出修正后的完整内容："""

        return await self.call_llm(prompt, label="修正生成")

    async def _verify_fixes(self, original: str, corrected: str,
                            issues: list, context: str) -> dict:
        """对比修正前后，判断问题是否被有效解决（替代不稳定的0-1数值评分）"""
        issues_text = "\n".join([
            f"{idx}. [{item['severity']}] {item['issue']}"
            for idx, item in enumerate(issues, 1)
        ])

        prompt = f"""请对比修正前后的内容，判断审核发现的问题是否已被有效解决。

[参考资料]
{context[:2000] if context else "（无参考资料）"}

[审核发现的问题]
{issues_text}

[修正前的内容]
{original[:2000]}

[修正后的内容]
{corrected[:2000]}

[判断标准]
- 如果修正针对性地解决了大部分问题（尤其是 critical 级别），且修正后的内容与参考资料一致，判定为 resolved
- 如果修正仅做了表面修改，核心问题仍在，或修正后引入了新的错误，判定为 unresolved

输出 JSON：
{{"verdict": "resolved"/"unresolved", "reason": "简要说明修正是否有效"}}

只输出 JSON，不要其他文字。"""

        response = await self.call_llm(prompt, label="修正验证")
        result = self._robust_json_parse(response, {
            "verdict": "unresolved",
            "reason": "验证响应解析失败",
        })
        return {
            "passed": result.get("verdict") == "resolved",
            "reason": result.get("reason", ""),
        }

    async def corrective_review(self, content: str, topic: str) -> dict:
        """
        合并审查+修正：双视角审查 → 评分 → 必要时修正 → 返回最终结果

        这是预审+辩论合并后的单一审核节点，在同一个方法内完成
        '发现问题 → 判断严重度 → 修正 → 再次评分' 的完整闭环。
        """
        # 检索知识库
        context = self.retrieve_context(topic, k=8)

        # ── 1. 双视角并行审查 ──
        # 学术审查者视角
        prompt_a = f"""你是一位严格的学术审查者。请**对照参考资料**，审查以下内容的学术准确性。

[参考资料]
{context if context else "（无可用参考资料，请基于常识判断）"}

[待审核内容]
{content}

请逐条核实：概念定义是否正确、理论推导是否严谨、引用来源是否可靠。
仅当你确认某条陈述与参考资料明确矛盾时才标记为问题。不确定或参考资料未覆盖的事项不要列为问题。

输出 JSON 数组，每个问题标注严重度：
[
  {{{{"issue": "问题描述", "severity": "critical"}}}},
  {{{{"issue": "问题描述", "severity": "minor"}}}},
  {{{{"issue": "问题描述", "severity": "suggestion"}}}}
]

severity 取值：
- "critical": 事实性错误、概念定义错误、编造不存在的内容/API/函数
- "minor": 表述不精确、推理不严谨、缺乏引用来源
- "suggestion": 优化建议、风格改进、补充说明建议

如无任何问题，输出空数组 []。"""

        # 工业实践者视角
        prompt_b = f"""你是一位有10年行业经验的实践专家。请**对照参考资料**，审查以下内容的实操可行性。

[参考资料]
{context if context else "（无可用参考资料，请基于常识判断）"}

[待审核内容]
{content}

请逐条核实：操作步骤是否可复现、代码是否可运行、是否符合行业规范。
仅当你确认某条陈述与参考资料明确矛盾或存在实际执行障碍时才标记为问题。不确定的事项不要列为问题。

输出 JSON 数组，每个问题标注严重度：
[
  {{{{"issue": "问题描述", "severity": "critical"}}}},
  {{{{"issue": "问题描述", "severity": "minor"}}}},
  {{{{"issue": "问题描述", "severity": "suggestion"}}}}
]

severity 取值同上。
如无任何问题，输出空数组 []。"""

        # 并行调用两个视角（可按需调用 fact_check_lookup 核查具体断言）
        response_a = await self.call_llm_with_tools(prompt_a, REVIEW_TOOLS, label="学术审查")
        response_b = await self.call_llm_with_tools(prompt_b, REVIEW_TOOLS, label="工业审查")

        issues_a = self._parse_issues(response_a)
        issues_b = self._parse_issues(response_b)
        all_issues = self._merge_issues(issues_a, issues_b)

        # ── 2. severity-weighted 评分 ──
        score = self._severity_weighted_score(all_issues)

        # ── 3. 如果通过，直接返回原始内容 ──
        if score >= 0.70:
            return {
                "passed": True,
                "score": score,
                "issues": [i["issue"] for i in all_issues],
                "suggestions": [f"({i['severity']}): {i['issue']}" for i in all_issues],
                "final_content": content,
                "correction_applied": False,
            }

        # ── 4. 不通过 → 生成修正内容 ──
        corrected = await self._generate_correction(content, topic, all_issues, context)

        # ── 5. 对比验证：判断问题是否被有效解决 ──
        fix_result = await self._verify_fixes(content, corrected, all_issues, context)

        # 构建反馈问题
        feedback_issues = [i["issue"] for i in all_issues]
        if not fix_result["passed"]:
            feedback_issues.append(
                f"修正验证未通过（{fix_result.get('reason', '未知原因')}），"
                "请重新生成更准确的内容，严格对照参考资料逐条核实"
            )

        return {
            "passed": fix_result["passed"],
            "score": score,
            "issues": feedback_issues,
            "suggestions": [f"({i['severity']}): {i['issue']}" for i in all_issues],
            "final_content": corrected if fix_result["passed"] else content,
            "correction_applied": True,
            "original_score": score,
        }

