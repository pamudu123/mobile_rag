# Modeling implementation plan

Follow the [architecture master plan](../architecture/06-step-by-step-plan.md), with implementation evidence saved in notebooks and reviewed step by step.

| Step | Specification | Planned notebook | Status |
| --- | --- | --- | --- |
| 1: Scope and acceptance | [Scope note](01-scope-and-acceptance-plan.md) | None; documentation only | Documented |
| 2: Corpus inventory and lightweight Markdown checks | [Combined build plan](02-corpus-inventory-plan.md) | `notebooks/02_corpus_inventory.ipynb` | Documented; awaiting user pass to build |
| 3: Merged into Step 2 | [Scope decision](03-markdown-validation-plan.md) | None | Skipped as a separate phase |
| 4: Use existing Q&A without a preparation stage | [Scope decision](04-benchmark-preparation-plan.md) | None | Skipped for now |
| 5: Markdown passages, chunks, and citation metadata | [Build plan](05-markdown-chunking-plan.md) | `notebooks/05_markdown_chunking.ipynb` | Documented; not implemented |

Step 2 is the first executable building phase. After authorization, build and run only its notebook and related outputs, then present the results for review. No indexing, embeddings, OCR repair, or model calls are included in this phase.

The Markdown versions already exist. Step 2 includes lightweight structure checks; detailed OCR/content auditing is deferred. Step 3 has no separate notebook. Step 4 is also skipped: use the existing Q&A as the working benchmark, assuming its correctness without additional review now. Existing numbering is retained, and Step 5 defines passage/chunk contracts after Step 2.
