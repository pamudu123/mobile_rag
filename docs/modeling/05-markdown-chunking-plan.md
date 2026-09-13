# Step 5: Markdown passages, chunks, and citation metadata

Status: implemented and ready for review. See [the build review](05-build-review.md).

## What we will build

Build **`notebooks/markdown_chunking/02_markdown_chunking.ipynb`** to convert the existing Markdown into traceable passages and retrieval-ready chunks. Each chunk will retain its document identity, heading context, ordered source spans, available page references, and links to neighboring passages.

This is the next active building phase after Step 2. Step 3 is merged into Step 2 and Step 4 is skipped. No OCR audit, benchmark annotation, or test-split preparation is required here. Use the existing text without rewriting clinical content; the Q&A remains outside the chunking inputs.

The deliverable is a reusable chunk dataset for Step 6's BM25 index. This phase does not construct the index, generate embeddings, call Gemma/OpenRouter, or implement the answer viewer.

## Inputs and selection

| Input | Purpose |
| --- | --- |
| Selected Step 2 corpus manifest | Explicit document/file identities, hashes, readable Markdown, source pairings, and known issues |
| Existing `data/md_docs/` files named in that manifest | Text to parse and chunk |
| Recorded chunking configuration | Deterministic grouping rules, size targets, metadata, and versions |

Do not discover and ingest unrelated files automatically. Exclude questions, reference answers, TXT sidecars, existing outputs, and empty/undecodable Markdown. Verify input hashes before processing; if they differ from the selected inventory, stop and request a refreshed inventory rather than using stale identities.

Readable Markdown with an unknown PDF mapping may still be chunked. Its citation target is the Markdown document and exact spans; PDF location remains unknown. An unresolved clinical-review field is not a new blocking OCR/benchmark gate, and must remain labeled rather than being silently approved.

For exact duplicate Markdown files, retain aliases but process the same bytes once according to a recorded canonical-path rule. When several different Markdown files map to the same PDF, report the choice and require an explicit selection rather than silently merging conflicting versions.

## Notebook sequence

| Section | Implementation | Visible result |
| --- | --- | --- |
| 1. Setup | Select inventory and verify inputs/environment | Corpus and provenance summary |
| 2. Parse | Identify headings, page markers, paragraphs, lists, and tables with source offsets | Block counts and representative parsed records |
| 3. Passages | Assign stable IDs and heading/page context to source blocks | Passage table and source-slice examples |
| 4. Chunk | Group passages using the rules below | Chunk dataset and size distribution |
| 5. Context/links | Attach source-backed headings, table context, and neighbor IDs | Context and linkage examples |
| 6. Citations | Export document/span/page reference records | Exact-source resolution examples |
| 7. Inspect/check | Check preservation, coverage, duplicates, sizes, and references | Technical checks and exception report |
| 8. Export/review | Save artifacts and build-review note | Paths, hashes, counts, and next-step status |

Use standard-library data handling with a small Markdown parser only if needed for accurate source mapping. Inspect existing dependencies before adding packages. No tokenizer/model download is necessary: the initial size policy uses Unicode character counts, not embedding tokens.

## Source parsing and passage rules

Load UTF-8 strictly and preserve original line endings. Keep source text separate from search/display representations. All offsets are zero-based, end-exclusive Unicode code-point offsets into that exact decoded Markdown file, not byte offsets or offsets into normalized text.

Parse headings into a hierarchy while preserving their original spans. Treat `## Page N` markers as page metadata rather than clinical section names. Their numbers are declared page references unless Step 2 established a mapping; they are not automatically verified physical/printed PDF page numbers.

Represent paragraphs, list groups, and tables as source passages. Preserve fenced or HTML blocks as opaque blocks when supported rather than discarding them. Unrecognized nonempty content receives an opaque block or an explicit exception record. Do not drop text because the parser cannot classify it.

Keep introductory conditions with the list or table they govern where structure indicates that relationship. Store heading and neighboring-block links even where the parser cannot determine clinical applicability. Structural grouping helps preserve context; it does not guarantee that all clinical dependencies have been recognized.

Every non-whitespace source region must be accounted for as passage content, structural context, or an explicitly excluded region with a reason. Source metadata/front matter may be excluded from searchable body text but retained in document records. Do not remove recurring text solely because it appears similar to a footer.

## Initial chunking policy

| Setting | Proposed starting rule |
| --- | --- |
| Target size | Approximately 600–1,000 Unicode characters of assembled retrieval text, including attached context |
| Minimum size | No forced minimum; a short self-contained section remains short |
| Boundaries | Prefer complete paragraphs/list groups/tables within one section |
| Documents | Never combine different documents in one chunk |
| Sections | Do not cross a clinical heading boundary merely to fill the size target |
| Pages | Preserve page transitions; page markers alone need not split a continuing block |
| Overlap | No arbitrary character-window overlap initially; use explicit heading/context spans and neighbor links |
| Large atomic block | Retain intact and flag `oversized`; do not truncate or split sentences blindly |
| Ordering | Deterministic document/source-span order |

Greedily add complete passages within a section until the next one would exceed the target maximum. Flush the current chunk at that point. If a passage alone exceeds the target, keep it as an oversized chunk with its full source provenance. Preserve safety/context groups intact even when that exceeds the target. Report oversized frequency and the largest examples; size targets are tuning parameters, not correctness criteria.

No automatic summarization, medical spelling correction, unit conversion, or generated context is allowed. Any display separator or label introduced by the assembler is marked synthetic and is not eligible as a supporting quote.

Later retrieval/prompt selection must measure actual model-token budgets and handle oversized chunks explicitly. Step 5 does not imply that every chunk will fit the future prompt. It reports those cases for Step 6/selection design rather than silently losing evidence now.

## Tables, lists, and clinical conditions

Keep a normal-sized table together with its header, introductory condition, and visibly associated footnotes. Handle escaped pipes and row separators correctly. Preserve original row order, units, and text; do not flatten columns into unrelated paragraphs.

For this first build, keep oversized tables intact and flag them. Row-based subdivision with repeated headers is a possible later refinement only if needed; it must maintain exact row/header/footnote span references and pass explicit preservation checks before adoption. Do not automatically split a dosing table to meet the size target.

For lists, retain the introducing paragraph and ordered/nested items as a context group when the structure identifies them. Do not detach an “if,” exception, or eligibility line solely to create similarly sized chunks. If a dependency is ambiguous, retain the larger block and record a context warning instead of inventing the connection.

These are text-preservation measures over the supplied Markdown. They do not reinstate a broad OCR review or claim that the original text is clinically correct.

## Identity, provenance, and contracts

Use Step 2's PDF content ID when the association is established. Otherwise use a namespaced Markdown-content ID. Keep the Markdown SHA-256 on every passage even when a PDF identity exists, because changing an extraction changes citation spans.

Derive passage IDs from source identity, ordered offsets, and parser version. Derive chunk IDs from ordered passage/context IDs and a fingerprint of the chunking configuration. Identical inputs and settings produce identical IDs. Different inputs/settings produce a new bundle version; do not reuse stale citations.

| Record | Required fields |
| --- | --- |
| Document | ID, Markdown hash/path, optional PDF ID/path, title/source metadata and their origin, mapping/review status |
| Passage | ID, document ID, kind, exact text, start/end offsets, heading path and heading-span IDs, declared/verified page fields |
| Chunk | ID, document ID, ordered body passage IDs, context span IDs, assembled retrieval text, character count, flags, config version |
| Segment mapping | Retrieval-text interval, source-span reference or synthetic marker; source and retrieval offsets remain distinct |
| Links | Previous/next passage and chunk IDs within the same document; section relationship |
| Citation target | Bundle version, document ID, ordered source spans, available page references, PDF-coordinate status |
| Run manifest | Selected inventory, input hashes, parser/schema/config versions, output hashes, counts, exclusions, exceptions |

Do not describe a chunk assembled from separate spans as one continuous source quote. Resolve citation quotes against original source spans, including ordered multi-span references when needed. Repeated headings attached to multiple chunks retain the same source ID so they can be deduplicated later.

PDF bounding boxes stay null/unavailable unless supplied with verified provenance. Markdown offsets enable exact Markdown highlighting later. This step creates citation metadata, not the PDF renderer or verified overlays.

The future answer contract remains `answered`, `abstained`, or `error`, with claim-level citation targets. Step 5 defines and demonstrates citation resolution only; it does not produce model answers or implement semantic claim verification.

## Planned outputs

| Path | Purpose |
| --- | --- |
| `notebooks/markdown_chunking/02_markdown_chunking.ipynb` | Executed notebook with saved examples and checks |
| `artifacts/step-05/<run-id>/documents.jsonl` | Selected documents and source metadata |
| `artifacts/step-05/<run-id>/passages.jsonl` | Exact source passages with offsets and structural context |
| `artifacts/step-05/<run-id>/chunks.jsonl` | Retrieval-ready chunks, segment mappings, and links |
| `artifacts/step-05/<run-id>/citation_targets.jsonl` | Source references for later answer citations |
| `artifacts/step-05/<run-id>/chunking_config.json` | Reproducible settings and version |
| `artifacts/step-05/<run-id>/exceptions.csv` | Oversized/opaque content, missing mappings, exclusions, and context warnings |
| `artifacts/step-05/<run-id>/check_results.json` | Structural and preservation checks |
| `artifacts/step-05/<run-id>/run_manifest.json` | Input/output provenance, counts, statistics, and readiness |
| `docs/modeling/05-build-review.md` | What was built, representative chunks, actual statistics, limits, and next-step decision |

These files are planned, not created by this document. Use new run directories and preserve previous artifacts. Check for existing user edits before writing notebook/review files. Leave source Markdown, PDFs, and Q&A unchanged.

## Verification after authorization

1. Execute the notebook from a fresh kernel with a valid selected Step 2 manifest.
2. Check every passage's exact text against its source slice and every retrieval segment against its referenced span or declared synthetic separator.
3. Reconcile source coverage; account for all non-whitespace source regions and all input files without silent omissions.
4. Check unique IDs, valid context/citation links, deterministic order, no cross-document chunks, and valid neighbor boundaries.
5. Exercise temporary synthetic cases: CRLF plus non-ASCII offsets, repeated headings, escaped table pipes, an oversized table, nested conditional lists, a page-spanning paragraph, unrecognized content, and missing PDF mapping.
6. Inspect representative real chunks for prose, lists, tables, and oversized/context-warning cases. Compare with the existing Markdown, not a broad PDF/OCR audit.
7. Verify numbers, units, inequality signs, and negation text in selected source spans are not changed by assembly. This verifies preservation, not medical correctness.
8. Rebuild on unchanged inputs/settings and compare substantive IDs/content hashes; run timestamps may differ. Read exports back and verify source hashes remain unchanged.
9. Report per-document passage/chunk counts, minimum/median/p95/maximum character sizes, oversized counts, context duplication, excluded content, and mapping availability.

## Acceptance and stopping point

Ready for review means every input is accounted for, all emitted passages/chunks are traceable, preservation/link checks pass, outputs are reproducible, and every oversized/unmapped/unsupported structure is visible. Unknown PDF mappings do not block valid Markdown chunks. Parser failures that lose or misattribute text must be fixed or explicitly exclude the affected content from this run with an issue record; do not claim full coverage in that case.

Acceptance does not establish retrieval quality, OCR accuracy, clinical correctness, or model performance. Those claims are not made by chunking. No Step 3/4 review prerequisite is reintroduced.

After review and authorization, Step 6 can build the SQLite FTS5/BM25 index from `chunks.jsonl` and its linked source records. This phase stopped before indexing, embeddings, or inference. See [the build review](05-build-review.md) for the executed evidence.
