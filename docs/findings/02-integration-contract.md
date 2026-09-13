# Kotlin and Swift integration contract

## Recommended boundary

Use native UI and lifecycle code in Swift/SwiftUI or Kotlin/Compose. Keep the pipeline interfaces language-neutral so the same knowledge bundle, IDs, prompts, fixtures, and acceptance cases can be shared.

```text
Question
  -> QueryValidator
  -> Retriever
  -> EvidenceGate
  -> ContextPacker
  -> ExistingModelAdapter
  -> AnswerValidator
  -> AnswerView / SourceView
```

The generator adapter is intentionally small. Retrieval, packing, validation, and source resolution must remain application-controlled.

## Core records

Equivalent Kotlin `data class` or Swift `struct: Codable` types should represent these records.

```json
{
  "EvidenceGroup": {
    "label": "S1",
    "document_id": "stable-document-id",
    "chunk_id": "stable-chunk-id",
    "source_passages": [
      {"passage_id": "stable-passage-id", "text": "Exact source text"}
    ],
    "page_status": "declared_unverified"
  },
  "GroundedAnswer": {
    "status": "answered",
    "answer": "Direct answer",
    "reason": "S1 states the requested rule.",
    "citations": ["S1"]
  }
}
```

A repeated source passage may use `{"passage_id":"...","reference":"S1"}` instead of repeating its text. References must point backward to the first group that owns the same `(document_id, passage_id)`.

## Retrieval contract

### Input checks

- question must be nonblank and at most 2,000 characters;
- tokenization must yield between 1 and 64 distinct terms;
- `topK` must be an integer from 1 through 20;
- mode is `OR` or `AND`;
- an optional document filter must identify a document in the open bundle;
- filler-only or punctuation-only queries fail as `invalid_query` and never reach the embedding model.

### Lexical path

- Use SQLite FTS5 with the `unicode61` tokenizer.
- Quote query terms and bind SQL parameters; never concatenate untrusted raw MATCH syntax.
- Preserve SQLite BM25 semantics: lower raw BM25 is better before normalization/fusion.
- Enhanced OR mode removes only the reviewed conversational filler list. Do not remove clinical setting/role terms, negation, or numeric qualifiers.
- Use heading/body weighting of 3:1 for the enhanced branches.
- The existing corpus-attested alias is `cpap -> continuous positive airway pressure`; do not invent an uncontrolled medical synonym dictionary.

### Dense path

The reference dense index uses:

- model: `BAAI/bge-small-en-v1.5`;
- pinned revision: `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`;
- 384 dimensions, CLS pooling, L2 normalization;
- query prefix: `Represent this sentence for searching relevant passages: `;
- maximum encoder input: 512 tokens, with no silent truncation;
- source windows: 448 tokens with a 384-token stride;
- exact dot-product search across stored normalized vectors.

If dense retrieval is ported, verify tokenizer output, embeddings within an agreed numeric tolerance, and ranked chunk IDs against Python fixtures. Otherwise ship BM25 first and add dense only after measured benefit.

### Fusion and result

- Each enabled main path contributes at most `candidateLimit=20` candidates.
- Fuse unique chunk IDs using `score += 1 / (60 + rank)`.
- Sort by descending RRF score and then stable chunk ID.
- Return the top five by default with branch ranks and source records.
- Do not use RRF score or cosine similarity as an uncalibrated answerability threshold.

## Evidence gate

The current Python reference ranks evidence but does not finish this semantic gate. The mobile team must not hide that gap. Initially, mark it as an explicit feature flag and instrument:

- retrieval acceptance/rejection;
- required passage present in candidate pool;
- applicable population and setting;
- numeric/unit/negation coverage;
- unresolved source conflict;
- reason for local abstention.

Thresholds must be frozen on development questions and then evaluated on held-out answerable and unanswerable questions. A reranker can reorder candidates but cannot recover a passage absent from its candidate pool.

## Context packing contract

1. Re-resolve every selected chunk from the currently open, hash-verified bundle.
2. Reject the whole package if any returned text or identity differs from canonical storage.
3. Add direct hits in rank order; add a neighbor only when its explicit previous/next relationship and shared context identity are valid.
4. Deduplicate chunks and passage text by stable IDs.
5. Include or exclude a whole evidence group. Never truncate a table or detach a qualifier.
6. Assign labels consecutively starting at `S1` and build a local `citationMap` that is never produced by the model.
7. Compute the fully rendered prompt/request size using the mobile model's tokenizer. Reserve output tokens before accepting the final group.
8. If no group fits, return local `insufficient_evidence` with origin `context`; do not invoke generation.

Reference Python character budget: total 40,000 characters, 7,000 instruction reserve, and 4,000 answer reserve. These values are experiment defaults, not mobile token limits.

## Generator adapter contract

The mobile adapter accepts one immutable request and returns raw model text plus generation metadata. It must not retrieve sources, choose citations, edit the source bundle, or call tools.

Required configuration to record:

- model artifact ID and SHA-256;
- quantization and runtime version;
- tokenizer and chat-template identity;
- prompt version/hash and JSON-schema hash;
- temperature (`0` baseline), input/output limits, stop reason, and latency;
- device/app build and whether the request ran completely offline.

Use the app's existing model. If its runtime supports grammar- or schema-constrained decoding, apply the schema in [03-prompts.md](03-prompts.md). Always validate locally as well. If the runtime does not support a system role consistently, send one user turn containing instructions followed by `INPUT DATA`, as the Python reference does.

## Answer validation contract

Decode with strict types and reject unknown fields.

| Condition | Required behavior |
| --- | --- |
| `status=answered` | `answer` is nonblank; `reason` is nonblank; citations are nonempty and unique. |
| `status=insufficient_evidence` | `answer` is exactly empty; citations are empty; `reason` is nonblank. |
| any citation | label exists in this request's local citation map. |
| incomplete stop reason | do not display partial answer. Record `incomplete_response`. |
| malformed/extra/mistyped fields | record `invalid_response`; do not convert it to abstention. |
| model/runtime/network failure | record a technical error distinct from evidence insufficiency. |

A bounded regeneration for truncated or invalid structure is optional. If used, restart from the complete original request, append the relevant retry feedback from [03-prompts.md](03-prompts.md), log the attempt, and revalidate. Never continue partial clinical text.

Before clinical release, add claim-support validation. At minimum, check cited spans for every consequential number, unit, comparator, route, frequency, duration, time, population, condition, exception, and negation. Failure should block display or produce a clearly defined safe outcome; it must not silently pass.

## UI states

Keep these states visibly distinct:

- `answered`: show the direct answer and tappable citation chips;
- `insufficient_evidence`: show the evidence-gap reason, with no guessed advice;
- `technical_error`: explain that the answer could not be generated and allow a safe retry;
- `source`: show title, edition when available, physical/printed page labels, and exact extracted passage.

Selecting `S1` resolves through the local citation map. Never trust document names, page values, or source text echoed by the model. Preserve the current answer and selected source when navigating between screens.

## Offline and update behavior

- Bundle the verified SQLite/index/source assets and model locally.
- Test new questions in airplane mode after a fresh install.
- Never ship an OpenRouter or developer API key in the app.
- Verify schema, sizes, file hashes, model/tokenizer identity, and index/bundle identity before activating an update.
- Install to a staging location, fsync/close, then switch atomically. Keep the previous valid bundle for rollback.
- Handle cancellation, background/resume, memory pressure, and model unload/reload without presenting partial output as an answer.
