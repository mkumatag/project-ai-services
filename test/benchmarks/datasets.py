"""
Benchmark evaluation datasets and deterministic payload generators.

Provides token-controlled prompt matrices, multi-document reranker candidate pools,
and batched text sequences aligned with vLLM deployment profiles (standard vs compact,
Spyre AIU vs CPU).
"""

import json
from pathlib import Path
from typing import Dict, List, Any

# Standard reference vocabulary and text segments to construct deterministic token sequences
BASE_PASSAGES = [
    "Machine learning models deployed at the edge require optimized inference pipelines with low latency and bounded memory consumption.",
    "OpenSearch provides vector indexing with k-NN algorithms supporting both dense cosine similarity and sparse BM25 keyword matching.",
    "Hardware accelerators such as Spyre AIU leverage dedicated neural processing units with tensor parallelism across multiple accelerator cards.",
    "vLLM employs PagedAttention algorithms to manage key-value cache memory without internal fragmentation during autoregressive decoding.",
    "Cross-encoder rerankers compute all-to-all attention between query and candidate passage pairs for high-precision relevance scoring.",
    "Document ingestion pipelines parse PDF, DOCX, and tabular structures into semantically coherent chunk representations.",
    "Container liveness and readiness probes verify model weight initialization before traffic routes to serving runtimes.",
    "Data deduplication using SHA-256 and MD5 cryptographic hashes prevents duplicate embedding generation in knowledge bases.",
]

def generate_text_of_approx_tokens(target_tokens: int) -> str:
    """Generate deterministic synthetic text approximating the target token length (assuming ~1.3 words per token)."""
    words_per_token = 0.75
    target_words = max(1, int(target_tokens * words_per_token))
    
    words = []
    passage_idx = 0
    while len(words) < target_words:
        passage = BASE_PASSAGES[passage_idx % len(BASE_PASSAGES)]
        words.extend(passage.split())
        passage_idx += 1
    
    return " ".join(words[:target_words])


def get_llm_benchmark_payloads(profile: str = "standard", max_tokens_limit: int = 32768) -> List[Dict[str, Any]]:
    """
    Generate prompt payloads for LLM inference benchmarks.
    Profiles:
      - standard: prompts from 128 tokens up to 32K (Spyre) or 26.2K (CPU)
      - compact: prompts from 128 tokens up to 3K tokens
    """
    if profile == "compact":
        token_lengths = [128, 512, 1024, 2048, min(3000, max_tokens_limit)]
    else:
        # Standard profile
        token_lengths = [128, 512, 2048, 8192]
        if max_tokens_limit >= 26208:
            token_lengths.append(min(26000, max_tokens_limit))
        if max_tokens_limit >= 32768:
            token_lengths.append(32000)

    payloads = []
    for length in token_lengths:
        prompt_text = generate_text_of_approx_tokens(length)
        payloads.append({
            "name": f"prompt_{length}_tokens",
            "approx_tokens": length,
            "messages": [
                {"role": "system", "content": "You are a helpful and concise assistant."},
                {"role": "user", "content": f"Summarize the following document in 50 words:\n\n{prompt_text}"}
            ],
            "max_tokens": 128,
            "temperature": 0.0,
        })
    return payloads


def get_reranker_benchmark_payloads() -> List[Dict[str, Any]]:
    """
    Generate query + candidate document collections for reranker benchmarks.
    Doc set sizes: 1, 5, 10, 25, 50 documents.
    """
    query = "What are the advantages of tensor parallelism on hardware accelerators?"
    doc_counts = [1, 5, 10, 25, 50]
    
    payloads = []
    for count in doc_counts:
        docs = []
        for i in range(count):
            base_p = BASE_PASSAGES[i % len(BASE_PASSAGES)]
            docs.append({
                "chunk_id": f"doc_{i+1:03d}",
                "page_content": f"Document {i+1}: {base_p} " + generate_text_of_approx_tokens(100),
                "filename": f"source_{i+1}.pdf"
            })
        
        payloads.append({
            "name": f"rerank_{count}_docs",
            "doc_count": count,
            "query": query,
            "documents": docs
        })
    return payloads


def get_embedding_benchmark_payloads() -> List[Dict[str, Any]]:
    """
    Generate batch text lists for embedding benchmarks.
    Batch sizes: 1, 4, 8, 16, 32, 64 texts.
    """
    batch_sizes = [1, 4, 8, 16, 32, 64]
    payloads = []
    
    for batch_size in batch_sizes:
        texts = []
        for i in range(batch_size):
            texts.append(f"Sentence {i+1}: " + BASE_PASSAGES[i % len(BASE_PASSAGES)] + " " + generate_text_of_approx_tokens(64))
        
        payloads.append({
            "name": f"embedding_batch_{batch_size}",
            "batch_size": batch_size,
            "texts": texts
        })
    return payloads


def dump_all_datasets(output_dir: Path):
    """Save all benchmark datasets to JSON files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / "llm_standard.json", "w") as f:
        json.dump(get_llm_benchmark_payloads("standard", 32768), f, indent=2)
        
    with open(output_dir / "llm_compact.json", "w") as f:
        json.dump(get_llm_benchmark_payloads("compact", 3072), f, indent=2)

    with open(output_dir / "reranker.json", "w") as f:
        json.dump(get_reranker_benchmark_payloads(), f, indent=2)

    with open(output_dir / "embedding.json", "w") as f:
        json.dump(get_embedding_benchmark_payloads(), f, indent=2)


if __name__ == "__main__":
    out = Path(__file__).parent / "data"
    dump_all_datasets(out)
    print(f"Benchmark datasets generated in {out}")
