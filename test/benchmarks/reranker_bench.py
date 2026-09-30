"""
Automated Benchmark Harness for Reranker Models (/v1/rerank or Cohere-compatible API).

Evaluates cross-encoder document reranking latency, scoring fidelity,
and throughput across candidate document pool sizes [1, 5, 10, 25, 50].
"""

import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import requests
import numpy as np

# Ensure project root is in sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from test.benchmarks.datasets import get_reranker_benchmark_payloads


def run_reranker_benchmarks(
    endpoint: str,
    model_name: str = "BAAI/bge-reranker-v2-m3",
    iterations_per_payload: int = 5,
    api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Run reranker benchmarks across different document candidate pool sizes.
    Supports both native /v1/rerank and vLLM Cohere-compatible endpoint.
    """
    url = f"{endpoint.rstrip('/')}/v1/rerank"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payloads = get_reranker_benchmark_payloads()
    results = []
    session = requests.Session()

    for item in payloads:
        doc_count = item["doc_count"]
        query = item["query"]
        docs = [d["page_content"] for d in item["documents"]]

        payload = {
            "model": model_name,
            "query": query,
            "documents": docs,
            "top_n": doc_count
        }

        latencies = []
        errors = 0

        # Warmup call
        try:
            session.post(url, json=payload, headers=headers, timeout=30.0)
        except Exception:
            pass

        for _ in range(iterations_per_payload):
            t0 = time.perf_counter()
            try:
                resp = session.post(url, json=payload, headers=headers, timeout=60.0)
                if resp.status_code == 200:
                    latencies.append((time.perf_counter() - t0) * 1000.0)  # ms
                else:
                    errors += 1
            except Exception:
                errors += 1

        if latencies:
            lat_arr = np.array(latencies)
            p50 = float(np.percentile(lat_arr, 50))
            p90 = float(np.percentile(lat_arr, 90))
            p95 = float(np.percentile(lat_arr, 95))
            p99 = float(np.percentile(lat_arr, 99))
            avg_lat = float(np.mean(lat_arr))
            docs_per_sec = (doc_count / (avg_lat / 1000.0))
        else:
            p50 = p90 = p95 = p99 = avg_lat = docs_per_sec = 0.0

        results.append({
            "suite": "reranker",
            "doc_count": doc_count,
            "iterations": iterations_per_payload,
            "avg_latency_ms": round(avg_lat, 2),
            "p50_latency_ms": round(p50, 2),
            "p90_latency_ms": round(p90, 2),
            "p95_latency_ms": round(p95, 2),
            "p99_latency_ms": round(p99, 2),
            "throughput_docs_per_sec": round(docs_per_sec, 2),
            "error_rate_pct": round((errors / (errors + len(latencies))) * 100.0 if (errors + len(latencies)) > 0 else 100.0, 2),
        })

    return results
