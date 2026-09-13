# System overview

[Reading order](README.md)

## At a glance

- Local pipeline: inventory ? chunking ? retrieval ? context ? answer generation ? evaluation.
- Inventory, chunking, retrieval and context preparation are implemented.
- Answer generation is implemented locally; hosted verification remains pending.
- Evaluation and mobile deployment are planned.
- Current answer fields are status, answer, reason and citations; see the answer-generation specification.


## Technical working: contracts between functions

```mermaid
sequenceDiagram
    participant R as Retriever
    participant C as Context preparer
    participant G as Generation adapter
    participant P as OpenRouter
    R->>C: Ranked hits + source IDs + bundle identity
    C->>R: Resolve and compare canonical source records
    C->>G: Context text + citation map + status
    G->>G: Validate package and local token budget
    alt Ready and configured
        G->>P: Question + evidence + JSON Schema
        P-->>G: Generated JSON + usage
        G->>G: Pydantic and citation validation
    else Missing setup or evidence
        G->>G: Return explicit local outcome
    end
```

- Build-time functions export versioned files; query-time functions use a verified read-only SQLite index.
- IDs link records across stages. A changed bundle cannot silently reuse another bundle's evidence.
- `generate_answer()` returns an application result envelope. Its `answer` field contains the generated object only after validation.
- Example path to text: `result["answer"]["answer"]`. First inspect the outer status; setup failures have no generated answer.
- Input question text is separate from evaluation reference answers throughout this path.


## How to read the detailed design

- The summary above and current function specifications describe the active scope.
- The detailed design below retains earlier proposals and rationale for traceability.
- Older OCR/gold-review/split requirements are deferred. Earlier claim-based output, retry settings and model budgets are superseded by [Answer generation](06-answer-generation.md).
- Original stage numbers do not change the purpose-based notebook layout.

## Architecture

Start with a single Python application and a versioned local knowledge bundle. A corpus of approximately 15 documents does not initially justify a hosted vector database, agent framework, or distributed services.

```mermaid
flowchart TD
    P[Original PDFs] --> I[Offline extraction and document review]
    I --> B[Versioned knowledge bundle]
    B --> T[SQLite text and provenance]
    B -. Later only if justified .-> V[Optional dense vectors]
    Q[Question] --> R[Local retrieval]
    T --> R
    V --> R
    R --> E[Evidence selection and conflict checks]
    E --> C[Bounded prompt]
    C --> G[Generation adapter]
    G --> O[OpenRouter Gemma: experiment]
    G --> L[Embedded model: later mobile stage]
    O --> A[Answer and citation validation]
    L --> A
    A --> U[Answer or abstention with source viewer]
    T --> U
```

Document preparation happens before distribution. The final mobile query path performs retrieval, generation, validation, and viewing locally. If on-device import/OCR is later required, treat it as additional scope with its own resource measurements.

## Components and contracts

| Component | Responsibility | Output |
| --- | --- | --- |
| Corpus builder | Inventory PDFs, extract text, audit OCR, map original pages | Immutable knowledge bundle and manifest |
| Retriever | Rank corpus chunks using the question | Chunk IDs, ranks, scores, and retrieval version |
| Evidence selector | Remove duplication, preserve qualifiers, apply reviewed precedence | Ordered evidence within the token budget |
| Prompt builder | Combine instructions, question, and labeled evidence | Model request independent of provider |
| Generator | Execute one model call through a replaceable adapter | Raw response, finish status, usage, timings |
| Validator | Check output shape, source IDs, exact quotes, and missing support | Answer, abstention, or technical error |
| Presenter | Show cited claims and navigate to source spans | Answer screen and source view |
| Evaluation runner | Run frozen questions and record stage-level outcomes | Per-question results and aggregate report |

Use plain typed records and explicit interfaces. No model-controlled tools or recursive agent loops are required. The default question contract is single-turn; future follow-up questions must retrieve fresh evidence rather than treat previous generated answers as sources.

## Knowledge bundle

| Record | Required fields |
| --- | --- |
| Document | Stable ID, title, original filename, SHA-256, edition/date, publisher, language, review status |
| Page | Document ID, 1-based physical PDF page, printed page label if available, extraction method, dimensions/rotation |
| Passage | Stable ID, page, section path, source text, normalized retrieval text, source character offsets, bounding boxes if verified |
| Chunk | ID, ordered passage IDs, retrieval text, token count, chunking version |
| Precedence rule | Topic/scope, preferred document, superseded document, rationale, reviewer/status |
| Manifest | Corpus version, file hashes, schema version, extraction/chunking configuration, index settings, embedding revision if used |

- Keep source text separate from normalized search text and preserve the mapping between them.
- Use zero-based, end-exclusive Unicode code-point offsets in the interchange format; mobile adapters must convert to platform string indices.
- Store PDF boxes in unrotated page coordinates with dimensions and rotation metadata for the renderer.

- Re-extraction can change spans, so citations always include the corpus version.
- Existing repaired Markdown may be useful for retrieval but must be reconciled against original PDFs, especially numeric tables, units, age bands, and symbols.
- Quarantine unreadable or unmappable passages.
- If reliable PDF boxes are unavailable, highlight the verified extracted passage and label PDF highlighting unavailable; do not fabricate a precise overlay.

## Retrieval strategy

- The initial stage uses no embedding model.
- Follow [the healthcare accuracy plan](09-healthcare-quality.md) for lexical indexing and clinical evidence checks.
- Dense/hybrid options below are deferred experiments, not initial dependencies.
- Start lexical chunks at coherent paragraph/table boundaries with a provisional 600–1,000-character size target; preserve complete clinical conditions even when this exceeds the target.
- Embedding-tokenizer sizing below applies only if dense retrieval is later introduced.

1. Build a lexical baseline using SQLite FTS5/BM25. It is small, portable, and transparent. FTS5 exposes BM25 ranking, with better matches receiving lower scores; normalize score direction in the retriever contract. [SQLite documentation](https://www.sqlite.org/fts5.html)
2. Start with section-aware chunks of roughly 150–220 embedding-tokenizer tokens, with up to 30 tokens of overlap when needed. Preserve table headers, units, footnotes, and conditions; split long tables by rows with repeated headers. Link adjacent passages for bounded expansion.
3. Evaluate optional local dense retrieval using `sentence-transformers/all-MiniLM-L6-v2` as an English baseline. Its model card specifies 384-dimensional embeddings and a default 256-word-piece truncation limit. Count using its tokenizer so chunks are not silently truncated. Domain suitability remains an experiment. [Model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
4. For the hybrid candidate, retrieve up to 20 results from each branch, combine ranks using reciprocal rank fusion with an initial constant of 60, deduplicate, and select approximately 4–6 chunks within budget. Measure against lexical-only retrieval before adopting the additional model.
5. For a small bundle, use exact dense-vector search first. At 10,000 chunks, 384 float32 values per chunk occupy about 15.36 MB before metadata; this is an illustrative estimate, not the observed corpus size.

Do not impose a universal similarity threshold. Tune evidence gating on development data and inspect precision/coverage trade-offs. Similarity alone cannot establish that a passage answers the question.

- Source priority must be topic-specific.
- The benchmark metadata prefers applicable newer PNG/WHO updates and distinguishes national guidance from older supporting material.
- Convert this into reviewed metadata; do not assume every newer document overrides every older document.
- For unresolved contradictions, show the relevant passages and abstain from choosing a treatment instruction.

## Grounded response contract

| LLM field | Meaning |
| --- | --- |
| `status` | `answered` or `insufficient_evidence`. |
| `answer` | Answer text; empty for insufficient evidence. |
| `reason` | Brief evidence-based justification or missing-support explanation. |
| `citations` | Supplied source labels; empty for insufficient evidence. |

- The application resolves labels into stored document/chunk/passage metadata.
- Validation checks structure, citation membership and normal completion.
- Semantic support is evaluated separately; supporting quotes are not current schema fields.
- API failures remain separate from abstention. No automatic repair calls or retries.
- See [Answer generation](06-answer-generation.md) for the authoritative schema and examples.

## Source experience

The answer shows a citation beside each claim. Selecting it opens the original document page with the exact supporting passage highlighted, plus title, edition, and printed/physical page labels. Multi-passage claims can open each source. An abstention explains the evidence gap without inventing a clinical recommendation. Preserve the current answer and source selection while navigating between answer and document screens.
