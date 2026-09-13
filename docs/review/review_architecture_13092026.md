# Implementation issues — 13 September 2026

Issues in the running code only. Documentation mismatches are out of scope. No code was changed for this review.

The pipeline is careful with hashes, IDs, and JSON shape. It is permissive about which passages count as evidence and whether a generated answer is actually supported. The items below are bugs, logic errors, and missing checks in that implementation.

## Bugs

### 1. Package entry point crashes

`src/mobile_rag/__main__.py` imports `from .rag import main`. There is no `rag` module. `python -m mobile_rag` fails immediately. `python -m mobile_rag.retrieval_hybrid` works because that module has its own `__main__` block.

### 2. Bulk notebook is missing imports

`05_2_bulk_answer_generation.ipynb` calls `RetrievalConfig`, `latest_index`, and `HybridRetriever` but never imports them. The first code cell imports generation, bulk helpers, context budget, environment, and file helpers only. A fresh kernel raises `NameError`. The CLI runner imports hybrid correctly; the notebook does not. It can appear to work only if another notebook already defined those names in the kernel.

### 3. Resume can mix generators in one run

`GenerationConfig` stores `max_output_tokens`, `timeout_seconds`, and `provider`. `MODEL` and temperature are module globals in `answer_generation.py`. Bulk run manifests store `generation_config` and prompt hashes, not the model ID.

Changing `MODEL` and resuming the same directory reuses completed records from the previous model and generates the rest with the new one. Resume comparison treats that as a valid continue.

### 4. Shared PDF pairing reuses `document_id` and can emit a corrupt chunk bundle

`build_chunks()` sets `document_id` to the matched `pdf_content_id`. Two different Markdown files paired to the same PDF therefore share one ID.

Chunking then selects passages with `document_id == ...`, so it mixes both files, can emit duplicate chunk IDs, and rewrites neighbor links twice. `validate_inventory()` records `multiple_markdown_for_pdf` as a warning and still sets `technical_status` to `"passed"`. `validate_chunks()` checks unique passage/chunk IDs, not unique document IDs.

Index build later fail-closes on a duplicate document primary key. The chunk export can already be wrong by then.

### 5. Hybrid constructor can leak SQLite connections

`HybridRetriever` opens a base `Retriever` (FTS DB + in-memory tokenizer), then may open `EnhancedRetriever`, which opens the **same** FTS DB again plus `passage.sqlite`.

If `EnhancedRetriever(...)` raises after opening handles, the object is not assigned to `self.lexical`. `close()` therefore does not close those connections. The outer `except` only closes objects already stored on `self`.

### 6. Hybrid search ignores lexical `invalid_query`

`EnhancedRetriever.search` can return `invalid_query` (no clinical terms, too many terms) with empty hits. `HybridRetriever.search` only aborts on lexical `status == "error"`. For `invalid_query` it takes the empty BM25 list and continues with embeddings.

A stopword-only question can still return five dense nearest neighbors and go to generation.

Hybrid also skips the baseline `max_terms = 64` check. A 65-term question is invalid on BM25 and `ok` on hybrid if embeddings return anything.

### 7. Passage search applies `document_id` after `LIMIT`

The passage branch runs `LIMIT 160`, then drops rows whose parent is not the requested document. Restricted-document search can therefore return far fewer than 40 parent candidates, while unrestricted search gets the full pool.

Each kept row also calls `self.resolve(cid)` inside that loop, which re-reads the chunk, document, passages, and citation from SQLite.

### 8. Provider JSON Schema does not match local validation

`answer_json_schema()` only adds a citation-label enum. Local Pydantic then enforces:

- `answered` requires nonempty answer text and at least one citation
- `insufficient_evidence` requires empty answer and empty citations
- `reason` must be nonblank in both cases
- citation labels must exist in the current map

The model can return JSON that satisfies the provider schema and then fail locally as `invalid_response`. There is no regenerate, repair, or conversion to abstention. Duplicate labels such as `["S1", "S1"]` are also allowed (`uniqueItems` is not set).

### 9. Inventory never fails on unusable corpus content

`validate_inventory()` checks ID uniqueness, hash format, and internal references. Unreadable PDFs, unmatched Markdown, bad page markers, and duplicate pairings are appended to `issues` and ignored by `passed`. `run.technical_status` is always `"passed"`. Chunking will still consume that inventory if the ID/hash checks succeed.

### 10. `assert` is used as an integrity gate

`build_enhanced()` uses `assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"`. Running Python with `-O` strips asserts, so that check disappears. Index build in `retrieval.py` uses a real `if`/`raise` for the same kind of check.

## Logical issues

### Query construction

Benchmark rows already have `topic` and `question_template`. Retrieval always searches the wrapped `question`:

- `A frontline health worker asks: {topic}. What is the correct action or answer?`
- `During a busy clinic, I face this situation: {topic}. What should I remember from the guideline?`

`clean_question()` drops some filler (`during`, `busy`, `frontline`, `asks`, `remember`, `correct`, `answer`) and keeps `clinic`, `health`, `worker`, `action`, `guideline`. Those leftover tokens are common in antenatal and general-care passages. That is consistent with off-topic hits that keep ranking because they share wrapper language, not the clinical topic.

Phrase and NEAR branches run only when the focused term count is between 2 and 8 inclusive. Leftover wrapper tokens push many questions over that limit, so the only lexical branches that reward exact phrases are disabled.

All enhanced lexical branches use the cleaned term list. The original word order of the topic phrase is not searched as a phrase unless that 2–8 gate passes.

### Ranking always returns evidence

Default search mode is OR. Fusion is reciprocal rank with `k=60`. Each enabled path returns up to `candidate_limit` (20) parents, then the fused list is truncated to `top_k=5`.

There is no minimum matched-term count, no cosine floor, no domain filter, and no path that returns `no_matches` when the best hit is weak. Dense search returns nearest neighbors for any embeddable string, including nonsense. Hybrid then marks `status="ok"` and packs those chunks as evidence.

Rank is treated as permission to generate.

### Neighbor expansion grows irrelevant hits

`expand()` takes the first three hits and adds previous/next chunks when they share `document_id` and `context_passage_ids` and fit a character budget. Relevance is not checked.

If hit 1 is off-topic, its section neighbors are added too. Context packing then includes them as `neighbor_context` as long as the seed chunk itself was packed.

Neighbors that sit under a different subheading are skipped (`section_or_document_boundary`), even when they hold the qualifier, footnote, or contraindication for the selected chunk. Expansion is therefore both too wide (irrelevant same-heading neighbors) and too narrow (needed text across a heading change).

### Context packing is greedy by rank, not by usefulness

`prepare_context()` is strict about provenance: it re-resolves every chunk from the open index and rejects the whole package on any mismatch. That part is sound.

Selection is not:

- Groups are appended in retrieval order, then neighbors.
- A large off-topic group that fits consumes budget that a later supporting group needs.
- Oversized groups are skipped rather than truncated (correct), but there is no attempt to keep a later relevant group in preference to an earlier irrelevant one.
- `status="ready"` means at least one group fit. `generate_answer()` treats `ready` as “call the model.” Irrelevant nonempty context is sent.

Character budgeting is also mis-sized relative to the real request. Defaults: 20,000 total, 2,000 instruction reserve, 4,000 answer reserve. Prompt `v3` plus JSON encoding of question and evidence already exceeds a 2,000-character instruction reserve. There is no tokenizer pass. Over-budget requests fail as `api_error` after the call is made.

Rendered evidence is JSONL with escaped Markdown. Repeated headings become `{"reference": "S1"}`. Provenance is correct; a generator that must resolve aliases and read JSON-escaped tables is being asked to do two extra jobs that the packing format created.

### Chunking splits clinical units in the wrong places

The 600-character minimum in `CHUNK_CONFIG` is never used. A heading change flushes the current group even if it is short.

Tables are one passage. A dose/weight table becomes one oversized chunk. Retrieval returns the whole table. BGE then windows that string at 448 tokens with stride 384 and **does not repeat headers** on later windows. A matching row can be embedded without its column labels.

Lists stop at the first blank line. Blank-separated guideline lists become multiple paragraphs and can split a rule from its exceptions.

### FTS tokenization breaks clinical strings

The index uses SQLite FTS5 `unicode61`. Punctuation is a separator, so `F-75`, `11.5`, `140/90`, and `90%` become fragments (`f`/`75`, `11`/`5`, `140`/`90`, `90`). Exact BM25 lookup of doses and thresholds is weaker than the stored source text suggests. Embeddings can recover some of those, but they also retrieve related-but-wrong passages.

Alias expansion is a single hard-coded map: `cpap` → `continuous positive airway pressure`. No other abbreviations, drug names, or units are expanded.

### Generation trusts the model for clinical truth

`support_validation` is always `"not_performed"`. Citation validation is “label exists in this request’s map.” That passed on every record in the scored Q_S1 run while most answers were clinically wrong.

Empty or budget-blocked context returns local `insufficient_evidence` and does not call the API. Any nonempty packed context calls the model. The prompt tells the model to abstain; the application never converts an unsupported `answered` payload into abstention.

On success, `generate_answer()` copies the LLM’s inner `status` onto the outer envelope. Bulk `pipeline_status` is that collapsed value. Local context abstention (`answer is None`) and model abstention (`answer.status == "insufficient_evidence"`) are different events stored under similar statuses.

There is no retry on 429/5xx. A transient rate limit is a permanent `api_error` for that question. That is consistent with the “no automatic retries” comment in bulk generation; it is still a bulk-run failure mode.

`qwen/qwen3-14b` is a module constant, not a run-config field. Qwen3 may emit thinking tokens. Those count against `max_tokens=1024` and can produce `incomplete_response`, or they can leak into the JSON content and become `invalid_response`. Neither case is handled specially.

### Status and identity gaps in records

`process_question()` stores the full benchmark row, including the reference answer, in `question_record`. Tests confirm that text does not enter the prompt. Fine for later scoring; easy to misuse if a later caller concatenates the record into a request.

`select_questions(n)` takes the first N rows. The file is ordered as topic pairs (frontline, then busy-clinic). `n=10` is five topics, not a category sample.

`latest_index()` / `latest_bundle()` pick artifacts by sorted path. There is no check that the chosen index was built from the current chunk bundle, or that the chunk bundle was built from the current inventory, beyond hashes stored *inside* an already-selected directory. Passing no path means “newest folder name,” not “matching fingerprint.”

Hybrid `query_id` is a hash of a `json.dumps` list without `sort_keys`. The dataclass field order is currently stable; any reordering of `RetrievalConfig` fields changes IDs for the same search.

Prompt path and `.env` discovery use `Path(__file__).resolve().parents[2]`. That is the project root only while the file lives at `src/mobile_rag/...`. A non-editable install resolves to `site-packages` and will not find `prompts/answer_generation.md` or the project `.env`.

### Missing stages that the query path already assumes

There is no evaluation module. Retrieval recall, packed-evidence precision, oracle generation (gold passage only), numeric/negation checks, and Q_S2 unanswerable abstention are not computed in code. Bulk defaults to `Q_S1.json`, so the 30 Q_S2 unanswerable items never exercise abstention unless the path is changed by hand.

There is no source viewer. `page_status` is hard-coded `"declared_unverified"` and citation targets store `pdf_coordinate_status: "unavailable"`. Offsets exist on passages; nothing uses them to highlight a PDF.

Documents have no edition, date, publisher, or supersession record. When two manuals disagree, retrieval can return both and generation picks one. The application has no conflict state other than hoping the model returns `insufficient_evidence`.

Each bulk worker opens a new `HybridRetriever` per question: two FTS connections, a memory tokenizer DB, optional passage DB, and a shared BGE encoder (locked, so parallel workers serialize embedding). `MAX_WORKERS=4` multiplies SQLite handles, not embedding throughput.

## What is working as implemented

These should stay:

- Read-only hashed SQLite indexes; tampered files are rejected
- Reference answers do not enter the generation prompt
- Whole groups/tables are kept or omitted; source text is not silently truncated
- DeepInfra is pinned with `allow_fallbacks: False`
- API keys and raw error bodies are not written into results
- Bulk JSONL checkpoints flush per question; worker exceptions become `worker_error` records
- `support_validation: "not_performed"` is recorded instead of faked

## Priority to fix in code

**P0 — correctness of the running experiment**

1. Import hybrid symbols in the bulk notebook; fix `__main__.py` or remove it.
2. Put `MODEL`, temperature, and prompt identity into `GenerationConfig` / run manifests; refuse resume on mismatch.
3. Reject duplicate `document_id` at chunk validation; fail inventory when two Markdown files map to one PDF.
4. Do not send `ready` context that has no relevance gate. Empty or below-threshold retrieval must become `insufficient_evidence` without a model call.
5. After an `answered` payload, check that cited passage text actually contains the claimed numbers, units, and negations. On failure, reject or abstain. Leave `support_validation` as `not_performed` only until that exists.

**P1 — retrieval and packing logic**

1. Search the canonical topic for benchmark runs; keep the wrapped question for the generator.
2. Always run a phrase query on the topic terms; use OR as fallback with a minimum term-match requirement.
3. Stop forcing five hits. Allow `no_matches` from weak dense/lexical scores.
4. Expand a neighbor only when it completes a kept chunk (header, footnote, continuation), not because it is adjacent to a top-3 hit.
5. Pack fewer groups; prefer later relevant chunks over earlier off-topic ones when the budget is tight.
6. Index tables as row/column units for retrieval; keep the parent chunk for citation. Do not embed table tails without headers.

**P2 — robustness**

1. Treat unreadable PDFs, unmatched Markdown, and duplicate pairings as inventory failures.
2. Replace the passage-search post-`LIMIT` document filter with a SQL constraint.
3. Encode answered/abstention rules in the provider schema (`uniqueItems`, consistency), or map local validation failure to abstention instead of a dead `invalid_response`.
4. Close hybrid sub-retrievers in `finally` even when assignment fails.
5. Replace `assert` integrity checks with `raise`.
6. Add evaluation over saved records: retrieval hit/miss, packed on-topic fraction, inner vs outer status, Q_S2 unanswerables. Do not require another live bulk run to see these.

The implementation validates bytes and labels well. It does not validate that a hit answers the question or that an answer is entailed by the cited text. Those two missing checks explain most of the unsafe outputs.
