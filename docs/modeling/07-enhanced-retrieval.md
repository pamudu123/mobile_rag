# Step 7: Mobile-oriented lexical retrieval refinements

Implemented as an experimental alternative to the unchanged Step 6 baseline. No embeddings, model calls, OCR repair, or separate Step 3/4 work.

## What is built

1. Original BM25 candidate branch, plus heading-weighted BM25 (heading 3, body 1).
2. Focused-query branch removing a small explicit conversational filler list. Original terms remain in the baseline branch; negation, ages, numbers, units and clinical terms are retained by the focused filter.
3. Exact phrase and NEAR searches for focused queries of 2–8 distinct terms. These are supplementary ranking signals, not clinical interpretation or constraint enforcement.
4. Controlled CPAP expansion to “continuous positive airway pressure”, explicitly defined in `Bubble-CPAP-guidelines-2017.md`. No generated synonym dictionary or automatic ambiguous abbreviation expansion.
5. Reciprocal rank fusion: sum `1/(60 + rank)` across branches. Each chunk votes once per branch, ties resolve by chunk ID. Scores are not confidence probabilities.
6. A separate SQLite FTS5 passage index. Existing paragraphs/lists/tables remain whole. Match small units and return the original containing chunk, citations and source passages; optional existing neighbor expansion remains available.

Each chunk branch retrieves at most 40 candidates. Passage search examines at most 160 units and contributes at most 40 distinct parents. Document filtering on passages currently follows candidate selection, so a restricted document may have fewer passage candidates. Query branches and contributing ranks are returned for inspection. Individual refinements can be disabled for experiments; explicit AND search uses the baseline contract.

## Execution and evidence

Run `uv run python notebooks/retrieval/run_step.py --output-root artifacts/03_retrieval_enhanced --baseline-output-root artifacts/03_retrieval_baseline`, or execute `notebooks/retrieval/03_retrieval.ipynb`. This single workflow builds a baseline from the latest validated Step 5 bundle, then packages a verified copy plus a separate passage database under `artifacts/03_retrieval_enhanced/<run>/`. A separate Step 6 notebook or existing index is unnecessary. Hashes bind both databases; query connections are read-only.

The runner compares all 200 existing Q_S1/Q_S2 question strings and four probes. It does not use answers for retrieval or claim clinical accuracy. Outputs include ranked-ID comparisons, desktop latency/size, sample branch ablations, and one full citation/context example. Changes in ranking are not evidence of improvement. No new annotation/preparation stage is introduced.

Before selecting this over Step 6, evaluate relevant evidence coverage and regressions using the accepted Q&A, including negation, dosage/units, age restrictions, and unanswerable questions. Currently no recall, clinical correctness or safe-abstention claim is established. Lexical matching cannot enforce medical qualifiers. Context preservation guarantees stored text, not semantic completeness across source sections.

## Recorded build evidence (2026-09-13)

Fresh-kernel notebook execution completed. Ruff passed and all 9 tests passed. Artifact run: `artifacts/03_retrieval_enhanced/20260913T084506488345Z/`. Both database hashes remained unchanged during queries.

| Measure | Step 6 baseline | Enhanced experiment |
| --- | ---: | ---: |
| Desktop median search | 48.24 ms | 209.62 ms |
| Desktop p95 search | 61.64 ms | 270.19 ms |
| Database size | 54.29 MiB | 65.70 MiB total |

204 queries ran; top-five rankings changed on 199. This is a behavior comparison, not an accuracy result. The enhanced median is about 4.3 times slower in this run. Timings are one sequential desktop pass, include evidence resolution, and exclude startup verification; they are not phone or cold-start benchmarks. Per-feature ablations are saved for one demonstration query only. Keep the baseline available until evidence-quality gains justify the extra cost.

## Mobile deployment constraints

Runtime needs SQLite FTS5, tokenization, bounded SQL searches and a small rank-fusion loop; no neural retrieval runtime. The Python code is the experiment reference, not an iOS/Android integration. Port query logic and verify FTS5 availability/tokenizer parity. Measure cold/warm latency, memory, storage and energy on target phones before accepting these defaults. The extra passage index and searches have a real cost; retain the baseline when that tradeoff is unfavorable. OpenRouter answer generation remains a later, network-dependent phase.

FTS5 column weights, phrases and NEAR syntax follow the [official SQLite documentation](https://www.sqlite.org/fts5.html). The chosen weights, candidate limits and fusion constant are experimental defaults, not tuned clinical optima.
