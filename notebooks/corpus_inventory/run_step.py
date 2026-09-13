"""Run Step 2 without Jupyter."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mobile_rag.corpus import build_inventory, export_inventory, validate_inventory


def main(output_root: Path) -> None:
    inventory = build_inventory(PROJECT_ROOT)
    checks = validate_inventory(inventory)
    if not checks["passed"]:
        raise RuntimeError(f"Inventory checks failed: {checks}")
    output = export_inventory(inventory, PROJECT_ROOT, output_root=output_root)
    print(output.resolve())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    main(parser.parse_args().output_root)
