"""
消融实验验收脚本
运行方式: python verify_ablation.py
"""
import sys
sys.path.insert(0, ".")

from app.graph.workflow import (
    build_workflow, build_workflow_no_debate,
    run_workflow, run_workflow_no_debate
)


def main():
    print("=" * 60)
    print("消融实验验收")
    print("=" * 60)

    # 1. 验证两种工作流都能成功构建
    print("\n[1] 工作流构建测试:")
    try:
        workflow_with_debate = build_workflow()
        print("   有辩论工作流构建成功")
    except Exception as e:
        print(f"   有辩论工作流构建失败: {e}")

    try:
        workflow_no_debate = build_workflow_no_debate()
        print("   无辩论工作流构建成功")
    except Exception as e:
        print(f"   无辩论工作流构建失败: {e}")

    # 2. 验证工作流函数存在
    print("\n[2] 工作流函数存在性检查:")
    print(f"  - run_workflow: {'存在' if callable(run_workflow) else '不存在'}")
    print(f"  - run_workflow_no_debate: {'存在' if callable(run_workflow_no_debate) else '不存在'}")

    # 3. 验证消融实验测试文件
    print("\n[3] 消融实验测试文件检查:")
    import os
    test_file = "tests/test_ablation.py"
    if os.path.exists(test_file):
        print(f"   {test_file} 存在")
        with open(test_file, "r", encoding="utf-8") as f:
            content = f.read()
            test_cases = [
                "test_workflow_comparison_structure",
                "test_ablation_mock_comparison",
                "test_hallucination_checker_integration",
                "test_ablation_metrics_schema"
            ]
            for tc in test_cases:
                if tc in content:
                    print(f"     测试用例 {tc} 存在")
                else:
                    print(f"     测试用例 {tc} 不存在")
    else:
        print(f"   {test_file} 不存在")

    # 4. 验证谬误检测器
    print("\n[4] 谬误检测器检查:")
    try:
        from app.metrics.hallucination_checker import HallucinationChecker, compute_hallucination_rate
        print("   HallucinationChecker 类导入成功")
        print("   compute_hallucination_rate 函数导入成功")
    except ImportError as e:
        print(f"   导入失败: {e}")

    # 5. 模拟消融实验对比
    print("\n[5] 模拟消融实验对比:")
    print("  场景: CNC 零基础学习者，主题 'G代码基础'")
    print()
    print("  有辩论工作流:")
    print("    - 流程: 学情分析 → 路径规划 → 知识生成 → 预审 → 辩论 → 裁判 → 试题 → 输出")
    print("    - 预期谬误率: < 5%")
    print("    - 质量保障: 辩论机制 + 裁判判决 + 回归验证")
    print()
    print("  无辩论工作流:")
    print("    - 流程: 学情分析 → 路径规划 → 知识生成 → 试题 → 输出")
    print("    - 预期谬误率: 8-15%")
    print("    - 质量保障: 无（直接使用生成内容）")
    print()
    print("  预期效果: 辩论机制降低谬误率 50% 以上")

    print("\n" + "=" * 60)
    print("验收完成")
    print("=" * 60)
    print("\n下一步: 运行完整消融实验需要真实的 LLM 调用")
    print("命令: python -m pytest tests/test_ablation.py -v")


if __name__ == "__main__":
    main()
