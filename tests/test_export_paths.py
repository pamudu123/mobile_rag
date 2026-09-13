import re

from mobile_rag.corpus import build_chunks, build_inventory, export_chunks, export_inventory


def test_exports_outside_project_can_feed_chunking(tmp_path):
    project = tmp_path / "project"
    (project / "data/pdf_docs").mkdir(parents=True)
    (project / "data/md_docs").mkdir()
    (project / "data/md_docs/example.md").write_text("# Example\n\nSource text.\n", encoding="utf-8")
    inventory = export_inventory(build_inventory(project), project, output_root=tmp_path / "external_inventory")
    bundle = build_chunks(project, inventory / "corpus_manifest.json")
    chunks = export_chunks(bundle, project, output_root=tmp_path / "external_chunks")
    assert inventory.parent == tmp_path / "external_inventory"
    assert chunks.parent == tmp_path / "external_chunks"
    assert (chunks / "chunks.jsonl").is_file()
    assert not (project / "artifacts").exists()
    assert re.fullmatch(r"\d{8}_\d{6}", inventory.name)
    assert re.fullmatch(r"\d{8}_\d{6}", chunks.name)
