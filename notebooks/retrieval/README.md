# Retrieval: BM25 and lexical refinements

Run `uv run python notebooks/retrieval/run_step.py --output-root artifacts/03_retrieval_enhanced --baseline-output-root artifacts/03_retrieval_baseline` from the repository root, or execute `03_retrieval.ipynb`.

Requires a validated chunking bundle. This single entry point builds the baseline index, adds lexical refinements, compares retrieval, and displays source evidence. No separate baseline notebook or prebuilt index is needed. Outputs are stored in `artifacts/03_retrieval_baseline/` and `artifacts/03_retrieval_enhanced/`. See [scope and limitations](../../docs/modeling/07-enhanced-retrieval.md). Clinical accuracy and mobile performance are not yet established.
