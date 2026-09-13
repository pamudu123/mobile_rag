# Answer generation

Pydantic models `GroundedAnswer` in `src/mobile_rag/answer_schema.py` define the output contract. The request preview shows their generated JSON Schema. Local validation rejects extra fields, incorrect types, blank answers or reasons, unknown citations and inconsistent abstention responses.

Prepare evidence-only requests for `google/gemma-3-4b-it` on OpenRouter. The default notebook run makes no inference request and saves a request preview and setup status.

```powershell
uv sync --extra generation
uv run --extra generation python notebooks/answer_generation/run_answer_generation.py
```

For live use, set `OPENROUTER_API_KEY` in the process environment and `GEMMA_TOKENIZER_DIR` to a local copy of Google's `google/gemma-3-4b-it` tokenizer files, including its configuration and chat template. Obtain these through your authenticated Hugging Face account after accepting the model terms. Model weights are unnecessary. Keep credentials out of notebook cells and saved outputs. `.env` is not automatically loaded.

```powershell
uv run --extra generation python notebooks/answer_generation/run_answer_generation.py --live --question "What should I remember about bubble CPAP?"
```

Optional flags: `--index <enhanced-index-directory>` and `--tokenizer-dir <local-directory>`. Default index selection uses the latest enhanced retrieval package. The runner prepares fresh context from verified stored evidence.

Artifacts under `artifacts/answer-generation/<run>/`: `context.json`, `request_preview.json` (when ready), and `result.json`. These contain question/source text; authorization headers are never saved. Each live run sends at most one inference request. No automatic retries, model fallback or full benchmark runs.

Local template token counts are not guaranteed to equal provider counts. The configurable default reserves 512 tokens for formatting differences and 1,024 for completion within a 32,768-token budget. Oversized prompts are blocked without cutting evidence. Provider usage is recorded for comparison when available.

Valid citation labels do not prove semantic support. See [architecture and verification](../../docs/architecture/06-answer-generation.md).
