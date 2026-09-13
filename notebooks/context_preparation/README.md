# Context preparation

Execute `04_context_preparation.ipynb`, or run from the repository root:

```powershell
uv run python notebooks/context_preparation/run_context_preparation.py
```

Use `--index <directory>` to select an existing enhanced retrieval package. The default is the most recent package in `artifacts/step-07/`. Run the retrieval notebook first if none exists.

Outputs under `artifacts/context-preparation/<run>/` include normal, overlapping, budget-blocked, empty and invalid-evidence cases. Context is JSON Lines: each line is one complete evidence group. Shared source passages reference the label where their text first appears. Citation maps also list heading/context passage IDs separately from body citation IDs.

The budget counts rendered Unicode characters, including JSON formatting, labels and headings. It is not a verified model token allowance. The model adapter must implement token accounting before making requests. No model requests, embeddings, or source modifications occur here.

See [architecture](../../docs/architecture/05-context-preparation.md). Ready context is structurally valid evidence, not a guarantee of answerability or clinical completeness.
