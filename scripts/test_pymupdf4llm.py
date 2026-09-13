import pymupdf4llm
import pymupdf

pdf_path = "data/pdf_docs/WHO-Oxygen-therapy-for-children-2016.pdf"
doc = pymupdf.open(pdf_path)

# Extract markdown for pages 20-25 (0-indexed 19 to 24)
chunks = pymupdf4llm.to_markdown(doc, pages=list(range(19, 25)), page_chunks=True)
for c in chunks[:3]:
    print(f"=== Metadata: {c['metadata']} ===")
    print(c['text'][:500])
    print("\n-------------------\n")

