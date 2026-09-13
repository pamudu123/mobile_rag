"""Convert PDF documents into clean, human-readable Markdown with preserved tables and page markers."""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

import pymupdf
import pymupdf4llm

# Configure UTF-8 stdout
sys.stdout.reconfigure(encoding="utf-8")

# Common running headers to strip from pages
RUNNING_HEADERS = [
    r"^OXYGEN THERAPY FOR CHILDREN\s*$",
    r"^Oxygen therapy for children\s*$",
    r"^PACIFIC OUTBREAK MANUAL\s*[-–—]?\s*(?:March 2016)?\s*$",
    r"^PPHSN Pacific Outbreak Manual\s*[-–—]?\s*(?:March 2016)?\s*$",
    r"^Standard Treatment for Common Illnesses of Children.*$",
    r"^NATIONAL CLINICAL GUIDELINES FOR HIV.*$",
    r"^WHO operational handbook on tuberculosis.*$",
    r"^POCKET BOOK OF Hospital care for children.*$",
    r"^CHILD HEALTH FOR NURSES AND HEOS.*$",
    r"^PAEDIATRICS FOR DOCTORS IN PAPUA NEW GUINEA.*$",
    r"^\d+\s*\|\s*P\s*a\s*g\s*e\s*$",
    r"^Page\s+\d+\s+of\s+\d+\s*$",
]

RUNNING_HEADER_PATTERNS = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in RUNNING_HEADERS]


def clean_page_markdown(text: str, page_num: int) -> str:
    """Clean up extracted markdown for a single page."""
    # 1. Remove null bytes from embedded font encodings
    text = text.replace("\x00", "")

    # 2. Fix known encoding / OCR glyphs
    text = text.replace("acid\ufffdbase", "acid-base")
    text = text.replace("acidbase", "acid-base")
    text = text.replace("\ufffd", "–")
    text = text.replace("", "-")
    text = text.replace("cmH20", "cmH2O")
    text = text.replace("brochioitis", "bronchiolitis")
    text = text.replace("diarhoea", "diarrhoea")
    text = text.replace("sulfamethoxozole", "sulfamethoxazole")
    text = text.replace("WHo ", "WHO ")
    text = text.replace("HIv", "HIV")
    text = text.replace("«", "<")

    # 3. Remove HTML picture markers
    text = re.sub(r"<!--\s*Start of picture text\s*-->", "", text)
    text = re.sub(r"<!--\s*End of picture text\s*-->", "", text)

    # 4. Remove running headers
    for pat in RUNNING_HEADER_PATTERNS:
        text = pat.sub("", text)

    # 5. Remove standalone orphan page numbers at end or start of page
    lines = text.splitlines()
    filtered_lines = []
    for line in lines:
        stripped = line.strip()
        # Page numbers like "12", "iv", "vi", "123" on their own line
        if re.match(r"^(?:\d+|[ivxlcdm]+)\s*$", stripped, re.IGNORECASE):
            # If it matches current page number or close to it, drop it
            try:
                val = int(stripped)
                if abs(val - page_num) <= 30 or val < 1000:
                    continue
            except ValueError:
                if len(stripped) <= 4:
                    continue
        filtered_lines.append(line)

    text = "\n".join(filtered_lines)

    # 6. Normalize whitespace
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def extract_existing_page_text(existing_md_path: Path, page_num: int) -> str:
    """Retrieve text of a specific page from existing markdown if available."""
    if not existing_md_path.exists():
        return ""
    content = existing_md_path.read_text(encoding="utf-8", errors="ignore")
    marker = f"## Page {page_num}\n"
    if marker not in content:
        return ""
    start = content.index(marker) + len(marker)
    next_marker = f"\n## Page {page_num + 1}\n"
    if next_marker in content:
        end = content.index(next_marker, start)
        return content[start:end].strip()
    return content[start:].strip()


def convert_document(pdf_path: Path, output_path: Path, force: bool = False) -> dict:
    """Convert a single PDF document to human-readable Markdown."""
    t0 = time.time()
    doc = pymupdf.open(pdf_path)
    total_pages = len(doc)
    page_texts: list[str] = []
    ocr_pages = 0

    print(f"[{pdf_path.name}] Processing {total_pages} pages...")

    # Enable layout analysis for rich table & header extraction
    pymupdf4llm.use_layout(True)

    for page_idx in range(total_pages):
        page_num = page_idx + 1
        page = doc[page_idx]
        raw_text = page.get_text().strip()

        # Check if page is low-text / scanned
        if len(raw_text) < 30:
            existing = extract_existing_page_text(output_path, page_num)
            if existing:
                page_texts.append(f"## Page {page_num}\n\n{existing}")
                ocr_pages += 1
                continue
            # If no existing text, attempt extraction anyway
            try:
                md_chunk = pymupdf4llm.to_markdown(doc, pages=[page_idx], page_chunks=False)
                clean_md = clean_page_markdown(md_chunk, page_num)
                page_texts.append(f"## Page {page_num}\n\n{clean_md}")
            except Exception as e:
                page_texts.append(f"## Page {page_num}\n\n*[Page {page_num} contains image or illustration]*")
            continue

        try:
            md_chunk = pymupdf4llm.to_markdown(doc, pages=[page_idx], page_chunks=False)
            clean_md = clean_page_markdown(md_chunk, page_num)
            page_texts.append(f"## Page {page_num}\n\n{clean_md}")
        except Exception as e:
            print(f"  Warning: page {page_num} layout extraction error: {e}. Falling back...")
            pymupdf4llm.use_layout(False)
            md_chunk = pymupdf4llm.to_markdown(doc, pages=[page_idx], page_chunks=False)
            pymupdf4llm.use_layout(True)
            clean_md = clean_page_markdown(md_chunk, page_num)
            page_texts.append(f"## Page {page_num}\n\n{clean_md}")

        if page_num % 50 == 0 or page_num == total_pages:
            print(f"  Processed page {page_num}/{total_pages} ({time.time()-t0:.1f}s)")

    doc.close()

    # Form metadata header
    title = pdf_path.stem
    header = (
        f"# {title}\n\n"
        f"| Field | Value |\n"
        f"| --- | --- |\n"
        f"| Source | `{pdf_path.name}` |\n"
        f"| Pages | {total_pages} |\n"
        f"| OCR pages | {ocr_pages} |\n\n"
    )

    full_text = header + "\n\n".join(page_texts) + "\n"
    # Clean redundant blank lines across whole doc
    full_text = re.sub(r"\n{3,}", "\n\n", full_text)

    output_path.write_text(full_text, encoding="utf-8")
    elapsed = time.time() - t0
    print(f"Completed {pdf_path.name}: {total_pages} pages, {len(full_text):,} chars in {elapsed:.1f}s\n")

    return {
        "name": pdf_path.name,
        "pages": total_pages,
        "chars": len(full_text),
        "seconds": elapsed,
    }


def main():
    parser = argparse.ArgumentParser(description="Convert PDF to human-readable Markdown.")
    parser.add_argument("--pdf", type=str, help="Specific PDF filename to process")
    parser.add_argument("--all-unformatted", action="store_true", help="Process all 9 unformatted PDFs")
    args = parser.parse_args()

    pdf_dir = Path("data/pdf_docs")
    md_dir = Path("data/md_docs")

    if args.pdf:
        pdf_path = pdf_dir / args.pdf
        out_path = md_dir / f"{pdf_path.stem}.md"
        convert_document(pdf_path, out_path, force=True)
        return

    # List of 9 unformatted PDFs in order of size
    unformatted_pdfs = [
        "WHO-Oxygen-therapy-for-children-2016.pdf",
        "Pacific-Outbreak-Manual-Pacific-Public-Health-Surveillance-Network-PPHSN.pdf",
        "HIV Treatment Guidelines 2019.pdf",
        "PNG-Standard-Treatment-Book-10th-edition-2016.pdf",
        "PNG-Standard-Treatment-Manual-for-Obstetrics-and-Gynaecology-7th-Edition-2018.pdf",
        "WHO Guidelines for TB.pdf",
        "WHO-Pocket-Book-Hospital-Care-for-Children-2nd-Edition-2013.pdf",
        "Child-Health-for-Nurses-and-HEOs-in-Papua-New-Guinea-3th-Edition-March-2022.pdf",
        "Paediatrics-for-Doctors-in-Papua-New-Guinea.pdf",
    ]

    for name in unformatted_pdfs:
        pdf_path = pdf_dir / name
        out_path = md_dir / f"{pdf_path.stem}.md"
        convert_document(pdf_path, out_path, force=True)


if __name__ == "__main__":
    main()

