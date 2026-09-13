# Test, parity, and release checklist

## Phase 1: contract parity

- [ ] Import a fixed verified bundle and reject a changed file/hash.
- [ ] Produce the same `unicode61` lexical terms as Python for punctuation, Unicode, numbers, and units.
- [ ] For fixed questions, return the same ordered BM25 chunk IDs, including stable tie ordering.
- [ ] If dense is enabled, match tokenizer IDs and embeddings within a documented tolerance.
- [ ] Match RRF results using `k=60` and the same candidate limit.
- [ ] Reject blank, punctuation-only, filler-only, over-2,000-character, and over-64-term queries before embedding.
- [ ] Re-resolve selected chunks and reject changed text, identity, or citation mappings.
- [ ] Preserve whole oversized tables; never cut away headers, units, or footnotes.
- [ ] Deduplicate repeated chunks and passage IDs deterministically.
- [ ] Reproduce `S1...Sn` label assignment and local citation-map resolution.
- [ ] Confirm benchmark reference answers never occur in a model request.

## Phase 2: generation safety

- [ ] Keep the existing mobile model and pin its exact artifact, quantization, tokenizer, template, and runtime.
- [ ] Embed and hash prompt `evidence-answer/v6`.
- [ ] Use temperature zero for the baseline and record all decoding parameters.
- [ ] Enforce the four-field schema with unknown fields forbidden.
- [ ] Reject unknown, blank, non-string, and duplicate citation labels.
- [ ] Reject `answered` with an empty answer or no citations.
- [ ] Reject `insufficient_evidence` with answer text or citations.
- [ ] Do not display a completion stopped for length, cancellation, filtering, or runtime error.
- [ ] Keep evidence abstention separate from malformed output and technical error.
- [ ] If structural retry is enabled, bound and record attempts and revalidate from scratch.
- [ ] Verify all accepted citations resolve to source records in the same installed bundle.

## Phase 3: adversarial and clinical-quality cases

The test set must contain answerable and unanswerable questions and must be reviewed against the exact indexed source version.

- [ ] Same number in the wrong population or age band.
- [ ] Correct number with the wrong unit.
- [ ] Reversed `<`, `>`, `at least`, or `at most` relationship.
- [ ] Missing `not`, `unless`, exception, or conditional clause.
- [ ] Starting rule confused with target or stopping rule.
- [ ] Tablet strength confused with tablet count.
- [ ] Per-feed quantity confused with daily quantity.
- [ ] Prevention guidance confused with treatment guidance.
- [ ] Table row returned without its column header or footnote.
- [ ] Two applicable sources conflict and have no precedence rule.
- [ ] Relevant passage absent while related but insufficient text is present.
- [ ] Prompt injection text appears inside the question or evidence.
- [ ] Paraphrases of the same question retrieve materially different evidence.
- [ ] Signs/list question tries to produce a treatment plan.
- [ ] Model adds unrequested clinical advice.

Track at least:

- relevant-evidence recall at candidate and packed-context stages;
- packed-evidence precision;
- false answer rate on unanswerable questions;
- false abstention rate on answerable questions;
- answer-intent accuracy;
- qualifier completeness;
- unsupported consequential claims;
- schema/citation rejection and truncation rates.

Do not treat reference-answer string overlap, a high cosine score, or a valid citation label as proof of clinical correctness.

## Phase 4: physical-device measurements

Measure iOS first if following the original delivery order, then repeat on Android with the same bundle and questions.

- [ ] artifact sizes: model, tokenizer, SQLite, vectors, and source documents;
- [ ] cold and warm startup;
- [ ] retrieval p50/p95 and dense-encoder load time;
- [ ] time to first token and total validated-answer latency;
- [ ] peak process memory and memory-pressure recovery;
- [ ] sustained throughput and repeated-query thermal degradation;
- [ ] energy/battery impact;
- [ ] cancellation and app background/resume;
- [ ] airplane-mode operation after fresh install;
- [ ] zero network attempts during retrieval, generation, and citation viewing;
- [ ] atomic bundle update and rollback after an injected corrupt update.

## Release blockers

Do not describe the application as clinically reliable or release it for unsupervised clinical decision support while any of these remain true:

- the corpus has unresolved extraction/page-order defects;
- source editions and conflicts have no reviewed governance policy;
- relevant-evidence recall and unanswerable-question behavior have not been measured on held-out cases;
- consequential generated claims are not checked against cited spans;
- source highlights are inferred from unverified Markdown offsets;
- the installed model/runtime pair has not passed physical-device offline testing;
- technical errors can be shown as answers or as evidence abstentions.

## Handover acceptance

The integration is complete when the mobile app can, entirely offline, load a hash-verified bundle, retrieve source-backed passages, invoke the existing model with the v6 prompt, strictly validate the answer, abstain safely, and open every accepted citation at the exact stored passage. Kotlin and Swift builds should run the same parity fixtures and report any deliberate platform difference.
