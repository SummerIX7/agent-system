"""
指标验证脚本
验证三项核心指标：
1. 知识谬误率（幻觉率） < 5%
2. 学习者画像-资源难度匹配准确率 ≥ 85%
3. 知识点覆盖率 ≥ 90%
"""

import json
import asyncio
from pathlib import Path

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
    方法：用审核 Agent 验证生成内容的准确性
    """
    from app.agents.review import ReviewAgent
    from app.agents.generation import GenerationAgent

    review_agent = ReviewAgent()
    gen_agent = GenerationAgent()
    profiles = load_profiles()

    total_checks = 0
    errors = 0
    results = []

    for profile in profiles:
        topic = "Python 数据分析基础"
        difficulty = profile.get("expected_difficulty", "beginner")

        # 生成内容
        content = await gen_agent.generate_lecture_notes(topic, {"recommended_difficulty": difficulty})

        # 审核验证
        review_result = await review_agent.verify(content, topic)

        total_checks += 1
        if not review_result.passed:
            errors += 1

        results.append({
            "profile": profile["profile_name"],
            "passed": review_result.passed,
            "score": review_result.score,
            "issues": review_result.issues,
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
        print(f"\n  [{r['profile']}] 得分: {r['score']:.2f}, 通过: {r['passed']}")
        if r['issues']:
            for issue in r['issues'][:3]:
                print(f"    - {issue}")

    return error_rate < 0.05


async def test_difficulty_match():
    """
    测试难度匹配准确率（目标 ≥ 85%）
    方法：对比画像推荐难度与实际生成资源难度
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
        diag_result = await diag_agent.run(profile)
        actual = diag_result.get("difficulty", "beginner")

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

    # Python 数据分析核心知识点
    core_topics = [
        "NumPy 数组创建",
        "NumPy 索引切片",
        "Pandas DataFrame",
        "Pandas 数据清洗",
        "Matplotlib 基础图表",
        "数据分组聚合",
    ]

    covered = 0
    total = len(core_topics)
    results = []

    for topic in core_topics:
        content = await gen_agent.generate_lecture_notes(topic, {"recommended_difficulty": "beginner"})
        # 简单检查：内容长度 > 200 字且包含关键词
        is_covered = len(content) > 200 and topic.split()[0] in content

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
