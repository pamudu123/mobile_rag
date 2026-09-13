"""Deterministic source-preserving context packing, without model calls."""

import json
from dataclasses import asdict, dataclass

from mobile_rag.retrieval import Retriever


@dataclass(frozen=True)
class ContextBudget:
    total_chars: int = 20000
    instruction_reserve: int = 7000
    answer_reserve: int = 4000

    def allowance(self, question):
        if any(type(v) is not int or v < 0 for v in asdict(self).values()):
            raise ValueError("Budget values must be nonnegative integers")
        return max(0, self.total_chars - self.instruction_reserve - self.answer_reserve - len(question))


def prepare_context(retriever: Retriever, result, expansion=None, budget=None):
    """Validate against the open index before packing whole parent-chunk groups.

    Shared passages are rendered once and referenced by label thereafter. JSON
    encoding separates evidence text from structural labels; it is not a prompt
    injection detector. Exact provider token accounting is deliberately absent.
    """
    budget = budget or ContextBudget()
    question = result.get("question", "")
    if not isinstance(question, str):
        raise TypeError("Question must be text")
    allowance = budget.allowance(question)
    package = {
        "question": question,
        "index_identity": retriever.metadata["index_identity"],
        "bundle_identity": retriever.metadata["bundle_identity"],
        "status": "invalid_evidence",
        "context_text": "",
        "evidence_groups": [],
        "citation_map": {},
        "excluded_evidence": [],
        "budget": {
            **asdict(budget),
            "question_reserve": len(question),
            "evidence_allowance": allowance,
            "counting_method": "unicode_characters_not_tokens",
            "used": 0,
        },
        "diagnostics": {
            "duplicate_passages_removed": 0,
            "limitations": [
                "Structural preservation does not establish clinical completeness or answerability.",
                "Cross-chunk qualifier links are unavailable; no semantic conflict detection.",
                "Character budgeting does not guarantee a provider token limit.",
            ],
            "upstream_exclusions": (expansion or {}).get("skipped", []),
        },
    }
    try:
        for key in ("index_identity", "bundle_identity"):
            if result[key] != package[key]:
                raise ValueError("Mixed or unknown evidence identity")
        if result["status"] not in {"ok", "no_matches"}:
            raise ValueError("Retrieval did not complete successfully")
        hits = result["hits"]
        if (result["status"] == "ok") != bool(hits):
            raise ValueError("Inconsistent retrieval status")
        seeds = {h["chunk"]["chunk_id"]: h["chunk"] for h in hits}
        rows = [(h, "direct") for h in hits]
        rows += [(h, "neighbor_context") for h in (expansion or {}).get("neighbors", [])]
        verified = []
        for row, origin in rows:
            cid = row["chunk"]["chunk_id"]
            canonical = retriever.resolve(cid)
            for key in ("chunk", "document", "passages", "citation", "bundle_identity", "page_status"):
                if row[key] != canonical[key]:
                    raise ValueError("Evidence differs from stored source: " + cid)
            if origin == "neighbor_context":
                seed = seeds.get(row.get("seed_chunk_id"))
                chunk = canonical["chunk"]
                if (
                    not seed
                    or cid not in (seed.get("previous_chunk_id"), seed.get("next_chunk_id"))
                    or seed["document_id"] != chunk["document_id"]
                    or seed["context_passage_ids"] != chunk["context_passage_ids"]
                ):
                    raise ValueError("Invalid neighbor relationship")
            verified.append((canonical, origin, row.get("seed_chunk_id")))
    except (KeyError, TypeError, ValueError) as exc:
        package["diagnostics"]["error"] = str(exc)
        return package

    rendered, included_chunks, owners = [], set(), {}
    for row, origin, seed_id in verified:
        chunk = row["chunk"]
        cid, did = chunk["chunk_id"], chunk["document_id"]
        reason = None
        if cid in included_chunks:
            reason = "duplicate_chunk"
        elif origin == "neighbor_context" and seed_id not in included_chunks:
            reason = "seed_not_included"
        if reason:
            package["excluded_evidence"].append({"chunk_id": cid, "reason": reason})
            continue
        label = f"S{len(rendered) + 1}"
        passages = sorted(row["passages"], key=lambda p: (p["start_offset"], p["passage_id"]))
        entries, new_owners, duplicates = [], {}, 0
        for passage in passages:
            pid = passage["passage_id"]
            key = (did, pid)
            if key in owners:
                entries.append({"passage_id": pid, "reference": owners[key]})
                duplicates += 1
            else:
                entries.append({"passage_id": pid, "text": passage["text"]})
                new_owners[key] = label
        group = {
            "label": label,
            "document_id": did,
            "chunk_id": cid,
            "source_passages": entries,
            "page_status": "declared_unverified",
        }
        block = json.dumps(group, ensure_ascii=False, sort_keys=True)
        proposed = "\n".join([*rendered, block])
        if len(proposed) > allowance:
            package["excluded_evidence"].append({"chunk_id": cid, "reason": "whole_group_exceeds_remaining_budget"})
            continue
        rendered.append(block)
        owners.update(new_owners)
        included_chunks.add(cid)
        package["diagnostics"]["duplicate_passages_removed"] += duplicates
        package["evidence_groups"].append(
            {**group, "origin": origin, "seed_chunk_id": seed_id, "flags": chunk.get("flags", [])}
        )
        package["citation_map"][label] = {
            "document_id": did,
            "chunk_id": cid,
            "citation": row["citation"],
            "source_passage_ids": [p["passage_id"] for p in passages],
            "body_passage_ids": chunk["body_passage_ids"],
            "context_passage_ids": chunk["context_passage_ids"],
            "page_status": "declared_unverified",
        }
    package["context_text"] = "\n".join(rendered)
    package["budget"]["used"] = len(package["context_text"])
    package["status"] = "ready" if rendered else ("budget_blocked" if verified else "empty")
    return package
