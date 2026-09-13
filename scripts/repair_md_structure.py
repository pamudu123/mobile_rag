"""Repair markdown structure after over-aggressive OCR cleanup."""

from __future__ import annotations

import re
from pathlib import Path


def repair_metadata_header(text: str) -> str:
    return re.sub(
        r"^(# [^\n|]+)\s*\|\s*Field\s*\|\s*Value\s*\|",
        r"\1\n\n| Field | Value |",
        text,
        count=1,
    )


def repair_inline_page_markers(text: str) -> str:
    return re.sub(
        r"([^\n])\s+(## Page \d+)\s*$",
        r"\1\n\n\2",
        text,
        flags=re.MULTILINE,
    )


def repair_page_markers(text: str) -> str:
    text = re.sub(
        r"(## Page \d+)\s+(#{1,3}\s)",
        r"\1\n\n\2",
        text,
    )
    text = re.sub(
        r"(## Page \d+)\s+([^\n#])",
        r"\1\n\n\2",
        text,
    )
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text


def repair_paediatrics_title(text: str) -> str:
    if "Paediatrics-for-Doctors" not in text[:200]:
        return text
    text = text.replace(
        "AGUIDEFORDOCTORS PROVIDING HEALTH SERVICES FORCHILDREN\n"
        "PAEDIATRICS\n"
        "FORDOCTORS\n"
        "INPAPUANEWGUINEA\n",
        "A GUIDE FOR DOCTORS PROVIDING HEALTH SERVICES FOR CHILDREN\n\n"
        "PAEDIATRICS\n"
        "FOR DOCTORS\n"
        "IN PAPUA NEW GUINEA\n",
    )
    text = text.replace(
        "Second Edition 2003 ## Page 2",
        "Second Edition 2003\n\n## Page 2",
    )
    text = text.replace(
        "ISBN 9980-85-411-1 Cover photographs by Trevor Duke",
        "ISBN 9980-85-411-1\n\nCover photographs by Trevor Duke",
    )
    return text


def repair_nested_list_indent(text: str) -> str:
    return re.sub(r"^ \-", "  -", text, flags=re.MULTILINE)


def remove_empty_consecutive_pages(text: str) -> str:
    while True:
        new_text, n = re.subn(
            r"(## Page \d+)\n\n(## Page \d+\n\n(?![#]))",
            r"\2",
            text,
        )
        if not n:
            return text
        text = new_text


def process_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    text = original
    text = repair_metadata_header(text)
    text = repair_inline_page_markers(text)
    text = repair_page_markers(text)
    text = repair_paediatrics_title(text)
    text = repair_nested_list_indent(text)
    text = remove_empty_consecutive_pages(text)
    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    base = Path("data/md_docs")
    changed = 0
    for path in sorted(base.glob("*.md")):
        if process_file(path):
            print(f"repaired: {path.name}")
            changed += 1
    print(f"Total repaired: {changed}")


if __name__ == "__main__":
    main()
