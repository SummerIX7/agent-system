"""
指标验证脚本
验证三项核心指标：
1. 知识谬误率（幻觉率） < 5%
2. 学习者画像-资源难度匹配准确率 ≥ 85%
3. 知识点覆盖率 ≥ 90%
"""

import json
import asyncio
import sys
import os
from pathlib import Path

# 添加 backend 目录到 Python 路径
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))
os.chdir(str(backend_dir))  # 切换工作目录到 backend，确保 .env 被加载

# 测试数据路径
TEST_DATA_DIR = Path(__file__).parent / "test_data"
PROFILES_DIR = TEST_DATA_DIR / "learner_profiles"


def load_profiles() -> list[dict]:
    """加载 3 组测试画像"""
    profiles = []
    for f in PROFILES_DIR.glob("*.json"):
        with open(f, "r", encoding="utf-8") as fp:
            profiles.append(json.load(fp))
    return profiles


async def test_knowledge_accuracy():
    """
    测试知识谬误率（目标 < 5%）
    方法：完整辩论流程 challenge → defend → judge，用裁判最终判决判定
    """
    from app.agents.generation import GenerationAgent
    from app.agents.debate import DebateManager
    from app.agents.judge import JudgeAgent

    gen_agent = GenerationAgent()
    debate_mgr = DebateManager()
    judge_agent = JudgeAgent()
    profiles = load_profiles()

    total_checks = 0
    errors = 0
    results = []

    for profile in profiles:
        topic = "CNC 数控编程基础"
        difficulty = profile.get("expected_difficulty", "beginner")
        learner_input = {
            "topic": topic,
            "profile": profile,
            "recommended_difficulty": difficulty,
        }

        # 1. 生成内容
        content = await gen_agent.generate_lecture_notes(topic, learner_input)

        # 2. 审核 Agent 质疑
        challenge_result = await debate_mgr.challenge(content, topic, "lecture_notes")
        issues = challenge_result.get("issues", [])

        # 3. 生成 Agent 辩护
        defend_result = await debate_mgr.defend(content, topic, issues)
        responses = defend_result.get("responses", [])
        revised_content = defend_result.get("revised_content", content)
        has_revision = defend_result.get("has_revision", False)

        # 4. 独立裁判判决
        final_content = revised_content if has_revision else content
        judge_result = await judge_agent.judge(
            original_content=content,
            topic=topic,
            content_type="lecture_notes",
            challenge_issues=issues,
            defend_responses=responses,
            revised_content=final_content,
        )

        passed = judge_result.get("passed", True)
        quality_score = judge_result.get("quality_score", 0.5)
        effective_issues = judge_result.get("effective_issues", [])
        reason = judge_result.get("reason", "")

        total_checks += 1
        if not passed:
            errors += 1

        results.append({
            "profile": profile["profile_name"],
            "passed": passed,
            "quality_score": quality_score,
            "effective_issues_count": len(effective_issues),
            "has_revision": has_revision,
            "reason": reason[:100],
        })

    error_rate = errors / total_checks if total_checks > 0 else 0

    print(f"\n{'='*60}")
    print(f"指标1：知识谬误率")
    print(f"{'='*60}")
    print(f"测试数量: {total_checks}")
    print(f"错误数量: {errors}")
    print(f"谬误率: {error_rate:.1%}")
    print(f"目标: < 5%")
    print(f"结果: {'✅ 达标' if error_rate < 0.05 else '❌ 未达标'}")
    print(f"{'='*60}")

    for r in results:
        status = "✅" if r['passed'] else "❌"
        print(f"  {status} [{r['profile']}] 质量分: {r['quality_score']:.2f}, "
              f"有效问题: {r['effective_issues_count']}, 有修正: {r['has_revision']}")
        if not r['passed']:
            print(f"    原因: {r['reason']}")

    return error_rate < 0.05


async def test_difficulty_match():
    """
    测试难度匹配准确率（目标 ≥ 85%）
    方法：对比画像推荐难度与诊断 Agent 输出难度
    """
    from app.agents.diagnosis import DiagnosisAgent

    diag_agent = DiagnosisAgent()
    profiles = load_profiles()

    total = 0
    matched = 0
    results = []

    for profile in profiles:
        expected = profile.get("expected_difficulty", "beginner")

        # 诊断
        diag_result = await diag_agent.build_profile(profile)
        actual = diag_result.get("recommended_difficulty", "beginner")

        total += 1
        is_match = expected == actual
        if is_match:
            matched += 1

        results.append({
            "profile": profile["profile_name"],
            "expected": expected,
            "actual": actual,
            "match": is_match,
        })

    match_rate = matched / total if total > 0 else 0

    print(f"\n{'='*60}")
    print(f"指标2：难度匹配准确率")
    print(f"{'='*60}")
    print(f"测试数量: {total}")
    print(f"匹配数量: {matched}")
    print(f"匹配率: {match_rate:.1%}")
    print(f"目标: ≥ 85%")
    print(f"结果: {'✅ 达标' if match_rate >= 0.85 else '❌ 未达标'}")
    print(f"{'='*60}")

    for r in results:
        status = "✅" if r['match'] else "❌"
        print(f"  {status} [{r['profile']}] 预期: {r['expected']}, 实际: {r['actual']}")

    return match_rate >= 0.85


async def test_knowledge_coverage():
    """
    测试知识点覆盖率（目标 ≥ 90%）
    方法：检查生成资源是否覆盖了主题的核心知识点
    """
    from app.agents.generation import GenerationAgent

    gen_agent = GenerationAgent()

    # CNC 数控编程核心知识点
    core_topics = [
        "G 代码基础指令",
        "数控车床编程",
        "数控铣床编程",
        "切削参数选择",
        "刀具选择与管理",
        "公差与配合",
    ]

    covered = 0
    total = len(core_topics)
    results = []

    for topic in core_topics:
        learner_input = {
            "topic": topic,
            "recommended_difficulty": "beginner",
        }
        content = await gen_agent.generate_lecture_notes(topic, learner_input)
        # 检查：内容长度 > 200 字且包含主题关键词
        keyword = topic.split()[0]
        is_covered = len(content) > 200 and keyword in content

        if is_covered:
            covered += 1

        results.append({
            "topic": topic,
            "covered": is_covered,
            "content_length": len(content),
        })

    coverage_rate = covered / total if total > 0 else 0

    print(f"\n{'='*60}")
    print(f"指标3：知识点覆盖率")
    print(f"{'='*60}")
    print(f"知识点数量: {total}")
    print(f"覆盖数量: {covered}")
    print(f"覆盖率: {coverage_rate:.1%}")
    print(f"目标: ≥ 90%")
    print(f"结果: {'✅ 达标' if coverage_rate >= 0.9 else '❌ 未达标'}")
    print(f"{'='*60}")

    for r in results:
        status = "✅" if r['covered'] else "❌"
        print(f"  {status} [{r['topic']}] 内容长度: {r['content_length']}")

    return coverage_rate >= 0.9


async def run_all_tests():
    """运行所有指标测试"""
    print("\n" + "🎯" * 20)
    print("三项核心指标验证")
    print("🎯" * 20)

    r1 = await test_knowledge_accuracy()
    r2 = await test_difficulty_match()
    r3 = await test_knowledge_coverage()

    print(f"\n{'='*60}")
    print(f"总结")
    print(f"{'='*60}")
    print(f"知识谬误率: {'✅' if r1 else '❌'}")
    print(f"难度匹配率: {'✅' if r2 else '❌'}")
    print(f"知识点覆盖率: {'✅' if r3 else '❌'}")
    print(f"总体: {'✅ 全部达标' if all([r1, r2, r3]) else '❌ 部分未达标'}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
