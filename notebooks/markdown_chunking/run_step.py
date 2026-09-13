"""Run Step 5 without Jupyter."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mobile_rag.corpus import (
    build_chunks,
    export_chunks,
    latest_inventory_manifest,
    validate_chunks,
)


def main(output_root: Path, inventory_path: Path | None = None) -> None:
    inventory = inventory_path or latest_inventory_manifest(PROJECT_ROOT)
    bundle = build_chunks(PROJECT_ROOT, inventory)
    checks = validate_chunks(bundle, PROJECT_ROOT)
    if not checks["passed"]:
        raise RuntimeError(f"Chunk checks failed: {checks}")
    output = export_chunks(bundle, PROJECT_ROOT, output_root=output_root)
    print(output.resolve())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--inventory", type=Path)
    args = parser.parse_args()
    main(args.output_root, args.inventory)
