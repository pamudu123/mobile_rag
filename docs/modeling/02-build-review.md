# Step 2 build review

Status: ready for user review. Executed: 2026-09-13.

## Built

- [Step 2 notebook](../../notebooks/corpus_inventory/01_corpus_inventory.ipynb) with saved outputs.
- [Step 2 folder guide](../../notebooks/corpus_inventory/README.md) and headless runner.
- Reusable inventory implementation in `src/mobile_rag/corpus.py`.
- Machine-readable evidence in [`artifacts/step-02/2026-09-13T07-57-37+00-00_d6d0852754/`](../../artifacts/step-02/2026-09-13T07-57-37+00-00_d6d0852754/).

## Results

| Measure | Result |
| --- | ---: |
| Tracked data files | 31 |
| PDF paths in `data/pdf_docs` | 14 |
| Unique PDF contents | 14 |
| Markdown files in `data/md_docs` | 14 |
| Markdown-to-PDF matches | 14 |
| Inventory issues | 3 |
| Structural checks | Passed |

The earlier 15-versus-14 discrepancy is explained by `data/questions/FrontlineAI_100_Clinically_Grounded_QA_Benchmark.pdf`, which is outside `data/pdf_docs` and is not included in the clinical corpus. All 14 intended Markdown files matched 14 unique PDFs.

Two structural warnings apply to `WHO-Oxygen-therapy-for-children-2016.md`: duplicate page markers and out-of-order page markers. They remain visible in `issues.csv`; no OCR or source edit was performed.

## Verification

The inventory checks passed for unique file IDs, valid hashes, nonnegative sizes, and valid file references. The notebook was executed from a fresh kernel and saved with outputs. Focused automated tests also cover a valid PDF/Markdown match and an orphan Markdown case.

This establishes file inventory and lightweight Markdown readiness only. Clinical authority, transcription/OCR accuracy, and source-coordinate accuracy were not assessed. Steps 3 and 4 remain skipped as directed.
