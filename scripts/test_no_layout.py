import pymupdf
import pymupdf4llm

doc = pymupdf.open("data/pdf_docs/WHO-Oxygen-therapy-for-children-2016.pdf")
pymupdf4llm.use_layout(False)
c2 = pymupdf4llm.to_markdown(doc, pages=[3])
print("No layout length:", len(c2))
print("First 300 chars repr:", repr(c2[:300]))
print("First 300 chars clean:", c2[:300])

