"""Deep OCR cleanup for Child Health for Nurses (PNG, 2022)."""

from __future__ import annotations

import re
from pathlib import Path

TARGET = Path("data/md_docs/Child-Health-for-Nurses-and-HEOs-in-Papua-New-Guinea-3th-Edition-March-2022.md")

REPLACEMENTS: list[tuple[str, str]] = [
    ("", "-"),
    ("🗝Key Message:", "**Key message:**"),
    ("🗝Key message:", "**Key message:**"),
    ("Artemetherlumefantrine", "Artemether-Lumefantrine"),
    ("If child weights", "If child weighs"),
    ("50-100mls inbetween", "50-100 ml in between"),
    ("100mls in", "100 ml in"),
    ("less than 10Kg", "less than 10 kg"),
    ("than 10Kg", "than 10 kg"),
    ("change back to F100 or MOF not \navailable.", "change back to F-100 or MOF when available."),
    ("change back to F100 or MOF not\navailable.", "change back to F-100 or MOF when available."),
    ("change back to F100 or MOF not available.", "change back to F-100 or MOF when available."),
    ("0.6mls", "0.6 ml"),
    ("4weeks", "4 weeks"),
    ("5-9.9Kg", "5-9.9 kg"),
    ("10-19.9Kg", "10-19.9 kg"),
    ("20.39.9Kg", "20-39.9 kg"),
    ("40-49.9Kg", "40-49.9 kg"),
    ("11/2 ", "1 1/2\n\n-"),
    ("11/2 -", "1 1/2\n\n-"),
    ("9 to 12months", "9 to 12 months"),
    ("18-24months", "18-24 months"),
    ("125mg in 5mls", "125 mg in 5 ml"),
    ("antivenom to 100mls of", "antivenom to 100 ml of"),
    ("a dose of 2mls", "a dose of 2 ml"),
    ("more than 5mls", "more than 5 ml"),
    (" 40ml ", " 40 ml "),
    (" 60ml ", " 60 ml "),
    (" 80ml ", " 80 ml "),
    (" 100ml ", " 100 ml "),
    ("6mls", "6 ml"),
]

IRON_TABLE_OLD = """Dose of oral iron (Fefol Tablets) 
Weight 
 
5-9.9 kg 
1/4 10-19.9 kg 
1/2 20-39.9 kg 
1 40-49.9 kg 
11/2 - Tell the parents to keep the tablets"""

IRON_TABLE_NEW = """Dose of oral iron (Fefol Tablets)

| Weight (kg) | Dose (Fefol tablet) |
| --- | --- |
| 5–9.9 | 1/4 |
| 10–19.9 | 1/2 |
| 20–39.9 | 1 |
| 40–49.9 | 1 1/2 |

- Tell the parents to keep the tablets"""

PAGE2_OLD = """## Page 2

Inside page, title, author 
Child Health for nurses and health extension officers in Papua New Guinea 
 
Publication/publisher details"""

PAGE2_NEW = """## Page 2

*Inside cover — title and publication details (scanned page; minimal text extracted).*"""


def parse_toc_line(line: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for match in re.finditer(r"(Chapter\s+[^\.]+?)\s*\.{2,}\s*(\d+)", line):
        title = re.sub(r"\s+", " ", match.group(1)).strip()
        page = match.group(2)
        entries.append((title, page))
    return entries


def rebuild_toc(text: str) -> str:
    marker = "## Page 3\n\nContents \n"
    if marker not in text:
        return text

    start = text.index(marker) + len(marker)
    end = text.index("\n\n## Page 5", start)
    toc_block = text[start:end]
    lines = [ln.strip() for ln in toc_block.splitlines() if ln.strip() and ln.strip() != "Contents"]

    entries: list[tuple[str, str]] = []
    for line in lines:
        entries.extend(parse_toc_line(line))

    if not entries:
        return text

    toc_md = marker + "\n".join(f"- {title} (p. {page})" for title, page in entries) + "\n"
    return text[: text.index(marker)] + toc_md + text[end:]


def remove_empty_consecutive_pages(text: str) -> str:
    return re.sub(
        r"(## Page \d+)\n\n(## Page \d+\n\n(?![#]))",
        r"\2",
        text,
    )


def process(text: str) -> str:
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)

    if IRON_TABLE_OLD.split("\n")[0] in text:
        # Try flexible match for iron table after replacements
        pattern = (
            r"Dose of oral iron \(Fefol Tablets\)\s+Weight\s+"
            r"5-9\.9 kg\s+1/4 10-19\.9 kg\s+1/2 20-39\.9 kg\s+"
            r"1 40-49\.9 kg\s+1 1/2\s+- Tell the parents to keep the tablets"
        )
        text = re.sub(pattern, IRON_TABLE_NEW.replace("\n", " ").replace("  ", " "), text, count=1)
        text = text.replace(
            "Dose of oral iron (Fefol Tablets) \nWeight \n \n5-9.9 kg \n1/4 10-19.9 kg \n1/2 20-39.9 kg \n1 40-49.9 kg \n1 1/2 \n\n- Tell the parents to keep the tablets",
            IRON_TABLE_NEW,
        )

    text = text.replace(PAGE2_OLD, PAGE2_NEW)
    text = rebuild_toc(text)
    text = remove_empty_consecutive_pages(text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text


def main() -> None:
    original = TARGET.read_text(encoding="utf-8")
    cleaned = process(original)
    if cleaned != original:
        TARGET.write_text(cleaned, encoding="utf-8")
        print(f"Fixed {TARGET.name}")
    else:
        print("No changes needed")


if __name__ == "__main__":
    main()
