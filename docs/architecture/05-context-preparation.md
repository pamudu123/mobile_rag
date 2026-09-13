# Context preparation

[Reading order](README.md)

## At a glance

- Input: ranked source evidence and its citation mappings.
- Output: deduplicated evidence groups within an explicit character budget.
- Whole groups are kept or omitted; source text is not silently truncated.
- Implemented with a purpose-based notebook; token-provider parity is separate.


## Technical working: validation and greedy packing

Implementation: [context_preparation.py](../../src/mobile_rag/context_preparation.py), `ContextBudget` and `prepare_context()`.

1. Validate result/index/bundle identities and successful retrieval status.
2. Resolve each supplied chunk from the open index; compare its text, passages, document, citation and metadata with the supplied record. Reject the entire package if any evidence differs.
3. Process direct hits before neighbors. A neighbor must have a valid seed relationship, and its seed must already be included.
4. Sort each group's passages by source offset. Use `(document_id, passage_id)` as the deduplication key.
5. Render new passage text once. Later groups refer to its first label; identical text from different documents remains separate.
6. Serialize the candidate group as JSON, including IDs and labels. Append it only if the complete resulting context fits. Otherwise record an exclusion and continue to later groups.

```text
evidence_allowance = max(0, total_chars - instruction_reserve
                           - answer_reserve - len(question))

Example: 20,000 - 2,000 - 4,000 - 100 = 13,900 characters
```

Budgeting counts the rendered JSON and line separators, not only source text. This is greedy selection, not an optimization for maximum evidence coverage.

### Example: shared heading

```json
{"label":"S1","source_passages":[{"passage_id":"heading_1","text":"Example heading"}]}
{"label":"S2","source_passages":[{"passage_id":"heading_1","reference":"S1"}]}
```

Abbreviated illustration only; actual groups also contain document/chunk IDs, body passages and page status. Ownership is registered only after a group fits, preventing references to omitted text.

- At least one included group: `ready`.
- Valid candidates but none fit: `budget_blocked`.
- No retrieved candidates: `empty`.
- Invalid identity or altered source evidence: `invalid_evidence`.


## Function flow

```mermaid
flowchart LR
    A[Retrieved evidence] --> B[Validate source links]
    B --> C[Deduplicate and group]
    C --> D[Pack whole groups]
    D --> E[Context and citation map]
```

Status: implemented; ready for review. This function follows retrieval. See the [notebook](../../notebooks/context_preparation/04_context_preparation.ipynb) and [run guide](../../notebooks/context_preparation/README.md).

## Purpose

Convert retrieved source evidence into a bounded, traceable context package for answer generation. Retrieval finds candidate passages; context preparation decides which source text can be supplied together within the available budget.

Pipeline: **Markdown chunking → Retrieval → Context preparation → Answer generation → Answer evaluation**.

This function runs locally without embeddings, model calls or another OCR/benchmark preparation phase. The existing Q&A remain the accepted working benchmark. Answer generation using `google/gemma-3-4b-it` through OpenRouter is a separate function.

## Inputs

- Original question and retrieval status.
- Ranked retrieval hits, including chunk IDs, document IDs, source passages, citation targets and branch-ranking evidence.
- Optional neighboring context from the existing retrieval expansion function.
- Matching index/bundle identity and an explicit context budget, with capacity reserved for instructions, the question and the generated answer.

The normal function input must not include reference answers. Retrieval scores indicate ranking, not clinical confidence.

## Behavior

1. **Validate provenance.** Reject missing or inconsistent source links and evidence from different bundles. Resolve text from stored source passages; do not reconstruct it from generated summaries.
2. **Remove duplicate source spans.** Deduplicate by document and passage identity. Keep similar text from different documents separately so source differences remain visible.
3. **Group evidence.** Keep each selected passage associated with its heading context and parent chunk. Preserve source order within a group and deterministic retrieval order across groups. Neighbor passages are supplementary evidence, not independently ranked hits.
4. **Preserve context.** Keep tables with their headers, lists with their applicable introduction when available, and explicitly linked qualifiers with the text they qualify. Do not cut through sentences, table rows or source passages to satisfy the budget. Existing structural links cannot guarantee that every clinical condition has been captured; report incomplete groups instead of claiming semantic completeness.
5. **Pack within the budget.** Add complete evidence groups in deterministic order, prioritizing direct hits before optional neighbors. Record groups excluded because they do not fit. If an oversized group cannot fit intact, omit it with a reason; do not silently truncate it or replace it with an inferred summary.
6. **Assign citations.** Give each included evidence group a short prompt label, such as `S1`, mapped to the existing document, chunk, passage and citation-target IDs. Preserve declared page references as unverified; do not invent PDF coordinates.
7. **Return the package and diagnostics.** Include rendered source context, citation mappings, included/excluded IDs, budget usage and reasons for omissions. Treat source text as evidence, never as instructions to the model.

Conflicting source statements must not be silently merged or resolved using rank. Preserve their source identities when included. Automatic clinical conflict detection is outside this initial function.

## Budget contract

Accept the total input allowance and explicit reserves as configuration rather than hard-coding a provider context limit. The final rendered package, including citation labels and headings, must fit the evidence allowance.

- Exact token budgeting requires a tokenizer compatible with the generation model and accounting for its message formatting.
- That choice must be verified during implementation.
- Until it is available, support a clearly labeled conservative character budget; do not report character estimates as exact token counts.
- Using a tokenizer does not require an embedding model.

## Output contract

| Field | Meaning |
| --- | --- |
| `question` | Original user question |
| `bundle_identity`, `index_identity` | Evidence provenance |
| `status` | `ready`, `empty`, `budget_blocked` or `invalid_evidence` |
| `context_text` | Ordered source text with citation labels |
| `evidence_groups` | Included source IDs and grouping relationships |
| `citation_map` | Prompt labels mapped to original citation metadata |
| `excluded_evidence` | Omitted IDs and explicit reasons |
| `budget` | Limit, reserves, counting method and measured usage |
| `diagnostics` | Duplicate removal, missing context and other structural limitations |

- `ready` means a structurally valid package exists; it does not mean the question is answerable.
- Empty or invalid packages must not proceed as normal grounded-answer inputs.
- The later answer-generation function must still assess whether the supplied evidence supports an answer and abstain when it does not.

## Planned implementation layout

| Location | Responsibility |
| --- | --- |
| `src/mobile_rag/context_preparation.py` | Reusable validation, grouping, packing and citation mapping |
| `notebooks/context_preparation/04_context_preparation.ipynb` | Inspect retrieval inputs, packing decisions and rendered evidence |
| `notebooks/context_preparation/run_context_preparation.py` | Headless execution of the same workflow |
| `notebooks/context_preparation/README.md` | Inputs, execution and limitations |
| `artifacts/04_context_preparation/<run>/` | Saved configuration, packages, diagnostics and checks |

These locations are implemented. Existing retrieval artifacts and the single purpose-based retrieval notebook are retained.

## Implementation decisions

- The initial implementation uses explicit character budgets (20,000 total, 2,000 instruction reserve, 4,000 answer reserve, plus the question length).
- These are configurable experiment defaults, not model limits.
- No compatible provider tokenizer/message accounting has been established in this function; exact token enforcement remains required before model requests.

- Complete parent chunks are the packing groups.
- Source passages are ordered by source offset; headings shared across chunks are rendered once and referenced by their first group label.
- Context is JSON Lines with escaped source strings.
- This formatting separates data from labels but is not a prompt-injection defense by itself.
- The generation adapter must treat all source strings as untrusted evidence.

- Every supplied hit is compared with evidence resolved from the verified read-only index before any context is emitted.
- Neighbor relationships must match the stored adjacency and section.
- Neighbors whose seed did not fit are excluded.
- The package exposes chunk flags and explicitly states that cross-chunk qualifier completeness and clinical conflict detection are unavailable.

## Completion checks

- Verification on 2026-09-13: all 10 project tests passed; Ruff passed; the notebook executed in a fresh kernel with saved outputs. [Recorded run](../../artifacts/04_context_preparation/20260913T091159118667Z/summary.json) covers normal, overlapping, budget-blocked, empty and invalid evidence.
- The normal example packed 7 groups into 6,927 rendered characters in approximately 4.96 ms on the desktop (one measurement, excluding retrieval/startup).
- Both source database hashes remained unchanged.
- Repeated packing produced identical packages.
- No clinical accuracy or phone-performance claim is established.

- Every included source span matches stored evidence and resolves through its citation label.
- Duplicate passages are removed without merging different documents or dropping their provenance.
- Tables and explicitly associated conditions remain intact; omitted groups are reported.
- Rendered context respects the configured budget, including labels and headings.
- Empty retrieval, invalid provenance and a group larger than the budget produce explicit outcomes.
- Repeated inputs and configuration produce identical packages.
- The notebook saves examples and diagnostics for normal, overlapping, oversized and empty evidence.

Measure packing latency and package size on the desktop; phone latency and memory remain later deployment checks. These checks establish engineering behavior, not clinical answer accuracy. After reviewing this function, the next proposed function is answer generation with evidence-only prompting, citation handling and insufficient-evidence behavior.
