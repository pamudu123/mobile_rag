# Step 2: Corpus inventory and lightweight Markdown checks

Status: documented; awaiting the user's pass to implement. This is the first executable building phase. Step 1 is documentation-only.

User scope update: Step 3 is merged into this phase and skipped as a separate build. Include only practical Markdown readability/structure checks here. Detailed OCR diagnostics, original-PDF content auditing, manual review queues, and bounding-box alignment are deferred; there is no Step 3 notebook or prerequisite audit to complete before Step 5.

## What we will build

Build and execute **`notebooks/02_corpus_inventory.ipynb`** to produce an auditable inventory of the supplied PDFs and their existing Markdown extractions. The notebook will identify exact duplicates, unreadable/empty files, missing extractions, and uncertain file pairings before retrieval work begins.

The previous inspection reported 15 PDFs recursively and 14 Markdown files. Treat these as observations to reconcile, not expected counts to hard-code. The notebook must report actual files and locations, including nested files, and distinguish physical file count from unique PDF content count.

This implements the technical inventory portion of [master Step 2](../architecture/06-step-by-step-plan.md). Clinical authority, applicability, and supersession remain manual review fields; successful execution alone does not complete that clinical review.

## Inputs and boundaries

| Input | Use |
| --- | --- |
| `data/pdf_docs/` | Primary PDF collection; inspect recursively |
| `data/md_docs/` | Existing Markdown extractions; inspect recursively |
| Other PDF/Markdown paths under `data/` | Report as outside expected locations; do not silently include as approved sources |
| Existing Markdown source/page headers | Candidate pairing and extraction-coverage evidence |
| Requirements and architecture documents | Design context only |

Benchmark files under `data/questions/` must not become clinical corpus sources. TXT sidecars may be counted as auxiliary files but are not substitutes for Markdown or automatically indexed. Skip symbolic links/reparse-point directories and record the exclusion, keeping discovery within the resolved data root.

Read source files without changing them. Do not run OCR, repair text, rename/delete duplicates, construct chunks/indexes, create embeddings, call OpenRouter, or download models. Do not read `.env` or display secrets.

## Notebook sequence

| Cell group | Implementation | Visible result |
| --- | --- | --- |
| 1. Purpose | State scope, inputs, output location, and limitations | Phase summary |
| 2. Environment | Resolve project root from repository markers or explicit path; report Python/PyMuPDF versions | Non-sensitive environment table |
| 3. Discovery | Recursively enumerate allowed files with deterministic ordering | Counts by type and location, unexpected-location list |
| 4. File identity | Stream SHA-256 hashes; collect relative path and byte size | Inventory and exact-duplicate groups |
| 5. PDF inspection | Open with PyMuPDF; record page count, encryption, errors, and available metadata | PDF health table |
| 6. Markdown inspection | Decode UTF-8 strictly; detect empty/whitespace-only content; summarize headings, page markers, and basic table structure | Markdown readiness table and lightweight structural flags |
| 7. Pairing | Match explicit source references and filename candidates conservatively | PDF-to-Markdown mapping with reason and confidence category |
| 8. Issues | Classify missing, ambiguous, unreadable, duplicate, and coverage cases | Issues table and count reconciliation |
| 9. Validation/export | Check record consistency and write machine-readable reports | Check outcomes, output paths, hashes |
| 10. Checkpoint | Summarize findings and manual decisions needed | Ready-for-review report; no automatic next step |

Use Python standard-library modules for paths, hashing, JSON, CSV, and simple tables, plus the project's existing PyMuPDF dependency for PDF inspection. Add only notebook execution tooling if missing after authorization. Keep this phase notebook-first; reusable package modules are unnecessary unless the implementation demonstrates a clear need.

## Exact duplicate detection

Hash raw file bytes in chunks. Group PDFs with identical SHA-256 values as exact-content duplicates, preserving a separate file record for every path. Use the full PDF hash as the stable content/document identity for this inventory; assign a separate path-based file identifier for copies. A changed file gets a different content identity. Record zero-byte files separately from usable duplicate groups.

Do not infer that similar titles, filenames, extracted text, or page counts mean identical editions. Near-duplicate/version detection is outside this first implementation. Do not remove duplicates automatically. If a source changes between inspection and final verification, mark the run inconsistent and rerun before accepting its manifest.

## PDF and Markdown checks

For each PDF, record whether it opens, whether a password is required, page count when readable, and metadata title/author/date when present. Preserve metadata as unverified observations; PDF creation dates are not publication dates or proof of clinical currency. Handle individual failures as inventory issues and continue scanning other files.

For each Markdown file, record byte size, decoding status, character count, declared source filename if present, and physical-page markers such as `## Page 1`. Do not silently replace invalid UTF-8 bytes. Detect duplicate, nonpositive, missing, and out-of-range page numbers relative to a matched PDF. If page markers are absent, report coverage as unknown rather than zero verified coverage.

Also summarize heading levels and table presence, flagging clearly malformed table rows without rewriting them. Account for escaped pipes and legitimate Markdown variants; a structural flag is a review hint, not an automatically confirmed error. These checks use the existing Markdown and add no OCR work.

Count comparison and page-marker checks are structural signals only. Matching page counts do not prove that doses, table rows, or clinical conditions were extracted correctly. Detailed content auditing is deferred. Record transcription accuracy as not assessed; investigate source fidelity later when a benchmark/source check or concrete defect warrants it.

## Pairing policy

1. Prefer an explicit Markdown source reference when it resolves unambiguously to a discovered PDF. If it conflicts with the filename-derived candidate, report a conflict rather than choosing silently.
2. Otherwise use a unique exact relative-stem match; a unique basename-stem match across subdirectories is a weaker fallback and must be labeled.
3. Unicode normalization and case-insensitive matching may suggest candidates, but collisions must remain ambiguous. Do not strip punctuation or use fuzzy similarity to force a match.
4. Duplicate PDF copies can point to one content identity, while retaining all file paths. A shared extraction does not justify counting each copy as a separate clinical document.
5. Report a PDF without a confident extraction, Markdown without a PDF, multiple competing extractions, and contradictory source declarations explicitly. Leave uncertain pairings unresolved for review.

A matching filename establishes a candidate association, not verified text fidelity or clinical eligibility.

## Exported records

| Record | Key fields |
| --- | --- |
| Run | Schema version, UTC run time, Python/PyMuPDF versions, roots, settings, input-set fingerprint |
| File | File ID, relative path, extension, size, SHA-256, read status, error code/message |
| PDF content | Full-hash document ID, member file IDs, readable status, page count, password status, observed metadata |
| Extraction | Markdown file ID, decoding status, source declaration, character count, headings summary, table summary, page-marker list, structural flags, transcription review status |
| Pairing | PDF content ID, Markdown file ID, matching rule, matched/ambiguous/unmatched status, candidate IDs |
| Issue | Stable issue ID/code, severity, affected file IDs, details, suggested next action, review status |
| Review fields | Clinical authority, publication edition, eligibility, supersession, reviewer and review date; unknown unless actually reviewed |

Keep unknowns as null or explicit unknown states, never invented values. Store relative paths for portability. Sort records deterministically, excluding timestamps from the stable content fingerprint. Technical checks, user acceptance, and clinical review are separate status fields.

## Planned output files

All paths below are future outputs, not artifacts created during this documentation task.

| Path | Purpose |
| --- | --- |
| `notebooks/02_corpus_inventory.ipynb` | Runnable notebook with saved output tables |
| `artifacts/step-02/<run-id>/corpus_manifest.json` | Complete versioned inventory, content identities, pairings, and review placeholders |
| `artifacts/step-02/<run-id>/file_inventory.csv` | Flat inventory for inspection |
| `artifacts/step-02/<run-id>/issues.csv` | File, matching, and structural problems |
| `artifacts/step-02/<run-id>/check_results.json` | Technical validation outcomes and run consistency |
| `docs/modeling/02-build-review.md` | Actual findings, executed checks, artifact links, limitations, and next review decision |

Use a new run directory instead of overwriting prior reports. Re-execution should produce equivalent substantive records for unchanged inputs, with separate run metadata. Inspect existing notebook/report files before writing so user edits are preserved. No changes to source data are necessary.

## Failure behavior

| Condition | Behavior |
| --- | --- |
| Missing project/data root or required dependency | Stop with an actionable setup error; do not export a successful empty inventory |
| Individual unreadable PDF or Markdown | Record error and continue; mark the corpus as having issues |
| Missing Markdown, ambiguous pairing, or page mismatch | Retain in issues report; do not automatically repair or approve |
| Exact duplicates | Group by content and retain every path for review |
| Unexpected location or skipped link | Report exclusion/candidate status explicitly |
| Output-write failure or inconsistent input snapshot | Fail technical completion; do not claim a valid exported run |

The notebook can complete correctly while discovering corpus problems. Distinguish **inventory execution passed** from **corpus ready for extraction/clinical review**. Do not hide source problems to make the check summary green.

## Verification and acceptance

After the user gives a pass:

1. Execute from a fresh kernel and save all outputs; root resolution must work from the project or notebook directory.
2. Reconcile discovery counts with independent file enumeration, separating expected-location, outside-location, auxiliary, skipped, and failed files.
3. Validate unique IDs, valid pairing references, nonnegative sizes, hash format for successfully read files, and complete accounting of every discovered PDF/Markdown file.
4. Exercise meaningful edge cases with temporary synthetic files outside source directories: exact duplicate PDFs, whitespace-only Markdown, invalid UTF-8, orphan extraction, ambiguous stems, malformed PDF, and missing/duplicate page markers. Do not retain clinical test copies unnecessarily.
5. Check a representative real PDF page count and pairing against the actual file; inspect all reported ambiguities and count discrepancies.
6. Read exported JSON/CSV back and reconcile their record counts with notebook tables. Confirm source hashes are unchanged and compare substantive output across a repeat run when checking determinism.
7. Publish the build-review note with actual counts, defects, execution evidence, and unresolved human-review fields. Do not mark clinical authority or source accuracy verified by these checks.

Acceptance requires a reproducible, complete inventory and an honest issues report, not an issue-free corpus. Proceeding beyond this phase requires review of the results and explicit next-step scope. Detailed OCR auditing/correction is deferred. Clinical source approval, benchmark annotation, and retrieval implementation are outside this build. Step 5 follows this combined phase; Step 3 is not a separate execution gate.

## Current approval boundary

This document specifies only the proposed Step 2 build. No notebook, artifact directory, implementation code, or model request has been created. After the user's pass, implement and execute this bounded inventory phase and return its evidence for review.

