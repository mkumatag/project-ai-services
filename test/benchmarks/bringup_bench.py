"""
Bring-up and Container Lifecycle Benchmark Module.

Measures cold and warm start initialization times, polling /health and /v1/models
against the template-derived timeout budgets (e.g., 420s for vllm-spyre, 120s for vllm-cpu).
"""

import time
import subprocess
import shutil
import requests
from pathlib import Path
from typing import Dict, Any, Optional, Union

try:
    import yaml
except ImportError:
    yaml = None

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


def start_podman_kube(
    pod_yaml_path: Union[str, Path],
    auto_teardown_existing: bool = True
) -> Dict[str, Any]:
    """
    Deploy a pod using 'podman play kube <pod_yaml_path>'.
    
    Returns:
        Dict containing success (bool), stdout, stderr, and exit_code.
    """
    yaml_path = Path(pod_yaml_path).resolve()
    if not yaml_path.exists():
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Pod YAML file does not exist: {yaml_path}",
            "exit_code": 1
        }

    podman_bin = shutil.which("podman") or "podman"
    
    if auto_teardown_existing:
        # Best effort cleanup of any prior instance of this kube YAML
        subprocess.run(
            [podman_bin, "play", "kube", "--down", str(yaml_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

    res = subprocess.run(
        [podman_bin, "play", "kube", str(yaml_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    return {
        "success": res.returncode == 0,
        "stdout": res.stdout,
        "stderr": res.stderr,
        "exit_code": res.returncode
    }


def stop_podman_kube(pod_yaml_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Tear down a pod deployed via 'podman play kube --down <pod_yaml_path>'.
    """
    yaml_path = Path(pod_yaml_path).resolve()
    podman_bin = shutil.which("podman") or "podman"
    res = subprocess.run(
        [podman_bin, "play", "kube", "--down", str(yaml_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    return {
        "success": res.returncode == 0,
        "stdout": res.stdout,
        "stderr": res.stderr,
        "exit_code": res.returncode
    }


def extract_probe_config_from_yaml(pod_yaml_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Parse pod YAML manifest to extract probe configurations (readiness/liveness),
    container names, pod name, and calculate dynamic probe timeout budgets.
    """
    yaml_path = Path(pod_yaml_path).resolve()
    if not yaml_path.exists():
        return {}

    manifest = None
    try:
        with open(yaml_path, "r") as f:
            if yaml is not None:
                manifest = yaml.safe_load(f)
            else:
                # Fallback simple parser for probe path if PyYAML is not installed
                content = f.read()
                probe_path = "/health"
                for line in content.splitlines():
                    if "path:" in line:
                        probe_path = line.split("path:")[-1].strip()
                        break
                manifest = {
                    "metadata": {"name": yaml_path.stem},
                    "spec": {"containers": [{"readinessProbe": {"httpGet": {"path": probe_path}}}]}
                }
    except Exception:
        return {}

    if not isinstance(manifest, dict):
        return {}

    pod_name = manifest.get("metadata", {}).get("name", "")
    containers = manifest.get("spec", {}).get("containers", [])
    if not containers:
        return {"pod_name": pod_name}

    main_container = containers[0]
    container_name = main_container.get("name", "")
    
    # Check readinessProbe first, fall back to livenessProbe
    probe = main_container.get("readinessProbe") or main_container.get("livenessProbe") or {}
    http_get = probe.get("httpGet", {})
    probe_path = http_get.get("path", "/health")
    probe_port = http_get.get("port", None)
    
    initial_delay = probe.get("initialDelaySeconds", 120)
    period_seconds = probe.get("periodSeconds", 10)
    failure_threshold = probe.get("failureThreshold", 3)
    timeout_seconds = probe.get("timeoutSeconds", 5)

    # Standard budget = initial_delay + (period_seconds * failure_threshold * 3) + buffer
    computed_budget = initial_delay + (period_seconds * max(failure_threshold, 3)) + 60

    return {
        "pod_name": pod_name,
        "container_name": container_name,
        "probe_path": probe_path,
        "probe_port": probe_port,
        "initial_delay": initial_delay,
        "period_seconds": period_seconds,
        "failure_threshold": failure_threshold,
        "timeout_seconds": timeout_seconds,
        "computed_budget": computed_budget
    }


def get_podman_container_logs(container_or_pod_name: str, tail: int = 50) -> str:
    """Fetch recent container logs using 'podman logs --tail'."""
    podman_bin = shutil.which("podman") or "podman"
    try:
        res = subprocess.run(
            [podman_bin, "logs", "--tail", str(tail), container_or_pod_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        return res.stdout or res.stderr
    except Exception as e:
        return f"<Failed to get container logs: {e}>"


def get_podman_container_state(pod_name: str, container_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Inspect container or pod state.
    Checks container inspect, pod inspect, and podman ps/pod ls to reliably detect if
    the pod or any of its containers has exited / terminated.
    """
    podman_bin = shutil.which("podman") or "podman"
    import json

    # 1. Check candidate container names via `podman inspect` first (to retrieve .State and .State.Health)
    candidates = []
    if pod_name and container_name:
        candidates.append(f"{pod_name}-{container_name}")
    if pod_name:
        candidates.append(pod_name)
    if container_name:
        candidates.append(container_name)

    for target in candidates:
        try:
            res = subprocess.run(
                [podman_bin, "inspect", "--format", "{{json .State}}", target],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
            if res.returncode == 0 and res.stdout.strip():
                state_data = json.loads(res.stdout)
                if isinstance(state_data, dict):
                    return state_data
        except Exception:
            pass

    # 2. Check pod status via `podman pod inspect` and inspect non-infra containers inside
    if pod_name:
        try:
            res = subprocess.run(
                [podman_bin, "pod", "inspect", pod_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)
                state = data.get("State", "")
                if isinstance(state, str) and state.lower() in ("exited", "dead", "stopped"):
                    return {"Running": False, "ExitCode": 1, "Status": state}
                # Check containers inside the pod
                containers = data.get("Containers", [])
                for c in containers:
                    c_id = c.get("Id", "")
                    c_names = c.get("Names", [""])
                    c_name_str = c_names[0] if c_names else ""
                    if "infra" in c_name_str:
                        continue
                    c_state = c.get("State", "")
                    if c_state in ("exited", "stopped", "dead"):
                        return {"Running": False, "ExitCode": c.get("ExitCode", 1), "Status": c_state}
                    # Inspect container to get its State object with Health details
                    if c_id:
                        c_insp = subprocess.run(
                            [podman_bin, "inspect", "--format", "{{json .State}}", c_id],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            timeout=5
                        )
                        if c_insp.returncode == 0 and c_insp.stdout.strip():
                            return json.loads(c_insp.stdout)
        except Exception:
            pass

    # 3. Fallback: check `podman pod ps --filter name=...`
    if pod_name:
        try:
            res = subprocess.run(
                [podman_bin, "pod", "ps", "--filter", f"name={pod_name}", "--format", "{{.Status}}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
            if res.returncode == 0 and res.stdout.strip():
                status = res.stdout.strip().lower()
                if "exited" in status or "dead" in status or "stopped" in status:
                    return {"Running": False, "ExitCode": 1, "Status": status}
        except Exception:
            pass

    return {}


def measure_endpoint_bringup(
    endpoint: str,
    image_type: str = "vllm-cpu",
    profile: str = "standard",
    poll_interval: float = 1.0,
    max_wait_override: Optional[float] = None,
    api_key: Optional[str] = None,
    pod_yaml_path: Optional[Union[str, Path]] = None,
    auto_stop_pod: bool = False
) -> Dict[str, Any]:
    """
    Deploys a Pod via Podman (if pod_yaml_path is given) and measures bring-up time.
    
    Evaluates readiness by:
    1. Parsing probe configuration (path, port, initial delay, budget) directly from Pod YAML
    2. Polling HTTP healthcheck/readiness probe endpoint
    3. Monitoring container exit status & logs via Podman CLI
    
    Returns:
        Dict with bringup_time_sec, status ("PASSED" / "FAILED"), budget_sec, logs, and diagnostic info.
    """
    yaml_probe_cfg = extract_probe_config_from_yaml(pod_yaml_path) if pod_yaml_path else {}
    
    # Determine timeout budget
    if max_wait_override:
        max_budget = max_wait_override
    elif "computed_budget" in yaml_probe_cfg:
        max_budget = yaml_probe_cfg["computed_budget"]
    else:
        profile_cfg = IMAGE_BRINGUP_BUDGETS.get(image_type, {}).get(profile, {"initial_delay": 120, "max_budget": 300})
        max_budget = profile_cfg["max_budget"]

    # Target health URL resolution
    probe_path = yaml_probe_cfg.get("probe_path", "/health")
    if not probe_path.startswith("/"):
        probe_path = "/" + probe_path
    
    health_url = f"{endpoint.rstrip('/')}{probe_path}"
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    start_time = time.perf_counter()
    pod_name = yaml_probe_cfg.get("pod_name")
    container_name = yaml_probe_cfg.get("container_name")

    if pod_yaml_path:
        launch = start_podman_kube(pod_yaml_path)
        if not launch["success"]:
            elapsed = time.perf_counter() - start_time
            return {
                "component": image_type,
                "profile": profile,
                "endpoint": endpoint,
                "bringup_time_sec": round(elapsed, 3),
                "max_budget_sec": max_budget,
                "status": "FAILED",
                "ready": False,
                "error": f"Failed to execute podman play kube: {launch['stderr'] or launch['stdout']}",
                "pod_yaml_path": str(pod_yaml_path)
            }

    http_ready_time: Optional[float] = None
    container_healthy_time: Optional[float] = None
    last_error = None
    container_target = f"{pod_name}-{container_name}" if (pod_name and container_name) else (container_name or pod_name)

    while time.perf_counter() - start_time < max_budget:
        now = time.perf_counter()
        
        # 1. Probe via explicit HTTP curl/GET call
        if http_ready_time is None:
            try:
                resp = requests.get(health_url, headers=headers, timeout=2.0)
                if resp.status_code == 200:
                    http_ready_time = round(now - start_time, 3)
                else:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:100]}"
            except Exception as e:
                last_error = str(e)

        # 2. Check container health status via Podman inspect
        state = get_podman_container_state(pod_name, container_name)
        has_health_status = False
        if state:
            # Check if container died
            if not state.get("Running", True):
                exit_code = state.get("ExitCode", -1)
                recent = get_podman_container_logs(container_target, tail=15)
                last_error = f"Container terminated prematurely with exit code {exit_code}.\nRecent logs:\n{recent}"
                break

            # Check if Podman health check transitioned to healthy
            health_info = state.get("Health", {})
            if isinstance(health_info, dict) and health_info.get("Status"):
                has_health_status = True
                h_status = health_info.get("Status", "").lower()
                if h_status == "healthy" and container_healthy_time is None:
                    container_healthy_time = round(now - start_time, 3)

        # When HTTP is ready:
        # If container healthcheck is configured and in "starting", keep waiting for "healthy"
        if http_ready_time is not None:
            if not has_health_status:
                # If no native Podman healthcheck is defined in container inspect,
                # mark container_healthy_time equivalent to HTTP readiness
                if container_healthy_time is None:
                    container_healthy_time = http_ready_time
                break
            elif container_healthy_time is not None:
                # Both HTTP and container healthcheck are confirmed healthy
                break
            # Continue polling until healthcheck reaches "healthy" or max_budget is reached
            
        time.sleep(poll_interval)
    
    elapsed = time.perf_counter() - start_time
    ready = http_ready_time is not None
    bringup_time = max(filter(lambda x: x is not None, [http_ready_time, container_healthy_time]), default=round(elapsed, 3))
    passed = ready and (bringup_time <= max_budget)

    # Capture container logs for diagnostics if available
    captured_logs = None
    if container_target:
        captured_logs = get_podman_container_logs(container_target, tail=30)

    if pod_yaml_path and auto_stop_pod:
        stop_podman_kube(pod_yaml_path)
    
    return {
        "component": image_type,
        "profile": profile,
        "endpoint": endpoint,
        "probe_url": health_url,
        "bringup_time_sec": bringup_time,
        "http_ready_time_sec": http_ready_time,
        "container_healthy_time_sec": container_healthy_time,
        "max_budget_sec": max_budget,
        "status": "PASSED" if passed else "FAILED",
        "ready": ready,
        "error": None if ready else (last_error or f"Timed out after {max_budget}s"),
        "pod_yaml_path": str(pod_yaml_path) if pod_yaml_path else None,
        "probe_config": yaml_probe_cfg if yaml_probe_cfg else None,
        "recent_logs": captured_logs
    }
