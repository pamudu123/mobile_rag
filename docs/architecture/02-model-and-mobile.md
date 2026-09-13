# Model integration and mobile path

## Hosted experimental configuration

The user-selected generator is exactly **`google/gemma-3-4b-it`**. Do not silently substitute the free variant or another model. The OpenRouter listing checked on 2026-09-13 reports a 131,072-token context window and prices of $0.05 per million input tokens and $0.10 per million output tokens. These are a dated planning snapshot; endpoint availability and prices must be refreshed before running. [OpenRouter model listing](https://openrouter.ai/google/gemma-3-4b-it)

| Setting | Proposed value or policy |
| --- | --- |
| API | `https://openrouter.ai/api/v1/chat/completions` |
| Authentication | Environment-supplied API key; never included in artifacts or prompts |
| Model | `google/gemma-3-4b-it` |
| Temperature | 0 for the initial baseline; not a determinism guarantee |
| Input budget | 4,096 total tokens, including instructions, question, and evidence |
| Output budget | 512 tokens initially; track truncation and revise on development data |
| Tools / web plugins | Disabled; evidence comes from the local corpus |
| Output shape | Prefer schema-constrained JSON when verified on the selected endpoint; validate locally regardless |
| Streaming | Off for the first scored baseline; assess buffered streaming separately |
| Concurrency | 1 initially for interpretable latency and rate-limit behavior |

OpenRouter uses a Chat API-style request/response schema and bearer authentication. Schema features depend on model/provider support. Capture the selected endpoint's supported parameters before each run and fail preflight if required capabilities are missing. A separately labeled prompt-only JSON experiment is possible, but do not silently switch protocols within a benchmark. [API reference](https://openrouter.ai/docs/api_reference/overview)

Keep tokenization and chat-template accounting explicit. Trim low-ranked evidence before making a request, never remove its citation labels or detach table qualifiers. The small context budget is intentional for later mobile comparisons, despite the larger hosted limit.

## Routing, failures, and data handling

For comparable experiments, pin a provider supported by the model at execution time and disable provider fallback. Record endpoint/provider identity, requested and returned model, request ID, supported parameters, prompt version, timestamps, finish reason, and usage. OpenRouter supports provider preferences and policies including fallback and data collection controls. Configure these deliberately and record the effective policy. [Provider routing documentation](https://openrouter.ai/docs/guides/routing/provider-selection)

Initial application policy: 10-second connection timeout, 45-second total request deadline, at most one retry for a transient connection error, 429, or 5xx when it fits the deadline. Respect Retry-After; if it exceeds the remaining budget, return an error. Do not retry authentication/configuration errors or malformed model content automatically. A timed-out request can still incur charges; report retries and costs separately.

Only the question and selected excerpts leave the machine. Use benchmark questions for the initial experiment, excluding real patient information. Keep raw prompts in access-controlled local evaluation artifacts only when needed; ordinary logs retain IDs, hashes, timings, and usage. Do not embed a developer OpenRouter key in a shipped mobile binary. A future cloud-enabled mobile mode would require a separate authenticated service and explicit product scope; it is not the offline design.

At the snapshot prices, an illustrative 4,000-input/400-output-token request costs $0.00024; 200 such requests cost $0.048 before retries and additional runs. Compute actual spend from returned usage and current pricing. Adopt an initial experiment cap of $1 with a preflight estimate and incremental accounting; this is a proposed budget, not authorization to run now.

## Moving to mobile

Gemma 3 4B is a hosted quality baseline, not evidence that a quantized local variant fits 1.5B-class resources. Google's model card documents the model family and its context capabilities; local performance still depends on the runtime, quantization, and device. [Gemma 3 model card](https://ai.google.dev/gemma/docs/core/model_card_3)

The nominal weight-only calculation for 4 billion parameters at 4 bits is approximately 2.0 GB decimal, compared with 0.75 GB for 1.5 billion at 4 bits. Actual artifacts include additional tensors and quantization overhead; resident memory also includes KV cache, runtime buffers, embeddings, retrieval, and UI. Comparing a 4B quantized model with a higher-precision 1.5B model can reverse a weight-only comparison. Therefore define the reference precision, context, hardware, and total memory budget before claiming equivalence.

Proposed implementation path after authorization:

| Area | Experimental stage | Mobile stage |
| --- | --- | --- |
| Orchestration | Python 3.11+ | Small portable C++ core where sharing adds value |
| User interface | Minimal local evaluation/source viewer | Swift/SwiftUI on iOS; Kotlin/Compose on Android |
| Generation | OpenRouter adapter | Embedded runtime adapter |
| Text index | SQLite FTS5 | Same schema; verify FTS5 build availability |
| Dense retrieval | Optional local embedding model and exact search | Only if tokenizer/runtime parity and resource gates pass |
| Knowledge | Versioned local bundle | Bundled/downloaded once, then used offline |
| Citations | Passage IDs and source spans | Same contract with platform PDF rendering |

Evaluate llama.cpp first as the shared generation-runtime candidate because its C/C++ implementation, Apple acceleration, and quantization support align with the portability goal. Pin and test the exact Gemma artifact/runtime pair on both targets; broad runtime support does not establish device compatibility. LiteRT-LM is an alternative to assess if conversion or performance warrants it. [llama.cpp project](https://github.com/ggml-org/llama.cpp), [LiteRT-LM documentation](https://developers.google.com/edge/litert-lm)

Reuse the corpus, chunk IDs, precedence rules, prompts, and evaluation cases. Reimplement only the platform execution layers as needed. Verify embedding vectors and retrieval ranking against Python fixtures if the dense path is retained; record tolerances and tokenization differences.

Run quantized Gemma on physical iOS first, then Android. Compare it with a separately selected approximately 1–1.5B local reference at fixed context and output budgets. Measure peak process memory, artifact size, cold load, time to first token, total validated-answer latency, sustained throughput, battery, and thermal degradation. If Gemma fails the reference resource envelope, retain it as the hosted baseline and evaluate a smaller local generator; do not declare the on-device requirement satisfied.

Offline acceptance includes fresh questions after installation in airplane mode, no network dependency for embeddings/generation/citations, cancellation, app background/resume, memory pressure, and repeated queries. Install/update bundles atomically with hash/schema verification, keeping the previous working version until the replacement is valid.
