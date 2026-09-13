"""
Script to compile all documents in docs/findings into a single professional PDF.
"""

import os
import re
import subprocess
import markdown
import pymupdf

FINDINGS_DIR = r"C:\Users\PK\Desktop\projects\mobile_rag\docs\findings"
OUTPUT_HTML = os.path.join(FINDINGS_DIR, "findings_compiled.html")
TEMP_PDF = os.path.join(FINDINGS_DIR, "temp_render.pdf")
OUTPUT_PDF = os.path.join(FINDINGS_DIR, "Mobile_RAG_Findings_and_Integration_Handover.pdf")
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

SECTIONS = [
    {
        "filename": "README.md",
        "num": 1,
        "id": "sec-overview",
        "title": "Integration Overview & Source of Truth",
        "desc": "System reading order, Kotlin/Swift handover scope, and non-negotiable clinical safety gates."
    },
    {
        "filename": "01-findings.md",
        "num": 2,
        "id": "sec-findings",
        "title": "Technical Findings & Architecture Decisions",
        "desc": "Empirical benchmark evaluation (100 Q_S1 questions), failure taxonomy, and mobile preservation rules."
    },
    {
        "filename": "02-integration-contract.md",
        "num": 3,
        "id": "sec-contract",
        "title": "Kotlin & Swift Integration Contract",
        "desc": "Platform-neutral architecture boundaries, core schemas, SQLite/BM25 retrieval, and context packing."
    },
    {
        "filename": "03-prompts.md",
        "num": 4,
        "id": "sec-prompts",
        "title": "Generation Prompts & Output Schema",
        "desc": "Authoritative prompt v6, strict JSON schema, dynamic citation enums, and retry feedback."
    },
    {
        "filename": "04-test-and-release-checklist.md",
        "num": 5,
        "id": "sec-checklist",
        "title": "Test, Parity, and Release Checklist",
        "desc": "Phase 1-4 validation matrices, adversarial clinical test cases, device profiling, and release blockers."
    }
]

CSS_STYLES = """
@page {
    size: A4 portrait;
    margin: 18mm 15mm 18mm 15mm;
}

:root {
    --primary: #1e3a8a;
    --primary-light: #eff6ff;
    --primary-border: #bfdbfe;
    --secondary: #0f172a;
    --text-main: #334155;
    --text-heading: #0f172a;
    --text-muted: #64748b;
    --border-color: #e2e8f0;
    --bg-card: #f8fafc;
}

* {
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: var(--text-main);
    line-height: 1.55;
    font-size: 10pt;
    margin: 0;
    padding: 0;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
}

/* ==========================================
   Cover Page (strictly fits 1 A4 page)
   ========================================== */
.cover-page {
    page-break-after: always;
    padding-top: 10px;
}

.cover-badge {
    display: inline-block;
    background: #dbeafe;
    color: #1e40af;
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    padding: 4px 12px;
    border-radius: 16px;
    margin-bottom: 14px;
}

.cover-title {
    font-size: 24pt;
    font-weight: 800;
    color: #0f172a;
    line-height: 1.2;
    margin: 0 0 10px 0;
    letter-spacing: -0.4px;
}

.cover-subtitle {
    font-size: 11pt;
    color: #475569;
    line-height: 1.45;
    margin: 0 0 18px 0;
    font-weight: 400;
}

.meta-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    padding: 12px 16px;
    margin-bottom: 16px;
}

.meta-item {
    display: flex;
    flex-direction: column;
}

.meta-label {
    font-size: 7.5pt;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    font-weight: 700;
    color: var(--text-muted);
    margin-bottom: 2px;
}

.meta-val {
    font-size: 9pt;
    font-weight: 600;
    color: var(--secondary);
}

.cover-callout {
    background: #fff1f2;
    border-left: 4px solid #e11d48;
    padding: 10px 14px;
    border-radius: 0 6px 6px 0;
    margin-bottom: 18px;
}

.cover-callout h4 {
    margin: 0 0 4px 0;
    color: #9f1239;
    font-size: 8.5pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.cover-callout p {
    margin: 0;
    font-size: 8.5pt;
    color: #881337;
    line-height: 1.45;
}

/* TOC inside Cover */
.toc-container {
    background: #ffffff;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    padding: 14px 18px;
}

.toc-title {
    font-size: 10.5pt;
    font-weight: 700;
    color: var(--secondary);
    margin: 0 0 10px 0;
    border-bottom: 2px solid var(--primary);
    padding-bottom: 4px;
}

.toc-list {
    list-style: none;
    padding: 0;
    margin: 0;
}

.toc-item {
    margin-bottom: 8px;
    font-size: 9pt;
}

.toc-item-header {
    display: flex;
    align-items: center;
}

.toc-num {
    background: var(--primary);
    color: white;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 7.5pt;
    font-weight: 700;
    margin-right: 8px;
    flex-shrink: 0;
}

.toc-item a {
    text-decoration: none;
    color: var(--primary);
    font-weight: 600;
}

.toc-desc {
    color: var(--text-muted);
    font-size: 8pt;
    margin-left: 26px;
    display: block;
    line-height: 1.35;
}

/* ==========================================
   Section Styling & Layout
   ========================================== */
.section-wrapper {
    page-break-before: always;
}

.section-header {
    border-bottom: 2px solid #1e3a8a;
    padding-bottom: 8px;
    margin-bottom: 18px;
}

.section-tag {
    font-size: 8pt;
    font-weight: 700;
    color: var(--primary);
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 2px;
}

h1 {
    font-size: 17pt;
    font-weight: 800;
    color: var(--text-heading);
    margin: 0;
    line-height: 1.25;
}

h2 {
    font-size: 12.5pt;
    font-weight: 700;
    color: var(--secondary);
    margin-top: 20px;
    margin-bottom: 8px;
    border-bottom: 1px solid var(--border-color);
    padding-bottom: 3px;
    page-break-after: avoid;
}

h3 {
    font-size: 11pt;
    font-weight: 700;
    color: #1e293b;
    margin-top: 15px;
    margin-bottom: 6px;
    page-break-after: avoid;
}

h4 {
    font-size: 10pt;
    font-weight: 600;
    color: #334155;
    margin-top: 12px;
    margin-bottom: 4px;
    page-break-after: avoid;
}

p {
    margin-top: 0;
    margin-bottom: 10px;
}

/* Code & Pre Blocks */
pre {
    background-color: #0f172a;
    color: #f1f5f9;
    padding: 10px 14px;
    border-radius: 5px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 8.5pt;
    line-height: 1.45;
    overflow-x: auto;
    page-break-inside: avoid;
    border: 1px solid #334155;
    margin: 10px 0 14px 0;
    white-space: pre-wrap;
    word-break: break-word;
}

code {
    font-family: "Consolas", "Courier New", monospace;
    font-size: 8.5pt;
    background-color: #f1f5f9;
    color: #0f172a;
    padding: 1.5px 4px;
    border-radius: 3px;
    border: 1px solid #e2e8f0;
}

pre code {
    background-color: transparent;
    color: inherit;
    padding: 0;
    border: none;
    font-size: 8.5pt;
}

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 14px 0 18px 0;
    font-size: 8.5pt;
    page-break-inside: avoid;
}

th, td {
    padding: 6px 10px;
    text-align: left;
    vertical-align: top;
    border: 1px solid var(--border-color);
}

th {
    background-color: #1e293b;
    color: #ffffff;
    font-weight: 600;
    font-size: 8pt;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}

tr:nth-child(even) td {
    background-color: #f8fafc;
}

/* Lists and Checkboxes */
ul, ol {
    margin-top: 0;
    margin-bottom: 12px;
    padding-left: 20px;
}

li {
    margin-bottom: 4px;
}

.box-check {
    display: inline-block;
    width: 11px;
    height: 11px;
    border: 1.5px solid #64748b;
    border-radius: 2px;
    margin-right: 6px;
    vertical-align: -1px;
}

.box-check.checked {
    background-color: #16a34a;
    border-color: #16a34a;
}

/* Callouts / Blockquotes */
blockquote {
    border-left: 3.5px solid var(--primary);
    background-color: var(--primary-light);
    margin: 12px 0;
    padding: 8px 14px;
    border-radius: 0 4px 4px 0;
    font-style: italic;
    color: #1e3a8a;
    font-size: 9pt;
}
"""

def clean_and_enhance_md(content: str, sec_info: dict) -> str:
    lines = content.splitlines()
    if lines and lines[0].startswith('# '):
        original_h1 = lines[0][2:].strip()
        lines = lines[1:]
    else:
        original_h1 = sec_info['title']

    body_text = "\n".join(lines)

    # Convert checkboxes to clean HTML span boxes
    body_text = re.sub(r'^- \[ \] ', r'* <span class="box-check unchecked"></span> ', body_text, flags=re.MULTILINE)
    body_text = re.sub(r'^- \[x\] ', r'* <span class="box-check checked"></span> ', body_text, flags=re.MULTILINE)

    html_body = markdown.markdown(
        body_text,
        extensions=['tables', 'fenced_code', 'toc', 'sane_lists']
    )

    section_html = f"""
    <section class="section-wrapper" id="{sec_info['id']}">
        <div class="section-header">
            <div class="section-tag">Section {sec_info['num']} of {len(SECTIONS)}</div>
            <h1>{original_h1}</h1>
        </div>
        <div class="section-content">
            {html_body}
        </div>
    </section>
    """
    return section_html

def generate_cover_and_toc() -> str:
    toc_items = ""
    for sec in SECTIONS:
        toc_items += f"""
        <li class="toc-item">
            <div class="toc-item-header">
                <span class="toc-num">{sec['num']}</span>
                <a href="#{sec['id']}">{sec['title']}</a>
            </div>
            <span class="toc-desc">{sec['desc']}</span>
        </li>
        """

    return f"""
    <div class="cover-page">
        <div class="cover-badge">Engineering Handover & Architecture Dossier</div>
        <h1 class="cover-title">Mobile RAG: Findings & Integration Handover</h1>
        <p class="cover-subtitle">
            On-Device Clinical Retrieval-Augmented Generation for iOS & Android: 
            Benchmark Evaluation, Integration Contracts, Prompts & Release Criteria
        </p>

        <div class="meta-grid">
            <div class="meta-item">
                <span class="meta-label">Prepared Date</span>
                <span class="meta-val">14 September 2026</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Target Platforms</span>
                <span class="meta-val">iOS (Swift / SwiftUI) · Android (Kotlin / Compose)</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Reference Implementation</span>
                <span class="meta-val"><code>src/mobile_rag/</code> (Python 3.11)</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Document Status</span>
                <span class="meta-val">Handover & Production Baseline Specification</span>
            </div>
        </div>

        <div class="cover-callout">
            <h4>Mandatory Clinical Governance Statement</h4>
            <p>
                This is an engineering baseline and research prototype, not yet an unsupervised clinical decision-support system. 
                Citation-label validation proves that a returned label exists; it does not prove that every generated clinical claim 
                is entailed by the cited text. Clinical review, source governance, relevance gating, claim-support validation, 
                and physical-device testing remain prerequisite release gates.
            </p>
        </div>

        <div class="toc-container">
            <div class="toc-title">Table of Contents</div>
            <ul class="toc-list">
                {toc_items}
            </ul>
        </div>
    </div>
    """

def add_headers_footers_and_bookmarks(pdf_in: str, pdf_out: str):
    doc = pymupdf.open(pdf_in)
    total_pages = len(doc)
    print(f"Total pages rendered: {total_pages}")

    toc_entries = []
    toc_entries.append([1, "Cover & Executive Overview", 1])

    for page_num in range(total_pages):
        page = doc[page_num]
        text = page.get_text()

        for sec in SECTIONS:
            marker = f"SECTION {sec['num']} OF {len(SECTIONS)}"
            if marker in text.upper():
                toc_entries.append([1, f"Section {sec['num']}: {sec['title']}", page_num + 1])

        # Running Header and Footer on pages 2..total_pages
        if page_num > 0:
            rect = page.rect

            # Header rule
            page.draw_line(
                pymupdf.Point(42, 38),
                pymupdf.Point(rect.width - 42, 38),
                color=(0.82, 0.86, 0.92),
                width=0.75
            )
            # Header text (using ASCII / helv safe characters)
            page.insert_text(
                pymupdf.Point(42, 32),
                "Mobile RAG Integration Handover",
                fontsize=8,
                color=(0.35, 0.42, 0.52),
                fontname="helv"
            )
            header_right = "Technical Specifications & Handover"
            page.insert_text(
                pymupdf.Point(rect.width - 42 - 165, 32),
                header_right,
                fontsize=8,
                color=(0.35, 0.42, 0.52),
                fontname="helv"
            )

            # Footer rule
            footer_line_y = rect.height - 36
            page.draw_line(
                pymupdf.Point(42, footer_line_y),
                pymupdf.Point(rect.width - 42, footer_line_y),
                color=(0.85, 0.88, 0.92),
                width=0.75
            )
            # Footer text
            footer_left = "Confidential | Healthcare On-Device RAG Dossier"
            page.insert_text(
                pymupdf.Point(42, footer_line_y + 15),
                footer_left,
                fontsize=8,
                color=(0.45, 0.5, 0.58),
                fontname="helv"
            )
            footer_page_text = f"Page {page_num + 1} of {total_pages}"
            page.insert_text(
                pymupdf.Point(rect.width - 42 - 60, footer_line_y + 15),
                footer_page_text,
                fontsize=8,
                color=(0.2, 0.25, 0.35),
                fontname="helv"
            )

    doc.set_toc(toc_entries)
    doc.set_metadata({
        "title": "Mobile RAG: Findings & Integration Handover",
        "author": "Mobile RAG Engineering Team",
        "subject": "On-device Clinical RAG Benchmark Evaluation, Integration Contracts, Prompts & Release Criteria",
        "keywords": "RAG, Mobile, On-Device, Clinical, Healthcare, BM25, Gemma, Kotlin, Swift, Evaluation",
        "creator": "PyMuPDF & Microsoft Edge Headless"
    })
    doc.save(pdf_out)
    doc.close()
    print(f"Saved finalized PDF with headers, footers & bookmarks to: {pdf_out}")

def main():
    print("Combining findings markdown files...")
    content_html_parts = []
    
    # 1. Cover & TOC
    cover_html = generate_cover_and_toc()
    content_html_parts.append(cover_html)

    # 2. Sections
    for sec in SECTIONS:
        file_path = os.path.join(FINDINGS_DIR, sec['filename'])
        if not os.path.exists(file_path):
            print(f"Warning: {file_path} not found!")
            continue
        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
        sec_html = clean_and_enhance_md(raw_text, sec)
        content_html_parts.append(sec_html)

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Mobile RAG: Findings & Integration Handover</title>
    <style>
        {CSS_STYLES}
    </style>
</head>
<body>
    {''.join(content_html_parts)}
</body>
</html>
"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"Wrote compiled HTML to {OUTPUT_HTML}")

    print("Rendering HTML to initial PDF via Microsoft Edge...")
    cmd = [
        EDGE_PATH,
        "--headless",
        "--disable-gpu",
        "--run-all-compositor-stages-before-draw",
        "--no-pdf-header-footer",
        f"--print-to-pdf={TEMP_PDF}",
        OUTPUT_HTML
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("Edge failed:", res.stderr)
        return
    print("Edge rendering complete.")

    print("Adding running headers, footers, page numbers and PDF outline...")
    add_headers_footers_and_bookmarks(TEMP_PDF, OUTPUT_PDF)

    if os.path.exists(TEMP_PDF):
        os.remove(TEMP_PDF)

    file_size_kb = os.path.getsize(OUTPUT_PDF) / 1024
    print(f"SUCCESS: Generated {OUTPUT_PDF} ({file_size_kb:.1f} KB)")

if __name__ == "__main__":
    main()

