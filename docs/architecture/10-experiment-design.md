# Experiment design

[Reading order](README.md)

## At a glance

- Current evaluation design is 07-answer-evaluation.md.
- Freeze inputs and configurations; compare like-for-like runs.
- Keep lexical baseline comparisons; embeddings remain conditional.
- Gold annotation, grouped splits and earlier numeric targets below are deferred proposals.
- Do not report gold-span recall or independent held-out accuracy without the necessary evidence.


## Technical comparison logic

**Planned evaluation controls:** compare one changed component at a time where possible.

```text
Fixed: benchmark hash, corpus hash, question IDs, model, provider, prompt
Variant A: baseline retrieval
Variant B: enhanced retrieval
Compare: per-question evidence, reviewed quality, failures, latency, storage
```

- Save complete records for both variants, including failures.
- Compare on matching question IDs; report any missing pairs.
- A changed top-five ranking is a behavior difference, not automatically an improvement.
- Once results influence tuning, describe subsequent scores on those questions as development results.


## Function flow

```mermaid
flowchart LR
    A[Freeze inputs] --> B[Run configuration A and B]
    B --> C[Record every outcome]
    C --> D[Review quality and cost]
    D --> E[Choose or investigate]
```

## How to read the detailed design

- The summary above and current function specifications describe the active scope.
- The detailed design below retains earlier proposals and rationale for traceability.
- Older OCR/gold-review/split requirements are deferred. Earlier claim-based output, retry settings and model budgets are superseded by [Answer generation](06-answer-generation.md).
- Original stage numbers do not change the purpose-based notebook layout.

All stages below are future work after implementation is authorized. No experiments were run as part of this planning task.

Use the [full step-by-step plan](12-delivery-roadmap.md) as the authoritative execution order and checkpoint tracker. The stages below are an overview; the master plan expands them into individually reviewable steps and places evidence viewing before generated-answer evaluation.

## Benchmark preparation

- **Current scope override:** Step 4 is skipped.
- Use Q_S1/Q_S2 unchanged, with correctness assumed per the user.
- The review, gold-annotation, and grouped-split procedures below are deferred options, not prerequisites.
- Initial results must be labeled agreement with the supplied benchmark; source-span metrics and independent held-out claims remain unavailable without their required annotations/splits.
- Keep answers outside runtime retrieval and ordinary generation evidence.

- Use the available Q_S1 and Q_S2 files as candidate inputs.
- Verify counts, IDs, encodings, topic overlap, and source labels programmatically during implementation.
- Q_S2's generator describes 35 answerable and 15 unanswerable topics, each with two question variants; verify that the committed JSON agrees before reporting denominators.

- Resolve each source-of-truth string to a document ID, physical page, printed label, and gold passage.
- Review answers against original pages, with particular attention to tables, age conditions, quantities, units, and document precedence.
- A generated question's “Not in corpus” label also needs review across the whole corpus.
- Preserve disagreements as benchmark issues instead of changing labels to match the system.

- Group paraphrases and overlapping topics across both sets before splitting.
- Allocate roughly 60% of topic groups to development and 40% to held-out evaluation, balancing answerability and categories where feasible.
- Freeze the split manifest and hashes.
- Do not simply use Q_S1 for tuning and Q_S2 as an independent test without checking overlap.
- Keep question files and reference answers outside the retrieval index and model evidence.

- Add reviewed cases for absent guidance, misleading premises, incomplete multi-part questions, conflicting editions, numeric/table evidence, ambiguous patient qualifiers, OCR corruption, and document prompt injection.
- Keep synthetic stress results separate from the original benchmark.
- If multilingual use is requested, add language-specific tests before choosing a multilingual retriever.

## Experimental sequence

| Experiment | Purpose | Controls |
| --- | --- | --- |
| E0: corpus and gold audit | Establish reliable source mapping | Frozen PDFs and reviewed annotations |
| E1: lexical retrieval only | Measure retrieval independent of generation | Fixed chunking; recall at 5 and 10 |
| E2: lexical refinement | Test reviewed aliases, headings, and adjacent-passage expansion | Same corpus and held-out split; no embeddings |
| E2b: deferred dense/hybrid comparison | Investigate persistent semantic retrieval failures only if justified after E2 | Separate experiment decision and frozen evaluation protocol |
| E3: Gemma with gold evidence | Isolate generator/grounding limitations | Gold passages used only in this diagnostic |
| E4: end-to-end Gemma RAG | Measure actual answer and abstention behavior | Selected retrieval configuration, frozen prompt/provider |
| E5: local mobile comparison | Measure quantization and device effects | Same questions and evidence budgets |

- Use development data to choose chunk size, evidence count, thresholds, and output budget.
- Freeze settings before held-out scoring.
- Repeat latency measurements at least three times per selected case, with cold and warm runs reported separately.
- Repeated paraphrases and repeated calls are not independent samples; report topic-level aggregates and uncertainty where sample counts permit.

## Metrics and proposed gates

- These are initial diagnostic targets for the research prototype, not observed results or permission for healthcare deployment.
- Report numerators/denominators as well as percentages.
- The stricter [healthcare accuracy gates](09-healthcare-quality.md) take precedence for clinical-answer display and progression beyond research evaluation.
- An aggregate score cannot excuse a critical clinical error.

| Metric | Definition | Proposed gate |
| --- | --- | --- |
| Evidence recall@5 | Answerable cases with required gold evidence in top five; also report full multi-passage coverage | At least 90% case coverage |
| Citation integrity | Returned citations resolve to exact source passages in the bundle | 100% for displayed answers |
| Claim support | Reviewed factual claims fully supported by cited evidence | At least 95%; separately list every unsupported claim |
| Answer correctness | Answerable cases with correct required facts and qualifiers | At least 90% under reviewed rubric |
| Unanswerable abstention | Reviewed unanswerable cases receiving abstention | At least 95% |
| False abstention | Answerable cases incorrectly refused | At most 15% |
| Critical numeric errors | Wrong dose, unit, threshold, age/weight qualifier in displayed answers | Zero observed on the frozen set; any occurrence blocks progression |
| Local retrieval latency | Warm retrieval plus evidence selection, excluding generation | p95 at most 500 ms initially |
| Hosted validated-answer latency | Submit to fully validated result, including retrieval/network | Warm p95 at most 15 s initially |
| Mobile resources | Measured peak total memory, storage, latency, and sustained operation | Within the agreed 1.5B reference envelope on both target devices |

- A low false-answer rate can be achieved by refusing everything, so always report answer coverage, correct-answer rate, and selective accuracy together.
- Score technical failures separately and include them in overall completion-rate denominators.
- Citation string validity is not a substitute for semantic support.
- Clinical answer review should use a suitably qualified reviewer; an LLM judge may assist triage but should not be the only authority.

## Measurement and artifacts

- Record ingestion time separately from per-query latency.
- Per query record question normalization, embedding, lexical/dense search, fusion, evidence selection, prompt tokenization, network/generation, validation, and total wall time.
- If streaming is later enabled, distinguish first received token from first validated visible answer; never display unvalidated partial clinical guidance merely to improve latency figures.

- Each run should produce a configuration manifest, environment/runtime versions, corpus and benchmark hashes, per-question retrieved IDs/scores, evidence and response records, validation outcomes, usage/cost, timing distributions, and an error analysis.
- Keep secrets out of artifacts.
- Save plots/tables and a readable report; later notebooks can provide runnable analysis entry points with saved outputs.

## Delivery stages and exit criteria

1. **Corpus and benchmark readiness.** Reconcile 15 PDFs versus 14 extracted documents, locate or explicitly replace the missing benchmark reference in future requirements maintenance, map pages/spans, review OCR and gold evidence. Exit: a frozen corpus manifest and auditable test annotations.
2. **Retrieval baseline.** Build local lexical retrieval and citation navigation; evaluate lexical refinements first. Dense/hybrid comparison is conditional on persistent, reviewed retrieval failures. Exit: retrieval report meeting the coverage target or a documented failure analysis before generation tuning.
3. **Hosted Gemma experiment.** Add the narrow OpenRouter adapter, bounded prompt, response validation, and failure accounting. Exit: gold-evidence and full-RAG reports, measured cost/latency, no unresolved critical numeric errors.
4. **Source-viewing prototype.** Implement the answer-to-passage interaction and error/abstention states. Exit: reviewed examples covering PDF highlighting, multi-source answers, invalid mappings, and conflicts.
5. **iOS feasibility.** Freeze target phone and reference model configuration; evaluate an embedded Gemma artifact and portable retrieval. Exit: measured offline quality/resource comparison, with an explicit continue-or-smaller-model decision.
6. **Android parity.** Use the same bundle and contracts on the target Android phone. Exit: equivalent evidence resolution, acceptable quality/resource results, and offline/lifecycle tests on both platforms.

## Decisions still needed before their dependent stage

| Open item | Planning assumption | Resolve by |
| --- | --- | --- |
| Target phones, RAM and minimum OS | Physical iOS first, then Android; no device performance claim yet | Stage 5 |
| Meaning of 1.5B-class resources | Fixed reference model, precision, context, and measured full-process envelope | Stage 5 |
| Corpus membership and authority | Only supplied, reviewed editions are indexed | Stage 1 |
| Query language | English baseline based on current question sets | Stage 2 |
| Embedding value and export parity | Lexical baseline always available; dense path must earn its cost | Stages 2 and 5 |
| Cloud provider policy | Fixed supported provider with explicit data settings | Stage 3 |
| Clinical reference review | Benchmark statements need source and domain review | Stage 1 |

No implementation schedule is asserted without device access and review availability. Work proceeds in dependency order, with each stage producing evidence for the next.
