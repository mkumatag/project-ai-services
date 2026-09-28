"""
Unit and Acceptance Tests for Benchmark Harness and Modules.
"""

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
    with patch("requests.get", return_value=mock_resp):
        res = measure_endpoint_bringup("http://localhost:8000", image_type="vllm-spyre", profile="standard")
        assert res["status"] == "PASSED"
        assert res["ready"] is True
        assert res["max_budget_sec"] == 510


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
        generate_llm_spyre_pod_yaml,
        generate_llm_cpu_pod_yaml,
        generate_reranker_pod_yaml,
        generate_embedding_pod_yaml
    )
    spyre_std = generate_llm_spyre_pod_yaml(profile="standard")
    assert spyre_std["kind"] == "Pod"
    assert spyre_std["spec"]["containers"][0]["resources"]["requests"]["podman.io/device=/dev/vfio"] == 4

    cpu_comp = generate_llm_cpu_pod_yaml(profile="compact")
    assert cpu_comp["spec"]["containers"][0]["resources"]["requests"]["cpu"] == "10"

    rerank = generate_reranker_pod_yaml(device="spyre")
    assert rerank["metadata"]["name"] == "benchmark-reranker-spyre"

    emb = generate_embedding_pod_yaml()
    assert emb["spec"]["containers"][0]["resources"]["requests"]["cpu"] == "2"
