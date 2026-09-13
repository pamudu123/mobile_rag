# Step 3: Existing Markdown validation and source mapping

Status: documented proposal; implementation not started.

## Purpose and numbering

Build `notebooks/03_markdown_validation.ipynb` after the relevant inventory inputs from Step 2 are available and implementation is authorized. Use the existing Markdown documents as the text inputs; use original PDFs only to verify source fidelity and citation locations. No OCR or PDF-to-Markdown conversion is planned.

This follows **Step 3: Validate extraction and source coordinates** in the [architecture master plan](../architecture/06-step-by-step-plan.md). The preceding conversation mentioned chunking as the next preparation task; under the existing numbering, benchmark review is Step 4 and final passage/chunk contracts are Step 5. This notebook prepares auditable source blocks for those steps; it does not build retrieval chunks or an index.

## What we will implement

1. Load a selected Step 2 manifest and check that its Markdown/PDF hashes still match the files being reviewed.
2. Parse existing Markdown headings, page markers, paragraphs, lists, and tables while preserving the original text and offsets.
3. Run structural and text-quality checks that identify candidates for review.
4. Build a source-review queue focused on tables, numeric statements, conditions, and suspicious extraction artifacts.
5. Present Markdown passages alongside the relevant original PDF page when its mapping is known.
6. Record reviewed source fidelity, defects, and citation-location status separately.
7. Export source-block records, a review ledger, issues, and coverage statistics for the next steps.

Automated flags are evidence to inspect, not proof of an OCR error. A successful notebook run is not a clinical-content approval.

## Inputs


| Input                                                      | Use                                                           |
| ---------------------------------------------------------- | ------------------------------------------------------------- |
| `data/md_docs/`                                            | Existing source text; read without modification               |
| Selected `artifacts/step-02/<run-id>/corpus_manifest.json` | File identities, hashes, pairings, and known inventory issues |
| Matched originals from `data/pdf_docs/`                    | Visual/source-coordinate verification where available         |
| Optional prior Step 3 review ledger                        | Resume reviews only when source hashes still match            |


The inventory remains a prerequisite; do not fabricate an accepted Step 2 result. Missing or ambiguous PDF pairings can still receive Markdown structural checks, but source fidelity and PDF mapping remain unverified. Do not guess a source file from a similar title.

Benchmark answers are not loaded into source text or used to rewrite the Markdown. Source locations established during Step 4 can be added to the review queue later. Step 3 can begin before that annotation exists; final review coverage of benchmark-supporting passages is checked after Step 4 identifies them. This avoids making Step 3 depend on gold annotations that do not yet exist.

## Planned notebook sections


| Section              | Work                                                                                   | Visible output                                         |
| -------------------- | -------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| Scope and provenance | Select inventory run, resolve paths, verify hashes and environment                     | Input summary and stale-input failures                 |
| Markdown structure   | Identify heading paths, physical-page markers, blocks, tables, and original offsets    | Per-document structure summary                         |
| Automated flags      | Check encoding artifacts, broken structures, and potentially damaged clinical notation | Issues table with exact excerpts                       |
| Review queue         | Select all flagged blocks, high-risk candidates, and a reproducible additional sample  | Prioritized, deduplicated queue with selection reasons |
| Source comparison    | Show the selected text and mapped PDF page                                             | Reviewable side-by-side or sequential comparison       |
| Review ledger        | Load/record explicit human findings without inventing reviewer decisions               | Reviewed, pending, defective, and unmapped cases       |
| Source mapping       | Record physical/printed page labels and verified text regions                          | Mapping status and highlight readiness                 |
| Validation/export    | Check records, source immutability, and output consistency                             | Artifact links and named checks                        |
| Checkpoint           | Summarize actual coverage and unresolved cases                                         | Build-review report for user review                    |


Keep simple reusable parsing helpers inside the notebook initially. Inspect available packages before adding dependencies; use the existing PyMuPDF dependency for source-page rendering and available text coordinates. A lightweight Markdown parser may be added if needed to handle the actual structures reliably. No model or embedding dependencies are needed.

## Automated checks and their limits


| Check                   | Flag for review                                                                              | Limitation                                                     |
| ----------------------- | -------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| UTF-8/text integrity    | Decode failures, replacement characters, suspicious control characters or encoding artifacts | A suspicious sequence is not necessarily corrupted text        |
| Page structure          | Duplicate/out-of-order markers, missing expected pages, out-of-range references              | Page-marker presence does not prove full page content          |
| Table structure         | Inconsistent row cell counts, missing header separators, apparently detached footnotes       | Legitimate Markdown variants and escaped pipes must be handled |
| Numeric notation        | Unusual spacing inside numbers/units, detached comparison symbols, suspicious line breaks    | Cannot determine the clinically correct value                  |
| Conditions and negation | Potentially detached qualifiers, exceptions, or continuation lines                           | Cannot establish meaning or safely insert missing words        |
| Heading/reading order   | Orphan sections, repeated headers/footers, page-boundary fragments                           | Some repetition is intentional                                 |
| Source mapping          | Ambiguous repeated phrases, unknown physical page, unavailable PDF text boxes                | Exact PDF highlighting must remain unavailable if not verified |


Do not normalize away inequality signs, negation, decimal points, or units. Do not automatically “correct” drug names, doses, spelling, or clinical wording. Preserve raw source text separately from any view-only normalization used to suggest matches.

## Review method

Prioritize numeric tables and instructions involving doses, thresholds, age/weight bands, negation, exclusions, and continuation across pages. Review all flagged blocks and include an additional reproducible sample from each document and block type. Record the sample rule/seed and report the denominator; if defects recur, broaden review of the affected document or structure.

For each item, compare the existing Markdown with the original PDF, checking wording, numbers, units, conditions, table row/column relationships, headings, footnotes, and reading order. Record the reviewed span, source page, finding, reviewer identity/role, and review time. If no review occurred, keep the entry pending.

Transcription fidelity review asks whether the Markdown matches the PDF. Clinical authority review asks whether the source is applicable and current for the intended use. Keep these separate; neither a parser nor a visual match establishes clinical authority.

A confirmed defect is logged and the affected span is marked excluded pending correction. This phase does not edit original documents. A correction requires a separately recorded action and subsequent re-review against the source; previous approvals are invalid when the relevant content changes.

## Source records and citation mapping


| Record           | Required fields                                                                                                                               |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Source block     | Stable ID derived from source hash and span, document/content ID, Markdown hash/path, block type, heading path, exact text, start/end offsets |
| Page association | Physical PDF page when established, printed label when verified, mapping method and status                                                    |
| Review item      | Block ID, selection reason, issue category, severity, evidence, review status, reviewer/time                                                  |
| Mapping          | Source/PDF hashes, page dimensions/rotation, boxes where verified, alignment status                                                           |
| Coverage         | Document and block-type counts, flagged/reviewed/pending/defective counts, sample definition                                                  |


Offsets use zero-based, end-exclusive Unicode code points against the exact decoded Markdown string. Preserve original line endings when loading; do not apply newline normalization before measuring offsets. For discontiguous or multi-page evidence, store ordered span references rather than pretending it occupies a single contiguous range.

Use 1-based physical PDF pages in exported records, translating explicitly to a library's 0-based page index. Printed page labels are separate and may be unknown. PDF boxes use the coordinate/rotation convention in the [system design](../architecture/01-system-design.md).

Native PDF text search may suggest a bounding box, but repeated phrases and table layouts require confirmation. For scanned pages without reliable text coordinates, retain an explicitly unverified mapping and offer the PDF page plus extracted-text highlight. Do not run OCR or invent a precise overlay. Source-block offsets can support Markdown highlighting even when PDF coordinates are unavailable.

## Output files after authorization


| Path                                              | Purpose                                                                        |
| ------------------------------------------------- | ------------------------------------------------------------------------------ |
| `notebooks/03_markdown_validation.ipynb`          | Executed notebook with saved structure, flag, and coverage tables              |
| `artifacts/step-03/<run-id>/source_blocks.jsonl`  | Exact source blocks and provenance; these are not retrieval chunks             |
| `artifacts/step-03/<run-id>/review_queue.csv`     | Prioritized cases needing inspection                                           |
| `artifacts/step-03/<run-id>/review_ledger.json`   | Explicit review outcomes and unresolved cases                                  |
| `artifacts/step-03/<run-id>/source_mappings.json` | Page/span associations and verified/unknown coordinate status                  |
| `artifacts/step-03/<run-id>/issues.csv`           | Structural flags and confirmed defects, distinguished clearly                  |
| `artifacts/step-03/<run-id>/check_results.json`   | Technical checks and provenance consistency                                    |
| `artifacts/step-03/<run-id>/run_manifest.json`    | Versions, input hashes, sampling configuration, and coverage                   |
| `docs/modeling/03-build-review.md`                | What was implemented, measured coverage, limitations, and next review decision |


Use new run directories and preserve prior reviews; carry reviews forward only for unchanged source identities. No output is described as a corrected corpus. Do not silently treat pending spans as reviewed or automatically approve a whole document because a sample passed.

## Verification after implementation is authorized

1. Execute in a fresh kernel and save outputs, with a valid selected inventory manifest.
2. Verify every block's text equals its recorded source slice and all IDs/references resolve.
3. Exercise synthetic edge cases outside source folders: CRLF/non-ASCII offsets, escaped table pipes, repeated page phrases, missing markers, a multi-page continuation, and unavailable PDF coordinates.
4. Check that automatic flags do not mark content as corrected, clinically approved, or manually reviewed.
5. Verify known mappings against the original page and explicitly preserve unknown/ambiguous cases.
6. Confirm review coverage totals reconcile with the queue and distinguish samples from all-document coverage.
7. Read exports back, confirm the selected source files remain unchanged, and reject stale review records when hashes differ.



## Acceptance and stopping point

The implementation is ready for review when parsing/mapping records are traceable, technical checks pass, pending reviews and defects are fully visible, and source text is unchanged. Corpus readiness is a separate outcome: no unresolved critical transcription error may remain in a span marked eligible and reviewed. Unaudited content and missing coordinates must remain explicitly labeled.

When reviewers or mappings are unavailable, finish the independent notebook/report work and record those items as pending. Do not claim a full content audit or precise PDF highlighting. Step 4 will identify any additional benchmark passages requiring review before downstream accuracy claims.

Stop after this phase's authorized work and review report. Benchmark annotation, final chunking, BM25 indexing, embeddings, and Gemma inference are not included. At present, only this plan is being written; the notebook and artifacts await a build instruction.
