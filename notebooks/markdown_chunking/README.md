# Markdown chunking

This folder contains the executable notebook and a headless runner for passage parsing, structure-aware chunking, and citation metadata.

```powershell
uv run python scripts/execute_notebook.py notebooks/markdown_chunking/02_markdown_chunking.ipynb
uv run python notebooks/markdown_chunking/run_step.py --output-root artifacts/02_markdown_chunking
```

Outputs go to a new directory under `artifacts/02_markdown_chunking/`. This step performs no retrieval indexing, embeddings, or model calls.
