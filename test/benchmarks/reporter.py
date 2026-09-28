"""
Reporting and Baseline Regression Comparator Module.

Generates CSV and Markdown benchmark summaries and evaluates metrics
against baseline SLA thresholds with configurable deviation gates.
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
        lines.extend([
            "## 1. Container Bring-Up & Readiness",
            "",
            "| Component | Endpoint | Elapsed (s) | Budget Limit (s) | Status |",
            "|---|---|---|---|---|",
            f"| {b.get('component')} | {b.get('endpoint')} | {b.get('bringup_time_sec')}s | {b.get('max_budget_sec')}s | {b.get('status')} |",
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
