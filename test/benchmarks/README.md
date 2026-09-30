# Model Acceptance Benchmarks

End-to-end acceptance and performance benchmark suite for model-serving runtimes (vLLM Spyre, vLLM CPU, Reranker, Embedding). The harness can optionally launch containers via Podman, measure bring-up time, run inference load tests, scrape Prometheus metrics, emit Markdown/CSV reports, and gate CI/CD pipelines against baseline thresholds.

---

## Directory Layout

```
test/benchmarks/
├── run_model_benchmarks.py   # Main CLI entrypoint
├── bringup_bench.py          # Container bring-up & health timing
├── llm_bench.py              # LLM streaming inference benchmark
├── embedding_bench.py        # Embedding /v1/embeddings benchmark
├── reranker_bench.py         # Reranker /v1/rerank benchmark
├── metrics_collector.py      # Prometheus /metrics scraper
├── reporter.py               # Markdown / CSV report generator & baseline comparator
├── history.py                # Persistent run history (runs.jsonl)
├── generate_pod_yamls.py     # Pod YAML generator for Podman / Kubernetes
├── download_models.py        # Hugging Face model pre-download utility
├── datasets.py               # Synthetic prompt / document dataset helpers
├── test_benchmarks.py        # Unit & acceptance tests (pytest)
├── requirements.txt          # Python dependencies
└── pod_yamls/                # Pre-generated Pod YAML manifests
    ├── vllm_spyre_standard.yaml
    ├── vllm_spyre_compact.yaml
    ├── vllm_cpu_standard.yaml
    ├── vllm_cpu_compact.yaml
    ├── reranker_spyre.yaml
    ├── reranker_cpu.yaml
    └── embedding_cpu.yaml
```

---

## Supported Models

The models below are the officially supported options defined in
[`ai-services/assets/components/*/podman/values.schema.json`](../../ai-services/assets/components).
These are the identifiers to pass via `--model-name`.

### LLM — vLLM CPU (`vllm-cpu`)

| HuggingFace Model ID | Default | Notes |
|---|---|---|
| `ibm-granite/granite-4.1-8b` | ✅ | 8B instruction-tuned; recommended for CPU deployments |
| `ibm-granite/granite-3.3-8b-instruct` | | Previous-generation Granite LLM; still supported |

**Container image:** `icr.io/ppc64le-oss/vllm-ppc64le:0.28.0`
**Default endpoint port:** `8000`

### LLM — vLLM Spyre (`vllm-spyre`)

| HuggingFace Model ID | Default | Notes |
|---|---|---|
| `ibm-granite/granite-4.1-8b-fp8` | ✅ | FP8-quantized Granite 4.1; optimised for Spyre AIU |
| `ibm-granite/granite-3.3-8b-instruct` | | Previous-generation; supported on Spyre |

**Container image:** `registry.redhat.io/rhaii/vllm-spyre-rhel9:3.5.0`
**Default endpoint port:** `8000`

### LLM — watsonx (`watsonx`)

> The `watsonx` backend is a managed proxy to IBM watsonx.ai and does not run a local container. Benchmark it via `--no-launch --image-type generic-openai`.

| Model ID | Default | Notes |
|---|---|---|
| `ibm/granite-4-h-small` | ✅ | 32B long-context instruct model from IBM Granite 4.0 family |

### Embedding — vLLM CPU (`embedding-cpu`)

| HuggingFace Model ID | Default | Notes |
|---|---|---|
| `ibm-granite/granite-embedding-278m-multilingual` | ✅ | 278M parameter multilingual dense embeddings (100+ languages) |

**Container image:** `icr.io/ppc64le-oss/vllm-ppc64le:0.28.0`
**Default endpoint port:** `8001`

### Reranker — vLLM CPU & Spyre (`reranker-cpu`, `reranker-spyre`)

| HuggingFace Model ID | Default | Notes |
|---|---|---|
| `BAAI/bge-reranker-v2-m3` | ✅ | Multilingual cross-encoder reranker; Cohere-compatible `/v1/rerank` API |

**Container images:**
- CPU: `icr.io/ppc64le-oss/vllm-ppc64le:0.28.0`
- Spyre: `registry.redhat.io/rhaii/vllm-spyre-rhel9:3.5.0`

**Default endpoint port:** `8002`

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python ≥ 3.9 | |
| `podman` CLI | Required only when launching pods via `--pod-yaml` |
| `huggingface_hub` | Required only for `download_models.py` |

Install Python dependencies:

```bash
pip install -r test/benchmarks/requirements.txt
```

---

## Quick Start

### 1. Pre-download models (optional but recommended)

Downloads model weights from Hugging Face Hub into `/mnt/models` so that pods can load them from a read-only host volume without network access at start time.

```bash
# Download all default benchmark models (granite-4.1-8b, granite-4.1-8b-fp8,
# granite-3.3-8b-instruct, granite-embedding-278m-multilingual, bge-reranker-v2-m3)
python -m test.benchmarks.download_models

# Download a specific model
python -m test.benchmarks.download_models \
    --models ibm-granite/granite-4.1-8b \
    --models-dir /data/models

# Dry run — print what would be downloaded without fetching
python -m test.benchmarks.download_models --dry-run

# Gated models require a Hugging Face token
python -m test.benchmarks.download_models --hf-token hf_...
# or: export HF_TOKEN=hf_...
```

After download the directory tree is:
```
/mnt/models/
  ibm-granite/
    granite-4.1-8b/
    granite-4.1-8b-fp8/
    granite-3.3-8b-instruct/
    granite-embedding-278m-multilingual/
  BAAI/
    bge-reranker-v2-m3/
```

### 2. Run benchmarks

#### Against an already-running endpoint

```bash
# LLM (vllm-cpu, granite-4.1-8b) running on localhost:8000
python -m test.benchmarks.run_model_benchmarks \
    --no-launch \
    --image-type vllm-cpu \
    --endpoint http://localhost:8000

# LLM with an explicit model name (e.g. legacy model)
python -m test.benchmarks.run_model_benchmarks \
    --no-launch \
    --image-type vllm-cpu \
    --endpoint http://localhost:8000 \
    --model-name ibm-granite/granite-3.3-8b-instruct

# Embedding endpoint
python -m test.benchmarks.run_model_benchmarks \
    --no-launch \
    --image-type embedding-cpu \
    --endpoint http://localhost:8001 \
    --suite embedding

# Reranker endpoint
python -m test.benchmarks.run_model_benchmarks \
    --no-launch \
    --image-type reranker-cpu \
    --endpoint http://localhost:8002 \
    --suite reranker
```

#### Launch a pod automatically, benchmark it, and tear it down

```bash
# vLLM CPU — granite-4.1-8b (default)
python -m test.benchmarks.run_model_benchmarks \
    test/benchmarks/pod_yamls/vllm_cpu_standard.yaml

# vLLM Spyre — granite-4.1-8b-fp8 (default)
python -m test.benchmarks.run_model_benchmarks \
    test/benchmarks/pod_yamls/vllm_spyre_standard.yaml

# Embedding
python -m test.benchmarks.run_model_benchmarks \
    test/benchmarks/pod_yamls/embedding_cpu.yaml

# Reranker (CPU)
python -m test.benchmarks.run_model_benchmarks \
    test/benchmarks/pod_yamls/reranker_cpu.yaml
```

The runner infers `--image-type`, `--endpoint`, `--suite`, and `--model-name` from the YAML filename and its contents automatically.

---

## CLI Reference — `run_model_benchmarks.py`

### Default mode (run benchmarks)

```
run_model_benchmarks.py [pod_yaml] [options]
```

| Flag | Default | Description |
|---|---|---|
| `pod_yaml` (positional) | — | Pod YAML to launch, benchmark, and tear down |
| `--pod-yaml` | — | Alternative way to supply the Pod YAML path |
| `--image-type` | auto-inferred | `vllm-spyre`, `vllm-cpu`, `embedding-cpu`, `reranker-spyre`, `reranker-cpu`, `generic-openai` |
| `--endpoint` | auto-inferred | Base URL, e.g. `http://localhost:8000` |
| `--suite` | `all` | Comma-separated list: `bringup`, `llm`, `embedding`, `reranker`, `all` |
| `--profile` | `standard` | Hardware profile: `standard` or `compact` |
| `--model-name` | auto-detected | Model ID used in benchmark payloads |
| `--no-launch` | `false` | Skip pod launch; test against an existing endpoint |
| `--no-stop` | `false` | Keep the pod running after benchmarks finish |
| `--api-key` | — | Bearer token for authenticated endpoints |
| `--output-dir` | `test/benchmarks/results` | Directory for reports and run history |
| `--baseline` | — | Path to a baseline JSON for CI regression gating |
| `--threshold-pct` | `15.0` | Regression tolerance percentage |

### `history` subcommand

List recent benchmark runs stored in `runs.jsonl`.

```bash
python -m test.benchmarks.run_model_benchmarks history [--output-dir DIR] [--limit N]
```

### `compare` subcommand

Produce a side-by-side Markdown diff between two runs.

```bash
python -m test.benchmarks.run_model_benchmarks compare <run_id_A> <run_id_B> \
    [--output-dir DIR] [--out comparison.md]
```

`run_id_A` / `run_id_B` are prefix strings that match a `run_id` in `runs.jsonl` — e.g. `20250601-143022`.

---

## Benchmark Suites

### Bring-Up (`bringup`)

Measures cold-start time by polling the pod's readiness/liveness probe endpoint (`/health` by default) and monitoring Podman container health state. Reports:

| Metric | Description |
|---|---|
| `http_ready_time_sec` | Seconds until the first HTTP 200 from the probe URL |
| `container_healthy_time_sec` | Seconds until Podman health status transitions to `healthy` |
| `bringup_time_sec` | Overall bring-up time (max of the two above) |
| `status` | `PASSED` / `FAILED` relative to the budget limit |

Timeout budgets per image type:

| Image Type | Standard | Compact |
|---|---|---|
| `vllm-spyre` | 510 s | 270 s |
| `vllm-cpu` | 480 s | 480 s |
| `reranker-spyre` | 210 s | 210 s |
| `reranker-cpu` | 210 s | — |
| `embedding-cpu` | 210 s | — |

### LLM Inference (`llm`)

Fires concurrent streaming chat-completion requests (`/v1/chat/completions`) across concurrency levels `[1, 4, 8, 16, 32]` (standard) or `[1, 4, 8, 16]` (compact) using a 512-token prompt baseline. Metrics per concurrency level:

| Metric | Description |
|---|---|
| `p95_ttft_ms` | 95th-percentile Time-to-First-Token (ms) |
| `avg_itl_ms` | Average Inter-Token Latency / TPOT (ms/token) |
| `aggregate_tokens_per_sec` | Total tokens generated across all concurrent requests per second |
| `error_rate_pct` | Percentage of requests that returned a non-200 status |

Default model: `ibm-granite/granite-4.1-8b` (CPU) / `ibm-granite/granite-4.1-8b-fp8` (Spyre)

### Embedding (`embedding`)

Sends batches of texts to `/v1/embeddings` across batch sizes `[1, 4, 8, 16, 32, 64]` with 5 iterations each (1 warmup). Reports latency percentiles and throughput:

| Metric | Description |
|---|---|
| `avg_latency_ms` / `p50` / `p90` / `p95` / `p99` | Latency distribution (ms) |
| `throughput_texts_per_sec` | Input texts processed per second |
| `throughput_tokens_per_sec` | Approximate tokens processed per second |
| `error_rate_pct` | Percentage of failed requests |

Default model: `ibm-granite/granite-embedding-278m-multilingual`

### Reranker (`reranker`)

Sends document reranking requests to `/v1/rerank` (Cohere-compatible) across candidate pool sizes `[1, 5, 10, 25, 50]` with 5 iterations each. Reports:

| Metric | Description |
|---|---|
| `avg_latency_ms` / `p50` / `p90` / `p95` / `p99` | Latency distribution (ms) |
| `throughput_docs_per_sec` | Documents ranked per second |
| `error_rate_pct` | Percentage of failed requests |

Default model: `BAAI/bge-reranker-v2-m3`

---

## Output Files

All outputs land in `--output-dir` (default: `test/benchmarks/results/`):

| File | Description |
|---|---|
| `benchmark_report.md` | Human-readable Markdown summary with tables for all suites |
| `benchmark_report.csv` | Flat CSV with all metric rows, suitable for spreadsheet import |
| `runs.jsonl` | Append-only JSON-Lines run history; one record per benchmark run |

---

## Run History & Comparison

Every completed run is automatically appended to `runs.jsonl` with a unique `run_id` in the format:

```
YYYYMMDD-HHMMSS-<image-type>-<profile>[-<model-name>]
```

**List recent runs:**

```bash
python -m test.benchmarks.run_model_benchmarks history --limit 10
```

```
RUN ID                                      TIMESTAMP             IMAGE TYPE            PROFILE    PASS
----------------------------------------------------------------------------------------------------------
20250601-143022-vllm-cpu-standard           2025-06-01T14:30:22   vllm-cpu (granite…)   standard   ✅
20250531-090011-vllm-spyre-compact          2025-05-31T09:00:11   vllm-spyre            compact    ✅
```

**Compare two runs:**

```bash
python -m test.benchmarks.run_model_benchmarks compare 20250531 20250601 \
    --out test/benchmarks/results/comparison.md
```

The comparison report uses `⚠️` to flag regressions > 5% and `✅` to highlight improvements > 5%.

---

## CI/CD Regression Gate

Pass `--baseline` to gate a run against a previously saved results JSON. Any metric that regresses beyond `--threshold-pct` (default `15%`) causes the process to exit with code 1.

```bash
python -m test.benchmarks.run_model_benchmarks \
    test/benchmarks/pod_yamls/vllm_cpu_standard.yaml \
    --baseline test/benchmarks/results/baseline.json \
    --threshold-pct 10
```

To create a baseline, copy `benchmark_report`-equivalent data from a known-good run's `runs.jsonl` entry into a `.json` file. The comparator checks `p95_ttft_ms` for LLM suites and `p95_latency_ms` for Reranker suites.

---

## Pod YAML Manifests

Pre-generated manifests live in [`pod_yamls/`](pod_yamls/). They can be applied directly with Podman:

```bash
podman play kube test/benchmarks/pod_yamls/vllm_cpu_standard.yaml
```

To regenerate them (e.g. after changing model names or images):

```bash
python -m test.benchmarks.generate_pod_yamls
```

| Manifest | Runtime | Profile | Default Model | Default Port |
|---|---|---|---|---|
| `vllm_spyre_standard.yaml` | vLLM Spyre (4 cards) | standard | `granite-4.1-8b-fp8` | 8000 |
| `vllm_spyre_compact.yaml` | vLLM Spyre (1 card) | compact | `granite-4.1-8b-fp8` | 8000 |
| `vllm_cpu_standard.yaml` | vLLM CPU | standard | `granite-4.1-8b` | 8000 |
| `vllm_cpu_compact.yaml` | vLLM CPU | compact | `granite-4.1-8b` | 8000 |
| `reranker_spyre.yaml` | Reranker Spyre | — | `bge-reranker-v2-m3` | 8002 |
| `reranker_cpu.yaml` | Reranker CPU | — | `bge-reranker-v2-m3` | 8002 |
| `embedding_cpu.yaml` | Embedding CPU | — | `granite-embedding-278m-multilingual` | 8001 |

---

## Running the Unit Tests

```bash
# From the repo root
pytest test/benchmarks/test_benchmarks.py -v
```

The test suite covers dataset generation, bringup probe logic (mocked Podman + HTTP), embedding/reranker runners, SSE stream parsing, Pod YAML generation, and Prometheus metrics scraping. All external I/O is mocked — no live endpoints or Podman installation required.

---

## Module Reference

| Module | Purpose |
|---|---|
| [`run_model_benchmarks.py`](run_model_benchmarks.py) | CLI driver; orchestrates pod lifecycle, suite dispatch, reporting, and CI gating |
| [`bringup_bench.py`](bringup_bench.py) | Podman pod launch, health polling, container state inspection |
| [`llm_bench.py`](llm_bench.py) | SSE streaming inference load test; TTFT / ITL / throughput metrics |
| [`embedding_bench.py`](embedding_bench.py) | Batched embedding latency and throughput tests |
| [`reranker_bench.py`](reranker_bench.py) | Document reranking latency and throughput tests |
| [`metrics_collector.py`](metrics_collector.py) | Prometheus `/metrics` scraper; extracts KV-cache, request queue, token counters |
| [`reporter.py`](reporter.py) | Markdown/CSV report generation; baseline regression comparator |
| [`history.py`](history.py) | `runs.jsonl` persistence; `save_run`, `load_runs`, `find_run`, `compare_runs` |
| [`generate_pod_yamls.py`](generate_pod_yamls.py) | Programmatic Pod YAML generator for all runtimes and profiles |
| [`download_models.py`](download_models.py) | Hugging Face `snapshot_download` wrapper with verification |
| [`datasets.py`](datasets.py) | Synthetic text generation for LLM, embedding, and reranker payloads |
| [`test_benchmarks.py`](test_benchmarks.py) | pytest unit and acceptance tests |
