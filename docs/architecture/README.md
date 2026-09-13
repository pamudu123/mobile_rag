# Mobile RAG architecture plan

Status: proposed design; documentation only. Updated: 2026-09-13.

Use Python to establish a document-grounded RAG baseline with **`google/gemma-3-4b-it` through OpenRouter**, then carry the retrieval artifacts and answer contract into an iOS-first, Android-compatible application. Hosted generation is the experimental stage; the final on-device requirement remains a separate acceptance gate.

Latest direction: **build and evaluate a model-free lexical index first; do not create dense embeddings in the initial stage. Healthcare accuracy takes priority over latency and answer coverage.** BM25 indexing does not require an embedding model and is not semantic embedding generation. Consider embeddings later only if reviewed retrieval failures justify them.

## Reading order

Step 4 is also **skipped for now** by user decision. Use the existing Q&A as the working benchmark with correctness assumed; no review or split-preparation notebook is required. Step 5 follows the combined Step 2. Older gold-review and held-out evaluation proposals are conditional later options, not current implementation gates.

Current implementation scope: **Step 3 is merged into Step 2**, using the existing Markdown with lightweight structural checks. Detailed OCR/content auditing is deferred. See the [combined Step 2 build plan](../modeling/02-corpus-inventory-plan.md); earlier broad audit recommendations are not requirements for this notebook.

**Start with the [full step-by-step plan](06-step-by-step-plan.md).** It is the master execution and review checklist, with 15 ordered steps, deliverables, checks, and a status tracker. Review each completed step before proceeding, unless multiple steps have been explicitly authorized together.

1. [System design](01-system-design.md): scope, components, data flow, retrieval, citations, and answer behavior.
2. [Model integration and mobile path](02-model-and-mobile.md): OpenRouter configuration, failures, costs, and local inference feasibility.
3. [Evaluation and delivery plan](03-evaluation-and-delivery.md): benchmark preparation, metrics, milestones, and unresolved decisions.
4. [Architecture decisions](04-decisions.md): choices, alternatives, consequences, and revisit triggers.
5. [Healthcare accuracy and model-free retrieval](05-healthcare-accuracy.md): initial indexing, clinical evidence checks, and stricter progression gates.

## Requirements and interpretation

The source requirements are [user_requirement.md](../user_requirement.md). The current instruction fixes the experimental generator and explicitly limits this work to planning.

| Requirement | Planned response | Proof required later |
| --- | --- | --- |
| Answers only from supplied documents | Retrieve locally, supply bounded evidence, validate citations, abstain when support is insufficient | Grounding and refusal evaluation |
| Highlight source passage | Stable document/page/span identifiers with original-PDF mapping | Viewer opens the correct page and highlights the supporting text |
| Consider latency | Measure each pipeline stage, cold/warm runs, and tail latency | Reproducible timing report |
| Python experiments and OpenRouter | Local Python pipeline with a narrow hosted generation adapter | Hosted benchmark run |
| Fully on-device mobile | Replace hosted generation with an embedded runtime; local retrieval and viewing | Airplane-mode tests on physical devices |
| Prefer 1.5B-class resources | Compare measured total resource use against an explicit reference configuration | Memory, storage, speed, and thermal comparison |
| iOS first, Android also | Shared artifact formats and portable native core; platform-specific UI | Equivalent retrieval and citation behavior on both |

## Repository observations

Read-only inspection found PDF/OCR preparation scripts, Python package scaffolding, and dependencies for PyMuPDF, Pillow, and RapidOCR. The inspected package entry point imports a `rag` module that is not present; an executable RAG pipeline is not established by the current files.

There are 14 Markdown files under `data/md_docs`, while recursive inventory found 15 PDFs under `data`. Reconcile originals, duplicates, and extraction coverage before defining the corpus. Existing Markdown includes page markers, but this alone does not establish accurate PDF bounding boxes.

The benchmark filename named in the requirements is absent. Available inputs are [Q_S1.json](../../data/questions/Q_S1.json) and [Q_S2.json](../../data/questions/Q_S2.json), each describing 100 questions. Q_S2 includes deliberately unanswerable items. These are candidate evaluation assets, not automatically verified ground truth.

## Scope boundary

This plan introduces no application code, dependency changes, data regeneration, model downloads, or inference calls. All configuration values and quality targets below are proposed starting points, not measured results. Clinical content is evaluated against the frozen supplied corpus; passing that benchmark does not establish that older documents reflect current clinical practice.
