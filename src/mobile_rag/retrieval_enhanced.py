"""Bounded lexical retrieval experiments; original evidence remains unchanged."""

import json
import shutil
import sqlite3
import time
from pathlib import Path

from mobile_rag.retrieval import Retriever, digest, new_run_dir, write_json

FILLER = frozenset(
    [
        "what",
        "should",
        "i",
        "remember",
        "please",
        "tell",
        "me",
        "about",
        "explain",
        "the",
        "a",
        "an",
        "is",
        "are",
        "of",
        "for",
        "to",
        "in",
        "how",
        "during",
        "busy",
        "frontline",
        "asks",
        "ask",
        "face",
        "facing",
        "this",
        "that",
        "these",
        "those",
        "situation",
        "correct",
        "answer",
        "from",
        "can",
        "could",
        "would",
        "you",
        "we",
        "my",
        "our",
        "your",
        "need",
        "know",
        "help",
        "understand",
        "give",
        "provide",
    ]
)
SETTINGS = {"version": 1, "heading_weight": 3.0, "candidate_limit": 40, "rrf_k": 60, "near_distance": 8}
# Corpus-attested expansion, not a generated medical synonym dictionary.
ALIASES = {"cpap": "continuous positive airway pressure"}


def clean_question(terms):
    """Filter conversational tokens independent of wording or sentence order.

    Input uses the index tokenizer. Preserve clinical setting/role terms such
    as clinic and health worker, as well as negations and numeric qualifiers.
    """
    return [term for term in terms if term not in FILLER]


def quoted(text):
    return '"' + text.replace('"', '""') + '"'


def fuse(branches, k=60):
    scores, evidence = {}, {}
    for name, ids in branches.items():
        for rank, cid in enumerate(dict.fromkeys(ids), 1):
            scores[cid] = scores.get(cid, 0.0) + 1 / (k + rank)
            evidence.setdefault(cid, {})[name] = rank
    return sorted(scores, key=lambda cid: (-scores[cid], cid)), scores, evidence


def build_enhanced(index_dir: Path, output_root: Path) -> Path:
    with Retriever(index_dir) as base:
        out = new_run_dir(output_root)
        for name in ("retrieval.sqlite", "index_manifest.json"):
            shutil.copyfile(index_dir / name, out / name)
        path = out / "passage.sqlite"
        with sqlite3.connect(path) as db:
            db.execute(
                "CREATE VIRTUAL TABLE units USING fts5(heading,body,chunk_id UNINDEXED,passage_id UNINDEXED,tokenize='unicode61')"
            )
            count = 0
            for (value,) in base.db.execute("SELECT value FROM chunks ORDER BY id"):
                chunk = json.loads(value)
                resolved = base.resolve(chunk["chunk_id"])
                passages = {p["passage_id"]: p for p in resolved["passages"]}
                heading = "\n".join(passages[p]["text"] for p in chunk["context_passage_ids"])
                for pid in chunk["body_passage_ids"]:
                    passage = passages[pid]
                    if passage["kind"] in {"heading", "page_marker"}:
                        continue
                    db.execute("INSERT INTO units VALUES (?,?,?,?)", (heading, passage["text"], chunk["chunk_id"], pid))
                    count += 1
            db.execute("INSERT INTO units(units) VALUES('integrity-check')")
            assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        write_json(
            out / "enhancement_manifest.json",
            {
                "settings": SETTINGS,
                "aliases": ALIASES,
                "alias_source": "Bubble-CPAP-guidelines-2017.md: Continuous positive airway pressure (CPAP)",
                "base_database_sha256": digest(out / "retrieval.sqlite"),
                "passage_database_sha256": digest(path),
                "units": count,
            },
        )
    return out


class EnhancedRetriever(Retriever):
    def __init__(self, index_dir):
        manifest = json.loads((index_dir / "enhancement_manifest.json").read_text(encoding="utf-8"))
        if (
            manifest["settings"] != SETTINGS
            or manifest["aliases"] != ALIASES
            or digest(index_dir / "passage.sqlite") != manifest["passage_database_sha256"]
            or digest(index_dir / "retrieval.sqlite") != manifest["base_database_sha256"]
        ):
            raise ValueError("Enhancement integrity mismatch")
        super().__init__(index_dir)
        self.units = sqlite3.connect((index_dir / "passage.sqlite").resolve().as_uri() + "?mode=ro", uri=True)

    def close(self):
        self.units.close()
        super().close()

    def search(self, question, top_k=5, mode="OR", document_id=None, disabled=()):
        start = time.perf_counter()
        result = super().search(question, top_k, mode, document_id)
        if result["status"] in {"invalid_query", "error"}:
            return result
        if mode != "OR":
            return result  # Explicit AND retains the baseline contract.
        focused = clean_question(result["terms"])
        result.update(
            cleaned_question=" ".join(focused),
            focused_terms=focused,
            query_cleanup_version="conversational-stopwords/v1",
            retrieval_variant="enhanced_v2_query_cleanup",
        )
        if not focused:
            return {
                **result, "status": "invalid_query", "reason": "no_clinical_terms",
                "hits": [], "compiled_query": None, "branches": {}, "branch_queries": {},
                "search_seconds": time.perf_counter() - start,
            }
        focused_query = " OR ".join(map(quoted, focused))
        result["compiled_query"] = focused_query
        # Every fused branch uses the cleaned terms; otherwise baseline/heading
        # votes can reintroduce the same conversational distractors.
        specs = [("baseline", focused_query, 1.0)]
        if "heading" not in disabled:
            specs.append(("heading", focused_query, SETTINGS["heading_weight"]))
        if "focused" not in disabled:
            specs.append(("focused", focused_query, 3.0))
        if 2 <= len(focused) <= 8:
            if "phrase" not in disabled:
                specs.append(("phrase", quoted(" ".join(focused)), 3.0))
            if "proximity" not in disabled:
                specs.append(("proximity", "NEAR(" + " ".join(map(quoted, focused)) + ", 8)", 3.0))
        expanded = [quoted(ALIASES[t]) for t in focused if t in ALIASES]
        if expanded and "aliases" not in disabled:
            specs.append(("aliases", focused_query + " OR " + " OR ".join(expanded), 3.0))
        branches, queries = {}, {}
        for name, expression, weight in specs:
            sql = "SELECT c.id,bm25(chunk_fts,?,1.0) score FROM chunk_fts JOIN chunks c ON c.rowid=chunk_fts.rowid WHERE chunk_fts MATCH ?"
            args = [weight, expression]
            if document_id is not None:
                sql += " AND c.document_id=?"
                args.append(document_id)
            rows = self.db.execute(sql + " ORDER BY score,c.id LIMIT 40", args)
            branches[name] = [r[0] for r in rows]
            queries[name] = expression
        matched_passages = {}
        if "passages" not in disabled:
            # Bounded candidate pool; repeated passages do not multiply a parent's vote.
            rows = self.units.execute(
                "SELECT chunk_id,passage_id,bm25(units,3.0,1.0) score FROM units WHERE units MATCH ? ORDER BY score,chunk_id,passage_id LIMIT 160",
                (focused_query,),
            )
            ids = []
            for cid, pid, _ in rows:
                if document_id is not None and self.resolve(cid)["chunk"]["document_id"] != document_id:
                    continue
                if cid not in matched_passages and len(ids) < 40:
                    ids.append(cid)
                    matched_passages[cid] = pid
            branches["passages"] = ids
            queries["passages"] = focused_query
        ids, scores, evidence = fuse(branches)
        result.update(
            hits=[
                {
                    **self.resolve(cid),
                    "rank": rank,
                    "rrf_score": scores[cid],
                    "score_direction": "higher_is_better",
                    "origin": "direct",
                    "branch_ranks": evidence[cid],
                    "matched_passage_id": matched_passages.get(cid),
                }
                for rank, cid in enumerate(ids[:top_k], 1)
            ],
            branches=branches,
            branch_queries=queries,
            focused_terms=focused,
            status="ok" if ids else "no_matches",
            retrieval_variant="enhanced_v2_query_cleanup",
        )
        result["search_seconds"] = time.perf_counter() - start
        return result
