# Step 6: Local BM25 indexing and search

Status: implemented and executed. See [the build review](06-build-review.md) for actual outputs and checks. The specification below records the agreed design; future-tense descriptions are retained as the original implementation contract.

## What we will build

Create `notebooks/retrieval/` containing `03_retrieval.ipynb`, `run_step.py`, and a README. The notebook will build a local SQLite search database from a selected Step 5 bundle and demonstrate ranked passage retrieval with source references.

This is the first searchable RAG component: question → matching chunks → original source passages. It produces retrieved evidence, not a generated clinical answer. No embedding model, OCR work, benchmark revalidation, or OpenRouter call is included. Steps 3 and 4 remain skipped.

Use Python's standard-library `sqlite3` and SQLite FTS5/BM25. At execution time, probe FTS5 support with a temporary test table; report a missing capability rather than silently using a different search method. FTS5 provides full-text indexing, BM25 ranking, Unicode tokenization, and integrity checks. [SQLite FTS5 documentation](https://www.sqlite.org/fts5.html)

## Input bundle and readiness

Select an explicit Step 5 run directory and display its identity in the notebook. A convenience default may select the latest complete passing run, but the resolved path and file hashes must be recorded. Do not combine files from different runs.

Required inputs are `run_manifest.json`, `check_results.json`, `documents.jsonl`, `passages.jsonl`, `chunks.jsonl`, `citation_targets.jsonl`, and `chunking_config.json`. Validate schema, artifact hashes, unique IDs, segment mappings, and document/passage/chunk/citation references before importing. A historical `passed` flag is not a substitute for validating files actually loaded.

The current Step 5 report describes 14 documents, 22,586 passages, and 4,355 chunks, including 980 oversized chunks. These are a recorded baseline, not hard-coded expected counts. Import the selected run's actual counts and carry its flags forward.

Declared pages are not verified PDF coordinates. Preserve the existing oxygen-document page-marker warnings. The index must support source quotes from the stored passages even when a PDF page is ambiguous. No source repair or new clinical approval is required by this build.

## Notebook sequence

| Section | Implementation | Visible result |
| --- | --- | --- |
| 1. Setup | Resolve root, select bundle, check SQLite/FTS5 and artifact hashes | Input and runtime summary |
| 2. Import preparation | Validate references and derive searchable heading/body fields | Counts, fields, exclusions, and flags |
| 3. Database build | Create local tables and FTS index in a new run directory | Database path, build time, and size |
| 4. Search | Compile a plain-text question into a safe lexical query | Original query, terms, compiled expression, and top results |
| 5. Source resolution | Fetch complete chunks and exact source passages | Ranked source cards and provenance |
| 6. Neighbor context | Demonstrate bounded optional expansion | Direct hits versus linked context |
| 7. Checks | Validate integrity, deterministic results, and failure behavior | Named checks and timing summary |
| 8. Export/review | Save examples, measurements, and build report | Artifact links and Step 6 checkpoint |

Reusable database/search logic should live in `src/mobile_rag/retrieval.py`; the phase runner and notebook call the same functions. Keep `corpus.py` focused on Steps 2/5. No dependency is expected beyond the current environment unless the FTS5 probe identifies a concrete platform limitation.

## Database design

| Table | Purpose |
| --- | --- |
| `bundle_metadata` | Schema/config versions, selected input hashes, bundle identity, SQLite version |
| `documents` | Document IDs, source paths, Markdown hash, PDF association, mapping/review status |
| `passages` | Exact source text, offsets, heading/page metadata keyed by passage ID |
| `chunks` | Integer row ID, unique chunk ID, document ID, original retrieval text, flags and neighbor IDs |
| `chunk_passages` | Ordered body/context associations and segment mappings |
| `citation_targets` | Original target IDs and ordered source associations |
| `chunk_fts` | FTS5 index with `heading_text` and `body_text` columns |

Build ordinary content tables plus a regular content-storing FTS table initially. Accept measured text duplication for simpler integrity and debugging; external-content optimization can be considered later. Enable foreign keys and validate all relationships. Assign integer row IDs by sorted chunk ID and map them one-to-one to FTS rows.

Derive heading text from context passage IDs, deduplicating those IDs within each chunk. Derive body text from body passage IDs. Do not index the combined `retrieval_text` in addition to these fields, because that would count attached headings twice. Preserve the original assembled text and exact passage text separately for display/citations.

Apply no clinical rewriting, stemming, aliases, or aggressive stopword removal initially. Record `unicode61` tokenizer configuration explicitly. Tokenization affects matching only; source text remains exact. Searchable punctuation handling does not validate numerical comparisons, units, or negation.

Import all valid selected chunks, including oversized/opaque flags, without silently truncating them. Any structurally invalid record fails preflight rather than disappearing from the denominator. Metadata-like chunks already emitted by Step 5 remain identifiable in results; changing the chunk selection policy requires an explicit recorded refinement.

## Query and ranking policy

| Setting | Initial choice |
| --- | --- |
| Query input | Plain text; user-supplied FTS operators are not executed |
| Default matching | OR across distinct query tokens for a transparent broad baseline |
| Additional diagnostic mode | Explicit AND mode; no hidden fallback between modes |
| Ranking | BM25 with equal heading/body weights initially |
| Ordering | Raw BM25 ascending, then chunk ID ascending for ties |
| Default result count | Top 5; caller may request 1–20 |
| Limits | At most 2,000 Unicode characters and 64 distinct indexed query tokens; reject excess explicitly |
| Expansion | Off by default; separate context operation |

Use a scratch tokenizer table with the same FTS5 tokenizer and its vocabulary to derive consistent query terms, or another verified equivalent method. Quote every term safely and bind the complete MATCH expression as a SQL parameter. SQL parameter binding alone does not neutralize FTS syntax. Preserve the original question for display and later generation; do not pass a keyword reconstruction as the original clinical question.

Terms such as `AND`, quotes, colons, and parentheses supplied in a question must be treated as text/tokens, not an advanced search program. No-token questions receive `invalid_query`; valid queries with zero matches receive `no_matches`; I/O/schema errors receive `error`. Unknown document filters or invalid result counts are explicit input errors.

SQLite BM25 assigns smaller values to better matches. Return the raw score with that direction documented, not a probability or clinical confidence. [SQLite BM25 reference](https://www.sqlite.org/fts5.html#the_bm25_function)

OR retrieval may return chunks matching common words but missing the actual clinical condition. That is an observable baseline limitation to inspect in Step 7, not evidence that the question is answerable. Do not select an answer or impose an uncalibrated answerability threshold in Step 6.

## Search-result contract

Return query ID, original text, indexed terms, matching mode, compiled-query/config version, bundle/index identity, elapsed search time, status, and ordered hits. Each hit includes rank, chunk/document IDs, raw score, source title/path, complete chunk text, exact passage references, available page metadata, flags, and citation target ID.

Validate citation associations against the selected bundle; do not assume targets contain verified coordinates or missing version fields. Expose the selected bundle identity alongside each response even if the older target record lacks it. Show page numbers as declared/unverified where appropriate.

Notebook previews may shorten text for display, but the returned evidence and stored example JSON must retain complete text. Term highlighting is only a search-match preview, not a supporting-claim highlight. Precise answer-to-source highlighting remains later viewer work.

## Optional neighbor context

Provide a separate expansion function for up to the top three direct hits. Follow at most one previous and one next chunk per seed, staying within the same document and matching structural heading context. Deduplicate repeated chunk/passage IDs while preserving source order. A cross-section neighbor is omitted with a reason, not appended silently.

Label added records `neighbor_context` and retain the originating seed ID; they receive no fabricated BM25 rank. Keep direct rankings unchanged. Apply a proposed 12,000-character added-context budget, accepting only whole neighbors and reporting skipped IDs/reasons. Direct oversized hits are not dropped or truncated by that expansion budget.

This character budget bounds a demonstration, not a future model-token budget. Token-aware prompt packing and complete clinical-context selection remain later work. Same-section links help with navigation but do not guarantee clinical applicability.

## Build and read lifecycle

Create a new run directory and build a temporary database there in a transaction. Verify row counts, relational checks, ordinary SQLite integrity, FTS integrity, and content-to-index mappings before publishing the final database name and passing manifest. A failed build must not appear as the latest passing run.

Close/checkpoint the builder connection and reopen the final database read-only for search. Keep query tokenization scratch state in memory rather than mutating the index. Persist all text needed to return passages in the database so read-only search does not depend on the original absolute desktop paths; opening the original PDFs remains optional viewer behavior.

Rebuilds should preserve substantive imported records and search ordering for the same bundle/config/runtime. Record database hashes per run for integrity, but do not require byte-identical SQLite files across versions. If a source bundle changes, create a new index identity rather than replacing an unrelated validated artifact.

## Examples and measurements

Use a small fixed set of direct keyword questions plus a handful of Q_S1/Q_S2 question texts to inspect actual behavior. Existing Q&A correctness remains assumed. Do not import reference answers, `source_of_truth`, or question files into the database; no answer matching is required to build or demonstrate search.

Measure build time, database size, import counts, initial-open query timing, and repeated warmed search/expansion timing. Report sample counts and median/p95 for the actual sample. An initial-open measurement is not a claim of a cold operating-system cache. Avoid comparing these desktop timings to mobile or hosted generation latency.

No gold-passage recall, independent test-set accuracy, or clinical accuracy is reported here because Step 4 was skipped and those annotations/splits were not established. Step 6 proves that local ranked retrieval and source resolution work.

## Planned files

| Path | Purpose |
| --- | --- |
| `notebooks/retrieval/03_retrieval.ipynb` | Executed notebook and saved search examples |
| `notebooks/retrieval/run_step.py` | Combined baseline/enhanced runner; optional bundle selection through `run(bundle=...)` |
| `notebooks/retrieval/README.md` | Run commands and input/output guide |
| `src/mobile_rag/retrieval.py` | Shared index, query compilation, search, and expansion logic |
| `tests/test_retrieval.py` | Focused integrity, query-safety, ranking, and provenance tests |
| `artifacts/03_retrieval_baseline/<run-id>/retrieval.sqlite` | Published local database |
| `artifacts/03_retrieval_baseline/<run-id>/index_manifest.json` | Input/output hashes, config, versions, counts, and status |
| `artifacts/03_retrieval_baseline/<run-id>/search_examples.jsonl` | Complete saved queries/results and evidence |
| `artifacts/03_retrieval_baseline/<run-id>/timings.csv` | Measured build/open/search/expansion timings |
| `artifacts/03_retrieval_baseline/<run-id>/check_results.json` | Named verification results |
| `docs/modeling/06-build-review.md` | Actual implementation, examples, measurements, and limitations |

These are proposed paths only. Preserve existing source data, prior runs, and user edits. No Step 6 folder or executable artifact is created by this planning task.

## Verification after authorization

1. Probe FTS5 and reject corrupted, stale, incomplete, or mixed-version input artifacts.
2. Reconcile imported documents/passages/chunks/citations with the selected bundle and run database/FTS integrity checks.
3. Use a small synthetic corpus with deliberately distinct terms to check exact-term retrieval, known ranking order, ties, OR/AND behavior, and document filters.
4. Test empty, punctuation-only, Unicode, oversized, quoted, and operator-like inputs; ensure they cannot alter SQL or execute unintended FTS expressions.
5. Confirm every returned ID/quote resolves to the exact imported source, and oversized tables are returned intact.
6. Check neighbor expansion boundaries, deduplication, budgets, source order, and explicit skip reasons.
7. Rebuild using identical inputs/settings and compare IDs, counts, and ranked results; test search through a reopened read-only database.
8. Confirm runtime queries do not change the database hash and can resolve stored evidence without source files being accessible, using a temporary fixture rather than moving real sources.
9. Execute the notebook in a fresh kernel, save outputs, read exported results back, and run the focused test/lint checks.

## Acceptance and stopping point

Ready for review means the index contains the complete selected valid bundle, searches are deterministic and safely compiled, results preserve complete evidence/provenance, failures are explicit, and executed examples/timings are saved. All tests and integrity checks must pass. Poor relevance in a real example remains visible for Step 7; it must not be hidden by editing the benchmark or discarding difficult questions.

Stop at local BM25 retrieval and its review report. Ranking refinement, clinical aliases, full accuracy evaluation, answer generation, UI/mobile integration, and all skipped phases are outside this build. The next action after this document is authorization to implement Step 6.
