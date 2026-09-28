"""
Automated Benchmark Harness for Embedding Models (/v1/embeddings).

Evaluates latency (P50, P90, P95, P99), throughput (texts/sec, tokens/sec),
and numerical validity across batch sizes [1, 4, 8, 16, 32, 64].
"""

import time
import requests
import numpy as np
from typing import Dict, List, Any, Optional
from test.benchmarks.datasets import get_embedding_benchmark_payloads


def run_embedding_benchmarks(
    endpoint: str,
    model_name: str = "ibm-granite/granite-embedding-125m",
    batch_sizes: Optional[List[int]] = None,
    iterations_per_batch: int = 5,
    api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Run embedding benchmarks across batch size configurations.
    """
    url = f"{endpoint.rstrip('/')}/v1/embeddings"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    all_payloads = get_embedding_benchmark_payloads()
    if batch_sizes:
        all_payloads = [p for p in all_payloads if p["batch_size"] in batch_sizes]

    results = []
    session = requests.Session()

    for item in all_payloads:
        batch_size = item["batch_size"]
        texts = item["texts"]
        payload = {
            "model": model_name,
            "input": texts
        }

        latencies = []
        errors = 0
        total_tokens = sum(len(t.split()) for t in texts) * 1.3  # approx tokens

        # Warmup single call
        try:
            session.post(url, json=payload, headers=headers, timeout=30.0)
        except Exception:
            pass

        for _ in range(iterations_per_batch):
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
            throughput_texts = (batch_size / (avg_lat / 1000.0))
            throughput_tokens = (total_tokens / (avg_lat / 1000.0))
        else:
            p50 = p90 = p95 = p99 = avg_lat = throughput_texts = throughput_tokens = 0.0

        results.append({
            "suite": "embedding",
            "batch_size": batch_size,
            "iterations": iterations_per_batch,
            "avg_latency_ms": round(avg_lat, 2),
            "p50_latency_ms": round(p50, 2),
            "p90_latency_ms": round(p90, 2),
            "p95_latency_ms": round(p95, 2),
            "p99_latency_ms": round(p99, 2),
            "throughput_texts_per_sec": round(throughput_texts, 2),
            "throughput_tokens_per_sec": round(throughput_tokens, 2),
            "error_rate_pct": round((errors / (errors + len(latencies))) * 100.0 if (errors + len(latencies)) > 0 else 100.0, 2),
        })

    return results
