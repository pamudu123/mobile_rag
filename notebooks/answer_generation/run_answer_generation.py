"""Prepare one grounded request; live execution requires explicit --live."""

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from mobile_rag.answer_generation import GemmaTokenCounter, GenerationConfig, generate_answer, make_request
from mobile_rag.context_preparation import prepare_context
from mobile_rag.retrieval import write_json
from mobile_rag.retrieval_enhanced import EnhancedRetriever


def run(question="What should I remember about bubble CPAP?", index=None, tokenizer_dir=None, live=False):
    index = index or max((ROOT / "artifacts/step-07").glob("*/enhancement_manifest.json")).parent
    tokenizer_dir = tokenizer_dir or os.environ.get("GEMMA_TOKENIZER_DIR")
    out = ROOT / "artifacts/answer-generation" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    out.mkdir(parents=True)
    with EnhancedRetriever(index) as retriever:
        result = retriever.search(question)
        package = prepare_context(retriever, result, retriever.expand(result))
    counter = GemmaTokenCounter(Path(tokenizer_dir)) if tokenizer_dir else None
    generated = generate_answer(package, counter=counter, live=live)
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
    parser.add_argument("--tokenizer-dir", type=Path)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    run(args.question, args.index, args.tokenizer_dir, args.live)
