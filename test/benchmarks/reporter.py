"""
Reporting and Baseline Regression Comparator Module.

Generates CSV and Markdown benchmark summaries, evaluates metrics
against baseline SLA thresholds with configurable deviation gates,
and renders side-by-side Markdown comparison reports from run history.
"""

import csv
import json
from pathlib import Path
from typing import Dict, List, Any, Tuple


def generate_markdown_report(results: Dict[str, Any], output_path: Path) -> str:
    """Generate a clean Markdown summary table from all test results."""
    lines = [
        "# Model Acceptance & Performance Benchmark Report",
        "",
        f"- **Image Type**: `{results.get('image_type', 'N/A')}`",
        f"- **Deployment Profile**: `{results.get('profile', 'N/A')}`",
        f"- **Timestamp**: `{results.get('timestamp', 'N/A')}`",
        f"- **Overall Status**: `{'PASSED' if results.get('passed', True) else 'FAILED'}`",
        "",
    ]

    # 1. Bring-Up
    if "bringup" in results:
        b = results["bringup"]
        http_t = f"{b.get('http_ready_time_sec')}s" if b.get('http_ready_time_sec') is not None else "N/A"
        c_health_t = f"{b.get('container_healthy_time_sec')}s" if b.get('container_healthy_time_sec') is not None else "N/A"
        lines.extend([
            "## 1. Container Bring-Up & Readiness",
            "",
            "| Component | Endpoint | HTTP Ready (s) | Container Healthy (s) | Total Bringup (s) | Budget Limit (s) | Status |",
            "|---|---|---|---|---|---|---|",
            f"| {b.get('component')} | {b.get('endpoint')} | {http_t} | {c_health_t} | {b.get('bringup_time_sec')}s | {b.get('max_budget_sec')}s | {b.get('status')} |",
            "",
        ])

    # 2. LLM Inference
    if "llm" in results and results["llm"]:
        lines.extend([
            "## 2. LLM Inference Serving",
            "",
            "| Concurrency | Prompt Tokens | P95 TTFT (ms) | Avg ITL (ms/tok) | Aggregate Tokens/s | Error Rate (%) |",
            "|---|---|---|---|---|---|",
        ])
        for row in results["llm"]:
            lines.append(f"| {row['concurrency']} | {row['prompt_tokens']} | {row['p95_ttft_ms']}ms | {row['avg_itl_ms']}ms | {row['aggregate_tokens_per_sec']} | {row['error_rate_pct']}% |")
        lines.append("")

    # 3. Reranker
    if "reranker" in results and results["reranker"]:
        lines.extend([
            "## 3. Cross-Encoder Reranker",
            "",
            "| Candidate Docs | Avg Latency (ms) | P95 Latency (ms) | Throughput (docs/s) | Error Rate (%) |",
            "|---|---|---|---|---|",
        ])
        for row in results["reranker"]:
            lines.append(f"| {row['doc_count']} | {row['avg_latency_ms']}ms | {row['p95_latency_ms']}ms | {row['throughput_docs_per_sec']} | {row['error_rate_pct']}% |")
        lines.append("")

    # 4. Embedding
    if "embedding" in results and results["embedding"]:
        lines.extend([
            "## 4. Dense Vector Embedding",
            "",
            "| Batch Size | Avg Latency (ms) | P95 Latency (ms) | Throughput (texts/s) | Error Rate (%) |",
            "|---|---|---|---|---|",
        ])
        for row in results["embedding"]:
            lines.append(f"| {row['batch_size']} | {row['avg_latency_ms']}ms | {row['p95_latency_ms']}ms | {row['throughput_texts_per_sec']} | {row['error_rate_pct']}% |")
        lines.append("")

    # 5. Container & Server Metrics
    if "container_metrics" in results and results["container_metrics"].get("available"):
        m = results["container_metrics"]
        lines.extend([
            "## 5. Container & Server Runtime Metrics",
            "",
            "| Metric | Value |",
            "|---|---|",
            f"| KV Cache Utilization | {m.get('kv_cache_usage_pct', 0.0)}% |",
            f"| Requests Running | {m.get('num_requests_running', 0)} |",
            f"| Requests Waiting in Queue | {m.get('num_requests_waiting', 0)} |",
            f"| Requests Swapped | {m.get('num_requests_swapped', 0)} |",
            f"| Total Prompt Tokens Processed | {m.get('prompt_tokens_total', 0)} |",
            f"| Total Generation Tokens Produced | {m.get('generation_tokens_total', 0)} |",
            "",
        ])

    md_content = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(md_content)
    return md_content


def generate_csv_report(results: Dict[str, Any], output_path: Path):
    """Dump all flat metric rows to a CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = []

    if "bringup" in results:
        b = results["bringup"]
        rows.append({
            "suite": "bringup",
            "param": "startup",
            "metric_1": b.get("bringup_time_sec"),
            "metric_2": b.get("max_budget_sec"),
            "status": b.get("status")
        })

    for section in ["llm", "reranker", "embedding"]:
        if section in results and isinstance(results[section], list):
            for item in results[section]:
                rows.append(item)

    if rows:
        fieldnames = sorted(list({k for r in rows for k in r.keys()}))
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


def evaluate_against_baseline(
    current_results: Dict[str, Any],
    baseline_path: Path,
    tolerance_pct: float = 15.0
) -> Tuple[bool, List[str]]:
    """
    Compare measured results with baseline thresholds.
    Returns (passed, list_of_violations).
    """
    if not baseline_path.exists():
        return True, [f"Notice: Baseline file {baseline_path} not found. Skipping gate comparison."]

    with open(baseline_path, "r") as f:
        baseline = json.load(f)

    violations = []
    
    # Check LLM P95 TTFT
    if "llm" in current_results and "llm" in baseline:
        for cur, base in zip(current_results["llm"], baseline["llm"]):
            if cur.get("p95_ttft_ms") and base.get("p95_ttft_ms"):
                max_allowed = base["p95_ttft_ms"] * (1.0 + (tolerance_pct / 100.0))
                if cur["p95_ttft_ms"] > max_allowed:
                    violations.append(
                        f"LLM TTFT Regression: Concurrency {cur['concurrency']} measured {cur['p95_ttft_ms']}ms > baseline {base['p95_ttft_ms']}ms + {tolerance_pct}% ({max_allowed:.2f}ms)"
                    )

    # Check Reranker P95
    if "reranker" in current_results and "reranker" in baseline:
        for cur, base in zip(current_results["reranker"], baseline["reranker"]):
            if cur.get("p95_latency_ms") and base.get("p95_latency_ms"):
                max_allowed = base["p95_latency_ms"] * (1.0 + (tolerance_pct / 100.0))
                if cur["p95_latency_ms"] > max_allowed:
                    violations.append(
                        f"Reranker P95 Regression: Doc count {cur['doc_count']} measured {cur['p95_latency_ms']}ms > baseline {base['p95_latency_ms']}ms + {tolerance_pct}% ({max_allowed:.2f}ms)"
                    )

    passed = len(violations) == 0
    return passed, violations


def generate_comparison_report(diff: Dict[str, Any], output_path: Path) -> str:
    """
    Render a side-by-side Markdown comparison report from a compare_runs() diff dict.

    Columns show run A (baseline) value, run B (new) value, and percentage change.
    Regressions (latency increases > 5%, throughput decreases > 5%) are flagged with ⚠️.
    """

    def _fmt(val: Any) -> str:
        return str(val) if val is not None else "—"

    def _arrow(delta: Any, higher_is_worse: bool = True) -> str:
        """Return a directional indicator + flag for notable regressions/improvements."""
        if delta is None:
            return "—"
        sign = "+" if delta >= 0 else ""
        flag = ""
        if higher_is_worse and delta > 5:
            flag = " ⚠️"
        elif not higher_is_worse and delta < -5:
            flag = " ⚠️"
        elif higher_is_worse and delta < -5:
            flag = " ✅"
        elif not higher_is_worse and delta > 5:
            flag = " ✅"
        return f"{sign}{delta}%{flag}"

    meta = diff.get("meta", {})
    run_a_id = (meta.get("run_id") or {}).get("a") or "A"
    run_b_id = (meta.get("run_id") or {}).get("b") or "B"

    lines = [
        "# Benchmark Comparison Report",
        "",
        f"| Field | Baseline (`{run_a_id[:30]}`) | New (`{run_b_id[:30]}`) |",
        "|---|---|---|",
    ]
    for field in ("timestamp", "image_type", "profile", "model_name", "passed"):
        va = _fmt((meta.get(field) or {}).get("a"))
        vb = _fmt((meta.get(field) or {}).get("b"))
        lines.append(f"| {field} | {va} | {vb} |")
    lines.append("")

    # Bring-up
    bup = diff.get("bringup")
    if bup:
        bt = bup.get("bringup_time_sec", {})
        lines.extend([
            "## Bring-Up Time",
            "",
            f"| Metric | Baseline | New | Δ |",
            "|---|---|---|---|",
            f"| Bringup Time (s) | {_fmt(bt.get('a'))} | {_fmt(bt.get('b'))} | {_arrow(bt.get('delta_pct'))} |",
            f"| Status | {_fmt(bup.get('status',{}).get('a'))} | {_fmt(bup.get('status',{}).get('b'))} | — |",
            "",
        ])

    # LLM
    if diff.get("llm"):
        lines.extend([
            "## LLM Inference",
            "",
            "| Concurrency | Prompt Tokens | P95 TTFT (ms) A | P95 TTFT (ms) B | Δ TTFT | Avg ITL (ms) A | Avg ITL (ms) B | Δ ITL | Agg Tok/s A | Agg Tok/s B | Δ Tok/s |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ])
        for row in diff["llm"]:
            ttft = row.get("p95_ttft_ms", {})
            itl  = row.get("avg_itl_ms", {})
            tps  = row.get("aggregate_tokens_per_sec", {})
            lines.append(
                f"| {_fmt(row.get('concurrency'))} "
                f"| {_fmt(row.get('prompt_tokens'))} "
                f"| {_fmt(ttft.get('a'))} | {_fmt(ttft.get('b'))} | {_arrow(ttft.get('delta_pct'))} "
                f"| {_fmt(itl.get('a'))} | {_fmt(itl.get('b'))} | {_arrow(itl.get('delta_pct'))} "
                f"| {_fmt(tps.get('a'))} | {_fmt(tps.get('b'))} | {_arrow(tps.get('delta_pct'), higher_is_worse=False)} |"
            )
        lines.append("")

    # Reranker
    if diff.get("reranker"):
        lines.extend([
            "## Cross-Encoder Reranker",
            "",
            "| Doc Count | P95 Latency (ms) A | P95 Latency (ms) B | Δ Latency | Throughput (docs/s) A | Throughput (docs/s) B | Δ Throughput |",
            "|---|---|---|---|---|---|---|",
        ])
        for row in diff["reranker"]:
            p95 = row.get("p95_latency_ms", {})
            thr = row.get("throughput_docs_per_sec", {})
            lines.append(
                f"| {_fmt(row.get('doc_count'))} "
                f"| {_fmt(p95.get('a'))} | {_fmt(p95.get('b'))} | {_arrow(p95.get('delta_pct'))} "
                f"| {_fmt(thr.get('a'))} | {_fmt(thr.get('b'))} | {_arrow(thr.get('delta_pct'), higher_is_worse=False)} |"
            )
        lines.append("")

    # Embedding
    if diff.get("embedding"):
        lines.extend([
            "## Dense Vector Embedding",
            "",
            "| Batch Size | P95 Latency (ms) A | P95 Latency (ms) B | Δ Latency | Throughput (texts/s) A | Throughput (texts/s) B | Δ Throughput |",
            "|---|---|---|---|---|---|---|",
        ])
        for row in diff["embedding"]:
            p95 = row.get("p95_latency_ms", {})
            thr = row.get("throughput_texts_per_sec", {})
            lines.append(
                f"| {_fmt(row.get('batch_size'))} "
                f"| {_fmt(p95.get('a'))} | {_fmt(p95.get('b'))} | {_arrow(p95.get('delta_pct'))} "
                f"| {_fmt(thr.get('a'))} | {_fmt(thr.get('b'))} | {_arrow(thr.get('delta_pct'), higher_is_worse=False)} |"
            )
        lines.append("")

    lines.extend([
        "> **Legend:** ⚠️ regression (>5%)  ✅ improvement (>5%)  — no data",
        "",
    ])

    md_content = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(md_content)
    return md_content
