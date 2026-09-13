# Retrieval: BM25 + BGE hybrid

Hybrid is now the default. Set `ENABLE_BM25` and `ENABLE_EMBEDDINGS` independently in the notebooks. See [switches, build instructions, and limitations](HYBRID.md).

Start with [03_2_hybrid_sanity.ipynb](03_2_hybrid_sanity.ipynb) to inspect an existing hybrid bundle and compare all three modes without answer-generation API calls.

Run `uv run python notebooks/retrieval/run_step.py --output-root artifacts/03_retrieval_enhanced --baseline-output-root artifacts/03_retrieval_baseline` from the repository root, or execute `03_retrieval.ipynb`.

Requires a validated chunking bundle. This entry point builds lexical indexes and, by default, the BGE index, then compares retrieval and displays source evidence. The initial BGE build downloads a pinned local encoder; use `--no-embeddings` for lexical-only operation. Outputs are stored in `artifacts/03_retrieval_baseline/` and `artifacts/03_retrieval_enhanced/`. Clinical accuracy and mobile performance are not yet established.
