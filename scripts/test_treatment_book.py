import pymupdf
import pymupdf4llm
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Let's test on PNG-Standard-Treatment-Book-10th-edition-2016.pdf
pdf_path = "data/pdf_docs/PNG-Standard-Treatment-Book-10th-edition-2016.pdf"
doc = pymupdf.open(pdf_path)

# Let's extract pages 10 to 15 (0-indexed 9 to 14)
chunks = pymupdf4llm.to_markdown(doc, pages=list(range(9, 15)), page_chunks=True)
for i, c in enumerate(chunks):
    page_num = c['metadata']['page_number']
    print(f"=== Page {page_num} ===")
    print(c['text'])
    print("\n" + "="*40 + "\n")

