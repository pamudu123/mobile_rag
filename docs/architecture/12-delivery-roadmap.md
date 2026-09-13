# Delivery roadmap

[Reading order](README.md)

## At a glance

- Read files 01?07 for the current pipeline and its function contracts.
- Inventory, chunking, retrieval and context preparation are implemented.
- Answer generation is locally implemented; hosted verification is pending.
- Answer evaluation is documented; mobile deployment remains planned.
- Original stage numbers below are historical tracking references, not notebook names or new authorization.


## Technical dependency and completion logic

- Corpus changes invalidate downstream evidence identity; rebuild affected chunk/index artifacts.
- Retrieval changes require new comparisons with a fixed corpus.
- Prompt/schema changes require fresh generation records with a new identifiable configuration.
- Passing unit tests establishes tested software behavior, not clinical answer quality.
- Device readiness requires actual offline and resource evidence, not hosted timing.

Example checkpoint record: input bundle hash, implementation/configuration version, output artifact path, executed checks, known limitations and review outcome. A missing tokenizer is a setup dependency; a wrong supported answer is a quality failure. Track them separately.


## Function flow

```mermaid
flowchart LR
    A[Corpus preparation] --> B[Retrieval]
    B --> C[Context and generation]
    C --> D[Answer evaluation]
    D --> E[iOS validation]
    E --> F[Android parity]
    F --> G[Release review]
```

## How to read the detailed design

- The summary above and current function specifications describe the active scope.
- The detailed design below retains earlier proposals and rationale for traceability.
- Older OCR/gold-review/split requirements are deferred. Earlier claim-based output, retry settings and model budgets are superseded by [Answer generation](06-answer-generation.md).
- Original stage numbers do not change the purpose-based notebook layout.

Status: Steps 2, 5 and 6 implemented. Step 7 lexical refinements implemented as experiments; clinical retrieval evaluation remains pending. See the [Step 7 build note](../modeling/07-enhanced-retrieval.md).

This is the master checklist for reviewing the project one step at a time. The architecture documents explain the design; this document defines execution order, deliverables, evidence, and the decision at each checkpoint. It incorporates the user's request for stepwise review.

- Current scope update: Step 3 is merged into Step 2 and skipped as a separate build.
- Step 2 uses existing Markdown with lightweight structural checks; detailed OCR/content auditing is deferred.
- Step 4 is also skipped for now: accept existing Q&A correctness as a working assumption without additional benchmark review or split preparation.
- The [combined implementation specification](../modeling/02-corpus-inventory-plan.md) governs the first notebook.
- Keep stage numbers stable; Step 5 follows Step 2.

- Later evaluation descriptions involving reviewed gold spans or held-out splits are conditional designs, not prerequisites to the current build.
- Use the supplied Q&A for initial benchmark agreement checks.
- Do not report span-recall metrics without source annotations or independent held-out performance without a defined split.
- Reference answers stay outside retrieval inputs and normal model prompts.

## Working agreement

- Implementation authorization covers Steps 2, 5, 6 and the agreed lexical retrieval additions in Step 7. Later stages remain planning-only until authorized.
- Once a step is authorized, complete its bounded work and verification, present the evidence, and review that checkpoint with the user before beginning the next step. If several steps are explicitly authorized together, complete that scope without asking again between them.
- Mark a step complete only when its deliverables and checks are satisfied. A written plan is not implementation evidence.
- Fix failures within the active step and explain the cause. Do not silently relax a criterion or substitute a model to obtain a pass.
- Clinical review and engineering review are distinct. User acceptance of an engineering result does not substitute for qualified review of clinical content.
- Track each step as Not started, In progress, Ready for review, Accepted, or Needs revision. Record the actual date, evidence links, outstanding issues, and review outcome.

## Fixed direction

- Python experiments; `google/gemma-3-4b-it` through OpenRouter for generation; SQLite FTS5/BM25 for the initial model-free retrieval index; exact source citations and highlighting; explicit abstention; iOS first and Android next for offline deployment.
- Dense embeddings are a conditional later experiment.
- Healthcare accuracy takes priority over speed and the number of questions answered.

## Overview and current tracker

| Step | Outcome | Depends on | Status |
| --- | --- | --- | --- |
| 1 | Freeze scope and acceptance definitions | None | Not started |
| 2 | Corpus inventory and lightweight Markdown checks | 1 | Ready for review |
| 3 | Merged into Step 2 | 2 | Skipped as a separate phase |
| 4 | Use existing Q&A; preparation skipped | None | Skipped for now |
| 5 | Finalize passage, chunk, and citation contracts | 2 | Ready for review |
| 6 | Build the model-free retrieval baseline | 5 | Ready for review |
| 7 | Evaluate and refine retrieval accuracy | 6 | Not started |
| 8 | Verify evidence display and highlighting | 7 | Not started |
| 9 | Verify the OpenRouter generation adapter | 8 | Not started |
| 10 | Evaluate Gemma with known-correct evidence | 9 | Not started |
| 11 | Evaluate the complete RAG pipeline | 10 | Not started |
| 12 | Freeze the Python research prototype | 11 | Not started |
| 13 | Validate fully local iOS operation | 12 | Not started |
| 14 | Validate Android parity | 13 | Not started |
| 15 | Complete release-readiness and handover review | 14 | Not started |

This sequence is intentional: inspect source quality before retrieval, retrieval before generated answers, and hosted quality before mobile migration. Device availability and reference resource limits should be identified in Step 1 even though their full measurement occurs later.

## Step 1 — Freeze scope and acceptance definitions

**Purpose:** Agree on what the prototype must prove and what remains outside its claims.

- **Work:** Record intended users and use cases, English-first query scope, corpus-only answering, single-turn baseline, document-import expectations, and research versus intended clinical use.
- Define critical errors: wrong clinical instruction, quantity/unit, negation, population qualifier, omitted essential condition, or incorrect source precedence.
- Define which cases must abstain and which may show evidence only.
- Record available phones, operating systems, and the intended 1.5B reference model/precision/context or mark these explicitly unresolved.
- Confirm a proposed hosted-run budget before the first paid experiment.

**Deliverables:** Scope sheet, requirements-to-checks matrix, critical-error rubric, device/resource worksheet, open-decision register.

**Check:** Every requirement has a planned verification method; cloud experimentation is clearly distinguished from offline acceptance; unresolved inputs have an owner and a deadline step.

**Review:** Accept the scope and error definitions. No performance or clinical-accuracy claim is made here.

## Step 2 — Establish the authoritative corpus inventory

**Purpose:** Know exactly which documents may support answers.

- **Work:** Inventory PDFs and derived text by content hash; reconcile the observed PDF/Markdown count discrepancy rather than assuming 15 unique clinical documents.
- Identify duplicates, absent extractions, editions, publishers, scope, and review status.
- Assign stable IDs.
- Have applicable authority and topic-specific supersession reviewed; retain conflicting documents for audit but make eligibility explicit.
- Record distribution permissions for any eventual mobile bundle.

**Deliverables:** Corpus manifest, duplicate/missing-file report, document eligibility and precedence register.

**Check:** Every included document maps to an original, every exclusion has a reason, and uncertain authority is not represented as approved. No benchmark answer files enter the corpus.

**Review:** Accept the exact corpus membership; flag clinical authority questions for qualified review.

## Step 3 — Merged into Step 2; no separate build

**Decision:** Use existing Markdown. Include only readability, headings, page markers, basic table structure, and source-reference checks in the Step 2 notebook.

**Deferred:** Broad OCR diagnostics, original-PDF transcription auditing, manual review queues, and coordinate alignment. Do not perform these as a prerequisite stage for the current implementation.

**Deliverables:** Step 2's manifest and issues report; no separate Step 3 notebook or artifacts.

**Limit:** Structural checks do not establish transcription accuracy. Keep that status explicit. Targeted source checks remain part of benchmark review when needed, and verified highlighting is assessed in Step 8.

**Next:** Review the combined Step 2 results, then proceed to Step 5 when authorized. Steps 3 and 4 create no additional execution gates.

## Step 4 — Skipped; use the existing Q&A

**Decision:** Use Q_S1 and Q_S2 as supplied. Their correctness is assumed for current experiments at the user's direction; no additional review is performed now.

**Scope:** No separate notebook, gold annotation work, review queue, or split creation. Basic input loading checks occur only when needed by a later experiment. Preserve original files.

**Deliverable:** The [skip decision](../modeling/04-benchmark-preparation-plan.md); no Step 4 implementation artifacts.

**Reporting:** Results measure agreement with the supplied benchmark, not independently verified clinical correctness. Keep answers out of the retrieval corpus. Source-span metrics and independent held-out claims require evidence not established by this skipped step.

**Next:** Step 5 follows Step 2 without this preparation gate.

## Step 5 — Finalize passage, chunk, and citation contracts

Implementation specification: [Markdown chunking notebook plan](../modeling/05-markdown-chunking-plan.md). It follows Step 2 directly and uses existing Markdown without Step 3/4 audits. Oversized atomic blocks/tables are retained and flagged in the first build rather than automatically split.

**Purpose:** Preserve clinical meaning through indexing and display.

- **Work:** Define versioned Document, Page, Passage, Chunk, Citation, and Answer records using the architecture contracts.
- Form chunks at coherent paragraph/table boundaries, initially targeting 600–1,000 characters without enforcing a split that loses essential context.
- Retain headings, units, exceptions, adjacent-passage links, and original text separately from search normalization.
- Specify answer/abstention/error states and machine-readable reason codes.
- Keep dosage calculations outside scope.

**Deliverables:** Schema specification, representative records, chunk inspection report, versioning and invalidation rules.

**Check:** Every chunk resolves to source passages; no inspected clinical table loses its headers or conditions; normalization preserves source mapping; regenerated content gets a new bundle version.

**Review:** Inspect examples for prose, long tables, cross-page conditions, and repeated similar text. Accept the representation before indexing.

## Step 6 — Build the model-free retrieval baseline

- Implementation specification: [Step 6 BM25 indexing and search plan](../modeling/06-bm25-retrieval-plan.md).
- The notebook and runner are implemented; see the [build review](../modeling/06-build-review.md).
- They consume the validated Step 5 bundle without reinstating Steps 3/4 or performing answer generation.

**Purpose:** Produce searchable evidence without an embedding model or generator.

- **Work:** Build SQLite FTS5 over eligible chunk text and headings with BM25 ranking.
- Escape/tokenize user queries safely.
- Return ranked IDs, scores, and source metadata; implement deterministic tie handling and traceable neighboring-passage expansion.
- Do not infer evidence sufficiency from rank alone.
- Keep an immutable manifest for corpus, normalization, tokenizer/index settings, and build version.

**Deliverables:** Local index, retrieval entry point, reproducible build procedure, inspection output for development questions.

**Check:** Known exact terms retrieve their passages; empty/no-match queries return explicit outcomes; index rebuilds from the same inputs preserve behavior; no network or embedding dependency exists in retrieval.

**Review:** Show a question, ranked matches, complete passages, and why the top result can or cannot answer it. Record index size and build time as measurements.

## Step 7 — Evaluate and refine retrieval accuracy

**Purpose:** Prove that the needed evidence is present before asking Gemma to answer.

- **Work:** Measure recall@5/@10 and complete multi-passage evidence coverage on development data.
- Classify misses as extraction, vocabulary, chunk boundary, ranking, qualifier, or source-precedence failures.
- Compare baseline with heading weights, reviewed clinical aliases, and bounded context expansion.
- Evaluate evidence selection inside the eventual prompt budget, not just unconstrained search.
- Freeze settings and evaluate held-out retrieval without tuning against its outcomes.

**Deliverables:** Baseline/refinement comparison, per-question failure report, chosen retrieval configuration, latency and index-size report.

**Check:** Meet the diagnostic recall target in the evaluation document and fully recover required evidence on the reviewed critical subset. Every failed critical case must be resolved or explicitly excluded from the supported scope with justification. A high average cannot hide a critical miss.

**Review:** Accept the retrieval baseline or return to the failing preparation step. If failure analysis establishes persistent semantic misses, document a separate proposal to compare embeddings; do not add them automatically.

**Held-out policy:** Once test outcomes are used to change the system, label that set as exposed and use fresh reviewed topic groups for a new independent performance claim. Retain the exposed cases as regressions.

## Step 8 — Verify evidence display and highlighting

**Purpose:** Make the retrieved evidence independently inspectable before generation.

- **Work:** Provide a minimal local source viewer showing title, edition, physical/printed page, exact passage, and verified highlight.
- Support multiple sources and evidence-only responses.
- Preserve results while switching views.
- Make extraction-only highlighting explicit if PDF boxes cannot be verified.

**Deliverables:** Evidence-viewing prototype, screenshot/example set, citation navigation checks.

**Check:** Every selected citation opens the correct passage in the correct bundle; repeated phrases do not cause a wrong-page highlight; rotations and table spans are handled; invalid or stale citations are rejected.

**Review:** Inspect prose, table, multi-source, and unavailable-mapping cases. Accept the source experience.

## Step 9 — Verify the OpenRouter generation adapter

**Purpose:** Establish a measurable, controlled connection to the chosen model.

- **Work:** Refresh live model/provider metadata, pricing, and schema support; pin a supported provider and model ID.
- Configure secrets, bounded prompts, timeouts, retry limits, budget accounting, response validation, and technical-error states as specified in the model plan.
- Use benchmark material only.
- Run a small smoke set after this step is authorized; do not send all 200 questions immediately.

**Deliverables:** Adapter contract and implementation, configuration snapshot, redacted request/result evidence, actual usage/cost report.

**Check:** Exact model identity is recorded; invalid credentials, timeouts, rate limits, malformed output, and truncation remain distinguishable; no secret appears in logs; no silent provider/model/protocol fallback occurs.

**Review:** Verify one successful request and controlled failure handling, then accept the adapter. This checkpoint assesses integration, not clinical answer quality.

## Step 10 — Evaluate Gemma with known-correct evidence

**Purpose:** Isolate whether the generator can use supplied evidence correctly.

- **Work:** Supply reviewed gold passages as a diagnostic input.
- Compare exact evidence display with concise generated restatements.
- Check claim-level support, completeness, conditions, source IDs/quotes, conflict handling, and refusal on absent support.
- Tune prompts and output budgets on development cases only.
- Begin with non-streamed validated results.

**Deliverables:** Frozen prompt/answer contract, gold-evidence experiment report, reviewed error taxonomy, extractive-versus-generated comparison.

**Check:** Zero observed critical clinical errors in displayed outputs on the reviewed critical subset; all citations resolve; unsupported claims are suppressed or converted to abstention/evidence-only output. Record false abstention and incomplete answers alongside errors.

**Review:** Decide whether Gemma restatement is suitable for the next research stage. If it fails despite correct evidence, do not blame retrieval or proceed with unchecked output; retain evidence-only behavior while investigating.

## Step 11 — Evaluate the complete RAG pipeline

**Purpose:** Measure real question-to-answer performance without gold passages supplied at runtime.

- **Work:** Connect retrieval, evidence selection, prompt construction, Gemma, validation, and presentation.
- Run frozen held-out cases and the critical stress suite.
- Review clinical correctness separately from provenance validity.
- Test absent evidence, ambiguity, conflicting editions, irrelevant high-ranked results, prompt injection in documents, provider failures, and incomplete multi-part questions.

**Deliverables:** Full per-question records, reviewed scorecard, coverage/abstention results, error analysis, measured token cost and stage timings.

**Check:** Apply the healthcare gates plus the diagnostic targets. Technical errors count against completion rate. Report all unresolved critical failures; do not call the system validated merely because its JSON is correct or its citations exist.

**Review:** Compare full-RAG results with gold-evidence results and assign causes to each regression. Accept the bounded supported scope or return to the failed step.

## Step 12 — Freeze the Python research prototype

**Purpose:** Produce a reproducible and inspectable experiment before platform migration.

- **Work:** Profile cold/warm latency, memory, token budgets, and repeated runs.
- Optimize only measured bottlenecks; rerun affected quality checks after changes to evidence or prompts.
- Package pinned configuration, bundle/index hashes, dependency versions, runnable analysis, saved outputs, and a concise reproduction guide.
- Define update/rollback and artifact retention behavior.

**Deliverables:** Versioned research baseline, reproducibility report, runnable notebook/report entry points, known-limitations and supported-scope document.

**Check:** A clean environment can reproduce index construction and evaluation structure; provider variability is disclosed; saved results identify their exact inputs/configuration; no unmeasured performance claims are presented.

**Review:** Accept the hosted baseline and confirm readiness for device experiments. Hosted timing never counts as on-device timing.

## Step 13 — Validate fully local iOS operation

**Purpose:** Test the original offline requirement on a physical target phone.

- **Work:** Finalize the device, OS, reference 1.5B model/precision, context/output limits, and total resource envelope.
- Validate a pinned local Gemma artifact/runtime pair and its licensing/distribution conditions.
- Port retrieval, tokenization, answer contracts, and source viewing.
- Measure quantized quality, peak full-process memory, installed size, cold load, first-token and validated-answer latency, repeated-query energy/thermal behavior, and lifecycle handling.

**Deliverables:** iOS prototype, resource comparison with the reference model, parity report, offline test evidence.

**Check:** Fresh questions work in airplane mode after installation; retrieval, generation, validation, and citations require no server; quality gates still hold; resource limits are met under repeated use, memory pressure, cancellation, and background/resume.

**Review:** Accept Gemma on the target device or record a decision to evaluate a smaller local model. A hosted Gemma pass does not force acceptance of a failing local model.

## Step 14 — Validate Android parity

**Purpose:** Confirm the shared design works on the second required platform.

- **Work:** Integrate the same versioned corpus/contracts with the Android runtime and viewer.
- Check tokenization, retrieval order, citations, quantized generation quality, memory/latency, offline execution, and lifecycle behavior on the selected physical phone.
- Investigate differences rather than assuming native-runtime equivalence.

**Deliverables:** Android prototype, platform comparison, device-specific limitations, offline and resource evidence.

**Check:** Both platforms satisfy the agreed supported scope and device-specific resource gates with the same source bundle; any tolerances are declared and tested.

**Review:** Accept Android parity or narrow the documented supported device set based on evidence.

## Step 15 — Complete release-readiness and handover review

**Purpose:** Separate a completed research prototype from a product ready for its intended healthcare setting.

- **Work:** Consolidate all checkpoint evidence, source-review dates, supported questions/devices, unresolved failures, dependency/model versions, reproducibility instructions, and corpus update/rollback procedures.
- Assess the requirements of the actual intended deployment with the appropriate clinical and organizational reviewers.
- Define how users report incorrect answers and how affected documents/configurations are withdrawn and retested.

**Deliverables:** Final evidence dossier, operating guide, supported-scope statement, maintenance plan, and explicit research-only or deployment-readiness decision.

**Check:** No unresolved critical issue is hidden by averages; documents and benchmark labels have the required review; claimed functionality has actual evidence on both platforms. Any unavailable external review remains an explicit outstanding item.

**Review:** Accept the completed research deliverable, or identify specific remaining work for the intended deployment. A finite benchmark pass is not a universal healthcare-accuracy guarantee.

## Standard checkpoint report

Every step review should present the same compact record:

| Field | Required content |
| --- | --- |
| Step and status | Number, name, actual completion/review state |
| Scope completed | Concrete changes and deliverable links |
| Inputs | Corpus, benchmark, configuration, and versions used |
| Evidence | Checks run, examples inspected, measured results with denominators |
| Failures | Root cause, impact, remediation, unresolved items |
| Decision | Ready for review, accepted, or needs revision; never assume acceptance |
| Next step | Exact next bounded scope and dependencies |

- Proposed future evidence location: `docs/checkpoints/step-NN/` for review reports and `artifacts/step-NN/` for versioned or access-controlled machine outputs.
- These directories are not created by this planning document.
- Large artifacts should be referenced by hash/location rather than indiscriminately committed.

## Next review

Start with **Step 1: scope and acceptance definitions**. Review the intended use, error rubric, initial corpus-only behavior, device/resource assumptions, and experimental budget. Until implementation is requested, this remains a planning review and creates no executable system artifacts.
