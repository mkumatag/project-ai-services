"""
Server-Side Metrics Collector Module.

Scrapes and parses Prometheus metrics from vLLM/endpoint /metrics endpoint,
extracting cache utilization, memory pressure, request counts, and execution statistics.
"""

import re
import requests
from typing import Dict, Any, Optional


def scrape_container_metrics(endpoint: str, api_key: Optional[str] = None, timeout: float = 3.0) -> Dict[str, Any]:
    """
    Fetch and parse Prometheus metrics from {endpoint}/metrics.
    
    Returns structured metrics dict:
    - kv_cache_usage_pct: percentage of GPU/CPU KV cache used
    - num_requests_running: number of requests currently executing
    - num_requests_waiting: number of requests waiting in queue
    - num_requests_swapped: number of requests swapped to CPU
    - prompt_tokens_total: total prompt tokens processed
    - generation_tokens_total: total generation tokens produced
    - raw_metrics_count: total metric lines parsed
    - available: bool indicating whether /metrics was accessible
    """
    metrics_url = f"{endpoint.rstrip('/')}/metrics"
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    result: Dict[str, Any] = {
        "available": False,
        "endpoint": metrics_url,
        "num_requests_running": 0,
        "num_requests_waiting": 0,
        "num_requests_swapped": 0,
        "kv_cache_usage_pct": 0.0,
        "prompt_tokens_total": 0,
        "generation_tokens_total": 0,
        "raw_samples": {}
    }

    try:
        resp = requests.get(metrics_url, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            return result
        
        result["available"] = True
        text = resp.text

        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            # Match Prometheus line: metric_name{labels} value or metric_name value
            match = re.match(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)\s*(?:\{[^}]*\})?\s+([0-9.eE+-]+)", line)
            if not match:
                continue
            
            metric_name, val_str = match.group(1), match.group(2)
            try:
                val = float(val_str)
            except ValueError:
                continue

            result["raw_samples"][metric_name] = val

            # vLLM standard Prometheus metric names
            if metric_name in ("vllm:num_requests_running", "vllm_num_requests_running"):
                result["num_requests_running"] = int(val)
            elif metric_name in ("vllm:num_requests_waiting", "vllm_num_requests_waiting"):
                result["num_requests_waiting"] = int(val)
            elif metric_name in ("vllm:num_requests_swapped", "vllm_num_requests_swapped"):
                result["num_requests_swapped"] = int(val)
            elif metric_name in ("vllm:gpu_cache_usage_factor", "vllm_gpu_cache_usage_factor",
                                 "vllm:cpu_cache_usage_factor", "vllm_cpu_cache_usage_factor",
                                 "vllm:kv_cache_usage_perc", "vllm_kv_cache_usage_perc"):
                result["kv_cache_usage_pct"] = round(val * 100.0, 2)
            elif metric_name in ("vllm:prompt_tokens_total", "vllm_prompt_tokens_total"):
                result["prompt_tokens_total"] = int(val)
            elif metric_name in ("vllm:generation_tokens_total", "vllm_generation_tokens_total"):
                result["generation_tokens_total"] = int(val)
            elif metric_name in ("vllm:time_to_first_token_seconds_sum", "vllm:time_to_first_token_seconds_count"):
                pass

    except Exception as e:
        result["error"] = str(e)

    return result
