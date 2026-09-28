"""
Bring-up and Container Lifecycle Benchmark Module.

Measures cold and warm start initialization times, polling /health and /v1/models
against the template-derived timeout budgets (e.g., 420s for vllm-spyre, 120s for vllm-cpu).
"""

import time
import requests
from typing import Dict, Any, Optional

# Probe timeout budgets (seconds) derived from assets/components templates
IMAGE_BRINGUP_BUDGETS = {
    "vllm-spyre": {
        "standard": {"initial_delay": 420, "max_budget": 510},
        "compact": {"initial_delay": 180, "max_budget": 270},
    },
    "vllm-cpu": {
        "standard": {"initial_delay": 120, "max_budget": 480},
        "compact": {"initial_delay": 120, "max_budget": 480},
    },
    "reranker-spyre": {
        "standard": {"initial_delay": 120, "max_budget": 210},
        "compact": {"initial_delay": 120, "max_budget": 210},
    },
    "reranker-cpu": {
        "standard": {"initial_delay": 120, "max_budget": 210},
    },
    "embedding-cpu": {
        "standard": {"initial_delay": 120, "max_budget": 210},
    },
}


def measure_endpoint_bringup(
    endpoint: str,
    image_type: str = "vllm-cpu",
    profile: str = "standard",
    poll_interval: float = 1.0,
    max_wait_override: Optional[float] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Poll an endpoint until /health responds with 200 OK.
    
    Returns:
        Dict with bringup_time_sec, status ("PASSED" / "FAILED"), budget_sec, and error info.
    """
    profile_cfg = IMAGE_BRINGUP_BUDGETS.get(image_type, {}).get(profile, {"initial_delay": 120, "max_budget": 300})
    max_budget = max_wait_override or profile_cfg["max_budget"]
    
    health_url = f"{endpoint.rstrip('/')}/health"
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    start_time = time.perf_counter()
    ready = False
    last_error = None
    
    while time.perf_counter() - start_time < max_budget:
        try:
            resp = requests.get(health_url, headers=headers, timeout=2.0)
            if resp.status_code == 200:
                ready = True
                break
        except Exception as e:
            last_error = str(e)
            
        time.sleep(poll_interval)
    
    elapsed = time.perf_counter() - start_time
    passed = ready and (elapsed <= max_budget)
    
    return {
        "component": image_type,
        "profile": profile,
        "endpoint": endpoint,
        "bringup_time_sec": round(elapsed, 3),
        "max_budget_sec": max_budget,
        "status": "PASSED" if passed else "FAILED",
        "ready": ready,
        "error": None if ready else (last_error or f"Timed out after {max_budget}s")
    }
