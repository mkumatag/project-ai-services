#!/usr/bin/env python3
"""
Main CLI Driver for Model Acceptance Testing and Benchmarking.

Allows selecting test suites (--suite llm,embedding,reranker,bringup,all),
target images (--image-type vllm-spyre, vllm-cpu), deployment profiles (standard, compact),
automated evaluation against baseline SLA thresholds, and persistent run history.

Subcommands
-----------
  (default)          Run benchmarks and record results to history.
  history            List recent benchmark runs.
  compare <A> <B>    Compare two runs by run_id prefix and produce a diff report.
"""

import sys
import os
import argparse
import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Ensure project root is in sys.path when executed directly
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from test.benchmarks.bringup_bench import measure_endpoint_bringup
from test.benchmarks.llm_bench import run_llm_benchmarks
from test.benchmarks.reranker_bench import run_reranker_benchmarks
from test.benchmarks.embedding_bench import run_embedding_benchmarks
from test.benchmarks.reporter import (
    generate_markdown_report,
    generate_csv_report,
    evaluate_against_baseline,
    generate_comparison_report,
)
from test.benchmarks.history import save_run, load_runs, find_run, compare_runs, print_history
from test.benchmarks.generate_pod_yamls import generate_all_prep_pod_yamls
from test.benchmarks.metrics_collector import scrape_container_metrics


def parse_args():
    # Detect whether the first non-flag token is a named subcommand so that a
    # plain pod_yaml path (e.g. "test/benchmarks/pod_yamls/vllm_cpu_standard.yaml")
    # is never mistaken for a subcommand name.
    _SUBCOMMANDS = {"history", "compare"}
    first_positional = next(
        (a for a in sys.argv[1:] if not a.startswith("-")), None
    )
    subcommand = first_positional if first_positional in _SUBCOMMANDS else None

    if subcommand == "history":
        parser = argparse.ArgumentParser(
            prog="run_model_benchmarks.py history",
            description="List recent benchmark runs",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        parser.add_argument("subcommand")          # consume the word "history"
        parser.add_argument("--output-dir", default="test/benchmarks/results",
                            help="Directory containing runs.jsonl")
        parser.add_argument("--limit", type=int, default=20, help="Max runs to show")
        args = parser.parse_args()
        args.subcommand = "history"
        return args

    if subcommand == "compare":
        parser = argparse.ArgumentParser(
            prog="run_model_benchmarks.py compare",
            description="Compare two benchmark runs side-by-side",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        parser.add_argument("subcommand")          # consume the word "compare"
        parser.add_argument("run_a", help="run_id prefix for the baseline run")
        parser.add_argument("run_b", help="run_id prefix for the new run")
        parser.add_argument("--output-dir", default="test/benchmarks/results",
                            help="Directory containing runs.jsonl")
        parser.add_argument("--out", default=None,
                            help="Output path for comparison Markdown "
                                 "(default: <output-dir>/comparison_<A_vs_B>.md)")
        args = parser.parse_args()
        args.subcommand = "compare"
        return args

    # ── default: run benchmarks ───────────────────────────────────────────
    parser = argparse.ArgumentParser(
        description="Model Serving Acceptance & Benchmark Runner",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("pod_yaml", nargs="?", default=None,
                        help="Optional Pod YAML to automatically start, benchmark, and tear down")
    parser.add_argument("--pod-yaml", dest="pod_yaml_opt", default=None,
                        help="Alternative way to supply Pod YAML path")
    parser.add_argument("--image-type",
                        choices=["vllm-spyre", "vllm-cpu", "generic-openai",
                                 "embedding-cpu", "reranker-spyre", "reranker-cpu"],
                        default=None,
                        help="Container image runtime (auto-inferred from pod YAML if omitted)")
    parser.add_argument("--endpoint", default=None,
                        help="Endpoint URL (e.g. http://localhost:8001). Auto-inferred if omitted.")
    parser.add_argument("--suite", default="all",
                        help="Test suite to run: all, bringup, llm, embedding, reranker")
    parser.add_argument("--profile", choices=["standard", "compact"], default="standard",
                        help="Deployment hardware profile")
    parser.add_argument("--model-name", default=None,
                        help="Model ID to query in benchmark payloads (auto-detected if omitted)")
    parser.add_argument("--no-launch", action="store_true",
                        help="Do not launch a pod via Podman; test against an existing running endpoint")
    parser.add_argument("--no-stop", action="store_true",
                        help="Keep pod running after benchmark (by default pods launched from YAML are auto-stopped)")
    parser.add_argument("--api-key", default=None, help="Optional API key / Bearer token")
    parser.add_argument("--output-dir", default="test/benchmarks/results",
                        help="Directory for reports")
    parser.add_argument("--baseline", default=None,
                        help="Path to baseline JSON for CI regression gating")
    parser.add_argument("--threshold-pct", type=float, default=15.0,
                        help="Regression tolerance percentage")
    args = parser.parse_args()
    args.subcommand = None
    return args


def infer_runtime_from_yaml(pod_yaml_path: Optional[str]) -> tuple:
    """Infer image_type, default port/endpoint, suite, and model name from Pod YAML."""
    if not pod_yaml_path:
        return "vllm-cpu", "http://localhost:8000", "llm", None
    
    name = Path(pod_yaml_path).stem.lower()
    model_name = None
    
    # Try parsing served-model-name or model from the yaml file if present
    try:
        with open(pod_yaml_path, "r") as f:
            content = f.read()
            pod_dict = yaml.safe_load(content)
            containers = pod_dict.get("spec", {}).get("containers", [])
            if containers:
                args = containers[0].get("args", [])
                # First check individual string tokens in args list
                for i, arg in enumerate(args):
                    if arg in ("--served-model-name", "--model") and i + 1 < len(args):
                        val = args[i + 1]
                        if not val.startswith("-"):
                            model_name = val.removeprefix("/models/")
                            break
                # If not found, check if args is a shell command string (e.g. ['-c', 'exec vllm serve ...'])
                if not model_name:
                    import re
                    match = re.search(r"--served-model-name\s+([^\s\\]+)", content)
                    if match:
                        model_name = match.group(1).strip().removeprefix("/models/")
    except Exception:
        pass

    if "embedding" in name:
        return "embedding-cpu", "http://localhost:8001", "embedding", model_name
    elif "reranker" in name:
        device = "spyre" if "spyre" in name else "cpu"
        return f"reranker-{device}", "http://localhost:8002", "reranker", model_name
    elif "spyre" in name:
        return "vllm-spyre", "http://localhost:8000", "llm", model_name
    return "vllm-cpu", "http://localhost:8000", "llm", model_name


def cmd_history(args) -> None:
    """Handle the `history` subcommand."""
    print_history(Path(args.output_dir), limit=args.limit)


def cmd_compare(args) -> None:
    """Handle the `compare` subcommand."""
    out_dir = Path(args.output_dir)
    run_a = find_run(args.run_a, out_dir)
    run_b = find_run(args.run_b, out_dir)

    if run_a is None:
        print(f"❌ No run found matching prefix: {args.run_a}", file=sys.stderr)
        sys.exit(1)
    if run_b is None:
        print(f"❌ No run found matching prefix: {args.run_b}", file=sys.stderr)
        sys.exit(1)

    diff = compare_runs(run_a, run_b)

    out_file = args.out
    if out_file is None:
        a_slug = args.run_a[:12].replace("/", "-")
        b_slug = args.run_b[:12].replace("/", "-")
        out_file = str(out_dir / f"comparison_{a_slug}_vs_{b_slug}.md")

    md = generate_comparison_report(diff, Path(out_file))
    print(md)
    print(f"\nComparison report written to: {out_file}")


def main():
    args = parse_args()

    # Dispatch subcommands before touching run-specific args
    if args.subcommand == "history":
        cmd_history(args)
        return
    if args.subcommand == "compare":
        cmd_compare(args)
        return

    pod_yaml = args.pod_yaml or args.pod_yaml_opt
    
    inferred_type, inferred_ep, inferred_suite, inferred_model = infer_runtime_from_yaml(pod_yaml)
    image_type = args.image_type or inferred_type
    endpoint = args.endpoint or inferred_ep
    model_name = args.model_name or inferred_model
    
    suites = [s.strip().lower() for s in args.suite.split(",")]
    run_all = "all" in suites
    
    results: Dict[str, Any] = {
        "image_type": image_type,
        "profile": args.profile,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "passed": True
    }
    
    print(f"=== Starting Benchmark Suite for {image_type} (Profile: {args.profile}) ===")
    if pod_yaml:
        print(f"Target Pod YAML: {pod_yaml}")
    print(f"Target Endpoint: {endpoint}\n")
    
    # Auto-stop pod if started from YAML unless --no-stop is specified
    should_auto_stop = bool(pod_yaml and not args.no_stop)

    # Pod launch + readiness wait — always runs when a pod_yaml is provided,
    # regardless of which --suite was requested.  Without this gate the
    # benchmark requests hit a non-existent endpoint and silently return errors.
    if pod_yaml and not args.no_launch:
        print(f"[Pod] Launching {pod_yaml} and waiting for endpoint {endpoint} to become ready...")
        bringup_res = measure_endpoint_bringup(
            endpoint=endpoint,
            image_type=image_type,
            profile=args.profile,
            api_key=args.api_key,
            pod_yaml_path=pod_yaml,
            auto_stop_pod=False,   # teardown handled at the end of main()
        )
        http_t = f"{bringup_res.get('http_ready_time_sec')}s" if bringup_res.get('http_ready_time_sec') is not None else "N/A"
        c_health_t = f"{bringup_res.get('container_healthy_time_sec')}s" if bringup_res.get('container_healthy_time_sec') is not None else "N/A"
        print(f"  -> Bring-up Status  : {bringup_res['status']}")
        print(f"     HTTP ready        : {http_t}")
        print(f"     Container healthy : {c_health_t}")
        print(f"     Budget limit      : {bringup_res['max_budget_sec']}s")
        if bringup_res["status"] != "PASSED":
            results["passed"] = False
            results["bringup"] = bringup_res
            if bringup_res.get("error"):
                print(f"     Error: {bringup_res['error']}")
            # Abort early — no point benchmarking a pod that never came up
            print("\n❌ Pod did not become ready. Aborting benchmark suites.")
            if should_auto_stop:
                from test.benchmarks.bringup_bench import stop_podman_kube
                stop_podman_kube(pod_yaml)
            sys.exit(1)
        # Always record bringup timing in results
        results["bringup"] = bringup_res

    # 1. Bring-Up Suite — records bringup metrics in report (pod was already launched above)
    if run_all or "bringup" in suites:
        if not pod_yaml:
            # No pod_yaml: just probe the already-running endpoint health
            print(f"[1/4] Running Bring-up & Health Check on {endpoint}...")
            bringup_res = measure_endpoint_bringup(
                endpoint=endpoint,
                image_type=image_type,
                profile=args.profile,
                api_key=args.api_key,
                pod_yaml_path=None,
                auto_stop_pod=False,
            )
            results["bringup"] = bringup_res
            http_t = f"{bringup_res.get('http_ready_time_sec')}s" if bringup_res.get('http_ready_time_sec') is not None else "N/A"
            print(f"  -> Bring-up Status: {bringup_res['status']}  HTTP ready: {http_t}")
            if bringup_res["status"] != "PASSED":
                results["passed"] = False
        else:
            # pod_yaml case: bringup already measured above, just print the section header
            print(f"[1/4] Bring-up: already measured during pod launch (see above).")

    # 2. LLM Inference Suite
    if (run_all and inferred_suite == "llm") or "llm" in suites:
        print(f"\n[2/4] Running LLM Inference Benchmarks on {endpoint}...")
        llm_kwargs = {
            "endpoint": endpoint,
            "profile": args.profile,
            "api_key": args.api_key
        }
        if model_name:
            llm_kwargs["model_name"] = model_name
        llm_res = run_llm_benchmarks(**llm_kwargs)
        results["llm"] = llm_res
        print(f"  -> Completed {len(llm_res)} LLM concurrency tests.")

    # 3. Reranker Suite
    if (run_all and inferred_suite == "reranker") or "reranker" in suites:
        print(f"\n[3/4] Running Reranker Benchmarks on {endpoint}...")
        rerank_kwargs = {
            "endpoint": endpoint,
            "api_key": args.api_key
        }
        if model_name:
            rerank_kwargs["model_name"] = model_name
        rerank_res = run_reranker_benchmarks(**rerank_kwargs)
        results["reranker"] = rerank_res
        print(f"  -> Completed {len(rerank_res)} Reranker candidate tests.")

    # 4. Embedding Suite
    if (run_all and inferred_suite == "embedding") or "embedding" in suites:
        print(f"\n[4/4] Running Embedding Benchmarks on {endpoint}...")
        emb_kwargs = {
            "endpoint": endpoint,
            "api_key": args.api_key
        }
        if model_name:
            emb_kwargs["model_name"] = model_name
        emb_res = run_embedding_benchmarks(**emb_kwargs)
        results["embedding"] = emb_res
        print(f"  -> Completed {len(emb_res)} Embedding batch tests.")

    # 5. Collect Container & Runtime Prometheus Metrics
    print(f"\n[Metrics] Collecting container metrics from {endpoint}/metrics...")
    container_metrics = scrape_container_metrics(endpoint, api_key=args.api_key)
    results["container_metrics"] = container_metrics
    if container_metrics.get("available"):
        print(f"  -> Scraped metrics successfully (KV Cache: {container_metrics.get('kv_cache_usage_pct')}%, Running: {container_metrics.get('num_requests_running')})")
    else:
        print("  -> /metrics endpoint not available or returned non-200 (skipped).")

    # Generate Reports
    out_dir = Path(args.output_dir)
    md_file = out_dir / "benchmark_report.md"
    csv_file = out_dir / "benchmark_report.csv"
    
    generate_markdown_report(results, md_file)
    generate_csv_report(results, csv_file)

    # Persist to run history
    if model_name:
        results["model_name"] = model_name
    run_id = save_run(results, out_dir)
    print(f"\nReports generated:\n  - Markdown: {md_file}\n  - CSV: {csv_file}")
    print(f"  - History:  {out_dir}/runs.jsonl  (run_id: {run_id})")

    # Teardown pod if started via pod_yaml
    if pod_yaml and should_auto_stop:
        from test.benchmarks.bringup_bench import stop_podman_kube
        print(f"\nTearing down pod {pod_yaml}...")
        stop_podman_kube(pod_yaml)

    # Baseline CI Gate Evaluation
    if args.baseline:
        passed, violations = evaluate_against_baseline(
            results,
            Path(args.baseline),
            tolerance_pct=args.threshold_pct
        )
        if not passed:
            print("\n❌ CI/CD Regression Gate FAILED with the following violations:")
            for v in violations:
                print(f"  - {v}")
            sys.exit(1)
        else:
            print("\n✅ CI/CD Regression Gate PASSED (within tolerance thresholds).")

    sys.exit(0 if results["passed"] else 1)


if __name__ == "__main__":
    main()
