import re
import pymupdf
import pymupdf4llm

def clean_markdown_page(md_text: str, page_num: int) -> str:
    lines = md_text.splitlines()
    cleaned_lines = []
    
    # Strip running headers/footers
    for line in lines:
        stripped = line.strip()
        # Remove standalone page numbers (e.g. "12", "12 | P a g e", "iv", etc.)
        if re.match(r"^(?:\d+|[ivxlcdm]+)\s*(?:\|\s*P\s*a\s*g\s*e)?$", stripped, re.IGNORECASE):
            continue
        # Remove repeated book header banners
        if stripped in ["OXYGEN THERAPY FOR CHILDREN", "Oxygen therapy for children"]:
            continue
        # Remove HTML picture comments
        if stripped in ["<!-- Start of picture text -->", "<!-- End of picture text -->"]:
            continue
        # Fix replacement chars
        line = line.replace("\ufffd", "–")
        line = line.replace("", "–")
        cleaned_lines.append(line)
        
    text = "\n".join(cleaned_lines)
    # Collapse 3+ newlines to 2
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text

doc = pymupdf.open("data/pdf_docs/WHO-Oxygen-therapy-for-children-2016.pdf")
chunks = pymupdf4llm.to_markdown(doc, pages=list(range(5)), page_chunks=True)
for i, c in enumerate(chunks, start=1):
    page_md = clean_markdown_page(c["text"], i)
    print(f"## Page {i}\n")
    print(page_md[:400])
    print("\n" + "="*40 + "\n")

