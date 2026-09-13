# Corpus inventory

**Status:** Implemented. Uses the existing Markdown files.

## At a glance

- **Purpose:** Identify the supplied documents and their extraction files.
- **Input:** PDFs, existing Markdown and corpus configuration.
- **Output:** File inventory, document mappings, hashes and issue reports.
- **Next:** Markdown chunking.


## Technical working: identity and source matching

Implementation: [corpus.py](../../src/mobile_rag/corpus.py), principally `build_inventory()`, `validate_inventory()` and `export_inventory()`.

1. Walk eligible files under `data/` in stable path order; record paths, sizes, read status and SHA-256. Skip symbolic links.
2. Inspect PDFs with PyMuPDF for readability, password requirements, page counts and available metadata.
3. Group exact duplicate PDFs by content hash, retaining all original file paths.
4. Read Markdown structure and source declarations.
5. Match the declared PDF name first, otherwise use the Markdown basename with `.pdf`. Name comparison uses Unicode NFC and case folding.
6. If explicit source and basename disagree, record an ambiguous mapping. If an explicit declaration has no match, do not silently fall back to a different source.
7. Export the manifest and inventory/issue reports with a reproducible fingerprint.

### Example: matching without guessing

| Markdown | Declaration | Available PDF | Outcome |
| --- | --- | --- | --- |
| `guide.md` | None | `guide.pdf` | Basename match |
| `guide.md` | `manual.pdf` | Only `manual.pdf` | Explicit-source match |
| `guide.md` | `manual.pdf` | Both `guide.pdf` and `manual.pdf` | Ambiguous source/stem conflict |

Two differently named PDFs with identical bytes share a content record. Similar filenames or similar text do not establish duplicate content. These examples illustrate matching rules, not additional corpus files.


## Data flow

```mermaid
flowchart LR
    A[PDF and Markdown files] --> B[Inventory and hash files]
    B --> C[Match source documents]
    C --> D[Record structural issues]
    D --> E[Corpus manifest]
```

## What it does

- Records file identity and detects exact duplicates.
- Checks for empty or unreadable files and uncertain source mappings.
- Performs lightweight Markdown structure checks.
- Saves reproducible artifacts under `artifacts/01_corpus_inventory/`.

## Boundaries

- No new OCR extraction or repair phase.
- No separate detailed content audit.
- Inventory success does not establish clinical correctness.
- Existing Q&A reference answers stay outside retrieval inputs.

## Open the implementation

- [Notebook](../../notebooks/corpus_inventory/01_corpus_inventory.ipynb)
- [Run guide](../../notebooks/corpus_inventory/README.md)
- [Detailed specification](../modeling/02-corpus-inventory-plan.md)
- [Build evidence](../modeling/02-build-review.md)

Continue to [Markdown chunking](03-markdown-chunking.md).
