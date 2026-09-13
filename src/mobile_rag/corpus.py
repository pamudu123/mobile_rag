"""Deterministic corpus inventory and Markdown chunk preparation.

This module deliberately contains no OCR, embedding, retrieval, or model code.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pymupdf

INVENTORY_SCHEMA = "mobile-rag-corpus-inventory/v1"
CHUNK_SCHEMA = "mobile-rag-chunks/v1"
PARSER_VERSION = "markdown-blocks/v1"
CHUNK_CONFIG = {
    "version": "clinical-structure/v2",
    "target_min_chars": 600,
    "target_max_chars": 1000,
    "overlap": "none; explicit heading context and neighbor links",
}
PAGE_RE = re.compile(r"^##\s+Page\s+(\d+)\s*$", re.IGNORECASE)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
SOURCE_RE = re.compile(r"^\|\s*Source\s*\|\s*`?([^|`]+?\.pdf)`?\s*\|\s*$", re.IGNORECASE | re.MULTILINE)
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*$")
LIST_RE = re.compile(r"^\s*(?:[-+*]|\d+[.)])\s+")


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_utf8_exact(path: Path) -> str:
    with path.open("r", encoding="utf-8", errors="strict", newline="") as handle:
        return handle.read()


def _file_record(path: Path, root: Path, expected_location: bool) -> dict[str, Any]:
    rel = path.relative_to(root).as_posix()
    try:
        digest = sha256_file(path)
        status, error = "readable", None
    except OSError as exc:
        digest = None
        status, error = "unreadable", f"{type(exc).__name__}: {exc}"
    return {
        "file_id": "file_" + stable_hash(rel)[:16],
        "relative_path": rel,
        "extension": path.suffix.lower(),
        "size_bytes": path.stat().st_size if path.exists() else None,
        "sha256": digest,
        "read_status": status,
        "error": error,
        "expected_location": expected_location,
    }


def _markdown_structure(path: Path, record: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "file_id": record["file_id"],
        "decoding_status": "unreadable",
        "source_declaration": None,
        "character_count": None,
        "heading_counts": {},
        "page_markers": [],
        "table_count": 0,
        "structural_flags": [],
        "transcription_review_status": "not_assessed",
    }
    try:
        text = _read_utf8_exact(path)
    except (OSError, UnicodeDecodeError) as exc:
        result["structural_flags"].append(f"decode_error:{type(exc).__name__}")
        return result
    result["decoding_status"] = "readable"
    result["character_count"] = len(text)
    if not text.strip():
        result["structural_flags"].append("empty_or_whitespace")
    source = SOURCE_RE.search(text)
    result["source_declaration"] = source.group(1).strip() if source else None
    headings: Counter[int] = Counter()
    pages: list[int] = []
    lines = text.splitlines()
    for line in lines:
        match = HEADING_RE.match(line)
        if match:
            headings[len(match.group(1))] += 1
        page = PAGE_RE.match(line)
        if page:
            pages.append(int(page.group(1)))
    result["heading_counts"] = {str(k): headings[k] for k in sorted(headings)}
    result["page_markers"] = pages
    result["table_count"] = sum(1 for line in lines if TABLE_SEPARATOR_RE.match(line))
    duplicates = sorted(number for number, count in Counter(pages).items() if count > 1)
    if duplicates:
        result["structural_flags"].append("duplicate_page_markers:" + ",".join(map(str, duplicates)))
    if pages and pages != sorted(pages):
        result["structural_flags"].append("out_of_order_page_markers")
    if any(number <= 0 for number in pages):
        result["structural_flags"].append("nonpositive_page_marker")
    return result


def build_inventory(project_root: Path) -> dict[str, Any]:
    root = project_root.resolve()
    data_root = root / "data"
    pdf_root = data_root / "pdf_docs"
    md_root = data_root / "md_docs"
    if not pdf_root.is_dir() or not md_root.is_dir():
        raise FileNotFoundError("Expected data/pdf_docs and data/md_docs directories")

    files: list[dict[str, Any]] = []
    paths_by_id: dict[str, Path] = {}
    skipped_links: list[str] = []
    for path in sorted(data_root.rglob("*"), key=lambda item: item.as_posix().casefold()):
        if path.is_symlink():
            skipped_links.append(path.relative_to(root).as_posix())
            continue
        if not path.is_file() or path.suffix.lower() not in {".pdf", ".md", ".txt", ".json"}:
            continue
        expected = (path.suffix.lower() == ".pdf" and pdf_root in path.parents) or (
            path.suffix.lower() == ".md" and md_root in path.parents
        )
        rec = _file_record(path, root, expected)
        files.append(rec)
        paths_by_id[rec["file_id"]] = path

    pdf_files = [item for item in files if item["extension"] == ".pdf" and item["expected_location"]]
    md_files = [item for item in files if item["extension"] == ".md" and item["expected_location"]]
    pdf_contents: list[dict[str, Any]] = []
    for rec in pdf_files:
        inspection = {
            "content_id": "pdf_" + (rec["sha256"] or stable_hash(rec["relative_path"])),
            "file_ids": [rec["file_id"]],
            "readable": False,
            "needs_password": None,
            "page_count": None,
            "metadata": {},
            "error": rec["error"],
        }
        if rec["read_status"] == "readable":
            try:
                with pymupdf.open(paths_by_id[rec["file_id"]]) as doc:
                    inspection.update(
                        readable=not doc.needs_pass,
                        needs_password=bool(doc.needs_pass),
                        page_count=doc.page_count if not doc.needs_pass else None,
                        metadata={key: value for key, value in (doc.metadata or {}).items() if value},
                        error=None if not doc.needs_pass else "password_required",
                    )
            except Exception as exc:  # noqa: BLE001 - PyMuPDF exposes format-specific failures.
                inspection["error"] = f"{type(exc).__name__}: {exc}"
        pdf_contents.append(inspection)

    # Collapse exact duplicate PDFs to one content record while retaining paths.
    collapsed: dict[str, dict[str, Any]] = {}
    for content in pdf_contents:
        cid = content["content_id"]
        if cid in collapsed:
            collapsed[cid]["file_ids"].extend(content["file_ids"])
        else:
            collapsed[cid] = content
    pdf_contents = [collapsed[key] for key in sorted(collapsed)]

    extractions = [_markdown_structure(paths_by_id[rec["file_id"]], rec) for rec in md_files]
    pdf_name_to_content: dict[str, list[str]] = defaultdict(list)
    for content in pdf_contents:
        for fid in content["file_ids"]:
            name = paths_by_id[fid].name
            pdf_name_to_content[unicodedata.normalize("NFC", name).casefold()].append(content["content_id"])
    md_by_file = {item["file_id"]: item for item in extractions}
    pairings: list[dict[str, Any]] = []
    used_content: Counter[str] = Counter()
    for rec in md_files:
        ext = md_by_file[rec["file_id"]]
        declared = ext["source_declaration"]
        stem_candidate = rec["relative_path"].rsplit("/", 1)[-1][:-3] + ".pdf"
        declared_matches = (
            pdf_name_to_content.get(unicodedata.normalize("NFC", declared).casefold(), []) if declared else []
        )
        stem_matches = pdf_name_to_content.get(unicodedata.normalize("NFC", stem_candidate).casefold(), [])
        if len(declared_matches) == 1:
            candidates, status, rule = declared_matches, "matched", "explicit_source"
            if stem_matches and stem_matches != declared_matches:
                status, rule = "ambiguous", "source_stem_conflict"
                candidates = sorted(set(declared_matches + stem_matches))
        elif declared and len(declared_matches) != 1:
            candidates, status, rule = (
                declared_matches,
                "ambiguous" if declared_matches else "unmatched",
                "explicit_source",
            )
        elif len(stem_matches) == 1:
            candidates, status, rule = stem_matches, "matched", "basename_stem"
        else:
            candidates, status, rule = stem_matches, "ambiguous" if stem_matches else "unmatched", "basename_stem"
        content_id = candidates[0] if status == "matched" else None
        if content_id:
            used_content[content_id] += 1
        pairings.append(
            {
                "markdown_file_id": rec["file_id"],
                "pdf_content_id": content_id,
                "status": status,
                "matching_rule": rule,
                "candidate_pdf_content_ids": candidates,
            }
        )

    page_counts = {item["content_id"]: item["page_count"] for item in pdf_contents}
    issues: list[dict[str, Any]] = []

    def add_issue(code: str, severity: str, affected: list[str], details: str) -> None:
        base = {"code": code, "severity": severity, "affected_ids": affected, "details": details}
        issues.append({"issue_id": "issue_" + stable_hash(base)[:16], **base, "review_status": "open"})

    for rec in files:
        if rec["read_status"] != "readable" or rec["size_bytes"] == 0:
            add_issue("unusable_file", "error", [rec["file_id"]], rec["error"] or "zero-byte file")
        if rec["extension"] in {".pdf", ".md"} and not rec["expected_location"]:
            add_issue("unexpected_location", "warning", [rec["file_id"]], rec["relative_path"])
    for content in pdf_contents:
        if len(content["file_ids"]) > 1:
            add_issue("exact_duplicate_pdf", "warning", content["file_ids"], content["content_id"])
        if not content["readable"]:
            add_issue("unreadable_pdf", "error", content["file_ids"], content["error"] or "unreadable")
    for ext in extractions:
        for flag in ext["structural_flags"]:
            add_issue("markdown_structure", "warning", [ext["file_id"]], flag)
    for pairing in pairings:
        if pairing["status"] != "matched":
            add_issue("markdown_pdf_pairing", "warning", [pairing["markdown_file_id"]], pairing["status"])
        elif used_content[pairing["pdf_content_id"]] > 1:
            add_issue("multiple_markdown_for_pdf", "warning", [pairing["markdown_file_id"]], pairing["pdf_content_id"])
        else:
            ext = md_by_file[pairing["markdown_file_id"]]
            pdf_pages = page_counts[pairing["pdf_content_id"]]
            markers = ext["page_markers"]
            if pdf_pages and markers and max(markers) > pdf_pages:
                add_issue(
                    "page_marker_out_of_range",
                    "warning",
                    [pairing["markdown_file_id"]],
                    f"max={max(markers)}, pdf={pdf_pages}",
                )
    paired = {item["pdf_content_id"] for item in pairings if item["status"] == "matched"}
    for content in pdf_contents:
        if content["content_id"] not in paired:
            add_issue("pdf_without_markdown", "warning", content["file_ids"], content["content_id"])
    for link in skipped_links:
        add_issue("skipped_link", "warning", [], link)

    stable_inventory = {
        "schema": INVENTORY_SCHEMA,
        "project_relative_data_root": "data",
        "files": files,
        "pdf_contents": pdf_contents,
        "extractions": extractions,
        "pairings": pairings,
        "issues": sorted(issues, key=lambda item: item["issue_id"]),
    }
    input_fingerprint = stable_hash(stable_inventory)
    return {
        **stable_inventory,
        "run": {
            "created_at_utc": utc_now(),
            "python_version": sys.version.split()[0],
            "pymupdf_version": pymupdf.VersionBind,
            "input_fingerprint": input_fingerprint,
            "technical_status": "passed",
            "clinical_review_status": "not_assessed",
            "transcription_accuracy": "not_assessed",
        },
    }


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, values: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for value in values:
            handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def _write_csv(path: Path, values: list[dict[str, Any]]) -> None:
    if not values:
        path.write_text("", encoding="utf-8")
        return
    columns = list(values[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in values:
            writer.writerow(
                {
                    key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value
                    for key, value in row.items()
                }
            )


def export_inventory(inventory: dict[str, Any], project_root: Path, *, output_root: Path) -> Path:
    run_id = (
        inventory["run"]["created_at_utc"].replace(":", "-").replace("+00:00", "Z")
        + "_"
        + inventory["run"]["input_fingerprint"][:10]
    )
    output = Path(output_root) / run_id
    output.mkdir(parents=True, exist_ok=False)
    _write_json(output / "corpus_manifest.json", inventory)
    _write_csv(output / "file_inventory.csv", inventory["files"])
    _write_csv(output / "issues.csv", inventory["issues"])
    checks = validate_inventory(inventory)
    _write_json(output / "check_results.json", checks)
    return output


def latest_inventory_manifest(project_root: Path) -> Path:
    """Return the newest Step 2 manifest whose exported checks passed."""
    manifests = sorted((project_root / "artifacts" / "01_corpus_inventory").glob("*/corpus_manifest.json"))
    if not manifests:
        raise FileNotFoundError("No Step 2 corpus manifest found; execute the Step 2 notebook first")
    for manifest in reversed(manifests):
        checks_path = manifest.with_name("check_results.json")
        if checks_path.exists() and json.loads(checks_path.read_text(encoding="utf-8")).get("passed"):
            return manifest
    raise FileNotFoundError("No Step 2 corpus manifest with passing technical checks found")


def validate_inventory(inventory: dict[str, Any]) -> dict[str, Any]:
    file_ids = [item["file_id"] for item in inventory["files"]]
    known_files = set(file_ids)
    checks = {
        "unique_file_ids": len(file_ids) == len(set(file_ids)),
        "hashes_valid": all(
            item["sha256"] is None or re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) for item in inventory["files"]
        ),
        "sizes_nonnegative": all(item["size_bytes"] is None or item["size_bytes"] >= 0 for item in inventory["files"]),
        "pdf_file_references_valid": all(set(item["file_ids"]) <= known_files for item in inventory["pdf_contents"]),
        "extraction_file_references_valid": all(item["file_id"] in known_files for item in inventory["extractions"]),
        "pairing_file_references_valid": all(item["markdown_file_id"] in known_files for item in inventory["pairings"]),
    }
    return {"passed": all(checks.values()), "checks": checks, "clinical_review_status": "not_assessed"}


@dataclass
class _Block:
    kind: str
    start: int
    end: int
    text: str
    heading_path: list[str]
    heading_span_ids: list[str]
    page: int | None


def _line_records(text: str) -> list[tuple[int, int, str]]:
    records = []
    cursor = 0
    for line in text.splitlines(keepends=True):
        records.append((cursor, cursor + len(line), line))
        cursor += len(line)
    if cursor < len(text):
        records.append((cursor, len(text), text[cursor:]))
    return records


def parse_markdown(text: str, source_identity: str) -> list[dict[str, Any]]:
    lines = _line_records(text)
    blocks: list[_Block] = []
    headings: list[tuple[int, str, str]] = []
    page: int | None = None
    index = 0

    def context() -> tuple[list[str], list[str]]:
        return [item[1] for item in headings], [item[2] for item in headings]

    while index < len(lines):
        start, end, raw = lines[index]
        stripped = raw.strip("\r\n")
        if not stripped.strip():
            index += 1
            continue
        heading = HEADING_RE.match(stripped)
        if heading:
            level, title = len(heading.group(1)), heading.group(2).strip()
            pid = "passage_" + stable_hash([source_identity, start, end, PARSER_VERSION])[:20]
            marker = PAGE_RE.match(stripped)
            if marker:
                page = int(marker.group(1))
                kind = "page_marker"
            else:
                kind = "heading"
                headings = [item for item in headings if item[0] < level]
                headings.append((level, title, pid))
            path, span_ids = context()
            blocks.append(_Block(kind, start, end, text[start:end], path, span_ids, page))
            index += 1
            continue

        kind = "paragraph"
        if stripped.lstrip().startswith("```"):
            kind = "fenced"
            stop = index + 1
            while stop < len(lines) and not lines[stop][2].strip("\r\n").lstrip().startswith("```"):
                stop += 1
            stop = min(stop + 1, len(lines))
        elif stripped.lstrip().startswith("|"):
            kind = "table"
            stop = index + 1
            while stop < len(lines) and lines[stop][2].strip("\r\n").lstrip().startswith("|"):
                stop += 1
        elif LIST_RE.match(stripped):
            kind = "list"
            stop = index + 1
            while stop < len(lines):
                candidate = lines[stop][2].strip("\r\n")
                if not candidate.strip():
                    break
                if LIST_RE.match(candidate) or candidate.startswith((" ", "\t")):
                    stop += 1
                else:
                    break
        elif stripped.lstrip().startswith("<"):
            kind = "html_or_opaque"
            stop = index + 1
            while stop < len(lines) and lines[stop][2].strip():
                stop += 1
        else:
            stop = index + 1
            while stop < len(lines):
                candidate = lines[stop][2].strip("\r\n")
                if (
                    not candidate.strip()
                    or HEADING_RE.match(candidate)
                    or candidate.lstrip().startswith(("|", "```", "<"))
                    or LIST_RE.match(candidate)
                ):
                    break
                stop += 1
        block_end = lines[stop - 1][1]
        path, span_ids = context()
        blocks.append(_Block(kind, start, block_end, text[start:block_end], path, span_ids, page))
        index = stop

    return [
        {
            "passage_id": "passage_" + stable_hash([source_identity, block.start, block.end, PARSER_VERSION])[:20],
            "kind": block.kind,
            "start_offset": block.start,
            "end_offset": block.end,
            "text": block.text,
            "heading_path": block.heading_path,
            "heading_span_ids": block.heading_span_ids,
            "declared_page": block.page,
            "parser_version": PARSER_VERSION,
        }
        for block in blocks
    ]


def _assemble_chunk(
    passages: list[dict[str, Any]], passage_lookup: dict[str, dict[str, Any]]
) -> tuple[str, list[dict[str, Any]]]:
    context_ids: list[str] = []
    for item in passages:
        for heading_id in item["heading_span_ids"]:
            if heading_id not in context_ids:
                context_ids.append(heading_id)
    pieces: list[tuple[str, str | None]] = []
    for pid in context_ids:
        heading = passage_lookup[pid]
        pieces.append((heading["text"], pid))
    for item in passages:
        pieces.append((item["text"], item["passage_id"]))
    assembled = ""
    segments: list[dict[str, Any]] = []
    for position, (piece, pid) in enumerate(pieces):
        if position:
            start = len(assembled)
            assembled += "\n\n"
            segments.append(
                {
                    "retrieval_start": start,
                    "retrieval_end": len(assembled),
                    "source_passage_id": None,
                    "synthetic": True,
                }
            )
        start = len(assembled)
        assembled += piece
        segments.append(
            {"retrieval_start": start, "retrieval_end": len(assembled), "source_passage_id": pid, "synthetic": False}
        )
    return assembled, segments


def build_chunks(project_root: Path, inventory_path: Path) -> dict[str, Any]:
    root = project_root.resolve()
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    if not validate_inventory(inventory)["passed"]:
        raise ValueError("Selected inventory failed structural validation")
    pairing_by_md = {item["markdown_file_id"]: item for item in inventory["pairings"]}
    extraction_by_id = {item["file_id"]: item for item in inventory["extractions"]}
    documents: list[dict[str, Any]] = []
    passages: list[dict[str, Any]] = []
    exceptions: list[dict[str, Any]] = []

    readable_md = [
        item
        for item in inventory["files"]
        if item["extension"] == ".md" and item["expected_location"] and item["read_status"] == "readable"
    ]
    canonical_by_hash: dict[str, dict[str, Any]] = {}
    for item in sorted(readable_md, key=lambda row: row["relative_path"].casefold()):
        canonical_by_hash.setdefault(item["sha256"], item)
    selected = sorted(canonical_by_hash.values(), key=lambda row: row["relative_path"].casefold())
    aliases_by_hash: dict[str, list[str]] = defaultdict(list)
    for item in readable_md:
        aliases_by_hash[item["sha256"]].append(item["relative_path"])

    for file_rec in selected:
        path = root / file_rec["relative_path"]
        if sha256_file(path) != file_rec["sha256"]:
            raise ValueError(f"Stale inventory: {file_rec['relative_path']} changed")
        text = _read_utf8_exact(path)
        if not text.strip():
            exceptions.append(
                {
                    "code": "empty_markdown",
                    "document_id": None,
                    "passage_id": None,
                    "details": file_rec["relative_path"],
                }
            )
            continue
        pairing = pairing_by_md.get(file_rec["file_id"], {})
        pdf_id = pairing.get("pdf_content_id") if pairing.get("status") == "matched" else None
        document_id = pdf_id or "md_" + file_rec["sha256"]
        extraction = extraction_by_id[file_rec["file_id"]]
        document = {
            "document_id": document_id,
            "markdown_file_id": file_rec["file_id"],
            "markdown_path": file_rec["relative_path"],
            "markdown_sha256": file_rec["sha256"],
            "aliases": sorted(aliases_by_hash[file_rec["sha256"]]),
            "pdf_content_id": pdf_id,
            "source_declaration": extraction["source_declaration"],
            "mapping_status": pairing.get("status", "unmatched"),
            "clinical_review_status": "not_assessed",
        }
        documents.append(document)
        parsed = parse_markdown(text, file_rec["sha256"])
        for item in parsed:
            item.update(
                document_id=document_id, markdown_sha256=file_rec["sha256"], markdown_path=file_rec["relative_path"]
            )
        passages.extend(parsed)

    passage_lookup = {item["passage_id"]: item for item in passages}
    chunks: list[dict[str, Any]] = []
    for document in documents:
        doc_passages = [item for item in passages if item["document_id"] == document["document_id"]]
        body = [item for item in doc_passages if item["kind"] not in {"heading", "page_marker"}]
        groups: list[list[dict[str, Any]]] = []
        current: list[dict[str, Any]] = []
        for item in body:
            candidate = current + [item]
            candidate_text, _ = _assemble_chunk(candidate, passage_lookup)
            section_changed = bool(current and current[-1]["heading_span_ids"] != item["heading_span_ids"])
            if current and (section_changed or len(candidate_text) > CHUNK_CONFIG["target_max_chars"]):
                groups.append(current)
                current = [item]
            else:
                current = candidate
        if current:
            groups.append(current)
        for group in groups:
            retrieval_text, segments = _assemble_chunk(group, passage_lookup)
            context_ids = [
                segment["source_passage_id"]
                for segment in segments
                if not segment["synthetic"] and passage_lookup[segment["source_passage_id"]]["kind"] == "heading"
            ]
            flags = []
            if len(retrieval_text) > CHUNK_CONFIG["target_max_chars"]:
                flags.append("oversized")
            if any(item["kind"] == "html_or_opaque" for item in group):
                flags.append("opaque_content")
            if document["pdf_content_id"] is None:
                flags.append("pdf_mapping_unavailable")
            chunk_identity = {
                "document_id": document["document_id"],
                "body_passage_ids": [item["passage_id"] for item in group],
                "context_passage_ids": context_ids,
                "config": CHUNK_CONFIG,
            }
            chunks.append(
                {
                    "chunk_id": "chunk_" + stable_hash(chunk_identity)[:20],
                    **chunk_identity,
                    "retrieval_text": retrieval_text,
                    "character_count": len(retrieval_text),
                    "segments": segments,
                    "declared_pages": sorted(
                        {item["declared_page"] for item in group if item["declared_page"] is not None}
                    ),
                    "flags": flags,
                    "previous_chunk_id": None,
                    "next_chunk_id": None,
                }
            )
        doc_chunks = [item for item in chunks if item["document_id"] == document["document_id"]]
        for idx, chunk in enumerate(doc_chunks):
            chunk["previous_chunk_id"] = doc_chunks[idx - 1]["chunk_id"] if idx else None
            chunk["next_chunk_id"] = doc_chunks[idx + 1]["chunk_id"] if idx + 1 < len(doc_chunks) else None

    citation_targets = [
        {
            "citation_target_id": "citation_" + stable_hash([item["chunk_id"], CHUNK_SCHEMA])[:20],
            "chunk_id": item["chunk_id"],
            "document_id": item["document_id"],
            "source_passage_ids": item["body_passage_ids"],
            "declared_pages": item["declared_pages"],
            "pdf_coordinate_status": "unavailable",
        }
        for item in chunks
    ]
    for item in chunks:
        for flag in item["flags"]:
            exceptions.append(
                {"code": flag, "document_id": item["document_id"], "passage_id": None, "details": item["chunk_id"]}
            )
    content = {
        "schema": CHUNK_SCHEMA,
        "inventory_path": (
            inventory_path.relative_to(root).as_posix()
            if inventory_path.is_relative_to(root)
            else inventory_path.resolve().as_posix()
        ),
        "inventory_fingerprint": inventory["run"]["input_fingerprint"],
        "chunking_config": CHUNK_CONFIG,
        "documents": documents,
        "passages": passages,
        "chunks": chunks,
        "citation_targets": citation_targets,
        "exceptions": exceptions,
    }
    bundle_fingerprint = stable_hash(content)
    content["run"] = {
        "created_at_utc": utc_now(),
        "bundle_fingerprint": bundle_fingerprint,
        "technical_status": "passed",
    }
    return content


def validate_chunks(bundle: dict[str, Any], project_root: Path) -> dict[str, Any]:
    root = project_root.resolve()
    passage_by_id = {item["passage_id"]: item for item in bundle["passages"]}
    chunk_by_id = {item["chunk_id"]: item for item in bundle["chunks"]}
    passage_ids = [item["passage_id"] for item in bundle["passages"]]
    chunk_ids = [item["chunk_id"] for item in bundle["chunks"]]
    source_texts = {
        path: _read_utf8_exact(root / path) for path in sorted({item["markdown_path"] for item in bundle["passages"]})
    }
    slices_ok = True
    for passage in bundle["passages"]:
        source = source_texts[passage["markdown_path"]]
        if source[passage["start_offset"] : passage["end_offset"]] != passage["text"]:
            slices_ok = False
            break
    covered_ranges: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for passage in bundle["passages"]:
        covered_ranges[passage["markdown_path"]].append((passage["start_offset"], passage["end_offset"]))
    coverage_ok = True
    for path, source in source_texts.items():
        cursor = 0
        for start, end in sorted(covered_ranges[path]):
            if source[cursor:start].strip():
                coverage_ok = False
                break
            cursor = max(cursor, end)
        if source[cursor:].strip():
            coverage_ok = False
        if not coverage_ok:
            break
    segment_links_ok = all(
        segment["synthetic"] or segment["source_passage_id"] in passage_by_id
        for chunk in bundle["chunks"]
        for segment in chunk["segments"]
    )
    segment_text_ok = all(
        segment["synthetic"]
        or chunk["retrieval_text"][segment["retrieval_start"] : segment["retrieval_end"]]
        == passage_by_id[segment["source_passage_id"]]["text"]
        for chunk in bundle["chunks"]
        for segment in chunk["segments"]
    )
    neighbor_links_ok = all(
        (item["previous_chunk_id"] is None or item["previous_chunk_id"] in chunk_by_id)
        and (item["next_chunk_id"] is None or item["next_chunk_id"] in chunk_by_id)
        for item in bundle["chunks"]
    )
    no_cross_document = all(
        all(
            passage_by_id[pid]["document_id"] == item["document_id"]
            for pid in item["body_passage_ids"] + item["context_passage_ids"]
        )
        for item in bundle["chunks"]
    )
    source_hashes_unchanged = all(
        sha256_file(root / item["markdown_path"]) == item["markdown_sha256"] for item in bundle["documents"]
    )
    checks = {
        "unique_passage_ids": len(passage_ids) == len(set(passage_ids)),
        "unique_chunk_ids": len(chunk_ids) == len(set(chunk_ids)),
        "source_slices_exact": slices_ok,
        "nonwhitespace_source_coverage": coverage_ok,
        "segment_links_valid": segment_links_ok,
        "retrieval_segments_exact": segment_text_ok,
        "neighbor_links_valid": neighbor_links_ok,
        "no_cross_document_chunks": no_cross_document,
        "source_hashes_unchanged": source_hashes_unchanged,
        "all_documents_have_chunks": {item["document_id"] for item in bundle["documents"]}
        <= {item["document_id"] for item in bundle["chunks"]},
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "scope": "structural preservation only; not clinical/OCR validation",
    }


def export_chunks(bundle: dict[str, Any], project_root: Path, *, output_root: Path) -> Path:
    run_id = (
        bundle["run"]["created_at_utc"].replace(":", "-").replace("+00:00", "Z")
        + "_"
        + bundle["run"]["bundle_fingerprint"][:10]
    )
    output = Path(output_root) / run_id
    output.mkdir(parents=True, exist_ok=False)
    _write_jsonl(output / "documents.jsonl", bundle["documents"])
    _write_jsonl(output / "passages.jsonl", bundle["passages"])
    _write_jsonl(output / "chunks.jsonl", bundle["chunks"])
    _write_jsonl(output / "citation_targets.jsonl", bundle["citation_targets"])
    _write_json(output / "chunking_config.json", bundle["chunking_config"])
    _write_csv(output / "exceptions.csv", bundle["exceptions"])
    checks = validate_chunks(bundle, project_root)
    _write_json(output / "check_results.json", checks)
    stats = chunk_statistics(bundle)
    manifest = {
        key: value
        for key, value in bundle.items()
        if key not in {"documents", "passages", "chunks", "citation_targets", "exceptions"}
    }
    manifest.update(
        counts={
            "documents": len(bundle["documents"]),
            "passages": len(bundle["passages"]),
            "chunks": len(bundle["chunks"]),
            "exceptions": len(bundle["exceptions"]),
        },
        statistics=stats,
        checks_passed=checks["passed"],
    )
    manifest["output_sha256"] = {path.name: sha256_file(path) for path in sorted(output.iterdir()) if path.is_file()}
    _write_json(output / "run_manifest.json", manifest)
    return output


def chunk_statistics(bundle: dict[str, Any]) -> dict[str, Any]:
    sizes = sorted(item["character_count"] for item in bundle["chunks"])
    if not sizes:
        return {"count": 0}

    def percentile(fraction: float) -> int:
        return sizes[round((len(sizes) - 1) * fraction)]

    kinds = {item["passage_id"]: item["kind"] for item in bundle["passages"]}
    return {
        "count": len(sizes),
        "minimum_chars": sizes[0],
        "median_chars": percentile(0.5),
        "p95_chars": percentile(0.95),
        "maximum_chars": sizes[-1],
        "oversized_count": sum("oversized" in item["flags"] for item in bundle["chunks"]),
        "pdf_mapping_unavailable_count": sum("pdf_mapping_unavailable" in item["flags"] for item in bundle["chunks"]),
        "context_characters": sum(
            sum(
                segment["retrieval_end"] - segment["retrieval_start"]
                for segment in item["segments"]
                if not segment["synthetic"] and kinds.get(segment["source_passage_id"]) == "heading"
            )
            for item in bundle["chunks"]
        ),
    }
