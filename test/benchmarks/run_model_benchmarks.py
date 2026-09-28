#!/usr/bin/env python3
"""
Main CLI Driver for Model Acceptance Testing and Benchmarking.

Allows selecting test suites (--suite llm,embedding,reranker,bringup,all),
target images (--image-type vllm-spyre, vllm-cpu), deployment profiles (standard, compact),
and automated evaluation against baseline SLA thresholds.
"""

import sys
import argparse
import datetime
from pathlib import Path
from typing import Dict, Any

from test.benchmarks.bringup_bench import measure_endpoint_bringup
from test.benchmarks.llm_bench import run_llm_benchmarks
from test.benchmarks.reranker_bench import run_reranker_benchmarks
from test.benchmarks.embedding_bench import run_embedding_benchmarks
from test.benchmarks.reporter import generate_markdown_report, generate_csv_report, evaluate_against_baseline
from test.benchmarks.generate_pod_yamls import generate_all_prep_pod_yamls


def parse_args():
    parser = argparse.ArgumentParser(description="Model Serving Benchmark & Acceptance Testing CLI")
    
    parser.add_argument("--image-type", choices=["vllm-spyre", "vllm-cpu", "generic-openai"], default="vllm-cpu",
                        help="Container image runtime to target and evaluate")
    parser.add_argument("--profile", choices=["standard", "compact"], default="standard",
                        help="Deployment hardware profile")
    parser.add_argument("--suite", default="all",
                        help="Comma-separated test suites: llm, embedding, reranker, bringup, all")
    parser.add_argument("--prep-pod-yamls", action="store_true",
                        help="Generate prep Pod YAML files before executing benchmarks")
    parser.add_argument("--pod-yamls-dir", default="test/benchmarks/pod_yamls",
                        help="Directory to save prepared Pod YAML manifests")
    
    parser.add_argument("--llm-endpoint", default="http://localhost:8000", help="LLM endpoint URL")
    parser.add_argument("--embedding-endpoint", default="http://localhost:8001", help="Embedding endpoint URL")
    parser.add_argument("--reranker-endpoint", default="http://localhost:8002", help="Reranker endpoint URL")
    
    parser.add_argument("--api-key", default=None, help="Optional API key / Bearer token")
    parser.add_argument("--output-dir", default="test/benchmarks/results", help="Directory for CSV and Markdown reports")
    parser.add_argument("--baseline", default=None, help="Path to baseline JSON for CI regression gating")
    parser.add_argument("--threshold-pct", type=float, default=15.0, help="Allowable regression tolerance percentage")
    
    return parser.parse_args()


def main():
    args = parse_args()

    if args.prep_pod_yamls:
        print(f"=== Generating Prepared Pod YAML Manifests in {args.pod_yamls_dir} ===")
        generate_all_prep_pod_yamls(Path(args.pod_yamls_dir))
        print("Pod YAML generation complete.\n")

    suites = [s.strip().lower() for s in args.suite.split(",")]
    run_all = "all" in suites
    
    results: Dict[str, Any] = {
        "image_type": args.image_type,
        "profile": args.profile,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "passed": True
    }
    
    print(f"=== Starting Benchmark Suite for Image: {args.image_type} (Profile: {args.profile}) ===")
    
    # 1. Bring-Up Suite
    if run_all or "bringup" in suites:
        print(f"\n[1/4] Running Bring-up & Health Check on {args.llm_endpoint}...")
        bringup_res = measure_endpoint_bringup(
            endpoint=args.llm_endpoint,
            image_type=args.image_type,
            profile=args.profile,
            api_key=args.api_key
        )
        results["bringup"] = bringup_res
        print(f"  -> Bring-up Status: {bringup_res['status']} in {bringup_res['bringup_time_sec']}s (Budget: {bringup_res['max_budget_sec']}s)")
        if bringup_res["status"] != "PASSED":
            results["passed"] = False

    # 2. LLM Inference Suite
    if run_all or "llm" in suites:
        print(f"\n[2/4] Running LLM Inference Benchmarks on {args.llm_endpoint}...")
        llm_res = run_llm_benchmarks(
            endpoint=args.llm_endpoint,
            profile=args.profile,
            api_key=args.api_key
        )
        results["llm"] = llm_res
        print(f"  -> Completed {len(llm_res)} LLM concurrency tests.")

    # 3. Reranker Suite
    if run_all or "reranker" in suites:
        print(f"\n[3/4] Running Reranker Benchmarks on {args.reranker_endpoint}...")
        rerank_res = run_reranker_benchmarks(
            endpoint=args.reranker_endpoint,
            api_key=args.api_key
        )
        results["reranker"] = rerank_res
        print(f"  -> Completed {len(rerank_res)} Reranker candidate tests.")

    # 4. Embedding Suite
    if run_all or "embedding" in suites:
        print(f"\n[4/4] Running Embedding Benchmarks on {args.embedding_endpoint}...")
        emb_res = run_embedding_benchmarks(
            endpoint=args.embedding_endpoint,
            api_key=args.api_key
        )
        results["embedding"] = emb_res
        print(f"  -> Completed {len(emb_res)} Embedding batch tests.")

    # Generate Reports
    out_dir = Path(args.output_dir)
    md_file = out_dir / "benchmark_report.md"
    csv_file = out_dir / "benchmark_report.csv"
    
    generate_markdown_report(results, md_file)
    generate_csv_report(results, csv_file)
    print(f"\nReports generated:\n  - Markdown: {md_file}\n  - CSV: {csv_file}")

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
