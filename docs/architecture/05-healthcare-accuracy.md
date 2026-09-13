# Healthcare accuracy and model-free retrieval

Status: planning only. This document incorporates the user's clarification that healthcare accuracy is the priority and an approach without embedding models is preferred. Where earlier exploratory options differ, this document governs the initial stage.

## First build an index, not dense embeddings

Plan the first implementation around **SQLite FTS5/BM25 over reviewed source passages**, without a separate embedding model. This is an inverted text index: terms point to passages and a ranking function orders the matches. TF-IDF could also create sparse numeric representations without a learned embedding model, but no separate TF-IDF matrix is needed for the proposed BM25 baseline. [SQLite FTS5 documentation](https://www.sqlite.org/fts5.html)

Neither lexical nor dense retrieval is inherently accurate enough for healthcare. Lexical search can match precise terminology yet miss paraphrases; dense search can retrieve related passages that do not support the requested action. Decide from reviewed gold-passage coverage, qualifier preservation, and false-answer behavior on this corpus.

The initial indexing plan is:

1. Inventory and version the original documents. Identify their scope, edition, applicability, and reviewed supersession relationships before indexing.
2. Audit extraction against PDFs. Preserve negation, inequality symbols, decimals, units, age/weight ranges, table headings, row relationships, footnotes, and referral conditions. Do not let automated text repair silently alter clinical meaning.
3. Index coherent passages with title, heading, body, document ID, and physical/printed page metadata. Link neighboring passages so a retrieved treatment statement can include its eligibility conditions and exceptions.
4. Search original terms first, then perform a separate expanded search using a small reviewer-approved alias table. Merge results while preserving original-query matches. Store expansion provenance for evaluation.
5. Rank titles/headings and body matches with development-tuned weights. Preserve and compare clinical qualifiers rather than treating them as disposable stopwords. Do not turn a weak match into confidence merely because it ranks first.
6. Inspect the evidence for the specific population, condition, requested action, and applicable edition. If a required qualifier is missing or contradictory, request clarification or abstain rather than selecting a superficially similar passage.

Aliases may cover abbreviations or spelling variants, but ambiguous abbreviations must retain their ambiguity. Do not use Gemma to invent medical synonyms at query time. Do not equate drug names, formulations, strengths, or therapeutic classes without reviewed mappings. No comprehensive clinical ontology is assumed to exist in this repository.

## Evidence-first answering

For the first healthcare prototype, prefer **extractive evidence display**: show a short exact passage with its context and source location. Gemma may produce a concise, cited restatement for research comparison, but only after the retrieval baseline is audited. For numeric treatment instructions, exact quotation with complete conditions is the initial default. Do not introduce dose calculations or infer missing patient-specific inputs.

Separate these outputs in evaluation:

| Output | What it establishes | What it does not establish |
| --- | --- | --- |
| Retrieved source passage | The system located a particular document span | That it applies to the question or current practice |
| Exact quote and highlight | Displayed words and location match the source | That the source is authoritative or interpreted correctly |
| Generated answer | The model produced a readable response | Clinical correctness or complete source support |
| Reviewed supported answer | The cited evidence supports the reviewed claims and conditions | General reliability outside the evaluated cases |

Every displayed generated claim must be supported, and its references must resolve. If automated checks cannot establish support for a high-risk statement, use the verified evidence-only view or abstain. A prompt, JSON schema, exact-quote check, or second LLM is insufficient by itself to guarantee clinical correctness.

Corpus fidelity and current clinical accuracy are separate evaluation axes. A perfectly cited answer can faithfully repeat outdated guidance. Before any intended healthcare use beyond this research experiment, the document set and topic-specific precedence must receive qualified clinical review; record review date and scope. Do not use the model's background knowledge to silently update a source.

## Accuracy gates take precedence over aggregate scores

The available files contain 100 questions in Q_S1 and 100 in Q_S2; current JSON inspection found 30 Q_S2 items categorized as unanswerable. Source accuracy and answerability labels still require review. Group related questions across both sets before holding out evaluation cases.

For the reviewed critical subset, require:

- Complete supporting evidence for every required clinical instruction, including its conditions and exceptions. Any missing required passage triggers analysis before progression.
- Zero observed unsupported clinical instructions, incorrect quantities/units, reversed negations, or wrong population qualifiers in displayed answers. Any such error blocks progression until its cause is addressed and the affected tests rerun.
- Every displayed citation resolves to the exact supporting span; every required claim has a citation. Wrong-source and outdated-source errors are reported separately from invalid links.
- Abstention on every reviewed critical case where applicable evidence is absent, unresolved, contradictory, or unreadable. Record false abstentions separately so refusing everything cannot count as success.
- Qualified review of clinical correctness and completeness; model-based scoring is supplementary. Report all failures and denominators, not only averages.

These are finite-test gates, not a claim of 100% real-world accuracy. They do not replace a broader evaluation for the intended clinical setting. Keep uncertain answers out of the generated-answer view even if aggregate targets pass.

## When to consider embeddings

Only open a dense-retrieval experiment after error analysis shows that relevant passages are consistently missed because of vocabulary/paraphrase differences despite reviewed lexical refinement. Compare lexical and hybrid candidates on identical held-out topic groups, including hard negatives and conflicting clinical conditions. Require improved complete-evidence recall without increased misleading-evidence selection or unsafe generated answers, and measure mobile resource cost.

The decision sequence is therefore: **source review → model-free indexing → retrieval accuracy evaluation → evidence display → Gemma answer evaluation → optional retrieval changes → mobile validation**. Speed optimizations must not remove context needed for clinical accuracy. No code or embeddings are created during this planning phase.
