# Step 5 build review

Status: ready for user review. Executed: 2026-09-13.

## Built

- [Step 5 notebook](../../notebooks/markdown_chunking/02_markdown_chunking.ipynb) with saved outputs.
- [Step 5 folder guide](../../notebooks/markdown_chunking/README.md) and headless runner.
- Deterministic Markdown parsing, structure-aware chunking, provenance, citation targets, exports, and validation in `src/mobile_rag/corpus.py`.
- Machine-readable evidence in [`artifacts/step-05/2026-09-13T08-01-20+00-00_9f352c688e/`](../../artifacts/step-05/2026-09-13T08-01-20+00-00_9f352c688e/).

## Results

| Measure | Result |
| --- | ---: |
| Documents | 14 |
| Passages | 22,586 |
| Chunks | 4,355 |
| Minimum chunk characters | 44 |
| Median chunk characters | 929 |
| p95 chunk characters | 2,913 |
| Maximum chunk characters | 8,311 |
| Oversized chunks retained and flagged | 980 |
| Opaque-content flags | 55 |
| Chunks missing a PDF content mapping | 0 |

The large p95 and 980 oversized chunks are expected under the approved first-pass policy: large atomic paragraphs, lists, and especially tables are retained rather than split blindly. These are explicit Step 6 inputs for retrieval and prompt-budget analysis, not hidden failures.

## Verification

All preservation checks passed:

- Passage text exactly matches its recorded Markdown source slice.
- All non-whitespace source content is accounted for.
- Retrieval segments exactly match source passages or are marked synthetic separators.
- Passage, chunk, citation, and neighbor references resolve.
- No chunk crosses documents.
- Source hashes are unchanged.
- All selected documents have chunks.
- A repeated build produced the same bundle fingerprint and chunk IDs.

Three focused tests passed, including Unicode/CRLF offset fidelity and retention of an oversized table as one flagged chunk. Ruff passed on the active source, tests, notebook runners, and notebook executor. The notebook executed in a fresh kernel and saved its outputs.

This step establishes traceable chunks against the existing Markdown. It does not establish OCR accuracy, clinical correctness, retrieval accuracy, or model performance. No BM25 index, embeddings, OpenRouter request, or skipped Step 3/4 implementation was created.
