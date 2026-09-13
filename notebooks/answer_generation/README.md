# Answer generation

Uses OpenRouter `google/gemma-3-4b-it`. No local tokenizer or model files are required.

- Set `OUTPUT_ROOT` in the notebook to choose where artifacts are saved.
- `LIVE=False`: retrieve evidence, prepare context, validate the package and save a request preview; no API call or generated answer.
- `LIVE=True`: requires `OPENROUTER_API_KEY` in the process environment and sends one request. Do not place secrets in notebook cells. Keys are read automatically from the process environment, then the project-root `.env`, then `src/mobile_rag/.env`. `.env.example` is a template and is never loaded. Explicit function keys take precedence. Files are read at request time, so no kernel restart is needed for `.env` edits.
- Context preparation retains its character budget. `max_tokens` caps output at 1,024 by default. There is no local input-token count; provider context-limit errors return an API failure. Provider usage is retained when returned.
- Pydantic validates `status`, `answer`, `reason`, and `citations`. Valid citation labels do not prove semantic support.

```powershell
uv run python notebooks/answer_generation/run_answer_generation.py --output-root artifacts/05_answer_generation
uv run python notebooks/answer_generation/run_answer_generation.py --output-root artifacts/05_answer_generation --live
```

Optional inputs: `--question` and `--index`. Outputs in a fresh run directory: `context.json`, `request_preview.json` when ready, and `result.json`. No automatic retries or model fallback. See [architecture](../../docs/architecture/06-answer-generation.md).

## Bulk generation

Use [05_2_bulk_answer_generation.ipynb](05_2_bulk_answer_generation.ipynb) to process a question JSON file with bounded parallelism. Its configuration cell exposes:

- `QUESTION_PATH`: defaults to `data/questions/Q_S1.json`; change it for another compatible file.
- `NUMBER_OF_QUESTIONS`: a positive integer runs the first N rows; `None` runs all rows.
- `MAX_WORKERS`: number of parallel retrieval/generation workers.
- `LIVE`: `False` saves dry-run records; `True` makes OpenRouter requests.
- `OUTPUT_ROOT` and `RESUME_RUN_DIR`: new-run and explicit-resume locations.

The notebook saves a run manifest, full checkpointed JSONL records, a compact CSV, and a summary. Full records retain the benchmark row, retrieval, context, citation map, generation response, usage, timings, and configuration identities. Reference answers are saved for later evaluation but are excluded from retrieval and model prompts. No automatic API retry is performed.
