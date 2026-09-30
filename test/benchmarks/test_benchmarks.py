"""
Unit and Acceptance Tests for Benchmark Harness and Modules.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    import pytest
except ImportError:
    pytest = None

from unittest.mock import Mock, patch
from test.benchmarks.datasets import (
    generate_text_of_approx_tokens,
    get_llm_benchmark_payloads,
    get_reranker_benchmark_payloads,
    get_embedding_benchmark_payloads,
)
from test.benchmarks.bringup_bench import measure_endpoint_bringup
from test.benchmarks.embedding_bench import run_embedding_benchmarks
from test.benchmarks.reranker_bench import run_reranker_benchmarks
from test.benchmarks.llm_bench import parse_sse_stream
from test.benchmarks.reporter import evaluate_against_baseline
from test.benchmarks.metrics_collector import scrape_container_metrics


def test_dataset_generation():
    """Verify deterministic token lengths and batch payload generation."""
    text_128 = generate_text_of_approx_tokens(128)
    assert len(text_128.split()) > 50

    llm_payloads = get_llm_benchmark_payloads("standard", 32768)
    assert len(llm_payloads) >= 4
    assert any(p["approx_tokens"] == 128 for p in llm_payloads)

    reranker_payloads = get_reranker_benchmark_payloads()
    assert len(reranker_payloads) == 5
    assert reranker_payloads[0]["doc_count"] == 1

    embedding_payloads = get_embedding_benchmark_payloads()
    assert len(embedding_payloads) == 6
    assert embedding_payloads[-1]["batch_size"] == 64


def test_measure_endpoint_bringup_success():
    """Test successful health check within budget."""
    mock_resp = Mock(status_code=200)
    mock_state = {"Running": True, "Health": {"Status": "healthy"}}
    with patch("requests.get", return_value=mock_resp), \
         patch("test.benchmarks.bringup_bench.get_podman_container_state", return_value=mock_state):
        res = measure_endpoint_bringup("http://localhost:8000", image_type="vllm-spyre", profile="standard")
        assert res["status"] == "PASSED"
        assert res["ready"] is True
        assert res["http_ready_time_sec"] is not None
        assert res["container_healthy_time_sec"] is not None
        assert res["max_budget_sec"] == 510


def test_measure_endpoint_bringup_with_pod_yaml_and_logs():
    """Test bringup measuring with probe config parsing and podman launch/logs."""
    mock_resp = Mock(status_code=200)
    mock_proc = Mock(returncode=0, stdout="Started", stderr="")
    mock_state = {"Running": True, "Health": {"Status": "healthy"}}
    with patch("subprocess.run", return_value=mock_proc), \
         patch("requests.get", return_value=mock_resp), \
         patch("test.benchmarks.bringup_bench.get_podman_container_state", return_value=mock_state):
        res = measure_endpoint_bringup(
            "http://localhost:8001",
            image_type="embedding-cpu",
            pod_yaml_path="test/benchmarks/pod_yamls/embedding_cpu.yaml",
            auto_stop_pod=True
        )
        assert res["status"] == "PASSED"
        assert res["ready"] is True
        assert res["http_ready_time_sec"] is not None
        assert res["container_healthy_time_sec"] is not None
        assert res["pod_yaml_path"] is not None
        assert res["probe_config"] is not None
        assert res["probe_config"]["probe_path"] == "/health"

def test_measure_endpoint_bringup_container_failure_fast_exit():
    """Test that bringup fails immediately when container exits instead of hanging for full budget."""
    mock_proc = Mock(returncode=0, stdout="Started", stderr="")
    with patch("subprocess.run", return_value=mock_proc), \
         patch("test.benchmarks.bringup_bench.get_podman_container_state", return_value={"Running": False, "ExitCode": 1, "Status": "exited"}), \
         patch("test.benchmarks.bringup_bench.get_podman_container_logs", return_value="Error: 401 Unauthorized"), \
         patch("requests.get", side_effect=Exception("Connection refused")):
        res = measure_endpoint_bringup(
            "http://localhost:8001",
            image_type="embedding-cpu",
            pod_yaml_path="test/benchmarks/pod_yamls/embedding_cpu.yaml",
            max_wait_override=100.0,
            poll_interval=0.01
        )
        assert res["status"] == "FAILED"
        assert res["ready"] is False
        assert res["bringup_time_sec"] < 5.0
        assert "terminated prematurely" in res["error"]


def test_measure_endpoint_bringup_failure():
    """Test health check timeout failure."""
    with patch("requests.get", side_effect=Exception("Connection refused")):
        res = measure_endpoint_bringup("http://localhost:8000", image_type="vllm-cpu", profile="standard", max_wait_override=0.1, poll_interval=0.05)
        assert res["status"] == "FAILED"
        assert res["ready"] is False


def test_embedding_benchmarks_mock():
    """Test embedding benchmark runner with mock response."""
    mock_resp = Mock(status_code=200)
    with patch("requests.Session.post", return_value=mock_resp):
        res = run_embedding_benchmarks("http://localhost:8001", batch_sizes=[1, 4], iterations_per_batch=2)
        assert len(res) == 2
        assert res[0]["suite"] == "embedding"
        assert res[0]["error_rate_pct"] == 0.0


def test_reranker_benchmarks_mock():
    """Test reranker benchmark runner with mock response."""
    mock_resp = Mock(status_code=200)
    with patch("requests.Session.post", return_value=mock_resp):
        res = run_reranker_benchmarks("http://localhost:8002", iterations_per_payload=1)
        assert len(res) == 5
        assert res[0]["suite"] == "reranker"
        assert res[0]["error_rate_pct"] == 0.0


def test_parse_sse_stream():
    """Test SSE stream parsing for TTFT and ITL computation."""
    mock_lines = [
        'data: {"choices":[{"delta":{"content":"Hello"}}]}',
        'data: {"choices":[{"delta":{"content":" world"}}]}',
        'data: [DONE]'
    ]
    mock_resp = Mock()
    mock_resp.iter_lines = Mock(return_value=mock_lines)

    metrics = parse_sse_stream(mock_resp)
    assert metrics["num_tokens"] == 2
    assert metrics["text"] == "Hello world"
    assert "ttft_ms" in metrics
    assert "avg_itl_ms" in metrics


def test_pod_yaml_generation():
    """Test Pod YAML generation for prep work."""
    from test.benchmarks.generate_pod_yamls import (
        resolve_model_target,
        generate_llm_spyre_pod_yaml,
        generate_llm_cpu_pod_yaml,
        generate_reranker_pod_yaml,
        generate_embedding_pod_yaml
    )
    # When local path does not exist, should resolve directly to HF repo ID
    target_hf = resolve_model_target("ibm-granite/granite-embedding-278m-multilingual", "/non/existent/path")
    assert target_hf == "ibm-granite/granite-embedding-278m-multilingual"

    spyre_std = generate_llm_spyre_pod_yaml(profile="standard")
    assert spyre_std["kind"] == "Pod"
    assert spyre_std["spec"]["containers"][0]["resources"]["requests"]["podman.io/device=/dev/vfio"] == 4

    cpu_comp = generate_llm_cpu_pod_yaml(profile="compact")
    assert cpu_comp["spec"]["containers"][0]["resources"]["requests"]["cpu"] == "10"

    rerank = generate_reranker_pod_yaml(device="spyre")
    assert rerank["metadata"]["name"] == "benchmark-reranker-spyre"

    emb = generate_embedding_pod_yaml()
    assert emb["spec"]["containers"][0]["resources"]["requests"]["cpu"] == "2"


def test_scrape_container_metrics():
    """Test Prometheus metrics scraper parsing."""
    sample_prometheus_output = (
        "# HELP vllm:gpu_cache_usage_factor GPU KV-cache usage\n"
        "# TYPE vllm:gpu_cache_usage_factor gauge\n"
        "vllm:gpu_cache_usage_factor 0.425\n"
        "vllm:num_requests_running 3\n"
        "vllm:num_requests_waiting 1\n"
        "vllm:prompt_tokens_total 1024\n"
        "vllm:generation_tokens_total 512\n"
    )
    mock_resp = Mock(status_code=200, text=sample_prometheus_output)
    with patch("requests.get", return_value=mock_resp):
        m = scrape_container_metrics("http://localhost:8000")
        assert m["available"] is True
        assert m["kv_cache_usage_pct"] == 42.5
        assert m["num_requests_running"] == 3
        assert m["num_requests_waiting"] == 1
        assert m["prompt_tokens_total"] == 1024
        assert m["generation_tokens_total"] == 512
