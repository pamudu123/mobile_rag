# Corpus inventory

This folder contains the executable notebook and a headless runner for corpus inventory and lightweight Markdown checks.

```powershell
uv run python scripts/execute_notebook.py notebooks/corpus_inventory/01_corpus_inventory.ipynb
uv run python notebooks/corpus_inventory/run_step.py --output-root artifacts/01_corpus_inventory
```

Outputs go to a new directory under `artifacts/01_corpus_inventory/`. This step performs no OCR, indexing, embeddings, or model calls.
