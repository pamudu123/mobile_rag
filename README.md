# mobile_rag

Python experiment to find a configuration that can later run as an **on-device RAG system on mobile**, answering frontline healthcare questions from a small, versioned clinical corpus.

The eventual product must work **offline on iOS first, then Android**. This repository is the desktop reference: inventory documents, retrieve evidence, generate grounded answers, and compare retrieval/generation settings before anything is ported to a phone.

It is **not** a deployed clinical assistant. Valid JSON and citations do not mean the answer is medically correct.

## Goal

Health workers should be able to ask a question, get an answer **only from the supplied guidelines**, and open the exact source passage. If the documents do not support an answer, the system must abstain instead of guessing.

Constraints that drive the experiments:

- Answers come from the local corpus, not the model's training knowledge or the web.
- Latency, memory, and storage matter because the same contracts must later run on a phone.
- Prefer a ~1.5B-class on-device model (or a larger model that still fits after quantization). Hosted generation is for measurement, not the product runtime.
- Highlight the cited passage in the original source.
- Healthcare accuracy comes before answering more questions or going faster.

## What this corpus is

About 15 PNG and WHO clinical documents used by frontline workers (nurses, HEOs, CHWs, doctors). Topics include triage, child health, TB, HIV, malnutrition, oxygen therapy, and standard treatment.

Benchmark questions live in `data/questions/`:

- `Q_S1.json` — 100 clinically grounded Q&A pairs
- `Q_S2.json` — second set with answerable and unanswerable items

Reference answers are stored for later scoring. They are **never** given to retrieval or the generator.

## How the experiment is staged

Desktop Python is the reference implementation. Generation currently uses OpenRouter (`google/gemma-3-4b-it`) so retrieval, grounding, and prompts can be measured without a phone runtime. A replaceable generator interface is the handoff to an embedded model later.

```text
PDFs / Markdown  →  inventory  →  chunking  →  retrieval  →  context packing
                                                              ↓
Question  →  evidence  →  grounded JSON (status, answer, reason, citations)
                                                              ↓
                    evaluation  →  chosen config  →  iOS, then Android
```

| Stage | Status |
| --- | --- |
| Corpus inventory and Markdown chunking | Implemented |
| Lexical BM25 retrieval (SQLite FTS5) | Implemented |
| Hybrid BM25 + BGE dense retrieval | Implemented as a desktop experiment |
| Context packing and citation maps | Implemented |
| Grounded answer generation | Implemented; live calls need an OpenRouter key |
| Answer evaluation | Documented; scoring still being built |
| Offline iOS / Android | Planned |

Hosted results do **not** prove on-device quality, latency, or memory.

## Grounding contract

The model returns four fields:

| Field | Meaning |
| --- | --- |
| `status` | `answered` or `insufficient_evidence` |
| `answer` | Answer text; empty when evidence is missing |
| `reason` | Short justification, or why the system abstained |
| `citations` | Labels from the supplied evidence only |

Application code resolves those labels to document, page, and passage. Invalid citations, extra fields, and mixed answered/abstention shapes are rejected. API or setup failures are separate from abstention.

## Retrieval configurations under test

BM25 and embeddings can be switched independently. Both-off is rejected.

| BM25 | Embeddings | Mode |
| --- | --- | --- |
| On | On | Hybrid (default): reciprocal rank fusion |
| On | Off | Lexical only; no encoder needed |
| Off | On | Dense only |

Dense search uses a pinned `BAAI/bge-small-en-v1.5` ONNX encoder on CPU. Compare modes on the same frozen corpus and question IDs; a different ranking is not automatically a better ranking.

## Repository layout

```text
data/                 Clinical Markdown and benchmark questions
src/mobile_rag/       Retrieval, context, generation, evaluation
notebooks/            Ordered experiment notebooks and headless runners
artifacts/            Timestamped run outputs (indexes, contexts, answers)
docs/architecture/    Design, decisions, and mobile plan
tests/                Unit tests for contracts and pipeline helpers
```

Notebooks to run in order:

1. [Corpus inventory](notebooks/corpus_inventory/01_corpus_inventory.ipynb)
2. [Markdown chunking](notebooks/markdown_chunking/02_markdown_chunking.ipynb)
3. [Retrieval](notebooks/retrieval/03_retrieval.ipynb) and [hybrid sanity](notebooks/retrieval/03_2_hybrid_sanity.ipynb)
4. [Context preparation](notebooks/context_preparation/04_context_preparation.ipynb)
5. [Answer generation](notebooks/answer_generation/05_answer_generation.ipynb) and [bulk run](notebooks/answer_generation/05_2_bulk_answer_generation.ipynb)

Each notebook folder has a README and a script runner. Outputs go under `artifacts/` in a new timestamped directory.

## Setup

Python 3.11+. [uv](https://docs.astral.sh/uv/) is the package manager.

```powershell
uv sync
```

Live generation needs `OPENROUTER_API_KEY`. Put it in the process environment, a project-root `.env`, or `src/mobile_rag/.env`. Do not put keys in notebooks or commit them. `src/mobile_rag/.env.example` is a template and is never loaded.

```env
OPENROUTER_API_KEY=your_key
```

## Run

Dry-run a single question (retrieves and packs evidence; no model call):

```powershell
uv run python notebooks/answer_generation/run_answer_generation.py --output-root artifacts/05_answer_generation
```

Live single question:

```powershell
uv run python notebooks/answer_generation/run_answer_generation.py --output-root artifacts/05_answer_generation --live
```

Build dense vectors for an existing lexical index (first run downloads the pinned BGE model):

```powershell
uv run python -m mobile_rag build-dense --index artifacts/03_retrieval_enhanced/<run_dir> --output-root artifacts/03_retrieval_enhanced
```

Tests:

```powershell
uv run pytest
```

Bulk answer generation is `notebooks/answer_generation/05_2_bulk_answer_generation.ipynb` or `src/mobile_rag/batch_run.py`. Set `LIVE=False` until you intend to spend API credits.

## What “good configuration” means here

Keep the corpus hash, question IDs, prompt, and model fixed. Change one component at a time (retrieval mode, context budget, generation settings). Save every outcome, including failures.

A configuration is a candidate for mobile only if it:

1. Retrieves the passages that actually support the question.
2. Answers from those passages, or abstains when they are not enough.
3. Preserves clinical qualifiers (age bands, doses, units, negation, exceptions).
4. Stays within a budget that a phone could later meet.

See [experiment design](docs/architecture/10-experiment-design.md) and [healthcare quality](docs/architecture/09-healthcare-quality.md).

## Docs

- [User requirements](docs/user_requirement.md)
- [Architecture reading guide](docs/architecture/README.md)
- [System overview](docs/architecture/01-system-overview.md)
- [Mobile deployment](docs/architecture/08-mobile-deployment.md)
- [Hybrid retrieval](notebooks/retrieval/HYBRID.md)

## License and use

Internal research. Do not treat generated answers as medical advice or as a substitute for current national policy, specialist review, or local escalation pathways.
