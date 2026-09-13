"""Build inspectable context packages from an existing retrieval index."""

import argparse
import json
import sys
import time
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from mobile_rag.context_preparation import ContextBudget, prepare_context
from mobile_rag.retrieval import digest, new_run_dir, write_json
from mobile_rag.retrieval_hybrid import HybridRetriever, RetrievalConfig, latest_index


def run(index=None, *, output_root: Path, enable_bm25=True, enable_embeddings=True):
    config = RetrievalConfig(enable_bm25, enable_embeddings)
    config.validate()
    index = index or latest_index(ROOT, config)
    out = new_run_dir(output_root)
    hashes = {name: digest(index / name) for name in ("retrieval.sqlite", "passage.sqlite")}
    packages, measurements = {}, []
    with HybridRetriever(index, config) as retriever:
        result = retriever.search("What should I remember about bubble CPAP?")
        expansion = retriever.expand(result)
        overlap = deepcopy(result)
        overlap["hits"] += overlap["hits"][:1]
        invalid = deepcopy(result)
        invalid["bundle_identity"] = "invalid-demonstration"
        cases = [
            ("normal", result, expansion, ContextBudget()),
            ("overlapping", overlap, expansion, ContextBudget()),
            ("oversized", result, expansion, ContextBudget(100, 0, 0)),
            ("empty", {**result, "status": "no_matches", "hits": []}, None, ContextBudget()),
            ("invalid", invalid, None, ContextBudget()),
        ]
        for name, query_result, neighbors, budget in cases:
            start = time.perf_counter()
            package = prepare_context(retriever, query_result, neighbors, budget)
            elapsed = (time.perf_counter() - start) * 1000
            assert package == prepare_context(retriever, query_result, neighbors, budget)
            assert len(package["context_text"]) <= package["budget"]["evidence_allowance"]
            packages[name] = package
            write_json(out / f"{name}.json", package)
            measurements.append(
                {
                    "case": name,
                    "status": package["status"],
                    "packing_ms": elapsed,
                    "characters": package["budget"]["used"],
                    "groups": len(package["evidence_groups"]),
                }
            )
    assert [packages[n]["status"] for n in ("normal", "overlapping", "oversized", "empty", "invalid")] == [
        "ready",
        "ready",
        "budget_blocked",
        "empty",
        "invalid_evidence",
    ]
    assert all(digest(index / n) == h for n, h in hashes.items())
    summary = {
        "index": str(index),
        "retrieval_config": {"enable_bm25": enable_bm25, "enable_embeddings": enable_embeddings},
        "source_hashes": hashes,
        "checks_passed": True,
        "deterministic": True,
        "read_only_hashes_unchanged": True,
        "measurements": measurements,
        "counting_method": "unicode_characters_not_tokens",
        "clinical_accuracy": "not_measured",
    }
    write_json(out / "summary.json", summary)
    print(json.dumps({"output": str(out), **summary}, indent=2))
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--bm25", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--embeddings", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()
    run(args.index, output_root=args.output_root, enable_bm25=args.bm25, enable_embeddings=args.embeddings)
