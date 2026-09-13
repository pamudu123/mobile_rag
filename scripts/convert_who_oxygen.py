import re
import sys
import time
from pathlib import Path
import pymupdf
import pymupdf4llm

sys.stdout.reconfigure(encoding="utf-8")

def clean_page(text: str, page_num: int) -> str:
    text = text.replace("\x00", "")
    text = text.replace("acid\ufffdbase", "acid-base")
    text = text.replace("acidbase", "acid-base")
    text = text.replace("\ufffd", "–")
    text = text.replace("cmH20", "cmH2O")
    text = text.replace("brochioitis", "bronchiolitis")
    text = text.replace("diarhoea", "diarrhoea")
    text = text.replace("sulfamethoxozole", "sulfamethoxazole")
    text = text.replace("WHo ", "WHO ")
    text = text.replace("HIv", "HIV")
    text = text.replace("«", "<")

    # Clean HTML picture markers
    text = re.sub(r"<!--\s*Start of picture text\s*-->", "", text)
    text = re.sub(r"<!--\s*End of picture text\s*-->", "", text)

    lines = [l.strip() for l in text.splitlines()]
    # Remove empty lines from start
    while lines and not lines[0]:
        lines.pop(0)

    # If first line is a running header, strip it
    header_patterns = [
        r"^OXYGEN THERAPY FOR CHILDREN\s*$",
        r"^Oxygen therapy for children\s*$",
        r"^\d+\.\s+[A-Z\s]{4,}$", # e.g. "3. DETECTION OF HYPOXAEMIA"
        r"^PACIFIC OUTBREAK MANUAL.*$",
        r"^PPHSN Pacific Outbreak Manual.*$",
        r"^Standard Treatment for Common Illnesses.*$",
        r"^NATIONAL CLINICAL GUIDELINES FOR HIV.*$",
        r"^WHO operational handbook on tuberculosis.*$",
        r"^POCKET BOOK OF Hospital care for children.*$",
        r"^CHILD HEALTH FOR NURSES AND HEOS.*$",
        r"^PAEDIATRICS FOR DOCTORS IN PAPUA NEW GUINEA.*$",
        r"^\d+\s*\|\s*P\s*a\s*g\s*e\s*$",
    ]
    if lines:
        for pat in header_patterns:
            if re.match(pat, lines[0], re.IGNORECASE):
                lines.pop(0)
                break

    # Strip orphan page number at the bottom
    while lines and not lines[-1]:
        lines.pop(-1)
    if lines and re.match(r"^(?:\d+|[ivxlcdm]+)\s*$", lines[-1], re.IGNORECASE):
        lines.pop(-1)

    text = "\n".join(lines)
    # Tidy tables: clean bullet symbols inside tables
    text = text.replace("–Poor", "• Poor")
    text = text.replace("–Movement", "• Movement")
    text = text.replace("–Greater", "• Greater")
    text = text.replace("–Uncooperative", "• Uncooperative")
    text = text.replace("–Clotted", "• Clotted")
    text = text.replace("–Air", "• Air")
    text = text.replace("–Laboratory", "• Laboratory")
    
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text

pdf_path = Path("data/pdf_docs/WHO-Oxygen-therapy-for-children-2016.pdf")
out_path = Path("data/md_docs/WHO-Oxygen-therapy-for-children-2016.md")

print(f"Reading {pdf_path.name}...")
doc = pymupdf.open(pdf_path)
pymupdf4llm.use_layout(True)
chunks = pymupdf4llm.to_markdown(doc, page_chunks=True)
doc.close()

print(f"Extracted {len(chunks)} page chunks. Post-processing...")
page_sections = []
for i, chunk in enumerate(chunks, start=1):
    cleaned = clean_page(chunk["text"], i)
    page_sections.append(f"## Page {i}\n\n{cleaned}")

header = (
    f"# {pdf_path.stem}\n\n"
    f"| Field | Value |\n"
    f"| --- | --- |\n"
    f"| Source | `{pdf_path.name}` |\n"
    f"| Pages | {len(chunks)} |\n"
    f"| OCR pages | 0 |\n\n"
)

full_doc = header + "\n\n".join(page_sections) + "\n"
out_path.write_text(full_doc, encoding="utf-8")
print(f"Wrote {out_path.name}: {len(full_doc):,} chars, {len(page_sections)} pages")
