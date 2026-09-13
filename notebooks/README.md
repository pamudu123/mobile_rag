# Notebooks by purpose

Use these notebooks in order:

| Notebook | Purpose |
| --- | --- |
| [01 Corpus inventory](corpus_inventory/01_corpus_inventory.ipynb) | Inventory documents and check existing Markdown structure. |
| [02 Markdown chunking](markdown_chunking/02_markdown_chunking.ipynb) | Create traceable passages, chunks and citation metadata. |
| [03 Retrieval](retrieval/03_retrieval.ipynb) | Build BM25 and enhanced search, compare results, and inspect source evidence. |
| [04 Context preparation](context_preparation/04_context_preparation.ipynb) | Validate, deduplicate and package source evidence within a character budget. |
| [05 Answer generation](answer_generation/05_answer_generation.ipynb) | Prepare grounded OpenRouter requests and validate answer/citation structure. Live use requires credentials and a tokenizer. |

Each folder includes a README and a headless runner. Notebook prefixes show execution order; historical stage numbers remain in planning documents and artifact directories for traceability. Saved outputs are retained.
