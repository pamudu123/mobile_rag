import re
import sys
from pathlib import Path

# Force utf-8 stdout
sys.stdout.reconfigure(encoding='utf-8')

docs = sorted(Path('data/md_docs').glob('*.md'))
for p in docs:
    text = p.read_text(encoding='utf-8', errors='ignore')
    lines = [l for l in text.splitlines() if l.strip()]
    pages = [l for l in lines if l.startswith('## Page ')]
    tables = [l for l in lines if l.startswith('|')]
    h2_or_h3 = [l for l in lines if re.match(r'^#{2,4}\s+(?!Page\s+\d+)', l)]
    sample = lines[10:15] if len(lines) > 15 else lines
    print(f"=== {p.name} ===")
    print(f"  Pages: {len(pages)} | Content Lines: {len(lines)} | Headings (H2-H4): {len(h2_or_h3)} | Table lines: {len(tables)}")
    for s in sample:
        print(f"  | {s[:90]}")
    print()

