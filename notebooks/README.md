# Notebooks by purpose

Use these notebooks in order:

| Notebook | Purpose |
| --- | --- |
| [01 Corpus inventory](corpus_inventory/01_corpus_inventory.ipynb) | Inventory documents and check existing Markdown structure. |
| [02 Markdown chunking](markdown_chunking/02_markdown_chunking.ipynb) | Create traceable passages, chunks and citation metadata. |
| [03 Retrieval](retrieval/03_retrieval.ipynb) | Build BM25 and enhanced search, compare results, and inspect source evidence. |
| [04 Context preparation](context_preparation/04_context_preparation.ipynb) | Validate, deduplicate and package source evidence within a character budget. |
| [05 Answer generation](answer_generation/05_answer_generation.ipynb) | Prepare grounded OpenRouter requests and validate answer/citation structure. Live use requires an OpenRouter API key. |

Each folder includes a README and a headless runner. Notebook and artifact prefixes show execution order. Saved outputs are retained.

## Explicit save directories

Every notebook begins with a **Save configuration** section listing its files and defining `OUTPUT_ROOT`. Retrieval also defines `BASELINE_OUTPUT_ROOT`. Export/run calls pass these paths explicitly; runners do not choose output roots internally.

- `output_root` is a parent directory; each invocation creates a run subdirectory and returns the actual path.
- Headless runners require `--output-root`; retrieval also requires `--baseline-output-root`.
- Output roots may be outside the project. The corpus project root still identifies input files and validates source offsets.
- Custom output directories do not redirect input discovery. Use explicit bundle/index arguments for subsequent stages when needed.
- Save configuration controls artifact writes, not saving the `.ipynb` itself. `scripts/execute_notebook.py` still saves executed notebook outputs in place.
