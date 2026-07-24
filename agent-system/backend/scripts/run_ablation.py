"""消融实验闭环脚本（8.2）。

对比"有审核纠偏"（run_workflow）与"无审核"（run_workflow_no_debate）两种工作流
在三项指标上的差异：知识谬误率 / 难度匹配率 / 知识点覆盖率。

用法：
    python scripts/run_ablation.py --profiles 3 --mock
    python scripts/run_ablation.py --profiles 8 --output reports/my_ablation.md --no-mock

默认使用 MOCK 模式（不访问外部 API），便于无 Key 复现。
产物同时输出 Markdown 对比表与 CSV 到 reports/ 目录。
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROFILES_FILE = Path(__file__).resolve().parent / "ablation_profiles.json"
DEFAULT_REPORTS_DIR = BACKEND_DIR / "reports"

METRIC_KEYS = ("hallucination_rate", "difficulty_match_rate", "knowledge_coverage_rate")
METRIC_LABELS = {
    "hallucination_rate": "谬误率(%)",
    "difficulty_match_rate": "难度匹配率(%)",
    "knowledge_coverage_rate": "知识覆盖率(%)",
}


def load_profiles(count: int) -> list[dict]:
    """加载画像 fixtures，按需循环扩展到 count 个。"""
    with open(PROFILES_FILE, "r", encoding="utf-8") as f:
        base = json.load(f)
    if not base:
        raise RuntimeError(f"画像文件为空: {PROFILES_FILE}")
    profiles: list[dict] = []
    for i in range(count):
        src = base[i % len(base)]
        p = dict(src)
        if i >= len(base):
            p["profile_name"] = f"{src['profile_name']}#{i // len(base) + 1}"
        profiles.append(p)
    return profiles


def _extract_metric_inputs(result: dict) -> tuple[list[str], list[str]]:
    """从工作流结果中提取文本内容与难度列表（跳过非字符串内容如 learning_path）。"""
    all_content: list[str] = []
    all_difficulties: list[str] = []
    for res in result.get("final_resources", []):
        content = res.get("content", "")
        if isinstance(content, str) and content.strip():
            all_content.append(content)
        difficulty = res.get("difficulty")
        if difficulty:
            all_difficulties.append(difficulty)
    return all_content, all_difficulties


async def _run_variant(run_fn, profile: dict, topic: str, session_id: str) -> dict:
    """运行单个工作流变体并计算三项指标。"""
    from app.metrics.report_builder import build_report_cache

    result = await run_fn(learner_input=dict(profile), topic=topic, session_id=session_id)
    all_content, all_difficulties = _extract_metric_inputs(result)
    enriched_profile = result.get("profile", {}) or {}
    cache = await build_report_cache(
        all_content=all_content,
        all_difficulties=all_difficulties,
        topic=topic,
        profile=enriched_profile,
        learning_path=result.get("learning_path", {}) or {},
    )
    return {k: cache.get(k) for k in METRIC_KEYS}


async def run_ablation(profiles: list[dict]) -> list[dict]:
    """对每个画像分别运行有审核 / 无审核工作流，返回逐画像指标记录。"""
    from app.graph.workflow import run_workflow, run_workflow_no_debate

    rows: list[dict] = []
    for idx, profile in enumerate(profiles):
        name = profile.get("profile_name", f"profile_{idx}")
        topic = profile.get("topic") or (profile.get("goals") or ["通用主题"])[0]
        print(f"[{idx + 1}/{len(profiles)}] 运行画像: {name} (topic={topic})")

        with_debate = await _run_variant(
            run_workflow, profile, topic, f"ablation-debate-{idx}"
        )
        no_debate = await _run_variant(
            run_workflow_no_debate, profile, topic, f"ablation-nodebate-{idx}"
        )
        rows.append({
            "profile": name,
            "topic": topic,
            "with_debate": with_debate,
            "no_debate": no_debate,
        })
    return rows


def _avg(values: list[float]) -> float | None:
    nums = [v for v in values if isinstance(v, (int, float))]
    return round(sum(nums) / len(nums), 2) if nums else None


def _aggregate(rows: list[dict]) -> dict:
    agg = {"with_debate": {}, "no_debate": {}}
    for variant in ("with_debate", "no_debate"):
        for k in METRIC_KEYS:
            agg[variant][k] = _avg([r[variant].get(k) for r in rows])
    return agg


def _fmt(v) -> str:
    return "N/A" if v is None else f"{v:.2f}"


def _delta(with_v, no_v) -> str:
    if with_v is None or no_v is None:
        return "N/A"
    return f"{with_v - no_v:+.2f}"


def write_csv(rows: list[dict], agg: dict, path: Path) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["画像", "主题", "变体", *[METRIC_LABELS[k] for k in METRIC_KEYS]])
        for r in rows:
            for variant, label in (("with_debate", "有审核"), ("no_debate", "无审核")):
                writer.writerow([
                    r["profile"], r["topic"], label,
                    *[_fmt(r[variant].get(k)) for k in METRIC_KEYS],
                ])
        writer.writerow([])
        for variant, label in (("with_debate", "平均-有审核"), ("no_debate", "平均-无审核")):
            writer.writerow(["", "", label, *[_fmt(agg[variant][k]) for k in METRIC_KEYS]])


def write_markdown(rows: list[dict], agg: dict, path: Path, mock: bool, count: int) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: list[str] = []
    lines.append("# 消融实验报告：审核纠偏机制对内容质量的影响")
    lines.append("")
    lines.append(f"- 生成时间：{now}")
    lines.append(f"- 画像数量：{count}")
    lines.append(f"- 运行模式：{'MOCK（本地模拟）' if mock else '真实 LLM'}")
    lines.append("")
    lines.append("## 汇总对比（平均值）")
    lines.append("")
    lines.append("| 指标 | 有审核纠偏 | 无审核 | 差值(有-无) |")
    lines.append("|------|-----------|--------|-------------|")
    for k in METRIC_KEYS:
        w, n = agg["with_debate"][k], agg["no_debate"][k]
        lines.append(f"| {METRIC_LABELS[k]} | {_fmt(w)} | {_fmt(n)} | {_delta(w, n)} |")
    lines.append("")
    lines.append("> 谬误率越低越好；难度匹配率、知识覆盖率越高越好。")
    lines.append("")
    lines.append("## 逐画像明细")
    lines.append("")
    header = "| 画像 | 主题 | 变体 | " + " | ".join(METRIC_LABELS[k] for k in METRIC_KEYS) + " |"
    sep = "|------|------|------|" + "|".join(["------"] * len(METRIC_KEYS)) + "|"
    lines.append(header)
    lines.append(sep)
    for r in rows:
        for variant, label in (("with_debate", "有审核"), ("no_debate", "无审核")):
            cells = " | ".join(_fmt(r[variant].get(k)) for k in METRIC_KEYS)
            lines.append(f"| {r['profile']} | {r['topic']} | {label} | {cells} |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="消融实验闭环：有/无审核纠偏对比")
    parser.add_argument("--profiles", type=int, default=3, help="画像数量（3~64）")
    parser.add_argument("--output", type=str, default="", help="Markdown 输出路径")
    mock_group = parser.add_mutually_exclusive_group()
    mock_group.add_argument("--mock", dest="mock", action="store_true", help="使用 MOCK 模式（默认）")
    mock_group.add_argument("--no-mock", dest="mock", action="store_false", help="使用真实 LLM")
    parser.set_defaults(mock=True)
    args = parser.parse_args()

    count = max(1, min(args.profiles, 64))

    # 必须在导入 app 模块前设置 MOCK_MODE，pydantic-settings 在导入时读取环境变量
    if args.mock:
        os.environ["MOCK_MODE"] = "true"

    import sys
    sys.path.insert(0, str(BACKEND_DIR))

    DEFAULT_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = Path(args.output) if args.output else DEFAULT_REPORTS_DIR / f"ablation_{date_tag}.md"
    if not md_path.is_absolute():
        md_path = BACKEND_DIR / md_path
    md_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path = md_path.with_suffix(".csv")

    profiles = load_profiles(count)
    rows = asyncio.run(run_ablation(profiles))
    agg = _aggregate(rows)

    write_csv(rows, agg, csv_path)
    write_markdown(rows, agg, md_path, args.mock, count)

    print(f"\n完成。共 {count} 个画像。")
    print(f"Markdown: {md_path}")
    print(f"CSV:      {csv_path}")


if __name__ == "__main__":
    main()
