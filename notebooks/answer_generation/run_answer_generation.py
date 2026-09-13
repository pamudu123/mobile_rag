"""Prepare one grounded request; live execution requires explicit --live."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from mobile_rag.answer_generation import GenerationConfig, generate_answer, make_request
from mobile_rag.context_preparation import prepare_context
from mobile_rag.retrieval import new_run_dir, write_json
from mobile_rag.retrieval_hybrid import HybridRetriever, RetrievalConfig, latest_index


def run(
    question="What should I remember about bubble CPAP?",
    index=None,
    live=False,
    *,
    output_root: Path,
    enable_bm25: bool = True,
    enable_embeddings: bool = True,
):
    config = RetrievalConfig(enable_bm25, enable_embeddings)
    config.validate()
    index = index or latest_index(ROOT, config)
    out = new_run_dir(output_root)
    with HybridRetriever(index, config) as retriever:
        result = retriever.search(question)
        package = prepare_context(retriever, result, retriever.expand(result))
    write_json(out / "retrieval.json", result)
    generated = generate_answer(package, live=live)
    write_json(out / "context.json", package)
    if package["status"] == "ready":
        write_json(out / "request_preview.json", make_request(package, GenerationConfig()))
    write_json(out / "result.json", generated)
    print(
        json.dumps(
            {
                "output": str(out),
                "status": generated["status"],
                "live_request_sent": generated["live_request_sent"],
                "answer": generated["answer"],
            },
            indent=2,
        )
    )
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", default="What should I remember about bubble CPAP?")
    parser.add_argument("--index", type=Path)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--bm25", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--embeddings", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()
    run(args.question, args.index, args.live, output_root=args.output_root,
        enable_bm25=args.bm25, enable_embeddings=args.embeddings)
