# Modeling implementation plan

Follow the [architecture master plan](../architecture/12-delivery-roadmap.md), with implementation evidence saved in notebooks and reviewed step by step.

Latest purpose-based function: [Answer generation](../architecture/06-answer-generation.md), implemented in [its notebook](../../notebooks/answer_generation/05_answer_generation.ipynb). Local checks are available; hosted verification requires an OpenRouter API key.

| Step | Specification | Planned notebook | Status |
| --- | --- | --- | --- |
| 1: Scope and acceptance | [Scope note](01-scope-and-acceptance-plan.md) | None; documentation only | Documented |
| 2: Corpus inventory and lightweight Markdown checks | [Combined build plan](02-corpus-inventory-plan.md) | `notebooks/corpus_inventory/01_corpus_inventory.ipynb` | Implemented |
| 3: Merged into Step 2 | [Scope decision](03-markdown-validation-plan.md) | None | Skipped as a separate phase |
| 4: Use existing Q&A without a preparation stage | [Scope decision](04-benchmark-preparation-plan.md) | None | Skipped for now |
| 5: Markdown passages, chunks, and citation metadata | [Build plan](05-markdown-chunking-plan.md) | `notebooks/markdown_chunking/02_markdown_chunking.ipynb` | Implemented |
| 6: Local BM25 indexing and search | [Build review](06-build-review.md) | `notebooks/retrieval/03_retrieval.ipynb` | Implemented; ready for review |
| 7: Lexical retrieval refinements | [Build note](07-enhanced-retrieval.md) | `notebooks/retrieval/03_retrieval.ipynb` | Implemented experiment; accuracy comparison pending |

Steps 6 and 7 share one retrieval notebook, README and runner under `notebooks/retrieval/`. That workflow builds the baseline and enhanced indexes directly from Step 5 and compares their results. Steps 2/5 retain their own folders. Steps 3 and 4 remain skipped. No embeddings, OCR repair, or model calls are included in these phases.

The Markdown versions already exist. Step 2 includes lightweight structure checks; detailed OCR/content auditing is deferred. Step 3 has no separate notebook. Step 4 is also skipped: use the existing Q&A as the working benchmark, assuming its correctness without additional review now. Existing numbering is retained, and Step 5 defines passage/chunk contracts after Step 2.
