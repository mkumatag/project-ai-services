#!/usr/bin/env python3
"""
Model Pre-Download Utility.

Downloads model weights from Hugging Face Hub into the host models directory
(/mnt/models by default) so that benchmark pods can consume them from the
read-only hostPath volume mount without needing network access at start time.

Directory layout on the host after download:
  /mnt/models/
    ibm-granite/
      granite-3.0-8b-instruct/       ← full HF snapshot
      granite-embedding-278m-multilingual/
    BAAI/
      bge-reranker-v2-m3/

The pods see this tree at /models/<org>/<model> inside the container.
generate_pod_yamls.resolve_model_target() detects the local path automatically.

Usage
-----
  # Download all default benchmark models
  python -m test.benchmarks.download_models

  # Download a single model to a custom directory
  python -m test.benchmarks.download_models \\
      --models ibm-granite/granite-3.0-8b-instruct \\
      --models-dir /data/models

  # List what would be downloaded (dry-run)
  python -m test.benchmarks.download_models --dry-run

  # With a Hugging Face token (required for gated models)
  python -m test.benchmarks.download_models --hf-token hf_...
  # or set the environment variable: HF_TOKEN=hf_...

Requirements
------------
  pip install huggingface_hub
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

# Models used across all benchmark pod YAMLs in this repo.
# Kept in sync with ai-services/assets/components/*/podman/values.schema.json.
DEFAULT_MODELS = [
    # LLM — vllm-cpu (default: granite-4.1-8b)
    "ibm-granite/granite-4.1-8b",
    # LLM — vllm-cpu (legacy / alternate)
    "ibm-granite/granite-3.3-8b-instruct",
    # LLM — vllm-spyre (default: granite-4.1-8b-fp8)
    "ibm-granite/granite-4.1-8b-fp8",
    # Reranker — vllm-cpu and vllm-spyre
    "BAAI/bge-reranker-v2-m3",
    # Embedding — vllm-cpu
    "ibm-granite/granite-embedding-278m-multilingual",
]

DEFAULT_MODELS_DIR = "/mnt/models"


# ── helpers ────────────────────────────────────────────────────────────────

def _require_huggingface_hub():
    try:
        from huggingface_hub import snapshot_download, HfApi  # noqa: F401
    except ImportError:
        print(
            "❌  huggingface_hub is not installed.\n"
            "    Run:  pip install huggingface_hub",
            file=sys.stderr,
        )
        sys.exit(1)


def local_model_path(model_name: str, models_dir: Path) -> Path:
    """Return the expected on-disk path for a given HF model id."""
    return models_dir / model_name


def is_downloaded(model_name: str, models_dir: Path) -> bool:
    """
    Quick check: model is considered downloaded if its local directory exists
    and contains at least one weight file (*.safetensors or *.bin).
    """
    local = local_model_path(model_name, models_dir)
    if not local.is_dir():
        return False
    weight_files = list(local.glob("*.safetensors")) + list(local.glob("*.bin"))
    return len(weight_files) > 0


def download_model(
    model_name: str,
    models_dir: Path,
    hf_token: Optional[str] = None,
    force: bool = False,
) -> Path:
    """
    Download a Hugging Face model snapshot into models_dir/<model_name>.

    Uses snapshot_download which:
    - Downloads all files in the repo into a single flat directory
    - Skips files already present (safe to re-run)
    - Respects HF_TOKEN / token argument for gated models

    Returns the local Path where the model was saved.
    """
    from huggingface_hub import snapshot_download

    local_dir = local_model_path(model_name, models_dir)

    if not force and is_downloaded(model_name, models_dir):
        print(f"  ✅  {model_name}  →  already present at {local_dir}")
        return local_dir

    print(f"  ⬇️   {model_name}  →  {local_dir} ...")
    local_dir.mkdir(parents=True, exist_ok=True)

    snapshot_download(
        repo_id=model_name,
        local_dir=str(local_dir),
        token=hf_token,
        ignore_patterns=["*.msgpack", "flax_model*", "tf_model*", "rust_model*"],
    )
    print(f"  ✅  {model_name}  →  done")
    return local_dir


def verify_model(model_name: str, models_dir: Path) -> bool:
    """Print a brief verification summary for a downloaded model."""
    local = local_model_path(model_name, models_dir)
    if not local.is_dir():
        print(f"  ❌  {model_name}  →  directory not found: {local}")
        return False

    weight_files = list(local.glob("*.safetensors")) + list(local.glob("*.bin"))
    config_ok = (local / "config.json").exists()
    tokenizer_ok = (local / "tokenizer_config.json").exists() or (local / "tokenizer.json").exists()

    status = "✅" if (weight_files and config_ok) else "⚠️ "
    detail = (
        f"{len(weight_files)} weight file(s)"
        + ("  config.json ✓" if config_ok else "  config.json MISSING ⚠️")
        + ("  tokenizer ✓" if tokenizer_ok else "")
    )
    print(f"  {status}  {model_name}  →  {detail}")
    return bool(weight_files and config_ok)


# ── CLI ────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Pre-download HuggingFace models into the host models directory",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--models", action="append", dest="models", default=None, metavar="ORG/MODEL",
        help="Model repo id to download. May be repeated. Defaults to all benchmark models.",
    )
    parser.add_argument(
        "--models-dir", default=DEFAULT_MODELS_DIR,
        help="Host directory to download models into (mounted as /models in pods)",
    )
    parser.add_argument(
        "--hf-token", default=os.environ.get("HF_TOKEN"),
        help="Hugging Face access token for gated models (or set HF_TOKEN env var)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-download even if the model directory already exists",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be downloaded without actually downloading",
    )
    parser.add_argument(
        "--verify", action="store_true",
        help="After downloading, verify each model directory looks complete",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    models: List[str] = args.models or DEFAULT_MODELS
    models_dir = Path(args.models_dir)

    print(f"Models directory : {models_dir}")
    print(f"Models to process: {len(models)}\n")

    if args.dry_run:
        print("DRY RUN — nothing will be downloaded.\n")
        for m in models:
            present = is_downloaded(m, models_dir)
            tag = "already present" if present else "would download"
            print(f"  {'✅' if present else '⬇️ '}  {m}  ({tag})")
        return

    _require_huggingface_hub()

    failed: List[str] = []
    for model_name in models:
        try:
            download_model(model_name, models_dir, hf_token=args.hf_token, force=args.force)
        except Exception as e:
            print(f"  ❌  {model_name}  →  FAILED: {e}", file=sys.stderr)
            failed.append(model_name)

    if args.verify or not failed:
        print("\nVerification:")
        for model_name in models:
            verify_model(model_name, models_dir)

    if failed:
        print(f"\n❌  {len(failed)} model(s) failed to download: {failed}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"\n✅  All {len(models)} model(s) ready in {models_dir}")


if __name__ == "__main__":
    main()
