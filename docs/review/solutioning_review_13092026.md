# Architecture review validation and solutioning — 13 September 2026

**Implementation update:** the review below describes the pre-fix snapshot. The subsequent authorized code changes and their verification are recorded in [Implementation results](#implementation-results-after-code-authorization) at the end of this document.

The [architecture review](review_architecture_13092026.md) is substantially correct about missing relevance and answer-support checks. It also contains one invalid current-code claim, several overstated consequences, and proposed remedies that need evaluation before implementation. In particular, the bulk notebook already imports the hybrid symbols, duplicate chunk exports are rejected before database insertion, and the earlier Gemma results do not measure the current Qwen hybrid pipeline.

This document validates the current working tree, including its pre-existing uncommitted changes. It is a review and proposed implementation plan only. No application code, notebooks, prompts, benchmark data, or retained experiment artifacts were changed. No live generation requests were made.

## Evidence and verification scope

Reviewed all modules under `src/mobile_rag`, the bulk notebook and generation runner, existing tests, both question datasets, and saved run records. Source references below give file and function names; notebook cell numbers are zero-based JSON cell indices.

Verification performed:

| Check | Result |
|---|---|
| `.venv/Scripts/python.exe -m pytest -q` | **44 passed in 7.38 seconds**. Passing tests do not establish coverage of the defects below. |
| `python -m mobile_rag` using the project virtual environment | Exit 1: `ModuleNotFoundError: No module named 'mobile_rag.rag'`. |
| Bulk notebook import inspection and isolated execution of its cell 4 import | `HybridRetriever`, `RetrievalConfig`, and `latest_index` all available before their uses. The whole notebook was not executed because its current configuration enables live generation. |
| Temporary two-Markdown/one-PDF fixture | Inventory passes; two documents share one ID; four chunks have only two unique IDs; chunk validation fails `unique_chunk_ids`; export still writes files. `load_bundle()` rejects the failing manifest. |
| Temporary hybrid fixture with the existing test `FakeEncoder` | Stopword-only and 65-distinct-term queries: lexical `invalid_query`, hybrid `ok`. Nonsense: lexical `no_matches`, hybrid `ok`. Each returns the fixture's one parent. This proves control flow, not real BGE relevance. |
| Local tokenizer and schema checks | `F-75 11.5 140/90 90%` yields distinct terms `f, 75, 11, 5, 140, 90`; duplicate citation labels pass local validation. Blank-separated list items parse as two **list** passages. |
| Prompt length | Loaded v3 instructions alone contain **4,499 characters**, exceeding the 2,000-character instruction reserve. |
| Saved older run `20260913T124928720084Z` | 100 Gemma records, all `answered`, all citation checks `passed`. |
| Saved hybrid run `20260913_142522` | 10 Qwen records: nine `answered`, one `incomplete_response`; nine citation checks pass, one is `not_run`. |

Temporary fixtures were created outside the repository and removed by their temporary-directory context. No new test or reproduction code was added to the repository. Constructor resource leaks, wheel installation, and clinical accuracy were not independently reproduced or certified.

## Verdicts on the ten numbered bugs

| # | Verdict | Evidence, qualification, and implication |
|---|---|---|
| 1 | **Valid; reproduced** | [Package entry point](../../src/mobile_rag/__main__.py) imports the absent `.rag`. The hybrid module has its own build CLI, but it requires arguments and compatible assets; its existence does not repair the package entry point. |
| 2 | **Invalid in the current file** | [Bulk notebook](../../notebooks/answer_generation/05_2_bulk_answer_generation.ipynb), cell 4, imports all three symbols before configuring retrieval. Looking only at cell 2 misses this import. No missing-import fix is needed for the inspected snapshot. |
| 3 | **Valid, with wording correction** | [GenerationConfig / make_request](../../src/mobile_rag/answer_generation.py) omit model and temperature from the dataclass. `MODEL` is a module constant; temperature is a literal `0` in the request, not a module global. Notebook cells 6/8 store and compare prompt version/hash and generation config, but omit model and temperature. Changing the loaded model between sessions can mix completed and new records. Individual records retain model/request identity, so the mixture is diagnosable but not prevented. |
| 4 | **Valid export defect; downstream failure described incorrectly** | [build_chunks / validate_chunks / export_chunks](../../src/mobile_rag/corpus.py) reproduce the shared-ID and duplicate-chunk problem. Validation already detects duplicate chunk IDs, although it lacks a unique-document check. Export writes the invalid bundle and marks checks false. [load_bundle](../../src/mobile_rag/retrieval.py) rejects that manifest before SQL insertion; it also explicitly checks duplicate document IDs. Failure is not deferred to a SQLite primary-key exception. Exact-byte Markdown duplicates are deduplicated before this loop; different contents sharing a PDF are the important case. |
| 5 | **Valid exception-safety gap; persistent leakage not measured** | [HybridRetriever](../../src/mobile_rag/retrieval_hybrid.py) cannot close a partially constructed lexical object that never gets assigned. [EnhancedRetriever](../../src/mobile_rag/retrieval_enhanced.py) opens its base handles before connecting `units`, with no local cleanup around that connection. Base `Retriever` initialization also has unguarded failure points. Most enhancement-hash failures happen before any lexical handles open, and later hybrid failures close successfully assigned objects. Do not describe every constructor failure as a leak. |
| 6 | **Valid; reproduced with a fake encoder** | Hybrid only propagates lexical `error`, not `invalid_query`, and does not enforce the baseline distinct-term limit. It can turn invalid lexical input into evidence. In BM25-only hybrid mode, the same invalid status can become `no_matches`. A 65-word question is not necessarily 65 terms: `_terms()` deduplicates tokens. Embedding input can independently fail its 512-token limit. |
| 7 | **Valid restricted-search defect** | [EnhancedRetriever.search](../../src/mobile_rag/retrieval_enhanced.py) limits passage rows to 160 globally before applying the requested document filter. This can starve the passage branch, though other lexical branches filter in SQL. `resolve()` runs for every examined passage row only when a document restriction is supplied, including rejected rows; it is not an unconditional cost for unrestricted passage search. |
| 8 | **Valid schema gap; local rejection is working** | [answer_json_schema / GroundedAnswer](../../src/mobile_rag/answer_schema.py) expose basic fields, status values, reason minimum length, and citation enum. They do not encode whitespace-only reason rejection or cross-field consistency. Unknown citation labels are constrained in both layers. Duplicate labels pass both layers. [generate_answer](../../src/mobile_rag/answer_generation.py) returns `invalid_response` on local validation failure and does not accept that answer. Missing repair is an availability/design issue; it is not acceptance of invalid output. |
| 9 | **Valid missing corpus-usability gate; “never fails” is too broad** | [build_inventory / validate_inventory](../../src/mobile_rag/corpus.py) report content issues but exclude them from `passed`; build-time `technical_status` is hard-coded. Structural defects can still fail validation, discovery can raise, and chunking checks current Markdown hashes and decoding. Unmatched Markdown is deliberately allowed with an `md_` identity. Decide whether that is an admissible corpus mode rather than automatically treating every orphan as corruption. |
| 10 | **Valid, bounded integrity gap** | [build_enhanced](../../src/mobile_rag/retrieval_enhanced.py) uses `assert` for `PRAGMA integrity_check`; optimized Python omits it. The preceding explicit FTS integrity command still executes. Replace the assertion, but do not claim that all integrity checking disappears. |

## Verdicts on the logical and architectural claims

### Query construction and ranking

**Wrapper terms and phrase gating: valid mechanics, unproven effect size.** [process_question](../../src/mobile_rag/bulk_answer_generation.py) searches `row["question"]`, not `topic`. [clean_question and enhanced search](../../src/mobile_rag/retrieval_enhanced.py) retain the cited role/setting tokens and gate phrase/NEAR branches at 2–8 focused terms. Those retained tokens are an explicit design decision in the cleaner's docstring. A phrase branch is also not guaranteed to match when enabled: it searches the entire cleaned, deduplicated term sequence, rather than extracting the topic phrase. The assertion that these tokens explain the observed off-topic ranking needs a controlled comparison.

**No relevance acceptance threshold: valid. “Always five” is inaccurate.** [Hybrid search](../../src/mobile_rag/retrieval_hybrid.py) uses rank fusion with no minimum cosine or answerability score. With a nonempty eligible dense index and a successful embedding, nearest neighbors are returned regardless of absolute similarity. However, results are capped at five by default, not padded to five. Fewer eligible parents, disabled dense retrieval, invalid input, or errors can produce fewer or no hits. `no_matches` exists; the missing behavior is rejection of weak but nonempty results.

Candidate accounting has two levels: enhanced lexical subbranches take up to 40 parents (passage search first takes 160 units), then hybrid takes up to its effective per-path limit and fuses BM25 with embeddings. That effective limit is `max(top_k, candidate_limit)`, normally 20. An RRF score is a ranking signal, not a calibrated confidence probability.

### Neighbor expansion and context packing

**Expansion rules: valid; actual missing qualifiers remain a hypothesis.** [Retriever.expand](../../src/mobile_rag/retrieval.py) expands the first three hits within document/heading identity and a character budget. [prepare_context](../../src/mobile_rag/context_preparation.py) requires the seed to be included. Neither evaluates relevance or semantic continuation. Cross-heading neighbors are excluded even if potentially useful. That conservative boundary also prevents accidental mixing; removing it wholesale is not a justified fix.

**Greedy packing and absence of answerability checks: valid.** Packing verifies source identity and content, then selects complete groups in retrieval order followed by neighbors. It can skip an oversized group and still include later smaller ones, but cannot evict a large accepted distractor for a later supporting group. `ready` means structurally valid nonempty context, not sufficient evidence. Generation is attempted only with valid context, live mode, and credentials; dry-run operation does not call the provider.

**Budget mismatch: valid; API failure is not demonstrated by it.** V3 instructions alone are 4,499 characters against a 2,000-character reserve. Evidence JSON serialization is already counted by the packer, but full request framing, schema, and actual token accounting are not. The 20,000-character budget is an application heuristic, not the provider's token limit. Exceeding this heuristic does not necessarily produce an API error. A provider input-context overflow and an output completion ending at `max_tokens` are different failure modes.

**JSON escaping and aliases: valid representation, speculative harm.** Duplicate passages become references containing both passage ID and owner label. The provider receives evidence as a JSON array constructed from the JSONL representation. It is not repeatedly wrapping each JSONL line as an escaped string. Reading Markdown escapes and resolving aliases may affect quality, but exact-text deduplication and structured boundaries have benefits. Compare formats before changing them.

### Chunking, tables, and tokenizer behavior

**Unused minimum and table windows: valid.** [CHUNK_CONFIG / build_chunks](../../src/mobile_rag/corpus.py) never enforce `target_min_chars=600`. Heading changes flush groups regardless of size. Tables remain whole passages and can make oversized parent chunks; later packing may omit them. [BGEEncoder.windows](../../src/mobile_rag/retrieval_hybrid.py) takes 448-token windows with stride 384 without carrying table headers forward. The dense manifest explicitly records this limitation. The original parent remains available for evidence, but a window can lose column meaning during retrieval.

**Blank-separated lists: partially valid.** A blank ends a list passage, but another bullet starts another **list**, not necessarily a paragraph. Adjacent passages under the same heading can still be grouped into one chunk if they fit. A rule and exception can become separated at a size or heading boundary; blank lines alone do not prove they become separate chunks.

**Clinical string fragmentation: valid; matching is weakened, not impossible.** The local probe confirms punctuation splitting and deduplication. Documents and queries use the same tokenizer, so fragments still match; what is lost in ordinary OR queries is precision of the numeric/unit relationship. SQLite documents the default punctuation-separator behavior in its [FTS5 tokenizer specification](https://www.sqlite.org/fts5.html#unicode61_tokenizer). `ALIASES` contains only the CPAP expansion. An alias map is not a substitute for preserving thresholds, operators, and units.

### Generation, status, and experiment identity

**No claim entailment validation: valid.** Citation checks only establish label membership and output structure. `support_validation` is always `not_performed`. Unsupported but schema-valid answers can pass. Empty/budget-blocked context yields local abstention; model abstention is structurally distinguishable through the nested answer despite sharing the outer `insufficient_evidence` status.

**Older quality statistics need scope attribution.** The [earlier manual review](review_13092026.md) reports 18 passes, 27 partials, and 55 failures against supplied references for the 100-question **Gemma/v2** run. This validation rechecked the 100 accepted/citation-valid records, not all clinical judgments. The [newer manual review](review_20260913_142522_hybrid.md) assesses a **Qwen/v3 hybrid** run of ten questions. Neither comparison isolates retrieval, prompt, and model effects. “Most answers were clinically wrong” must be attributed to the earlier benchmark review, not presented as a measured result for the current configuration or independent clinical adjudication.

**Retries and reasoning: real limitations, qualified diagnosis.** The transport uses `urllib` with no automatic retry. Resume considers any saved record complete, including `api_error`; a transient error is retained unless an explicit rerun workflow changes that. Qwen run Q_S1:7 has finish reason `length` and 1,024 completion tokens, confirming output truncation. Its usage also reports 1,224 reasoning tokens, so an exact reasoning/output allocation cannot be inferred. OpenRouter documents reasoning tokens and model-dependent controls in its [reasoning guide](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens). This supports investigating reasoning-budget pressure, not asserting it caused this record. Thinking-text leakage into JSON was not established from the inspected records. Generic `incomplete_response` and `invalid_response` handling already exists; special recovery does not.

**Reference records and sampling: valid behavior, not current prompt leakage.** `question_record` retains the benchmark reference, but request construction selects question and evidence only. Existing tests cover reference exclusion. Future misuse by concatenating entire records is speculative. `select_questions(n)` deliberately takes the first N rows. Q_S1's first ten rows represent five triage topics, not a representative ten-topic/category sample.

**Artifact discovery: valid freshness gap with existing compatibility checks.** [latest_bundle](../../src/mobile_rag/retrieval.py) selects the first valid bundle in reverse path order; [latest_index](../../src/mobile_rag/retrieval_hybrid.py) selects by manifest presence and sorted path. Opening the index checks internal hashes and identities, including dense-to-base identity. Neither establishes freshness against the current source tree. Existing artifacts mix naming formats, so lexical path order is not even a universal chronological ordering. Explicit old-snapshot use should remain possible when recorded as such.

**Query identity: valid low-priority stability concern.** Hybrid hashes a JSON list containing the config dictionary without sorted keys. Dataclass field order is stable today; a future reordering changes query IDs. This is a reproducibility concern, not current nondeterminism.

**Installed-package paths: valid layout dependency; installation not reproduced.** The prompt is read at import from `parents[2]/prompts`, and default `.env` discovery also assumes the source checkout. `pyproject.toml` has no explicit prompt resource packaging configuration. A conventional wheel/site-packages layout can therefore fail to find the prompt. Credentials supplied through the environment or an explicit root remain supported. Do not claim every non-editable install necessarily fails without testing the built distribution.

### Missing stages and concurrency

**Evaluation: valid missing production stage; some checks already exist.** There is no application evaluation module computing the proposed quality metrics. Retrieval sanity notebooks, mode comparisons, and manual reviews do exist. Q_S2 has 100 questions including 30 `Unanswerable` rows; bulk currently selects Q_S1. Gold passage recall, oracle generation, and packed-evidence precision require reliable passage-level labels or adjudication. A reference answer and document-level `source_of_truth` are not automatically gold passage annotations.

**Viewer and source governance: valid capability gaps, not established runtime bugs.** Source resolution records unverified declared pages and unavailable PDF coordinates; Markdown character offsets cannot directly highlight a PDF. Chunk document records lack normalized edition/supersession/conflict policy. Inventory does capture raw PDF metadata, so “no date or publisher information anywhere” would be too broad. Selecting authoritative editions and resolving conflicts requires an explicit corpus policy.

**Worker cost: valid resource duplication, incomplete throughput conclusion.** Each BM25-enabled hybrid instance opens two file-backed base databases, **two** in-memory tokenizer databases, and a passage database: five SQLite connections per active retriever. Each question creates a new instance. Shared BGE inference is serialized by its encoder lock; four workers do not provide four simultaneous encoder calls. They can still overlap retrieval work and network generation, and each encoder call itself uses configured CPU threads. End-to-end benefit or harm needs measurement.

## Safeguards that should be retained

The original review correctly recognizes source/hash checks, exact source resolution, whole-group preservation, reference-answer exclusion, provider pinning (`allow_fallbacks=False`), per-question checkpoint flush/fsync, and explicit recording of unperformed support validation.

Two qualifications matter. Hashes detect mismatch against the selected manifest; they are not signatures proving authenticity if both data and manifest are replaced. Generation deliberately omits HTTP response bodies and keys from normal error records, but generic bulk `worker_error` stores truncated exception text. That is not a universal guarantee that every possible exception is sanitized. No secret values were inspected for this review.

Python's SQLite connection context manager manages transactions, not connection closure; its [official documentation](https://docs.python.org/3.13/library/sqlite3.html#how-to-use-the-connection-context-manager) reinforces the need for explicit resource ownership in the proposed cleanup.

## Proposed solution order and acceptance criteria

These are proposals for a later coding phase, not implemented changes or guaranteed quality improvements.

| Order | Work | Acceptance evidence |
|---|---|---|
| P0 — reproducible experiment | Repair or deliberately retire the package entry point; add loaded model, temperature, effective prompt hash, schema/adapter identity, and supported reasoning settings to immutable run identity. Keep the existing prompt mismatch checks. | Entry-point smoke check succeeds; changing each request-affecting setting rejects resume before scheduling calls; unchanged configuration resumes without mixing identities. No notebook import repair unless the file changes again. |
| P0 — source identity | Define canonical Markdown selection per PDF, or version transcription identity separately from PDF identity. Add unique-document validation and prevent invalid bundles being published as usable exports. Separate structural, usability, mapping, and clinical-review status. | Different transcriptions of one PDF are rejected or explicitly versioned; exact duplicates retain aliases; source/passages/chunks/citations all agree; failed exports cannot be consumed. Include corrupt PDF, empty/decode-failed Markdown, and invalid mapping fixtures. |
| P0 — measurement baseline | Evaluate saved records before another bulk call. Keep Gemma and Qwen cohorts separate; distinguish technical success, local abstention, model abstention, and benchmark quality. Prepare passage labels and a held-out answerability set including Q_S2 unanswerables. | Deterministic record/status counts; topic/category coverage shown; quality labels have a stated rubric and provenance; unavailable gold evidence is reported as unavailable rather than fabricated. |
| P0 — query validity | Enforce shared input limits before either retrieval branch. Define whether lexical “no focused terms” is a universal invalid-input condition or a permitted dense-only query; preserve the resulting status. | Stopword-only, punctuation-only, 65-distinct-term, unknown-document, and embedding-length cases have consistent explicit outcomes and do not accidentally become evidence. |
| P1 — evidence acceptance | Separate retrieval rank from acceptance. Evaluate query/topic cleanup, lexical coverage, dense similarity, reranking, and an answerability decision against the labeled set. Use a distinct retrieval query while retaining the original generation question and logging both. | Report relevant-evidence recall, false acceptance on unanswerables, and false abstention on answerables. Freeze thresholds on development data and validate on held-out topics. No arbitrary universal cosine/RRF cutoff. |
| P1 — answer support | Validate claims against cited spans, including quantity, unit, comparator, population, condition, and negation. Treat numeric/string overlap as one check, not proof of entailment. Preserve failed-support diagnostics and do not label unchecked answers supported. | Adversarial examples cover correct numbers in the wrong population, reversed operators, unit mismatch, dropped exceptions, and contradictory sources. Measure false acceptance/rejection. Valid paraphrases and permitted conversions need explicit handling. |
| P1 — structure and request budget | Evaluate table retrieval units with inherited headers/row labels and exact parent provenance; explicit continuation links for neighbors; evidence selection by usefulness under a fully rendered request budget. | Header-dependent rows remain interpretable; parent citation mapping is exact; qualifier cases improve without admitting unrelated sections; actual input token allowance plus output reserve fits the selected model's supported limit. |
| P2 — robustness and packaging | Move passage document restriction before candidate limiting; make every constructor own and close its partial resources; replace integrity assertions; align provider-supported schema constraints; add bounded transient-error retry with attempt logging; package the prompt as a resource. | Restricted queries recover eligible passage candidates; injected constructor failures leave no owned handles open; integrity failure raises under optimized Python; schema-invalid output remains distinguishable from evidence abstention; wheel import works outside the checkout; retries retain terminal history. |
| P2 — source governance and viewer | Add authoritative edition metadata, supersession/conflict rules, and independently validated PDF-coordinate mapping if the intended product needs it. | Conflicting editions produce an explicit policy outcome; displayed PDF highlights are checked against source pages, not inferred from Markdown character positions alone. |

### Changes to the original recommendations

- Do not automatically convert malformed model JSON into `insufficient_evidence`. That mislabels a technical failure as an evidence judgment. Retain a distinct failure state; any bounded repair must be logged and revalidated.
- Do not require exact topic phrases or lexical overlap for every accepted dense hit. Relevant paraphrases can have no shared terms. Use phrase retrieval as an evaluated branch, with limits and a fallback, rather than an unconditional requirement for long topics.
- Do not treat “pack fewer groups” as a quality guarantee. A smaller package can omit essential qualifiers. Measure supporting coverage and distracting content together.
- Do not fail every inventory warning indiscriminately. Exclude unusable content from the eligible corpus and decide whether incomplete mappings block the run or explicitly disable PDF-backed citation for those sources. Duplicate conflicting transcriptions require stronger treatment than harmless file aliases.
- Do not solve partial construction solely with an outer hybrid `finally`: the unassigned child is inaccessible there. Cleanup must be established inside each constructor/resource owner, and close operations must tolerate partial initialization.
- Do not infer that the two missing semantic checks explain **most** unsafe outputs from this review alone. Available evidence supports them as important risks; it also shows answer-intent errors, missing qualifiers, possible corpus limitations, and output truncation. Controlled retrieval, packing, and oracle-generation comparisons are needed to apportion causes.

The review is a useful basis for work after these corrections. The immediate decision is to stabilize experiment identity and source validation, establish a measured quality baseline, then evaluate evidence and answer acceptance before changing retrieval heuristics broadly.

## Implementation results after code authorization

The confirmed bounded defects have now been addressed in code. The current context-sidecar exports and five-question notebook setting were preserved. Historical run artifacts were not rewritten, and no live generation request was made. This change does not claim clinical quality improvement from a new live benchmark.

| Finding | Implemented behavior |
|---|---|
| Broken package entry point | `python -m mobile_rag` shows help; `build-dense` and offline `evaluate` are explicit subcommands. |
| Notebook imports | Already correct; preserved. |
| Generator mixing on resume | `GenerationConfig` includes model, temperature and retry policy. Requests and returned-model checks use the configured model. Loaded prompt text, schema and adapter identity are recorded, together with a runtime source fingerprint. Both run manifests and individual checkpoints are checked. Old manifests lacking identity are intentionally refused for continuation. |
| Shared PDF transcription identity | Different Markdown contents paired to one PDF fail inventory validation. Exact-byte aliases remain accepted. Chunk validation checks unique document IDs; invalid chunk bundles are rejected before creating an export directory. |
| Partial-constructor cleanup | Base and enhanced retrievers close their own partially opened connections. Close methods tolerate repeated calls. Hybrid closes successfully assigned children. Passage-index construction explicitly closes its SQLite connection. |
| Invalid hybrid query propagation | Stopword-only, punctuation-only and over-64-distinct-term inputs are rejected before either retrieval path. Lexical invalid/error status propagates. Embedding validation failure has an explicit error result. Bulk records retain the retrieval failure stage instead of calling generation. |
| Passage filtering | Passage SQL applies document membership before ranking/limiting its candidate pool, using a read-only attached base database. Existing stored passage indexes remain readable; per-row source resolution for filtering is removed. |
| Schema mismatch | Provider schema now includes nonblank reason/answer constraints, unique citations, and answered/abstention consistency branches. Local duplicate citation rejection was added. Invalid responses retain a technical failure status rather than being relabeled as evidence abstention. Provider acceptance of these schema features still requires a live compatibility check; only local JSON Schema validation was performed. |
| Corpus usability | Unreadable files/PDFs, decode failures, invalid Markdown/page structure, ambiguous pairings and conflicting transcriptions fail inventory checks. Technical status reflects those checks. Unmatched but readable Markdown remains an explicit supported mode with unavailable PDF mapping. |
| Integrity assertion | Passage database integrity failure raises `ValueError`, including under `python -O`; FTS integrity checking remains enabled. |
| Request budgeting | Default instruction reserve increased to 7,000 characters, including the bulk notebook. The entire serialized request plus answer reserve is checked before sending; excess returns `request_budget_exceeded`. This remains character accounting, not a provider-token guarantee. |
| Transient HTTP failures | Default policy allows two retries for HTTP 429/5xx with bounded exponential delays. Attempt statuses and HTTP codes are retained without raw bodies. Terminal HTTP errors are not retried. Network/timeouts and error objects returned with successful HTTP responses are not automatically replayed. Saved terminal records remain terminal on resume. |
| Status ambiguity | Local-context and model abstentions record `abstention_origin`; outer status and nested answer remain available. Generic worker exception text is omitted from persisted results. |
| Artifact discovery and query IDs | Automatic selection checks current source hashes/file membership and current inventory validity, matches the chosen chunk bundle identity, and validates index assets. Legacy ISO and compact timestamp names sort chronologically. Explicit index paths still support historical reproduction. Hybrid query hashing sorts config keys. |
| Installed prompt | Wheel includes the prompt and resolves it relative to the installed package outside a checkout. Environment-variable credentials remain supported; installed applications should use those or an explicitly supplied configuration root. |
| Wrapped benchmark queries | `query_source="topic"` is available as an explicit ablation, while the original question still enters generation. The notebook defaults to `"question"`; both query text and query-source identity are recorded and protected on resume. No unmeasured ranking improvement is claimed. |
| Missing offline evaluation | `mobile_rag.evaluation` reports statuses, cohorts, coverage, local/model abstention and Q_S2 unanswerable outcomes from saved records. Optional exhaustive `relevant_chunk_ids` annotations enable retrieval recall and packed precision/recall. Without annotations these metrics are null, not invented. Reference-answer string overlap is not treated as clinical correctness. |

### Validation of the changes

- **61 tests passed** (`.venv/Scripts/python.exe -m pytest -q`, 13.64 seconds in the recorded run), including constructor fault injection, candidate-pool starvation, invalid query suppression, changed/legacy resume identity, unusable corpus content, and optimized-Python integrity failure.
- **Ruff passed** for `src` and `tests`.
- Local JSON Schema validation rejected blank answers/reasons, duplicate citations, and inconsistent abstention, while accepting a consistent answer.
- A wheel built with `uv build --wheel` successfully imported generation and loaded all 4,499 prompt characters after extraction into an isolated directory outside the checkout.
- An in-memory copy of the bulk notebook executed in a fresh kernel with **two dry-run questions** and an explicit historical index. It produced checkpoints, context sidecar, results JSON/CSV and summary in a temporary directory. A second fresh kernel resumed without changing checkpoint bytes. User notebook live/count settings and historical artifacts were not altered for that validation.
- Offline evaluation reproduced the old saved Gemma run's **100 answered** and Qwen hybrid run's **nine answered / one incomplete response**. These are technical record counts, not re-scored clinical judgments.

The CLI-generated [hybrid saved-run evaluation](hybrid_saved_evaluation.json) is retained separately from the original experiment artifacts.

Example offline evaluation (creates a separate report; does not call a model):

```powershell
.venv/Scripts/python.exe -m mobile_rag evaluate artifacts/05_2_bulk_answer_generation/20260913_142522 --output docs/review/hybrid_saved_evaluation.json
```

An optional `--annotations annotations.json` file maps record keys to objects such as `{"relevant_chunk_ids": ["chunk_..."]}`. These labels must refer to the exact evaluated index; they must enumerate the relevant chunks rather than merely one convenient match.

### Current source issue and remaining work

**Automatic discovery now correctly blocks the current corpus.** `data/md_docs/WHO-Oxygen-therapy-for-children-2016.md` contains duplicate declared page markers for pages 3–66 and out-of-order markers. This is reported by the existing parser and is now a failing usability check. Verify those references against the PDF, correct or regenerate the extraction, and rebuild inventory/chunks/indexes before treating an automatically selected run as current. Source text and page numbering were not guessed or silently edited. An explicit historical index remains readable for reproducing old results; it does not certify the current source inventory.

The following remain open, rather than being disguised as small bug fixes: calibrated weak-evidence rejection; clinical claim entailment including numbers, units and negation; usefulness-based packing and semantic continuation links; header-aware table retrieval; numeric-aware tokenization; representative sampling policy; full provider token accounting/reasoning-budget tuning; normalized source edition/conflict policy; and a verified PDF viewer. Their proposed acceptance criteria remain in the earlier plan. The unused minimum-chunk-size setting remains advisory in practice. Per-question retriever construction and serialized encoder inference also remain; this change fixes connection lifetime, not throughput architecture.

Consequently, `support_validation` remains `not_performed`. A structurally valid nonempty context can still be off-topic, and a schema-valid answer can still be unsupported. The changes make the experiment and failure reporting more reliable; they do not establish a clinical safety gate.
