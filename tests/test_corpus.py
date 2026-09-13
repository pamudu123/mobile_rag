from __future__ import annotations

import json
from pathlib import Path

import pymupdf

from mobile_rag.corpus import build_chunks, build_inventory, parse_markdown, validate_chunks, validate_inventory


def _write_pdf(path: Path, text: str = "source") -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    document.save(path)
    document.close()


def test_inventory_matches_sources_and_reports_orphans(tmp_path: Path) -> None:
    (tmp_path / "data/pdf_docs").mkdir(parents=True)
    (tmp_path / "data/md_docs").mkdir(parents=True)
    _write_pdf(tmp_path / "data/pdf_docs/Guide.pdf")
    (tmp_path / "data/md_docs/Guide.md").write_text(
        "# Guide\n\n| Field | Value |\n| --- | --- |\n| Source | `Guide.pdf` |\n\n## Page 1\n\nAdvice.\n",
        encoding="utf-8",
    )
    (tmp_path / "data/md_docs/Orphan.md").write_text("# Orphan\n", encoding="utf-8")

    inventory = build_inventory(tmp_path)
    assert validate_inventory(inventory)["passed"]
    assert len(inventory["pdf_contents"]) == 1
    assert any(item["status"] == "matched" for item in inventory["pairings"])
    assert any(item["code"] == "markdown_pdf_pairing" for item in inventory["issues"])


def test_parse_markdown_preserves_exact_crlf_unicode_slices() -> None:
    text = "# Café\r\n\r\n## Page 1\r\n\r\nDose ≤ 5 mg.\r\n\r\n- if eligible\r\n- do not infer\r\n"
    passages = parse_markdown(text, "abc")
    assert passages
    for passage in passages:
        assert text[passage["start_offset"] : passage["end_offset"]] == passage["text"]
    assert any(item["declared_page"] == 1 for item in passages)
    assert any(item["kind"] == "list" for item in passages)


def test_chunk_build_is_deterministic_and_keeps_table_atomic(tmp_path: Path) -> None:
    (tmp_path / "data/pdf_docs").mkdir(parents=True)
    (tmp_path / "data/md_docs").mkdir(parents=True)
    _write_pdf(tmp_path / "data/pdf_docs/Table.pdf")
    rows = "".join(f"| {number} | {number} mg |\n" for number in range(150))
    source = (
        "# Table\n\n| Field | Value |\n| --- | --- |\n| Source | `Table.pdf` |\n\n## Page 1\n\n### Dose table\n\n| Weight | Dose |\n| --- | --- |\n"
        + rows
    )
    (tmp_path / "data/md_docs/Table.md").write_text(source, encoding="utf-8")
    inventory = build_inventory(tmp_path)
    manifest = tmp_path / "artifacts/01_corpus_inventory/test/corpus_manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps(inventory), encoding="utf-8")

    first = build_chunks(tmp_path, manifest)
    second = build_chunks(tmp_path, manifest)
    assert validate_chunks(first, tmp_path)["passed"]
    assert [item["chunk_id"] for item in first["chunks"]] == [item["chunk_id"] for item in second["chunks"]]
    table_passages = [item for item in first["passages"] if item["kind"] == "table"]
    assert any(len(item["text"]) > 1000 for item in table_passages)
    assert any("oversized" in item["flags"] for item in first["chunks"])
