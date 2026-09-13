"""Parallel PDF text extraction with OCR fallback for scanned pages."""

from __future__ import annotations

import argparse
import io
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import pymupdf
from PIL import Image
from rapidocr_onnxruntime import RapidOCR


MIN_PAGE_CHARS = 30
DEFAULT_DPI = 200


@dataclass
class PdfResult:
    pdf_name: str
    pages: int
    method: str
    chars: int
    seconds: float
    output_path: str
    error: str | None = None


def _ocr_page(page: pymupdf.Page, ocr: RapidOCR, dpi: int) -> str:
    pix = page.get_pixmap(dpi=dpi)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    result, _ = ocr(img)
    if not result:
        return ""
    return "\n".join(line[1] for line in result)


def _extract_page_text(page: pymupdf.Page, ocr: RapidOCR | None, dpi: int) -> tuple[str, bool]:
    text = page.get_text().strip()
    if len(text) >= MIN_PAGE_CHARS:
        return text, False
    if ocr is None:
        return text, False
    return _ocr_page(page, ocr, dpi).strip(), True


def process_pdf(pdf_path: str, output_dir: str, dpi: int = DEFAULT_DPI) -> PdfResult:
    start = time.perf_counter()
    pdf = Path(pdf_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"{pdf.stem}.md"

    try:
        doc = pymupdf.open(pdf)
        ocr: RapidOCR | None = None
        page_texts: list[str] = []
        ocr_pages = 0

        for page_num, page in enumerate(doc, start=1):
            text, used_ocr = _extract_page_text(page, ocr, dpi)
            if used_ocr:
                ocr_pages += 1
            elif len(text) < MIN_PAGE_CHARS and ocr is None:
                ocr = RapidOCR()
                text, used_ocr = _extract_page_text(page, ocr, dpi)
                if used_ocr:
                    ocr_pages += 1

            page_texts.append(f"## Page {page_num}\n\n{text}")

        doc.close()

        body = "\n\n".join(page_texts)
        header = (
            f"# {pdf.stem}\n\n"
            f"| Field | Value |\n"
            f"| --- | --- |\n"
            f"| Source | `{pdf.name}` |\n"
            f"| Pages | {len(page_texts)} |\n"
            f"| OCR pages | {ocr_pages} |\n\n"
        )
        output_path.write_text(header + body, encoding="utf-8")

        method = "ocr" if ocr_pages else "native"
        if ocr_pages and ocr_pages < len(page_texts):
            method = "mixed"

        return PdfResult(
            pdf_name=pdf.name,
            pages=len(page_texts),
            method=method,
            chars=len(body),
            seconds=time.perf_counter() - start,
            output_path=str(output_path),
        )
    except Exception as exc:  # noqa: BLE001
        return PdfResult(
            pdf_name=pdf.name,
            pages=0,
            method="error",
            chars=0,
            seconds=time.perf_counter() - start,
            output_path=str(output_path),
            error=str(exc),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract/OCR PDFs in parallel.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/pdf_docs"),
        help="Directory containing source PDFs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/md_docs"),
        help="Directory to write extracted .md files.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Parallel worker processes.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=DEFAULT_DPI,
        help="Render DPI for OCR pages.",
    )
    parser.add_argument(
        "pdfs",
        nargs="*",
        help="Optional specific PDF filenames to process.",
    )
    args = parser.parse_args()

    if args.pdfs:
        pdf_paths = [args.input_dir / name for name in args.pdfs]
    else:
        pdf_paths = sorted(args.input_dir.glob("*.pdf"))

    pdf_paths = [p for p in pdf_paths if p.exists()]
    if not pdf_paths:
        print("No PDFs found.", file=sys.stderr)
        return 1

    print(f"Processing {len(pdf_paths)} PDFs with {args.workers} workers...")
    results: list[PdfResult] = []

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(process_pdf, str(p), str(args.output_dir), args.dpi): p
            for p in pdf_paths
        }
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            status = "OK" if not result.error else f"ERROR: {result.error}"
            print(
                f"[{status}] {result.pdf_name} "
                f"({result.method}, {result.pages} pages, "
                f"{result.chars:,} chars, {result.seconds:.1f}s)"
            )

    results.sort(key=lambda r: r.pdf_name.lower())
    failed = [r for r in results if r.error]
    print(f"\nDone: {len(results) - len(failed)}/{len(results)} succeeded.")
    if failed:
        for item in failed:
            print(f"  FAILED: {item.pdf_name} -> {item.error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
