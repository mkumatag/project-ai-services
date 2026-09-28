"""
Automated Benchmark Harness for LLM Inference Serving.

Measures Time-to-First-Token (TTFT), Inter-Token Latency (ITL / TPOT),
Total Latency, and Token Generation Throughput over SSE streaming across
concurrency levels and context lengths.
"""

import time
import json
import requests
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional
from test.benchmarks.datasets import get_llm_benchmark_payloads


def parse_sse_stream(response: requests.Response) -> Dict[str, Any]:
    """Parse SSE chunks and capture arrival timestamps for TTFT and ITL computation."""
    start_time = time.perf_counter()
    first_token_time = None
    token_timestamps = []
    generated_text = []

    for line in response.iter_lines(decode_unicode=True):
        if not line:
            continue
        if line.startswith("data: "):
            chunk_str = line[6:].strip()
            if chunk_str == "[DONE]":
                break
            try:
                chunk = json.loads(chunk_str)
                choices = chunk.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        now = time.perf_counter()
                        if first_token_time is None:
                            first_token_time = now
                        token_timestamps.append(now)
                        generated_text.append(content)
            except Exception:
                continue

    end_time = time.perf_counter()
    ttft_ms = (first_token_time - start_time) * 1000.0 if first_token_time else 0.0
    total_time_ms = (end_time - start_time) * 1000.0
    num_tokens = len(token_timestamps)

    # Compute Inter-Token Latency (ITL) deltas
    itl_deltas = []
    for i in range(1, len(token_timestamps)):
        itl_deltas.append((token_timestamps[i] - token_timestamps[i-1]) * 1000.0)

    avg_itl_ms = float(np.mean(itl_deltas)) if itl_deltas else 0.0
    tokens_per_sec = (num_tokens / (total_time_ms / 1000.0)) if total_time_ms > 0 else 0.0

    return {
        "ttft_ms": round(ttft_ms, 2),
        "avg_itl_ms": round(avg_itl_ms, 2),
        "total_time_ms": round(total_time_ms, 2),
        "num_tokens": num_tokens,
        "tokens_per_sec": round(tokens_per_sec, 2),
        "text": "".join(generated_text)
    }


def _run_single_llm_request(
    url: str,
    payload: Dict[str, Any],
    headers: Dict[str, str]
) -> Dict[str, Any]:
    """Send a single streaming chat completion request."""
    req_body = {
        "model": payload.get("model", "default-llm"),
        "messages": payload["messages"],
        "max_tokens": payload.get("max_tokens", 128),
        "temperature": payload.get("temperature", 0.0),
        "stream": True
    }
    
    try:
        resp = requests.post(url, json=req_body, headers=headers, stream=True, timeout=120.0)
        if resp.status_code == 200:
            metrics = parse_sse_stream(resp)
            metrics["status"] = "OK"
            return metrics
        else:
            return {"status": "ERROR", "status_code": resp.status_code}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


def run_llm_benchmarks(
    endpoint: str,
    model_name: str = "ibm-granite/granite-3.0-8b-instruct",
    profile: str = "standard",
    concurrencies: Optional[List[int]] = None,
    api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Run LLM inference benchmarks across concurrency levels and prompt lengths.
    """
    url = f"{endpoint.rstrip('/')}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    if concurrencies is None:
        concurrencies = [1, 4, 8, 16] if profile == "compact" else [1, 4, 8, 16, 32]

    payloads = get_llm_benchmark_payloads(profile)
    # Use prompt length 512 as baseline for concurrency sweeps
    test_payload = next((p for p in payloads if p["approx_tokens"] == 512), payloads[0])
    test_payload["model"] = model_name

    results = []

    for concurrency in concurrencies:
        latencies_ttft = []
        latencies_itl = []
        total_times = []
        token_counts = []
        errors = 0

        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [
                executor.submit(_run_single_llm_request, url, test_payload, headers)
                for _ in range(concurrency)
            ]

            for future in as_completed(futures):
                res = future.result()
                if res.get("status") == "OK":
                    latencies_ttft.append(res["ttft_ms"])
                    latencies_itl.append(res["avg_itl_ms"])
                    total_times.append(res["total_time_ms"])
                    token_counts.append(res["num_tokens"])
                else:
                    errors += 1

        if latencies_ttft:
            ttft_arr = np.array(latencies_ttft)
            itl_arr = np.array(latencies_itl)
            p95_ttft = float(np.percentile(ttft_arr, 95))
            avg_itl = float(np.mean(itl_arr))
            agg_tokens = sum(token_counts)
            max_duration_sec = max(total_times) / 1000.0 if total_times else 1.0
            aggregate_tps = agg_tokens / max_duration_sec
        else:
            p95_ttft = avg_itl = aggregate_tps = 0.0

        results.append({
            "suite": "llm",
            "profile": profile,
            "concurrency": concurrency,
            "prompt_tokens": test_payload["approx_tokens"],
            "p95_ttft_ms": round(p95_ttft, 2),
            "avg_itl_ms": round(avg_itl, 2),
            "aggregate_tokens_per_sec": round(aggregate_tps, 2),
            "error_rate_pct": round((errors / concurrency) * 100.0, 2),
        })

    return results
