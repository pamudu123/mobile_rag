"""Step 6: immutable, source-backed SQLite FTS5 retrieval. No model calls."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self

CONFIG = {
    "schema": "mobile-rag-retrieval/v1",
    "tokenizer": "unicode61",
    "weights": [1.0, 1.0],
    "default_mode": "OR",
    "max_chars": 2000,
    "max_terms": 64,
}
INPUTS = ("documents", "passages", "chunks", "citation_targets")


def digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def encode(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def write_json(path: Path, value: Any) -> None:
    path.write_text(encode(value) + "\n", encoding="utf-8")


def load_bundle(folder: Path) -> dict[str, Any]:
    """Validate the files loaded, including source-segment and citation relationships."""
    manifest = json.loads((folder / "run_manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != "mobile-rag-chunks/v1" or not manifest.get("checks_passed"):
        raise ValueError("Unsupported or failing Step 5 manifest")
    required = [f"{name}.jsonl" for name in INPUTS] + ["check_results.json", "chunking_config.json"]
    for name in required:
        expected = manifest.get("output_sha256", {}).get(name)
        if not expected or digest(folder / name) != expected:
            raise ValueError(f"Missing or mismatched artifact hash: {name}")
    if not json.loads((folder / "check_results.json").read_text())["passed"]:
        raise ValueError("Step 5 checks did not pass")
    if json.loads((folder / "chunking_config.json").read_text()) != manifest["chunking_config"]:
        raise ValueError("Mixed chunk configuration")
    data = {
        name: [
            json.loads(line)
            for line in (folder / f"{name}.jsonl").read_text(encoding="utf-8").split("\n")
            if line.strip()
        ]
        for name in INPUTS
    }
    keys = {
        "documents": "document_id",
        "passages": "passage_id",
        "chunks": "chunk_id",
        "citation_targets": "citation_target_id",
    }
    maps = {}
    for name, key in keys.items():
        maps[name] = {row[key]: row for row in data[name]}
        if len(maps[name]) != len(data[name]) or not data[name]:
            raise ValueError(f"Empty or duplicate IDs: {name}")
        if name in manifest["counts"] and len(data[name]) != manifest["counts"][name]:
            raise ValueError(f"Count mismatch: {name}")
    for passage in data["passages"]:
        doc = maps["documents"][passage["document_id"]]
        if passage["markdown_sha256"] != doc["markdown_sha256"]:
            raise ValueError("Mixed passage source identity")
        if passage["end_offset"] - passage["start_offset"] != len(passage["text"]) or passage["start_offset"] < 0:
            raise ValueError("Invalid source offsets")
    for chunk in data["chunks"]:
        if chunk["config"] != manifest["chunking_config"]:
            raise ValueError("Mixed chunk version")
        pids = chunk["body_passage_ids"] + chunk["context_passage_ids"]
        if not chunk["body_passage_ids"] or any(
            maps["passages"][pid]["document_id"] != chunk["document_id"] for pid in pids
        ):
            raise ValueError("Invalid chunk source association")
        cursor = 0
        actual = []
        for segment in chunk["segments"]:
            start, end = segment["retrieval_start"], segment["retrieval_end"]
            if start != cursor or end < start or end > len(chunk["retrieval_text"]):
                raise ValueError("Invalid segment coverage")
            part = chunk["retrieval_text"][start:end]
            if segment["synthetic"]:
                if part.strip():
                    raise ValueError("Unexpected synthetic source content")
            else:
                pid = segment["source_passage_id"]
                if pid not in pids or part != maps["passages"][pid]["text"]:
                    raise ValueError("Segment/source mismatch")
                actual.append(pid)
            cursor = end
        if cursor != len(chunk["retrieval_text"]) or set(actual) != set(pids):
            raise ValueError("Incomplete segment mapping")
        for field in ("previous_chunk_id", "next_chunk_id"):
            neighbor = chunk.get(field)
            if neighbor and maps["chunks"][neighbor]["document_id"] != chunk["document_id"]:
                raise ValueError("Cross-document neighbor")
    targets = {}
    for target in data["citation_targets"]:
        chunk = maps["chunks"][target["chunk_id"]]
        if target["document_id"] != chunk["document_id"] or target["source_passage_ids"] != chunk["body_passage_ids"]:
            raise ValueError("Citation/source mismatch")
        if chunk["chunk_id"] in targets:
            raise ValueError("Multiple citation targets for chunk")
        targets[chunk["chunk_id"]] = target
    if set(targets) != set(maps["chunks"]):
        raise ValueError("Missing citation target")
    return {**data, "manifest": manifest, "maps": maps}


def latest_bundle(root: Path) -> Path:
    for path in sorted((root / "artifacts/step-05").glob("*/run_manifest.json"), reverse=True):
        try:
            load_bundle(path.parent)
            return path.parent
        except (ValueError, KeyError, OSError):
            continue
    raise FileNotFoundError("No complete, validated Step 5 bundle")


def build_index(bundle_dir: Path, output_root: Path) -> Path:
    start = time.perf_counter()
    probe = sqlite3.connect(":memory:")
    try:
        probe.execute("CREATE VIRTUAL TABLE probe USING fts5(text)")
    except sqlite3.OperationalError as exc:
        raise RuntimeError("SQLite FTS5 is required; install a Python/SQLite build with FTS5") from exc
    finally:
        probe.close()
    data = load_bundle(bundle_dir)
    identity = hashlib.sha256(
        encode(
            {"input_hashes": data["manifest"]["output_sha256"], "config": CONFIG, "sqlite": sqlite3.sqlite_version}
        ).encode()
    ).hexdigest()
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ") + "_" + identity[:10]
    out = output_root / run_id
    out.mkdir(parents=True, exist_ok=False)
    temp = out / "building.sqlite"
    counts = {name: len(data[name]) for name in INPUTS}
    metadata = {
        "config": CONFIG,
        "index_identity": identity,
        "bundle_identity": data["manifest"]["run"]["bundle_fingerprint"],
        "sqlite_version": sqlite3.sqlite_version,
        "counts": counts,
        "input_hashes": data["manifest"]["output_sha256"],
    }
    db = sqlite3.connect(temp)
    try:
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript("""
            CREATE TABLE bundle_metadata (value TEXT NOT NULL);
            CREATE TABLE documents (id TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE passages (id TEXT PRIMARY KEY, document_id TEXT REFERENCES documents(id), value TEXT NOT NULL);
            CREATE TABLE chunks (rowid INTEGER PRIMARY KEY, id TEXT UNIQUE, document_id TEXT REFERENCES documents(id), value TEXT NOT NULL);
            CREATE TABLE chunk_passages (chunk_id TEXT REFERENCES chunks(id), passage_id TEXT REFERENCES passages(id), role TEXT, ordinal INTEGER, PRIMARY KEY(chunk_id, role, ordinal));
            CREATE TABLE citation_targets (id TEXT PRIMARY KEY, chunk_id TEXT UNIQUE REFERENCES chunks(id), value TEXT NOT NULL);
            CREATE VIRTUAL TABLE chunk_fts USING fts5(heading_text, body_text, tokenize='unicode61');
        """)
        with db:
            db.execute("INSERT INTO bundle_metadata VALUES (?)", (encode(metadata),))
            db.executemany(
                "INSERT INTO documents VALUES (?,?)", [(d["document_id"], encode(d)) for d in data["documents"]]
            )
            db.executemany(
                "INSERT INTO passages VALUES (?,?,?)",
                [(p["passage_id"], p["document_id"], encode(p)) for p in data["passages"]],
            )
            for rowid, chunk in enumerate(sorted(data["chunks"], key=lambda c: c["chunk_id"]), 1):
                db.execute(
                    "INSERT INTO chunks VALUES (?,?,?,?)",
                    (rowid, chunk["chunk_id"], chunk["document_id"], encode(chunk)),
                )
                texts = []
                for role in ("context", "body"):
                    ids = list(dict.fromkeys(chunk[f"{role}_passage_ids"]))
                    texts.append("\n\n".join(data["maps"]["passages"][pid]["text"] for pid in ids))
                    db.executemany(
                        "INSERT INTO chunk_passages VALUES (?,?,?,?)",
                        [(chunk["chunk_id"], pid, role, i) for i, pid in enumerate(ids)],
                    )
                db.execute("INSERT INTO chunk_fts(rowid,heading_text,body_text) VALUES (?,?,?)", (rowid, *texts))
            db.executemany(
                "INSERT INTO citation_targets VALUES (?,?,?)",
                [(t["citation_target_id"], t["chunk_id"], encode(t)) for t in data["citation_targets"]],
            )
            db.execute("INSERT INTO chunk_fts(chunk_fts) VALUES ('integrity-check')")
        if (
            db.execute("PRAGMA integrity_check").fetchone()[0] != "ok"
            or db.execute("PRAGMA foreign_key_check").fetchall()
        ):
            raise ValueError("Database integrity failed")
        for table, name in (
            ("documents", "documents"),
            ("passages", "passages"),
            ("chunks", "chunks"),
            ("citation_targets", "citation_targets"),
            ("chunk_fts", "chunks"),
        ):
            if db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] != counts[name]:
                raise ValueError(f"Import count mismatch: {table}")
        for raw, heading, body in db.execute(
            "SELECT c.value,f.heading_text,f.body_text FROM chunks c JOIN chunk_fts f ON c.rowid=f.rowid"
        ):
            chunk = json.loads(raw)
            expected = [
                "\n\n".join(
                    data["maps"]["passages"][pid]["text"] for pid in dict.fromkeys(chunk[f"{role}_passage_ids"])
                )
                for role in ("context", "body")
            ]
            if [heading, body] != expected:
                raise ValueError("FTS row/content mismatch")
    finally:
        db.close()
    # Recheck inputs after construction; never publish a mixed snapshot.
    refreshed = load_bundle(bundle_dir)
    if refreshed["manifest"]["output_sha256"] != data["manifest"]["output_sha256"]:
        raise ValueError("Input bundle changed during build")
    final = out / "retrieval.sqlite"
    temp.rename(final)
    manifest = {
        **metadata,
        "selected_bundle": str(bundle_dir.resolve()),
        "passed": True,
        "database_sha256": digest(final),
        "database_bytes": final.stat().st_size,
        "build_seconds": time.perf_counter() - start,
    }
    write_json(out / "index_manifest.json", manifest)
    write_json(
        out / "check_results.json",
        {
            "passed": True,
            "checks": [
                "input_hashes",
                "source_segments",
                "citation_links",
                "foreign_keys",
                "sqlite_integrity",
                "fts_integrity",
                "import_counts",
                "fts_content_mapping",
            ],
        },
    )
    return out


class Retriever:
    """Read-only evidence retrieval; query tokenizer state is held in memory."""

    def __init__(self, index_dir: Path):
        manifest = json.loads((index_dir / "index_manifest.json").read_text(encoding="utf-8"))
        path = index_dir / "retrieval.sqlite"
        if not manifest.get("passed") or digest(path) != manifest["database_sha256"]:
            raise ValueError("Index integrity mismatch")
        self.db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        self.metadata = json.loads(self.db.execute("SELECT value FROM bundle_metadata").fetchone()[0])
        if self.metadata["config"] != CONFIG or self.metadata["index_identity"] != manifest["index_identity"]:
            self.db.close()
            raise ValueError("Index version/identity mismatch")
        self.scratch = sqlite3.connect(":memory:")
        self.scratch.execute("CREATE VIRTUAL TABLE tokens USING fts5(text,tokenize='unicode61')")
        self.scratch.execute("CREATE VIRTUAL TABLE vocab USING fts5vocab(tokens, 'instance')")

    def close(self) -> None:
        self.scratch.close()
        self.db.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _terms(self, question: str) -> list[str]:
        self.scratch.execute("DELETE FROM tokens")
        self.scratch.execute("INSERT INTO tokens VALUES (?)", (question,))
        return [row[0] for row in self.scratch.execute("SELECT term FROM vocab GROUP BY term ORDER BY min(offset)")]

    def resolve(self, chunk_id: str) -> dict[str, Any]:
        row = self.db.execute("SELECT value FROM chunks WHERE id=?", (chunk_id,)).fetchone()
        if row is None:
            raise ValueError("Unknown chunk ID")
        chunk = json.loads(row[0])
        doc = json.loads(
            self.db.execute("SELECT value FROM documents WHERE id=?", (chunk["document_id"],)).fetchone()[0]
        )
        passages = [
            json.loads(self.db.execute("SELECT value FROM passages WHERE id=?", (pid,)).fetchone()[0])
            for pid in dict.fromkeys(chunk["context_passage_ids"] + chunk["body_passage_ids"])
        ]
        citation = json.loads(
            self.db.execute("SELECT value FROM citation_targets WHERE chunk_id=?", (chunk_id,)).fetchone()[0]
        )
        return {
            "chunk": chunk,
            "document": doc,
            "passages": passages,
            "citation": citation,
            "page_status": "declared_unverified",
            "bundle_identity": self.metadata["bundle_identity"],
        }

    def search(self, question: str, top_k: int = 5, mode: str = "OR", document_id: str | None = None) -> dict[str, Any]:
        start = time.perf_counter()
        response = {
            "question": question,
            "query_id": hashlib.sha256(encode([question, mode, top_k, document_id]).encode()).hexdigest()[:20],
            "index_identity": self.metadata["index_identity"],
            "bundle_identity": self.metadata["bundle_identity"],
            "mode": mode,
            "terms": [],
            "compiled_query": None,
            "hits": [],
            "status": "invalid_query",
        }
        if (
            not isinstance(question, str)
            or len(question) > CONFIG["max_chars"]
            or type(top_k) is not int
            or not 1 <= top_k <= 20
            or mode not in ("OR", "AND")
        ):
            return {**response, "reason": "invalid_input", "search_seconds": time.perf_counter() - start}
        if (
            document_id is not None
            and not self.db.execute("SELECT 1 FROM documents WHERE id=?", (document_id,)).fetchone()
        ):
            return {**response, "reason": "unknown_document", "search_seconds": time.perf_counter() - start}
        terms = self._terms(question)
        if not terms or len(terms) > CONFIG["max_terms"]:
            return {**response, "reason": "no_terms_or_too_many_terms", "search_seconds": time.perf_counter() - start}
        expression = f" {mode} ".join('"' + term.replace('"', '""') + '"' for term in terms)
        response.update(terms=terms, compiled_query=expression)
        sql = "SELECT c.id, bm25(chunk_fts,1.0,1.0) AS score FROM chunk_fts JOIN chunks c ON c.rowid=chunk_fts.rowid WHERE chunk_fts MATCH ?"
        params: list[Any] = [expression]
        if document_id is not None:
            sql += " AND c.document_id=?"
            params.append(document_id)
        sql += " ORDER BY score ASC, c.id ASC LIMIT ?"
        params.append(top_k)
        try:
            rows = self.db.execute(sql, params).fetchall()
            response["hits"] = [
                {
                    "rank": rank,
                    "raw_bm25": score,
                    "score_direction": "lower_is_better",
                    "origin": "direct",
                    **self.resolve(cid),
                }
                for rank, (cid, score) in enumerate(rows, 1)
            ]
            response["status"] = "ok" if rows else "no_matches"
        except sqlite3.Error as exc:
            response.update(status="error", reason=str(exc))
        response["search_seconds"] = time.perf_counter() - start
        return response

    def expand(self, result: dict[str, Any], budget_chars: int = 12000) -> dict[str, Any]:
        if type(budget_chars) is not int or budget_chars < 0:
            raise ValueError("Context budget must be a nonnegative integer")
        if result["index_identity"] != self.metadata["index_identity"]:
            raise ValueError("Search result belongs to another index")
        seen = {hit["chunk"]["chunk_id"] for hit in result["hits"]}
        added, skipped, used = [], [], 0
        for hit in result["hits"][:3]:
            seed = hit["chunk"]
            for field in ("previous_chunk_id", "next_chunk_id"):
                cid = seed.get(field)
                if not cid or cid in seen:
                    continue
                seen.add(cid)
                resolved = self.resolve(cid)
                neighbor = resolved["chunk"]
                reason = None
                if (
                    neighbor["document_id"] != seed["document_id"]
                    or neighbor["context_passage_ids"] != seed["context_passage_ids"]
                ):
                    reason = "section_or_document_boundary"
                elif used + len(neighbor["retrieval_text"]) > budget_chars:
                    reason = "budget"
                if reason:
                    skipped.append({"chunk_id": cid, "reason": reason})
                else:
                    used += len(neighbor["retrieval_text"])
                    added.append({**resolved, "origin": "neighbor_context", "seed_chunk_id": seed["chunk_id"]})
        added.sort(
            key=lambda row: (
                row["chunk"]["document_id"],
                min(p["start_offset"] for p in row["passages"] if p["passage_id"] in row["chunk"]["body_passage_ids"]),
            )
        )
        unique_passages = {}
        for row in added:
            for passage in row["passages"]:
                unique_passages[passage["passage_id"]] = passage
        return {
            "neighbors": added,
            "unique_passages": sorted(unique_passages.values(), key=lambda p: (p["document_id"], p["start_offset"])),
            "skipped": skipped,
            "added_characters": used,
        }
