# Markdown chunking

**Status:** Implemented.

## At a glance

- **Purpose:** Turn Markdown into traceable retrieval units.
- **Input:** Validated inventory and the existing Markdown.
- **Output:** Documents, passages, chunks and citation targets.
- **Next:** Retrieval.


## Technical working: passages and chunk boundaries

Implementation: [corpus.py](../../src/mobile_rag/corpus.py): `parse_markdown()`, `_assemble_chunk()`, `build_chunks()` and `validate_chunks()`.

- **Parser:** tracks exact source offsets, active heading stack and declared page markers. Recognizes paragraphs, headings, tables, lists, fenced blocks and opaque content.
- **Heading stack:** when a heading arrives, remove headings at the same or deeper level, then add the new heading. Body passages inherit the current heading IDs.
- **Passage identity:** hash the source identity, start/end offsets and parser version. The text is the exact source slice `text[start:end]`.
- **Greedy grouping:** add the next whole body passage while its heading context matches and the assembled chunk is at most 1,000 characters. Otherwise flush the current group and start another.
- **Oversized unit:** a single passage longer than the target remains intact and gets an `oversized` flag. The configured 600-character minimum is not enforced by a rebalancing pass.
- **Chunk identity:** hash document ID, ordered body/context passage IDs and chunk configuration. Link previous/next chunks within each document.
- **Source mapping:** each assembled segment identifies its source passage; inserted whitespace is marked synthetic. Citation targets reference body passages, while heading context remains separately available.

### Example: why a chunk ends

Assume the assembled heading and passage A occupy 620 characters. Adding passage B makes the assembled candidate 1,080 characters.

```text
Same section:
  A -> chunk 1
  B -> chunk 2 because candidate would exceed 1,000 characters

Next passage is a 1,500-character table:
  keep the complete table in its own oversized chunk

Next passage has a new heading:
  start a new chunk even if the previous chunk was short
```

These are illustrative sizes, not recorded measurements. The algorithm preserves structural units; it does not automatically discover a qualifier stated elsewhere in the document.


## Data flow

```mermaid
flowchart LR
    A[Corpus manifest] --> B[Read Markdown]
    B --> C[Identify passages and headings]
    C --> D[Build source-linked chunks]
    D --> E[Export chunks and citations]
```

## What is preserved

| Item | Why it matters |
| --- | --- |
| Exact passage text and offsets | Trace each excerpt to the stored Markdown. |
| Heading and body relationships | Retain section context. |
| Whole structural units, including tables | Avoid arbitrary cuts through source content. |
| Neighbor links | Allow bounded context expansion. |
| Document and citation IDs | Resolve references through application metadata. |

## Boundaries

- Oversized or opaque units are recorded rather than silently discarded.
- Structural preservation does not prove that every clinical qualifier is captured.
- Declared pages are unverified; exact PDF coordinates are unavailable.
- No embeddings or model calls.
- Existing artifact directories retain their historical `step-05` names.

## Open the implementation

- [Notebook](../../notebooks/markdown_chunking/02_markdown_chunking.ipynb)
- [Run guide](../../notebooks/markdown_chunking/README.md)
- [Detailed specification](../modeling/05-markdown-chunking-plan.md)
- [Build evidence](../modeling/05-build-review.md)

Continue to [Retrieval](04-retrieval.md).
