# Architecture reading guide

Read the numbered files in order. Names describe each document's function; the numbers are reading order, not notebook stages.

## Pipeline

```mermaid
flowchart LR
    A[02 Corpus inventory] --> B[03 Markdown chunking]
    B --> C[04 Retrieval]
    C --> D[05 Context preparation]
    D --> E[06 Answer generation]
    E --> F[07 Answer evaluation]
    F --> G[08 Mobile deployment]
```

## Reading order

| Order | Document | What you will learn | Current state |
| --- | --- | --- | --- |
| 01 | [System overview](01-system-overview.md) | How the components fit together. | Architecture |
| 02 | [Corpus inventory](02-corpus-inventory.md) | Identify documents and check existing Markdown. | Implemented |
| 03 | [Markdown chunking](03-markdown-chunking.md) | Preserve passages, headings and citations. | Implemented |
| 04 | [Retrieval](04-retrieval.md) | Find evidence with BM25 and lexical refinements. | Implemented; accuracy gain unverified |
| 05 | [Context preparation](05-context-preparation.md) | Deduplicate and pack complete evidence groups. | Implemented |
| 06 | [Answer generation](06-answer-generation.md) | Generate answer, reason and citations through OpenRouter. | Local implementation; hosted verification pending |
| 07 | [Answer evaluation](07-answer-evaluation.md) | Measure correctness, evidence support, abstention and cost. | Documentation only |
| 08 | [Mobile deployment](08-mobile-deployment.md) | Validate offline iOS, then Android. | Planned |
| 09 | [Healthcare quality](09-healthcare-quality.md) | Understand evidence limits and critical-error review. | Cross-cutting guidance |
| 10 | [Experiment design](10-experiment-design.md) | Compare configurations and preserve measurement controls. | Includes deferred research proposals |
| 11 | [Architecture decisions](11-architecture-decisions.md) | Understand choices, trade-offs and revisit conditions. | Decision record |
| 12 | [Delivery roadmap](12-delivery-roadmap.md) | Track dependencies and later release checks. | Historical stages retained for traceability |

## Current decisions

- Use existing Markdown; separate detailed OCR auditing remains skipped.
- Use existing Q_S1/Q_S2 as the working benchmark; no new preparation/split prerequisite.
- Start with local SQLite BM25 and lexical refinements; embeddings remain deferred.
- Generate with `google/gemma-3-4b-it` through OpenRouter for experiments.
- The LLM answer has four fields: `status`, `answer`, `reason`, `citations`.
- Schema/citation validity does not establish clinical accuracy.
- Hosted generation does not establish offline mobile readiness.

## Where to work

- [Purpose-based notebooks](../../notebooks/README.md): runnable workflows and saved outputs.
- [Modeling documentation](../modeling/README.md): detailed build specifications and measurements.
- [Requirements](../user_requirement.md): source requirements.
- Existing `artifacts/step-*` directories retain historical names so saved evidence remains traceable.

## How to use these documents

- Start with **At a glance**, then the figure and tables.
- Files 02?07 describe the current pipeline functions.
- Files 08?12 cover deployment, quality, decisions and longer-term planning.
- Where older proposals differ, current function specifications and the decisions above govern this build.
- Documentation does not authorize new model calls, implementation or deployment.
