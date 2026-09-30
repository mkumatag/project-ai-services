"""
Benchmark Run History Store.

Persists every completed benchmark run as a JSON-Lines record in
`results/runs.jsonl` (one JSON object per line).  Each record contains
the full `results` dict produced by run_model_benchmarks.py plus a
short `run_id` slug for easy reference.

Public API
----------
save_run(results, output_dir)          -> run_id str
load_runs(output_dir, limit)           -> List[dict]
find_run(run_id_prefix, output_dir)    -> dict | None
compare_runs(run_a, run_b)             -> dict  (structured diff)
print_history(output_dir, limit)       -> None  (pretty-print table)
"""

import json
import hashlib
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# ── helpers ────────────────────────────────────────────────────────────────

def _runs_file(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / "runs.jsonl"


def _make_run_id(results: Dict[str, Any]) -> str:
    """
    Build a short deterministic ID from timestamp + image_type + profile.
    Format: YYYYMMDD-HHMMSS-<image_type>-<profile>
    Falls back to a 8-char hash when timestamp is missing.
    """
    ts = results.get("timestamp", "")
    image = results.get("image_type", "unknown").replace("/", "-")
    profile = results.get("profile", "unknown")
    model = (results.get("model_name") or "").replace("/", "-").replace(":", "-")

    if ts:
        # ISO timestamp → compact slug
        slug = ts[:19].replace(":", "").replace("T", "-").replace("-", "", 2)
        # e.g. 20250101-123045
        slug = slug[:8] + "-" + slug[9:]
    else:
        slug = hashlib.md5(json.dumps(results, sort_keys=True, default=str).encode()).hexdigest()[:8]

    parts = [slug, image, profile]
    if model:
        parts.append(model[:30])
    return "-".join(parts)


# ── core persistence ────────────────────────────────────────────────────────

def save_run(results: Dict[str, Any], output_dir: Path) -> str:
    """
    Append a benchmark run record to runs.jsonl.
    Attaches `run_id` into the record before saving.
    Returns the run_id string.
    """
    run_id = _make_run_id(results)
    record = {"run_id": run_id, **results}

    runs_path = _runs_file(output_dir)
    with open(runs_path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")

    return run_id


def load_runs(output_dir: Path, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Load benchmark run records from runs.jsonl, newest first.
    `limit` caps the number of records returned.
    """
    runs_path = _runs_file(output_dir)
    if not runs_path.exists():
        return []

    records: List[Dict[str, Any]] = []
    with open(runs_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    # Newest first
    records.reverse()
    if limit is not None:
        records = records[:limit]
    return records


def find_run(run_id_prefix: str, output_dir: Path) -> Optional[Dict[str, Any]]:
    """
    Find a single run whose run_id starts with run_id_prefix.
    Returns the first match (newest first), or None.
    """
    for record in load_runs(output_dir):
        if record.get("run_id", "").startswith(run_id_prefix):
            return record
    return None


# ── comparison ──────────────────────────────────────────────────────────────

def _delta(old: Optional[float], new: Optional[float]) -> Optional[float]:
    """Return percentage change (new vs old), or None if either is missing/zero."""
    if old is None or new is None:
        return None
    if old == 0:
        return None
    return round(((new - old) / old) * 100.0, 1)


def compare_runs(run_a: Dict[str, Any], run_b: Dict[str, Any]) -> Dict[str, Any]:
    """
    Produce a structured diff between two run records (run_a = baseline, run_b = new).

    Returns a dict with sections:
      meta       – side-by-side header fields
      llm        – per-concurrency TTFT / ITL / throughput deltas
      reranker   – per-doc-count latency deltas
      embedding  – per-batch throughput deltas
      bringup    – bringup time delta
    """
    diff: Dict[str, Any] = {"meta": {}, "llm": [], "reranker": [], "embedding": [], "bringup": None}

    # Meta
    for field in ("run_id", "timestamp", "image_type", "profile", "model_name", "passed"):
        diff["meta"][field] = {
            "a": run_a.get(field),
            "b": run_b.get(field),
        }

    # Bring-up
    ba = run_a.get("bringup", {})
    bb = run_b.get("bringup", {})
    if ba or bb:
        diff["bringup"] = {
            "bringup_time_sec": {
                "a": ba.get("bringup_time_sec"),
                "b": bb.get("bringup_time_sec"),
                "delta_pct": _delta(ba.get("bringup_time_sec"), bb.get("bringup_time_sec")),
            },
            "status": {"a": ba.get("status"), "b": bb.get("status")},
        }

    # LLM – align rows by (concurrency, prompt_tokens)
    def _key_llm(row: Dict) -> tuple:
        return (row.get("concurrency"), row.get("prompt_tokens"))

    llm_a = {_key_llm(r): r for r in (run_a.get("llm") or [])}
    llm_b = {_key_llm(r): r for r in (run_b.get("llm") or [])}
    for key in sorted(set(llm_a) | set(llm_b)):
        ra, rb = llm_a.get(key, {}), llm_b.get(key, {})
        diff["llm"].append({
            "concurrency": key[0],
            "prompt_tokens": key[1],
            "p95_ttft_ms": {
                "a": ra.get("p95_ttft_ms"),
                "b": rb.get("p95_ttft_ms"),
                "delta_pct": _delta(ra.get("p95_ttft_ms"), rb.get("p95_ttft_ms")),
            },
            "avg_itl_ms": {
                "a": ra.get("avg_itl_ms"),
                "b": rb.get("avg_itl_ms"),
                "delta_pct": _delta(ra.get("avg_itl_ms"), rb.get("avg_itl_ms")),
            },
            "aggregate_tokens_per_sec": {
                "a": ra.get("aggregate_tokens_per_sec"),
                "b": rb.get("aggregate_tokens_per_sec"),
                "delta_pct": _delta(ra.get("aggregate_tokens_per_sec"), rb.get("aggregate_tokens_per_sec")),
            },
        })

    # Reranker – align by doc_count
    rrk_a = {r.get("doc_count"): r for r in (run_a.get("reranker") or [])}
    rrk_b = {r.get("doc_count"): r for r in (run_b.get("reranker") or [])}
    for doc_count in sorted(set(rrk_a) | set(rrk_b)):
        ra, rb = rrk_a.get(doc_count, {}), rrk_b.get(doc_count, {})
        diff["reranker"].append({
            "doc_count": doc_count,
            "p95_latency_ms": {
                "a": ra.get("p95_latency_ms"),
                "b": rb.get("p95_latency_ms"),
                "delta_pct": _delta(ra.get("p95_latency_ms"), rb.get("p95_latency_ms")),
            },
            "throughput_docs_per_sec": {
                "a": ra.get("throughput_docs_per_sec"),
                "b": rb.get("throughput_docs_per_sec"),
                "delta_pct": _delta(ra.get("throughput_docs_per_sec"), rb.get("throughput_docs_per_sec")),
            },
        })

    # Embedding – align by batch_size
    emb_a = {r.get("batch_size"): r for r in (run_a.get("embedding") or [])}
    emb_b = {r.get("batch_size"): r for r in (run_b.get("embedding") or [])}
    for batch_size in sorted(set(emb_a) | set(emb_b)):
        ra, rb = emb_a.get(batch_size, {}), emb_b.get(batch_size, {})
        diff["embedding"].append({
            "batch_size": batch_size,
            "p95_latency_ms": {
                "a": ra.get("p95_latency_ms"),
                "b": rb.get("p95_latency_ms"),
                "delta_pct": _delta(ra.get("p95_latency_ms"), rb.get("p95_latency_ms")),
            },
            "throughput_texts_per_sec": {
                "a": ra.get("throughput_texts_per_sec"),
                "b": rb.get("throughput_texts_per_sec"),
                "delta_pct": _delta(ra.get("throughput_texts_per_sec"), rb.get("throughput_texts_per_sec")),
            },
        })

    return diff


# ── pretty-print ─────────────────────────────────────────────────────────────

def print_history(output_dir: Path, limit: int = 20) -> None:
    """Print a summary table of recent benchmark runs to stdout."""
    runs = load_runs(output_dir, limit=limit)
    if not runs:
        print("No benchmark history found in", output_dir)
        return

    header = f"{'RUN ID':<42}  {'TIMESTAMP':<20}  {'IMAGE TYPE':<20}  {'PROFILE':<9}  {'PASS'}"
    print(header)
    print("-" * len(header))
    for r in runs:
        ts = (r.get("timestamp") or "")[:19]
        passed = "✅" if r.get("passed", True) else "❌"
        model = r.get("model_name") or ""
        image = r.get("image_type", "")
        if model:
            image = f"{image} ({model[:20]})"
        print(f"{r.get('run_id',''):<42}  {ts:<20}  {image:<20}  {r.get('profile',''):<9}  {passed}")
