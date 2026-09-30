"""
Pod Specification Generator for Model Serving Benchmarks.

Generates deployable Podman / Kubernetes Pod YAML files for vLLM Spyre,
vLLM CPU, Reranker, and Embedding runtimes across standard and compact profiles.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional
import yaml

# Ensure project root is in sys.path when executed directly
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def resolve_model_target(model_name: str, models_dir: str = "/mnt/models") -> str:
    """
    Resolve model target argument for container launch.
    
    If the model exists locally in models_dir (e.g. /mnt/models/<model_name>),
    use the container-mounted path '/models/<model_name>'.
    Otherwise, fall back to the Hugging Face Hub repo id (e.g. 'ibm-granite/granite-embedding-125m')
    so that vLLM downloads it automatically from Hugging Face.
    """
    local_path = Path(models_dir) / model_name
    if local_path.exists() and local_path.is_dir():
        return f"/models/{model_name}"
    return model_name


def generate_llm_spyre_pod_yaml(
    model_name: str = "ibm-granite/granite-4.1-8b-fp8",
    image: str = "registry.redhat.io/rhaii/vllm-spyre-rhel9:3.5.0",
    profile: str = "standard",
    port: int = 8000,
    models_dir: str = "/mnt/models",
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """Generate Pod YAML for vLLM Spyre accelerator deployment."""
    num_cards = 4 if profile == "standard" else 1
    max_model_len = 32768 if profile == "standard" else 3072
    max_batch_size = 32 if profile == "standard" else 16
    initial_delay = 420 if profile == "standard" else 180

    model_target = resolve_model_target(model_name, models_dir)

    env_vars = [
        {"name": "VLLM_MODEL_PATH", "value": model_target},
        {"name": "AIU_WORLD_SIZE", "value": str(num_cards)},
        {"name": "VLLM_SPYRE_USE_CB", "value": "1"},
        {"name": "MAX_MODEL_LEN", "value": str(max_model_len)},
        {"name": "MAX_BATCH_SIZE", "value": str(max_batch_size)},
        {"name": "MASTER_PORT", "value": "12355"},
    ]
    if api_key:
        env_vars.append({"name": "VLLM_API_KEY", "value": api_key})

    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": f"benchmark-vllm-spyre-{profile}",
            "labels": {
                "ai-services.io/component": "llm",
                "ai-services.io/profile": profile,
                "ai-services.io/runtime": "vllm-spyre"
            },
            "annotations": {
                "io.podman.annotations.ulimit": "nofile=134217728:134217728,memlock=-1:-1",
                "io.podman.annotations.userns": "keep-id",
                "run.oci.keep_original_groups": "1",
                "ai-services.io/llm--spyre-cards": str(num_cards)
            }
        },
        "spec": {
            "restartPolicy": "Never",
            "volumes": [
                {
                    "name": "dshm",
                    "emptyDir": {"medium": "Memory", "sizeLimit": "64Gi"}
                },
                {
                    "name": "models",
                    "hostPath": {"path": models_dir, "type": "Directory"}
                }
            ],
            "containers": [
                {
                    "name": "vllm-spyre",
                    "image": image,
                    "command": ["/bin/bash"],
                    "args": [
                        "-c",
                        "exec /opt/app-root/spyre_entrypoint.sh "
                        f"--model ${{VLLM_MODEL_PATH}} "
                        f"-tp ${{AIU_WORLD_SIZE}} "
                        f"--max-model-len ${{MAX_MODEL_LEN}} "
                        f"--max-num-seqs ${{MAX_BATCH_SIZE}} "
                        f"--served-model-name {model_name} --port {port}"
                    ],
                    "livenessProbe": {
                        "httpGet": {"path": "/health", "port": port},
                        "initialDelaySeconds": initial_delay,
                        "periodSeconds": 30,
                        "timeoutSeconds": 5,
                        "failureThreshold": 3
                    },
                    "env": env_vars,
                    "resources": {
                        "requests": {
                            "podman.io/device=/dev/vfio": num_cards,
                            "memory": "200Gi"
                        },
                        "limits": {
                            "podman.io/device=/dev/vfio": num_cards,
                            "memory": "200Gi"
                        }
                    },
                    "ports": [{"containerPort": port, "hostPort": port}],
                    "volumeMounts": [
                        {"name": "models", "mountPath": "/models:z", "readOnly": True},
                        {"name": "dshm", "mountPath": "/dev/shm"}
                    ]
                }
            ]
        }
    }


def generate_llm_cpu_pod_yaml(
    model_name: str = "ibm-granite/granite-4.1-8b",
    image: str = "icr.io/ppc64le-oss/vllm-ppc64le:0.28.0",
    profile: str = "standard",
    port: int = 8000,
    models_dir: str = "/mnt/models",
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """Generate Pod YAML for vLLM CPU deployment."""
    max_tokens = 8096 if profile == "standard" else 3072
    max_batch = 32 if profile == "standard" else 16
    model_target = resolve_model_target(model_name, models_dir)

    env_vars = [
        {"name": "VLLM_CPU_OMP_THREADS_BIND", "value": "auto"},
        {"name": "VLLM_CPU_KVCACHE_SPACE", "value": "32"}
    ]
    if api_key:
        env_vars.append({"name": "VLLM_API_KEY", "value": api_key})

    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": f"benchmark-vllm-cpu-{profile}",
            "labels": {
                "ai-services.io/component": "llm",
                "ai-services.io/profile": profile,
                "ai-services.io/runtime": "vllm-cpu"
            },
            "annotations": {
                "io.podman.annotations.ulimit": "nofile=134217728:134217728,memlock=-1:-1"
            }
        },
        "spec": {
            "restartPolicy": "Never",
            "volumes": [
                {
                    "name": "dshm",
                    "emptyDir": {"medium": "Memory", "sizeLimit": "512Mi"}
                },
                {
                    "name": "models",
                    "hostPath": {"path": models_dir, "type": "Directory"}
                }
            ],
            "containers": [
                {
                    "name": "vllm-cpu",
                    "image": image,
                    "command": ["/bin/sh"],
                    "args": [
                        "-c",
                        f"exec vllm serve {model_target} "
                        f"--served-model-name {model_name} "
                        f"--max-num-batched-tokens={max_tokens} "
                        f"--max-model-len={max_tokens} "
                        f"--max-num-seqs={max_batch} "
                        f"--port={port}"
                    ],
                    "livenessProbe": {
                        "httpGet": {"path": "/health", "port": port},
                        "initialDelaySeconds": 120,
                        "periodSeconds": 30,
                        "timeoutSeconds": 5,
                        "failureThreshold": 12
                    },
                    "env": env_vars,
                    "resources": {
                        "requests": {"cpu": "10", "memory": "150Gi"},
                        "limits": {"cpu": "10", "memory": "150Gi"}
                    },
                    "ports": [{"containerPort": port, "hostPort": port}],
                    "volumeMounts": [
                        {"name": "models", "mountPath": "/models:z", "readOnly": True},
                        {"name": "dshm", "mountPath": "/dev/shm"}
                    ]
                }
            ]
        }
    }


def generate_reranker_pod_yaml(
    model_name: str = "BAAI/bge-reranker-v2-m3",
    image: Optional[str] = None,
    device: str = "spyre",
    port: int = 8002,
    models_dir: str = "/mnt/models"
) -> Dict[str, Any]:
    """Generate Pod YAML for Reranker runtime (Spyre or CPU)."""
    is_spyre = device.lower() == "spyre"
    if image is None:
        image = "registry.redhat.io/rhaii/vllm-spyre-rhel9:3.5.0" if is_spyre else "icr.io/ppc64le-oss/vllm-ppc64le:0.28.0"
    shm_size = "64Gi" if is_spyre else "512Mi"
    model_target = resolve_model_target(model_name, models_dir)

    pod = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": f"benchmark-reranker-{device}",
            "labels": {
                "ai-services.io/component": "reranker",
                "ai-services.io/runtime": f"reranker-{device}"
            },
            "annotations": {
                "io.podman.annotations.ulimit": "nofile=134217728:134217728,memlock=-1:-1"
            }
        },
        "spec": {
            "restartPolicy": "Never",
            "volumes": [
                {"name": "dshm", "emptyDir": {"medium": "Memory", "sizeLimit": shm_size}},
                {"name": "models", "hostPath": {"path": models_dir, "type": "Directory"}}
            ],
            "containers": [
                {
                    "name": "reranker",
                    "image": image,
                    "livenessProbe": {
                        "httpGet": {"path": "/health", "port": port},
                        "initialDelaySeconds": 120,
                        "periodSeconds": 30,
                        "timeoutSeconds": 5,
                        "failureThreshold": 3
                    },
                    "ports": [{"containerPort": port, "hostPort": port}],
                    "volumeMounts": [
                        {"name": "models", "mountPath": "/models:z", "readOnly": True},
                        {"name": "dshm", "mountPath": "/dev/shm"}
                    ]
                }
            ]
        }
    }

    if is_spyre:
        pod["metadata"]["annotations"]["ai-services.io/reranker--spyre-cards"] = "1"
        pod["spec"]["containers"][0]["command"] = ["/bin/bash"]
        pod["spec"]["containers"][0]["args"] = [
            "-c",
            f"/opt/app-root/spyre_entrypoint.sh --model {model_target} -tp 1 --served-model-name {model_name} --port {port}"
        ]
        pod["spec"]["containers"][0]["env"] = [
            {"name": "VLLM_MODEL_PATH", "value": model_target},
            {"name": "AIU_WORLD_SIZE", "value": "1"},
            {"name": "SENDNN_INFERENCE_WARMUP_BATCH_SIZES", "value": "4"},
            {"name": "SENDNN_INFERENCE_WARMUP_PROMPT_LENS", "value": "1024"},
            {"name": "MASTER_PORT", "value": "12356"}
        ]
        pod["spec"]["containers"][0]["resources"] = {
            "requests": {"podman.io/device=/dev/vfio": 1, "memory": "5Gi"},
            "limits": {"podman.io/device=/dev/vfio": 1, "memory": "5Gi"}
        }
    else:
        pod["spec"]["containers"][0]["args"] = [
            "--model", model_target,
            "--served-model-name", model_name,
            f"--port={port}",
            "--gpu-memory-utilization=0.5",
            "--dtype=bfloat16",
            "--max-model-len=1024"
        ]
        pod["spec"]["containers"][0]["env"] = [
            {"name": "OMP_NUM_THREADS", "value": "8"}
        ]
        pod["spec"]["containers"][0]["resources"] = {
            "requests": {"memory": "5Gi"},
            "limits": {"memory": "5Gi"}
        }

    return pod


def generate_embedding_pod_yaml(
    model_name: str = "ibm-granite/granite-embedding-278m-multilingual",
    image: str = "icr.io/ppc64le-oss/vllm-ppc64le:0.28.0",
    port: int = 8001,
    models_dir: str = "/mnt/models"
) -> Dict[str, Any]:
    """Generate Pod YAML for Embedding runtime (CPU)."""
    model_target = resolve_model_target(model_name, models_dir)
    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": "benchmark-embedding-cpu",
            "labels": {
                "ai-services.io/component": "embedding",
                "ai-services.io/runtime": "embedding-cpu"
            },
            "annotations": {
                "io.podman.annotations.ulimit": "nofile=134217728:134217728,memlock=-1:-1"
            }
        },
        "spec": {
            "restartPolicy": "Never",
            "volumes": [
                {"name": "dshm", "emptyDir": {"medium": "Memory", "sizeLimit": "512Mi"}},
                {"name": "models", "hostPath": {"path": models_dir, "type": "Directory"}}
            ],
            "containers": [
                {
                    "name": "embedding",
                    "image": image,
                    "args": [
                        "--model", model_target,
                        "--served-model-name", model_name,
                        f"--port={port}",
                        "--max-model-len=512",
                        "--gpu-memory-utilization=0.5"
                    ],
                    "livenessProbe": {
                        "httpGet": {"path": "/health", "port": port},
                        "initialDelaySeconds": 120,
                        "periodSeconds": 30,
                        "timeoutSeconds": 5,
                        "failureThreshold": 3
                    },
                    "env": [
                        {"name": "OMP_NUM_THREADS", "value": "16"}
                    ],
                    "resources": {
                        "requests": {"cpu": "2", "memory": "5Gi"},
                        "limits": {"cpu": "2", "memory": "5Gi"}
                    },
                    "ports": [{"containerPort": port, "hostPort": port}],
                    "volumeMounts": [
                        {"name": "models", "mountPath": "/models:z", "readOnly": True},
                        {"name": "dshm", "mountPath": "/dev/shm"}
                    ]
                }
            ]
        }
    }


def generate_all_prep_pod_yamls(output_dir: Path, models_dir: str = "/mnt/models"):
    """Generate all standard and compact pod YAML manifests for prep work."""
    output_dir.mkdir(parents=True, exist_ok=True)

    configs = [
        ("vllm_spyre_standard.yaml", generate_llm_spyre_pod_yaml(profile="standard", models_dir=models_dir)),
        ("vllm_spyre_compact.yaml", generate_llm_spyre_pod_yaml(profile="compact", models_dir=models_dir)),
        ("vllm_cpu_standard.yaml", generate_llm_cpu_pod_yaml(profile="standard", models_dir=models_dir)),
        ("vllm_cpu_compact.yaml", generate_llm_cpu_pod_yaml(profile="compact", models_dir=models_dir)),
        ("reranker_spyre.yaml", generate_reranker_pod_yaml(device="spyre", models_dir=models_dir)),
        ("reranker_cpu.yaml", generate_reranker_pod_yaml(device="cpu", models_dir=models_dir)),
        ("embedding_cpu.yaml", generate_embedding_pod_yaml(models_dir=models_dir)),
    ]

    for filename, pod_dict in configs:
        file_path = output_dir / filename
        with open(file_path, "w") as f:
            yaml.dump(pod_dict, f, default_flow_style=False, sort_keys=False)
        print(f"Generated prep pod YAML: {file_path}")


if __name__ == "__main__":
    out = Path(__file__).parent / "pod_yamls"
    generate_all_prep_pod_yamls(out)
