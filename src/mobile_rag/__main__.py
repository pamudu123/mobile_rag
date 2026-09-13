"""Package CLI; no model or network work is started without a subcommand."""

import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Source-backed mobile RAG tools")
    commands = parser.add_subparsers(dest="command")
    dense = commands.add_parser("build-dense", help="Build BGE vectors from a lexical index")
    dense.add_argument("--index", type=Path, required=True)
    dense.add_argument("--output-root", type=Path, required=True)
    evaluate = commands.add_parser("evaluate", help="Summarize saved records without model calls")
    evaluate.add_argument("run_dir", type=Path)
    evaluate.add_argument("--output", type=Path, required=True)
    evaluate.add_argument("--annotations", type=Path, help="JSON mapping record keys to relevant_chunk_ids")
    args = parser.parse_args()
    if args.command == "build-dense":
        from mobile_rag.retrieval_hybrid import build_dense

        print(build_dense(args.index, args.output_root))
    elif args.command == "evaluate":
        import json

        from mobile_rag.evaluation import evaluate_run
        from mobile_rag.retrieval import write_json

        annotations = json.loads(args.annotations.read_text(encoding="utf-8")) if args.annotations else None
        write_json(args.output, evaluate_run(args.run_dir, annotations))
        print(args.output)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
