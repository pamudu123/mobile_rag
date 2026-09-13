# Findings and decisions

## Executive finding

The experiments support a retrieval-augmented design, but they do not support relying on the generator alone. The safest integration strategy is to keep the app's existing model and reproduce the surrounding controls. Accuracy comes mainly from evidence quality, constrained context, abstention, validation, and traceable citations.

The pipeline is:

```text
verified local corpus
  -> section-aware chunks with stable IDs
  -> BM25 and/or dense retrieval
  -> reciprocal-rank fusion
  -> whole-source evidence packing
  -> existing mobile model with strict prompt/schema
  -> local response and citation validation
  -> answer or explicit abstention
  -> source passage viewer
```

No benchmark reference answer is included in retrieval, context, or generation.

## What worked

### Source-backed retrieval

- SQLite FTS5/BM25 gives a small, transparent, offline lexical baseline.
- Enhanced lexical retrieval removes conversational filler while retaining clinical setting, role, negation, and numeric terms.
- It searches chunks, headings, phrases, proximity matches, and passage-level units, then fuses ranked lists using reciprocal-rank fusion (RRF).
- The optional dense branch uses the pinned `BAAI/bge-small-en-v1.5` encoder, 384-dimensional L2-normalized vectors, and exact local similarity search.
- Dense retrieval is independent of BM25; a semantic result does not need to appear in the lexical candidate list.
- Hybrid mode retrieves up to 20 candidates per enabled path and fuses ranks with `RRF k=60`; the normal final result count is five.
- Corpus, index, encoder, vector, and tokenizer identities are checked so evidence from different builds cannot be silently mixed.

### Deterministic context preparation

- Every retrieved record is resolved again from the read-only index before use.
- Changed text, an unknown chunk, a mismatched bundle, or a changed citation mapping causes a fail-closed result.
- A complete evidence group is included or excluded; the packer does not cut a clinical table or passage merely to fit the budget.
- Repeated passages are rendered once and later groups reference their first label.
- Evidence is labeled `S1`, `S2`, and so on. The model sees opaque labels; application code owns the mapping to document, chunk, and passages.
- The complete serialized request is checked against the configured character budget before generation.

### Constrained generation

- The generator receives only the original question and selected evidence.
- Temperature is zero in the reference configuration.
- Tools, browsing, model-controlled retrieval, and agent loops are unnecessary.
- The response must contain exactly `status`, `answer`, `reason`, and `citations`.
- `answered` requires nonblank answer text and at least one supplied citation.
- `insufficient_evidence` requires an empty answer and an empty citation list.
- Unknown or duplicate labels, extra fields, malformed JSON, incomplete completion, and inconsistent response shapes are rejected.
- Empty or budget-blocked context abstains locally without calling the model.
- Technical failures remain technical failures; malformed output must not be mislabeled as a safe evidence abstention.

### Traceability

- Stable document, passage, chunk, index, prompt, schema, adapter, and run identities are recorded.
- A citation can be resolved without trusting text returned by the model.
- The intended UI is answer -> citation -> original passage. If verified PDF coordinates do not exist, show and highlight the verified extracted passage; do not invent a PDF overlay.

## Measured evidence

These figures describe particular saved runs, not a clinical certification and not a controlled comparison between models.

| Evidence | Result | Meaning |
| --- | --- | --- |
| Lexical retrieval build review | warm median 18.41 ms; warm p95 47.66 ms on desktop | The local baseline is technically lightweight; these are not phone timings. |
| Earlier Gemma/v2, 100 Q_S1 questions | 100 schema-valid `answered`; manual review: 18 pass, 27 partial, 55 fail | Structured output and valid citation labels did not establish clinical correctness. |
| Qwen/v3 hybrid, first 10 Q_S1 questions | 6 core-aligned, 2 partial, 1 answer-intent failure, 1 incomplete | Better small-sample behavior was observed, but retrieval, prompt, and model all changed. |
| Hybrid final-hit membership, same 10-question run | 34 in both candidate lists, 9 embedding-only, 7 lexical-only | Both branches contributed; contribution is not relevance. |
| Current v6/Qwen 3.5 9B completed sample | 5 of 5 technically `answered` | This confirms completion only; no corresponding clinical re-review is claimed. |
| Current automated suite | 67 tests passed on 14 September 2026; the prior review also recorded Ruff passing | Contracts and failure handling are covered; clinical accuracy is not. |

Important observed failure modes:

- relevant evidence was available but the model answered the wrong intent, such as giving management instead of a requested signs checklist;
- summarization dropped scope, age bands, alternatives, conditions, or other qualifiers;
- unrelated evidence entered the packed context;
- different wording of the same question changed which evidence was retrieved;
- a completion reached its output limit;
- answers with valid citation labels still contained unsupported or unnecessary additions.

## What the mobile implementation must preserve

1. The original user question goes to generation. A cleaned retrieval query may be separate, but it must never replace or rewrite the clinical question passed to the model.
2. Evidence must retain document ID, chunk ID, source passage ID, exact source text, and bundle/index identity.
3. Clinical values must preserve number, unit, comparator, route, frequency, duration, timing, population, condition, exception, and negation.
4. Table rows must remain attached to column headers, row labels, units, and footnotes.
5. Retrieval rank is not an answerability decision. Weak or unrelated evidence needs a separately evaluated acceptance gate.
6. A citation label is accepted only if it exists in the current request's citation map.
7. An answer is displayed only after response-shape and citation validation pass.
8. Evidence abstention and technical failure are different UI states and analytics events.
9. The model must never be allowed to cite its own prior answer as source evidence. Follow-up questions perform fresh retrieval.
10. Corpus updates are installed atomically after hash/schema validation, retaining the last valid bundle for rollback.

## Known gaps at handover

- `support_validation` is still recorded as `not_performed`. There is no production claim-entailment gate for numbers, units, comparators, conditions, and negation.
- Retrieval has no calibrated weak-evidence threshold. RRF and similarity scores are ranking signals, not probabilities of correctness.
- Source edition, supersession, and conflict policy still require reviewed metadata. Conflicting applicable guidance should cause abstention until precedence is explicit.
- Reliable PDF coordinate mapping is not complete. Markdown character offsets are not PDF bounding boxes.
- Character budgets are deterministic but are not exact model-token accounting.
- Dense retrieval adds model size, load latency, memory, and energy. Keep it only if held-out evidence recall improves enough on target phones.
- A current source-quality issue was reported for `WHO-Oxygen-therapy-for-children-2016.md`: duplicate/out-of-order declared page markers. Rebuild from corrected, verified source data before treating automatic artifact discovery as current.
- Hosted results do not prove offline latency, memory, thermal behavior, or quality for the mobile model/runtime pair.

## Decision for generation model

Keep the existing mobile model. Implement a small `Generator` adapter around it and preserve the prompt and validator contracts. Record its exact artifact hash, quantization, tokenizer/chat template, runtime version, context limit, and generation parameters.

Only reconsider the model if physical-device acceptance fails after retrieval and validation parity is established. A model swap would create a new experimental cohort and must not be mixed with prior results.
