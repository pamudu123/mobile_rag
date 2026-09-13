"""Scan markdown docs for common OCR issues."""

from __future__ import annotations

import re
from pathlib import Path


def scan_file(path: Path) -> dict[str, int]:
    text = path.read_text(encoding="utf-8")
    stats: dict[str, int] = {}

    ctrl = re.findall(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", text)
    if ctrl:
        stats["control_chars"] = len(ctrl)

    lig = len(re.findall(r"[\uFB00-\uFB06]", text))
    if lig:
        stats["ligatures"] = lig

    for pattern, name in [
        (r"cmH20\b", "cmH20"),
        (r"\bMl/kg\b", "Ml/kg"),
        (r"\bxray\b", "xray"),
        (r"brochioitis", "brochioitis"),
        (r"diarhoea", "diarhoea"),
        (r"sulfamethoxozole", "sulfamethoxozole"),
        (r"WHo ", "WHo"),
        (r"HIv\b", "HIv"),
        (r"^•\s*$", "broken_bullets"),
        (r"^## Page \d+\s*$", "empty_pages"),
    ]:
        count = len(re.findall(pattern, text, re.M))
        if count:
            stats[name] = count

    return stats


def main() -> None:
    base = Path("data/md_docs")
    for path in sorted(base.glob("*.md")):
        stats = scan_file(path)
        if stats:
            parts = ", ".join(f"{k}={v}" for k, v in stats.items())
            print(f"{path.name}: {parts}")


if __name__ == "__main__":
    main()
