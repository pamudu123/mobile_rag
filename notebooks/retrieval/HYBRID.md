# Hybrid retrieval and sanity notebook

Open [03_2_hybrid_sanity.ipynb](03_2_hybrid_sanity.ipynb) after `uv sync` and restart any already-running kernel so it loads the new modules.

The two switches are independent:

| ENABLE_BM25 | ENABLE_EMBEDDINGS | Mode |
| --- | --- | --- |
| True | True | Hybrid (default) |
| True | False | Lexical only; no embedding model required |
| False | True | BGE only; no lexical search executed |
| False | False | Rejected before execution |

The same switches are exposed in the retrieval, context-preparation, single-answer, and bulk-answer notebooks. Bulk run manifests include the configuration and dense manifest hash; resume rejects changed settings. The existing `EnhancedRetriever` remains a lexical comparison implementation. The current workflow uses `HybridRetriever` by default.

## First build

The implementation pins `BAAI/bge-small-en-v1.5` revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` and uses its official full-precision ONNX model on CPU. The first build downloads the model and tokenizer to the Hugging Face cache. Query-time loading uses cached files only. Keep that cache available for offline desktop use.

```powershell
uv sync
uv run python -m mobile_rag.retrieval_hybrid --index artifacts/03_retrieval_enhanced/20260913T120112863801Z --output-root artifacts/03_retrieval_enhanced
```

Alternatively set `BUILD_INDEX=True` in the sanity notebook. Building creates a new bundle and can take several minutes on CPU. Completed bundles contain `dense_manifest.json`, `vectors.npy`, and `embedding_units.json` alongside the copied lexical artifacts. Original bundles are preserved. Set `INDEX_DIR` explicitly when choosing a historical bundle; automatic discovery requires a dense manifest when embeddings are enabled.

## How results are combined

Both paths independently search their full indexes. BM25 candidates are not a filter for dense retrieval. The lexical result list and the dense parent list contribute one RRF vote each, with constant 60. Default candidate count is 20 per path, returning five parent chunks. Dense child windows use the maximum similarity per parent before ranking. Source text and citation resolution use the original parent chunks.

BGE receives the natural-language question with its query prefix, CLS pooling, and L2 normalization. BM25 retains its own generic token cleanup. Stored vectors are normalized FP32 and searched exactly. Enabled paths fail visibly if assets are missing or incompatible; the system does not silently fall back to another mode.

## Sanity checks and limitations

The notebook checks the switches, inspects source text/citations, demonstrates dense candidates with zero lexical matches, validates context construction, and performs a generation dry run. Its optional Q_S1 comparison performs 300 retrieval searches across the three modes and saves artifacts under `artifacts/03_2_hybrid_sanity`. It does not call OpenRouter.

Dense search returns nearest neighbors even for nonsense queries. These are not guaranteed supporting evidence. No calibrated relevance rejection threshold or neural reranker is implemented. Table text can span embedding windows; original full parents are preserved for context, but structural row-level table retrieval remains future work. Mobile packaging, quantization, latency, and memory have not been validated by the desktop implementation.

## Script switches

The existing retrieval, context, and single-answer scripts accept `--bm25` / `--no-bm25` and `--embeddings` / `--no-embeddings`. Both are enabled by default. The bulk notebook exposes the booleans directly. Leave the generation notebook's `LIVE` setting under your control; changing retrieval switches does not disable hosted generation.

In Python, use `HybridRetriever(index, RetrievalConfig(enable_bm25=True, enable_embeddings=True))`. Pass the same `RetrievalConfig` to `process_question(..., retrieval_config=config)` for bulk runs.

## Verified desktop run — 2026-09-13

- Saved index: [20260913_135906](../../artifacts/03_retrieval_enhanced/20260913_135906/dense_manifest.json), containing 5,494 embedding windows from 4,355 source chunks. `vectors.npy` is 8,438,912 bytes including its header.
- Fresh-kernel notebook evidence: [sanity summary](../../artifacts/03_2_hybrid_sanity/20260913_141554/summary.json), with 300 Q_S1 retrieval searches across the three modes and no answer-generation API calls.
- Context integration passed all five constructed cases; single-answer integration returned `dry_run` with `live_request_sent=false`.
- Test suite: 44 passed. These checks do not establish clinical accuracy or mobile performance.
