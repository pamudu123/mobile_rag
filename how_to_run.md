# How to run

Desktop RAG experiment. Answers come from the local clinical documents, not the web. Valid JSON is not medical proof.

## 1. Clone

```powershell
git clone https://github.com/pamudu123/mobile_rag.git
cd mobile_rag
```

## 2. Setup

Need:

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- An [OpenRouter](https://openrouter.ai/) key only if you want live model answers

Install:

```powershell
uv sync
```

For live generation, create a `.env` in the project root (or `src/mobile_rag/.env`):

```env
OPENROUTER_API_KEY=your_key
```

Do not put the key in notebooks or commit it. `src/mobile_rag/.env.example` is a template and is never loaded.

Check the install:

```powershell
uv run pytest
```

## 3. Run a sample

From the repo root. Dry-run retrieves evidence and builds a request. No model call, no API spend:

```powershell
uv run python notebooks/answer_generation/run_answer_generation.py --output-root artifacts/05_answer_generation
```

Live sample (uses the OpenRouter key and spends credits):

```powershell
uv run python notebooks/answer_generation/run_answer_generation.py --output-root artifacts/05_answer_generation --live
```

Optional:

```powershell
uv run python notebooks/answer_generation/run_answer_generation.py --output-root artifacts/05_answer_generation --question "What should I remember about bubble CPAP?" --live
```

Each run writes a new timestamped folder under the output root. Open `result.json` to check the generated answer, status, citations, and any error.

## 4. Bulk answers

Edit the flags at the top of `src/mobile_rag/batch_run.py`, then:

```powershell
uv run python -u src/mobile_rag/batch_run.py
```

Useful flags in that file:

| Flag | Meaning |
| --- | --- |
| `LIVE` | `False` = dry-run records. `True` = paid OpenRouter calls |
| `NUMBER_OF_QUESTIONS` | First N questions. `None` = all of `Q_S1.json` |
| `THINKING` | `True` / `False` loads thinking vs non-thinking generation settings |
| `RESUME_RUN_DIR` | Set to an existing run folder to continue it |

Or use `notebooks/answer_generation/05_2_bulk_answer_generation.ipynb`.

Keep `LIVE=False` until you mean to spend credits.

Answers are saved under `artifacts/05_2_bulk_answer_generation/<run>/`. Open them to check:

| File | What to check |
| --- | --- |
| `results.csv` | Spreadsheet of question, generated answer, reference answer, citations, status |
| `results.json` | Same review data in JSON |
| `records.jsonl` | Full per-question checkpoint (retrieval, context, usage, errors) |
| `summary.json` | Counts of answered / abstained / failed |

The generated answer is stored next to the reference answer. Compare those two fields; the model never sees the reference during generation.

## 5. Evaluate

Evaluation reads a saved bulk run. It does not call the model and it does not score clinical correctness. It counts statuses (answered, abstained, API error) and, with annotations, retrieval/packing overlap.

```powershell
uv run python -m mobile_rag evaluate artifacts/05_2_bulk_answer_generation/<run_dir> --output artifacts/eval.json
```

Optional gold chunks for retrieval metrics:

```powershell
uv run python -m mobile_rag evaluate artifacts/05_2_bulk_answer_generation/<run_dir> --output artifacts/eval.json --annotations annotations.json
```

`annotations.json` maps record keys to relevant chunk IDs, for example:

```json
{
  "Q_S1:1": { "relevant_chunk_ids": ["chunk_..."] }
}
```

## Rebuild indexes (only if needed)

A sample generation run can use an existing index under `artifacts/`. Rebuild from documents only when you change the corpus:

```powershell
uv run python notebooks/corpus_inventory/run_step.py --output-root artifacts/01_corpus_inventory
uv run python notebooks/markdown_chunking/run_step.py --output-root artifacts/02_markdown_chunking
uv run python notebooks/retrieval/run_step.py --output-root artifacts/03_retrieval_enhanced --baseline-output-root artifacts/03_retrieval_baseline
```

The first hybrid retrieval build downloads the pinned BGE encoder. Use `--no-embeddings` for BM25 only.
