# Context preparation

Execute `04_context_preparation.ipynb`, or run from the repository root:

```powershell
uv run python notebooks/context_preparation/run_context_preparation.py --output-root artifacts/04_context_preparation
```

Use `--index <directory>` to select an existing retrieval package. Hybrid BM25 + BGE is the default and requires a completed dense bundle. Use `--no-embeddings` for lexical-only or `--no-bm25` for embeddings-only. The notebook exposes `ENABLE_BM25` and `ENABLE_EMBEDDINGS`. See the [hybrid guide](../retrieval/HYBRID.md). The empty-context test is constructed explicitly because dense search can return nearest neighbors for meaningless queries.

Outputs under `artifacts/04_context_preparation/<run>/` include normal, overlapping, budget-blocked, empty and invalid-evidence cases. Context is JSON Lines: each line is one complete evidence group. Shared source passages reference the label where their text first appears. Citation maps also list heading/context passage IDs separately from body citation IDs.

The budget counts rendered Unicode characters, including JSON formatting, labels and headings. It is not a verified model token allowance. The model adapter must implement token accounting before making requests. No model requests, embeddings, or source modifications occur here.

See [architecture](../../docs/architecture/05-context-preparation.md). Ready context is structurally valid evidence, not a guarantee of answerability or clinical completeness.
