# Step 6 build review

Status: implemented, executed, ready for review. Date: 2026-09-13.

## Delivered

- [Executed notebook](../../notebooks/retrieval/03_retrieval.ipynb), [runner](../../notebooks/retrieval/run_step.py), and [folder guide](../../notebooks/retrieval/README.md).
- [Shared retrieval module](../../src/mobile_rag/retrieval.py) and [focused tests](../../tests/test_retrieval.py).
- [Validated run](../../artifacts/03_retrieval_baseline/20260913T082112738141Z_1e502c96a8/) containing the SQLite database, input/output provenance, checks, complete example results, timing samples, and search summary.

The selected input is Step 5 bundle `9f352c688e71637f0478088b17cea2ac52cbf46f90abde4120f63a6198cfcf68`. Its artifact hashes and source relationships were checked before indexing. SQLite version: 3.53.1. No new dependencies were needed.

## Measured results

| Item | Result |
| --- | ---: |
| Documents | 14 |
| Source passages | 22,586 |
| Searchable chunks | 4,355 |
| Citation targets | 4,355 |
| Database size | 56,922,112 bytes (54.29 MiB) |
| Build plus input/integrity checks | 4.02 seconds |
| Demonstration queries | 8 |
| Warmed query samples | 40 |
| Warm median latency | 18.41 ms |
| Warm p95 latency | 47.66 ms |

Timing includes result/source resolution. Samples are from this desktop environment, including a deliberately unmatched query; they are not mobile measurements. The database repeats some source text to keep the initial representation simple and independently readable; mobile storage optimization remains future work.

## Behavior

Plain-text OR search is the default; explicit AND mode and document filters are supported. Terms are generated with the same Unicode61 tokenizer as the index, individually quoted, and passed through parameterized SQL. Raw BM25 scores sort ascending with chunk IDs breaking ties. Scores are ranking values, not probabilities.

Results contain complete chunk text, exact source passages, document metadata, declared page references, and citation targets. Oversized tables remain intact. Optional expansion adds only whole same-section neighbors, with deduplication, a character budget, and explicit skip reasons. It does not alter direct-hit ranking.

The index opens read-only and contains the text required to resolve evidence. The database hash remained unchanged after the demonstration searches. Original Markdown/PDF paths are metadata, not dependencies for returning stored passages.

## Verification

Seven tests passed across the project (four Step 6 tests and three existing corpus tests). Step 6 tests cover query syntax safety, invalid/empty inputs, no matches, filters, exact source references, intact oversized tables, context budgets, Unicode separators in JSONL, deterministic rebuilds/ties, and rejection of changed hashes or invalid citations. Ruff passed for all newly added Python files. The notebook executed from a fresh kernel and saved outputs without cell errors.

Database checks cover artifact hashes, source-segment/citation relationships, ordinary/foreign-key/FTS integrity, imported row counts, and FTS-to-chunk text mappings. A failed or unsupported input bundle cannot be published as a passing index.

During full-corpus execution, the new loader initially misread Unicode line separators inside JSON strings as record boundaries. It now splits records only on newline delimiters, with a regression test. No source corpus correction was performed.

## Interpretation and next step

Seven example queries returned hits and the deliberately absent term returned `no_matches`. Hit presence is not a relevance or clinical-accuracy score. Common query words can produce weak OR matches; the saved examples expose this baseline for Step 7 refinement. Source pages remain declared/unverified, including the previously recorded oxygen-document marker issue.

Steps 3 and 4 remain skipped. Existing Q&A question text was used only for demonstrations; reference answers were not indexed or supplied as search hints. No gold-passage recall or held-out accuracy is claimed. No embeddings, OCR, inference, or model requests were added. Step 7 evaluation/refinement awaits its own scope instruction.
