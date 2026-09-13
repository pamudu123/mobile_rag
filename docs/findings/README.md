# Mobile RAG integration handover

Prepared: 14 September 2026

This folder is the handover package for the Kotlin/Android or Swift/iOS team. It records what was implemented, what the experiments showed, the runtime contracts that must be preserved, and the exact generation prompts.

## Integration decision

Keep the generation model already present in the mobile application. Do not begin the integration by replacing or fine-tuning it. The main engineering value of this work is the system around the model:

1. retrieve a small set of source-backed passages;
2. preserve their identity and clinical qualifiers;
3. give the model only those passages and a strict task;
4. require a small structured response;
5. reject invalid citations and inconsistent answers;
6. abstain when evidence is absent or ambiguous; and
7. let the user open the cited source passage.

The model is a bounded text transformer in this design, not the source of truth. A more capable model cannot compensate for irrelevant retrieval, missing table headers, conflicting guidance, or a validator that accepts unsupported claims.

## Read in this order

- [01-findings.md](01-findings.md) — executive findings, measured evidence, limitations, and decisions.
- [02-integration-contract.md](02-integration-contract.md) — platform-neutral flow and Kotlin/Swift implementation contract.
- [03-prompts.md](03-prompts.md) — copy-ready production prompt, request format, examples, and retry feedback.
- [04-test-and-release-checklist.md](04-test-and-release-checklist.md) — parity fixtures, safety tests, device measurements, and release gates.

## Source of truth at handover

The executable Python reference is under `src/mobile_rag/`. In particular:

| Concern | Reference implementation |
| --- | --- |
| lexical retrieval and immutable index | `src/mobile_rag/retrieval.py` |
| enhanced BM25 and rank fusion | `src/mobile_rag/retrieval_enhanced.py` |
| BGE dense retrieval and hybrid fusion | `src/mobile_rag/retrieval_hybrid.py` |
| deterministic evidence packing | `src/mobile_rag/context_preparation.py` |
| answer JSON contract | `src/mobile_rag/answer_schema.py` |
| prompt and generation adapter | `src/mobile_rag/answer_generation.py` |
| authoritative prompt text | `src/mobile_rag/prompts/answer_generation.md` |
| saved-run evaluation | `src/mobile_rag/evaluation.py` |

If older documents disagree with these files, use the executable implementation and this handover. At this snapshot the Python adapter requests `qwen/qwen3.5-9b`, prompt `evidence-answer/v6`, temperature `0`, and structured JSON. That hosted identifier is experimental metadata, not a requirement to replace the mobile application's existing model.

## Non-negotiable product statement

This is not yet a clinically approved decision-support system. Citation-label validation proves that a returned label exists; it does not prove that every generated claim is entailed by the cited text. Clinical review, source governance, relevance gating, claim-support validation, and physical-device testing remain release requirements.
