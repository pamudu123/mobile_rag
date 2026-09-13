"""Build inspectable context packages from an existing retrieval index."""

import argparse
import json
import sys
import time
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from mobile_rag.context_preparation import ContextBudget, prepare_context
from mobile_rag.retrieval import digest, write_json
from mobile_rag.retrieval_enhanced import EnhancedRetriever


def run(index=None):
    index = index or max((ROOT / "artifacts/step-07").glob("*/enhancement_manifest.json")).parent
    out = ROOT / "artifacts/context-preparation" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    out.mkdir(parents=True)
    hashes = {name: digest(index / name) for name in ("retrieval.sqlite", "passage.sqlite")}
    packages, measurements = {}, []
    with EnhancedRetriever(index) as retriever:
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
            ("empty", retriever.search("nonexistentxyzunfindable"), None, ContextBudget()),
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
    run(parser.parse_args().index)
