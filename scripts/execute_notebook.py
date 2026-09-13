"""Execute a notebook in a fresh kernel and save its outputs in place."""

from __future__ import annotations

import argparse
from pathlib import Path

import nbformat
from nbclient import NotebookClient


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("notebook", type=Path)
    parser.add_argument("--timeout", type=int, default=1200)
    args = parser.parse_args()
    notebook = args.notebook.resolve()
    with notebook.open("r", encoding="utf-8") as handle:
        document = nbformat.read(handle, as_version=4)
    client = NotebookClient(
        document, timeout=args.timeout, kernel_name="python3", resources={"metadata": {"path": str(notebook.parent)}}
    )
    client.execute()
    with notebook.open("w", encoding="utf-8", newline="\n") as handle:
        nbformat.write(document, handle)
    print(f"Executed and saved {notebook}")


if __name__ == "__main__":
    main()
