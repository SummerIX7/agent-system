"""真实 LLM 全链路端到端实测脚本。

跑一次完整 run_workflow（真实 API），实时打印节点进度，结束后自动归档：
- reports/real_llm_YYYYMMDD_HHMM.md   人类可读报告（时间线 / 评分 / 辩论 / 工具统计 / 内容长度）
- reports/real_llm_YYYYMMDD_HHMM.json 原始数据（节点耗时 / LLM 调用明细（prompt 截断）/ token 用量）

用法（在 backend 目录下）：
    python scripts/run_real_e2e.py
    python scripts/run_real_e2e.py --topic "数控车床编程与操作" --learner scripts/e2e_learner.json
    MOCK_MODE=false USE_AGENT_TOOLS=true python scripts/run_real_e2e.py --mock   # 显式 Mock 冒烟

注意：真实模式跑一次约 20~30 分钟、上百次 LLM 调用，请确认 .env 配置与 API 额度。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))  # 直接以 `python scripts/xxx.py` 运行时保证可导入 app
DEFAULT_REPORTS_DIR = BACKEND_DIR / "reports"

DEFAULT_LEARNER = {
    "education_background": "高职",
    "major": "机械制造",
    "work_experience_years": 1,
    "self_assessment": {"数控编程": "了解基础", "机床操作": "有一定经验"},
    "goals": ["数控车床编程与操作"],
    "career_track": "operator",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="真实 LLM 全链路端到端实测")
    parser.add_argument("--topic", default="数控车床编程与操作", help="学习主题")
    parser.add_argument("--learner", default="", help="学习者画像 JSON 文件路径（默认内置样例）")
    parser.add_argument("--session-id", default="", help="会话 ID（默认自动生成）")
    parser.add_argument("--output-dir", default=str(DEFAULT_REPORTS_DIR), help="报告输出目录")
    parser.add_argument("--mock", action="store_true", help="强制 MOCK_MODE=true（冒烟用）")
    return parser.parse_args()


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


async def run_with_progress(session_id: str, learner: dict, topic: str) -> tuple[dict, list, float]:
    from app.graph.workflow import run_workflow
    from app.core.store import get_trace_entries

    task = asyncio.create_task(run_workflow(
        learner_input=learner, topic=topic, session_id=session_id, profile={}))
    t0 = time.time()
    last_nodes = 0
    timeline = []
    while not task.done():
        await asyncio.sleep(15)
        entries = get_trace_entries(session_id)
        if len(entries) != last_nodes:
            last_nodes = len(entries)
            line = f"{time.time() - t0:.0f}s | 节点完成: {entries[-1]['node']} ({entries[-1]['duration_ms'] / 1000:.0f}s)"
            log(line)
            timeline.append(line)
    result = task.result()
    return result, get_trace_entries(session_id), time.time() - t0


def summarize(session_id: str, topic: str, learner: dict, result: dict,
              entries: list, total_seconds: float, timeline: list[str]) -> dict:
    """汇总本次运行的指标（写入 JSON 的核心结构）。"""
    tool_counter = Counter(
        tc["name"]
        for e in entries for c in e.get("llm_calls", []) for tc in c.get("tool_calls", [])
    )
    usage_total = Counter()
    for e in entries:
        for c in e.get("llm_calls", []):
            u = c.get("usage") or {}
            if u.get("total_tokens"):
                usage_total["input"] += u.get("input") or 0
                usage_total["output"] += u.get("output") or 0
                usage_total["total"] += u.get("total") or 0

    lecture = next((r for r in result["final_resources"]
                    if r.get("type") == "lecture" and r.get("stage") == 1), None)
    degraded = any("质量提醒" in str(r.get("content", ""))
                   for r in result["final_resources"] if r.get("type") != "learning_path")

    return {
        "session_id": session_id,
        "topic": topic,
        "learner": learner,
        "finished_at": datetime.now().isoformat(),
        "total_seconds": round(total_seconds, 1),
        "retry_count": result["retry_count"],
        "resources_count": len(result["final_resources"]),
        "degraded": degraded,
        "node_durations": [(e["node"], round(e["duration_ms"] / 1000)) for e in entries],
        "review_scores": {ct: round(r.get("score", 0), 2)
                          for ct, r in result["review_results"].items()},
        "debate_rounds": {ct: r.get("debate_rounds", 0)
                          for ct, r in result["review_results"].items()},
        "tool_calls": dict(tool_counter),
        "tool_calls_total": sum(tool_counter.values()),
        "token_usage": dict(usage_total) if usage_total else None,
        "lecture_chars": len(lecture["content"]) if lecture else 0,
        "timeline": timeline,
        "decision_log": result["decision_log"],
    }


def write_reports(summary: dict, entries: list, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    json_path = output_dir / f"real_llm_{stamp}.json"
    md_path = output_dir / f"real_llm_{stamp}.md"

    # JSON：节点明细 + LLM 调用明细（prompt/response 截断，控制体积）
    detail = {
        **summary,
        "nodes": [
            {
                "node": e["node"],
                "agent_name": e.get("agent_name", ""),
                "duration_ms": e["duration_ms"],
                "llm_calls": [
                    {
                        "label": c.get("label", ""),
                        "elapsed_ms": c.get("elapsed_ms"),
                        "cache_hit": c.get("cache_hit"),
                        "usage": c.get("usage"),
                        "tool_calls": c.get("tool_calls"),
                        "prompt_preview": str(c.get("prompt", ""))[:500],
                        "response_preview": str(c.get("response", ""))[:500],
                    }
                    for c in e.get("llm_calls", [])
                ],
            }
            for e in entries
        ],
    }
    json_path.write_text(json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8")

    node_times = " → ".join(f"{n}({d}s)" for n, d in summary["node_durations"])
    scores = ", ".join(f"{k}={v}" for k, v in summary["review_scores"].items())
    debates = ", ".join(f"{k}={v}轮" for k, v in summary["debate_rounds"].items())
    tools = ", ".join(f"{k}×{v}" for k, v in sorted(
        summary["tool_calls"].items(), key=lambda x: -x[1]))
    usage = summary.get("token_usage")
    usage_line = (f"input {usage['input']} + output {usage['output']} = {usage['total']} tokens"
                  if usage else "（未采集）")

    md_path.write_text(f"""# 真实 LLM 全链路实测 {stamp}

- 会话：`{summary['session_id']}` | 主题：{summary['topic']}
- 总耗时：**{summary['total_seconds']}s（{summary['total_seconds'] / 60:.1f} min）**
- 重试：{summary['retry_count']} 次 | 资源：{summary['resources_count']} 个 | 讲义：{summary['lecture_chars']} 字 | 降级：{'是' if summary['degraded'] else '否'}
- 审核评分：{scores}
- 辩论轮次：{debates}
- 工具调用（{summary['tool_calls_total']} 次）：{tools or '无'}
- Token 用量：{usage_line}
- 节点时间线：{node_times}

## 决策日志

```
{chr(10).join(summary['decision_log'])}
```
""", encoding="utf-8")
    return md_path, json_path


async def main_async(args: argparse.Namespace) -> None:
    if args.mock:
        # Settings 尚未加载（lru_cache 未实例化），环境变量方式生效
        os.environ["MOCK_MODE"] = "true"

    from app.core.config import get_settings
    from app.core.store import redis_is_available

    learner = json.loads(Path(args.learner).read_text(encoding="utf-8")) if args.learner else DEFAULT_LEARNER
    session_id = args.session_id or f"e2e-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    settings = get_settings()
    log(f"MOCK_MODE={settings.MOCK_MODE} | Redis={'可用' if redis_is_available() else '不可用（内存降级）'} | "
        f"模型={settings.LLM_MODEL} | 会话={session_id}")
    if not settings.MOCK_MODE and not settings.LLM_API_KEY:
        raise SystemExit("真实模式下 LLM_API_KEY 为空，请先配置 .env")

    result, entries, total = await run_with_progress(session_id, learner, args.topic)
    summary = summarize(session_id, args.topic, learner, result, entries, total, [])
    # timeline 在 run_with_progress 内部已打印，这里从日志不可得，重新按节点生成
    summary["timeline"] = [f"{n} 完成（{d}s）" for n, d in summary["node_durations"]]
    md_path, json_path = write_reports(summary, entries, Path(args.output_dir))
    log(f"=== 总耗时 {total:.0f}s | 重试 {summary['retry_count']} | 资源 {summary['resources_count']} "
        f"| 讲义 {summary['lecture_chars']} 字 | 工具 {summary['tool_calls_total']} 次")
    log(f"报告已归档: {md_path}")
    log(f"原始数据: {json_path}")


if __name__ == "__main__":
    asyncio.run(main_async(parse_args()))
