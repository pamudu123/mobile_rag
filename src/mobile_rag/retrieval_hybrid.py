"""Independent lexical and local BGE retrieval with source-preserving rank fusion."""

import argparse
import hashlib
import json
import shutil
import threading
import time
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

from mobile_rag.retrieval import (
    CONFIG,
    Retriever,
    artifact_order,
    digest,
    latest_bundle,
    load_bundle,
    new_run_dir,
    write_json,
)
from mobile_rag.retrieval_enhanced import EnhancedRetriever, clean_question, fuse

MODEL = "BAAI/bge-small-en-v1.5"
REVISION = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
MODEL_LOCK = threading.Lock()


@dataclass(frozen=True)
class RetrievalConfig:
    enable_bm25: bool = True
    enable_embeddings: bool = True
    candidate_limit: int = 20

    def validate(self):
        if type(self.enable_bm25) is not bool or type(self.enable_embeddings) is not bool:
            raise ValueError("Retrieval switches must be booleans")
        if not (self.enable_bm25 or self.enable_embeddings):
            raise ValueError("Enable at least one retrieval path: BM25 or embeddings")
        if type(self.candidate_limit) is not int or not 1 <= self.candidate_limit <= 20:
            raise ValueError("candidate_limit must be between 1 and 20")


class BGEEncoder:
    def __init__(self, *, download=False):
        import onnxruntime as ort
        from huggingface_hub import snapshot_download
        from tokenizers import Tokenizer

        root = Path(snapshot_download(
            MODEL, revision=REVISION, allow_patterns=["onnx/model.onnx", "tokenizer.json"],
            local_files_only=not download,
        ))
        self.tokenizer = Tokenizer.from_file(str(root / "tokenizer.json"))
        self.tokenizer.no_truncation()
        self.tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")
        options = ort.SessionOptions()
        options.intra_op_num_threads = 4
        self.session = ort.InferenceSession(
            str(root / "onnx/model.onnx"), sess_options=options, providers=["CPUExecutionProvider"],
        )
        self.identity = {
            "model": MODEL, "revision": REVISION, "dimensions": 384,
            "pooling": "cls", "normalization": "l2", "query_prefix": QUERY_PREFIX,
            "model_sha256": digest(root / "onnx/model.onnx"),
            "tokenizer_sha256": digest(root / "tokenizer.json"),
        }
        self.lock = threading.Lock()

    def windows(self, text):
        # Overlapping character spans derived from token offsets avoid dropping
        # the tail of oversized source chunks. Context still resolves the parent.
        with self.lock:
            encoded = self.tokenizer.encode(text, add_special_tokens=False)
        for start in range(0, len(encoded.ids), 384):
            offsets = encoded.offsets[start:start + 448]
            if offsets:
                yield text[offsets[0][0]:offsets[-1][1]], offsets[0][0], offsets[-1][1]
            if start + 448 >= len(encoded.ids):
                break

    def encode(self, texts, *, query=False):
        if query:
            texts = [QUERY_PREFIX + text for text in texts]
        with self.lock:
            encodings = self.tokenizer.encode_batch(texts)
            if any(len(e.ids) > 512 for e in encodings):
                raise ValueError("BGE input exceeds 512 tokens; input was not silently truncated")
            values = {
                "input_ids": np.array([e.ids for e in encodings], dtype=np.int64),
                "attention_mask": np.array([e.attention_mask for e in encodings], dtype=np.int64),
                "token_type_ids": np.array([e.type_ids for e in encodings], dtype=np.int64),
            }
            outputs = self.session.run(None, {i.name: values[i.name] for i in self.session.get_inputs()})
        vectors = outputs[0]
        if vectors.ndim == 3:
            vectors = vectors[:, 0, :]
        vectors = np.asarray(vectors, dtype=np.float32)
        if vectors.shape != (len(texts), 384) or not np.isfinite(vectors).all():
            raise ValueError("Invalid BGE output")
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        if (norms == 0).any():
            raise ValueError("Zero BGE embedding")
        return vectors / norms


@lru_cache(maxsize=1)
def _encoder():
    return BGEEncoder()


def get_encoder():
    # Prevent multiple simultaneous cache misses from loading four model copies.
    with MODEL_LOCK:
        return _encoder()


def build_dense(index_dir, output_root, *, encoder=None):
    """Create a new compatible bundle; never modify an existing index."""
    encoder = encoder or BGEEncoder(download=True)
    out = new_run_dir(Path(output_root))
    units, matrices = [], []
    with EnhancedRetriever(Path(index_dir)) as retriever:
        for name in ("retrieval.sqlite", "index_manifest.json", "passage.sqlite", "enhancement_manifest.json"):
            shutil.copyfile(Path(index_dir) / name, out / name)
        pending = []
        for (value,) in retriever.db.execute("SELECT value FROM chunks ORDER BY id"):
            chunk = json.loads(value)
            for text, start, end in encoder.windows(chunk["retrieval_text"]):
                units.append({
                    "chunk_id": chunk["chunk_id"], "document_id": chunk["document_id"],
                    "start": start, "end": end, "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                })
                pending.append(text)
                if len(pending) == 16:
                    matrices.append(encoder.encode(pending))
                    pending = []
                    if len(units) % 256 == 0:
                        print(f"Embedded {len(units)} source windows", flush=True)
        if pending:
            matrices.append(encoder.encode(pending))
        if not units:
            raise ValueError("Cannot embed an empty corpus")
        np.save(out / "vectors.npy", np.concatenate(matrices), allow_pickle=False)
        write_json(out / "embedding_units.json", units)
        write_json(out / "dense_manifest.json", {
            "schema": "bge-dense/v1", "encoder": encoder.identity,
            "index_identity": retriever.metadata["index_identity"],
            "bundle_identity": retriever.metadata["bundle_identity"],
            "retrieval_sha256": digest(out / "retrieval.sqlite"),
            "vectors_sha256": digest(out / "vectors.npy"),
            "units_sha256": digest(out / "embedding_units.json"),
            "units": len(units), "window_tokens": 448, "stride_tokens": 384,
            "table_limitations": "Token windows can separate headers; original full parents are used for evidence.",
        })
    return out


@lru_cache(maxsize=2)
def _load_dense(path, manifest_hash, vectors_hash, units_hash):
    root = Path(path)
    manifest = json.loads((root / "dense_manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != "bge-dense/v1":
        raise ValueError("Unsupported dense index schema")
    if vectors_hash != manifest["vectors_sha256"] or units_hash != manifest["units_sha256"]:
        raise ValueError("Dense artifact integrity mismatch")
    units = json.loads((root / "embedding_units.json").read_text(encoding="utf-8"))
    vectors = np.load(root / "vectors.npy", allow_pickle=False)
    if (manifest["units"] != len(units) or vectors.shape != (len(units), 384)
            or vectors.dtype != np.float32 or not np.isfinite(vectors).all()):
        raise ValueError("Invalid dense matrix")
    if not np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-4):
        raise ValueError("Dense vectors are not normalized")
    vectors.flags.writeable = False
    return manifest, units, vectors


def latest_index(root, config=None):
    config = config or RetrievalConfig()
    config.validate()
    pattern = "*/dense_manifest.json" if config.enable_embeddings else "*/enhancement_manifest.json"
    source = load_bundle(latest_bundle(Path(root)))["manifest"]["run"]["bundle_fingerprint"]
    found = sorted((Path(root) / "artifacts/03_retrieval_enhanced").glob(pattern), key=artifact_order, reverse=True)
    for path in found:
        try:
            # Validate assets without loading/downloading the query encoder.
            with EnhancedRetriever(path.parent) as retriever:
                if retriever.metadata["bundle_identity"] != source:
                    continue
                if config.enable_embeddings:
                    manifest, _, _ = _load_dense(
                        str(path.parent.resolve()), digest(path), digest(path.parent / "vectors.npy"),
                        digest(path.parent / "embedding_units.json"),
                    )
                    if (manifest["bundle_identity"] != source
                            or manifest["index_identity"] != retriever.metadata["index_identity"]
                            or manifest["retrieval_sha256"] != digest(path.parent / "retrieval.sqlite")):
                        continue
            return path.parent
        except (ValueError, KeyError, OSError):
            continue
    raise ValueError("No compatible index matches current chunks; rebuild the requested retrieval index")


class HybridRetriever(Retriever):
    def __init__(self, index_dir, config=None, *, encoder=None):
        self.config = config or RetrievalConfig()
        self.config.validate()
        self.lexical = None
        super().__init__(Path(index_dir))
        try:
            if self.config.enable_bm25:
                self.lexical = EnhancedRetriever(Path(index_dir))
            if self.config.enable_embeddings:
                root = Path(index_dir)
                if not (root / "dense_manifest.json").exists():
                    raise ValueError("Embeddings enabled but dense index missing; build the BGE index first")
                self.manifest, self.dense_units, self.vectors = _load_dense(
                    str(root.resolve()), digest(root / "dense_manifest.json"),
                    digest(root / "vectors.npy"), digest(root / "embedding_units.json"),
                )
                if (self.manifest["index_identity"] != self.metadata["index_identity"]
                        or self.manifest["bundle_identity"] != self.metadata["bundle_identity"]
                        or self.manifest["retrieval_sha256"] != digest(root / "retrieval.sqlite")):
                    raise ValueError("Dense index belongs to another source bundle")
                self.encoder = encoder or get_encoder()
                if self.encoder.identity != self.manifest["encoder"]:
                    raise ValueError("Query encoder differs from index encoder")
        except Exception:
            self.close()
            raise

    def close(self):
        if self.lexical is not None:
            self.lexical.close()
            self.lexical = None
        super().close()

    def search(self, question, top_k=5, mode="OR", document_id=None):
        start = time.perf_counter()
        result = {
            "question": question, "mode": mode, "terms": [], "compiled_query": None,
            "index_identity": self.metadata["index_identity"], "bundle_identity": self.metadata["bundle_identity"],
            "retrieval_variant": "hybrid_bge/v1", "retrieval_config": asdict(self.config),
            "query_id": hashlib.sha256(json.dumps(
                [question, top_k, mode, document_id, asdict(self.config)], sort_keys=True,
            ).encode()).hexdigest()[:20],
            "status": "invalid_query", "hits": [], "branches": {}, "branch_queries": {},
        }
        if (not isinstance(question, str) or not question.strip() or len(question) > CONFIG["max_chars"]
                or type(top_k) is not int or not 1 <= top_k <= 20 or mode not in ("OR", "AND")):
            return {**result, "reason": "invalid_input"}
        if document_id is not None and not self.db.execute("SELECT 1 FROM documents WHERE id=?", (document_id,)).fetchone():
            return {**result, "reason": "unknown_document"}
        terms = self._terms(question)
        result["terms"] = terms
        if not terms or len(terms) > CONFIG["max_terms"]:
            return {**result, "reason": "no_terms_or_too_many_terms"}
        if not clean_question(terms):
            return {**result, "reason": "no_clinical_terms"}
        paths, timings, dense_scores = {}, {}, {}
        limit = max(top_k, self.config.candidate_limit)
        if self.lexical is not None:
            t = time.perf_counter()
            lexical = self.lexical.search(question, limit, mode, document_id)
            if lexical["status"] in {"error", "invalid_query"}:
                return {**result, "status": lexical["status"], "reason": lexical.get("reason")}
            paths["bm25"] = [h["chunk"]["chunk_id"] for h in lexical["hits"]]
            timings["bm25"] = time.perf_counter() - t
            result["lexical_diagnostics"] = {k: lexical.get(k) for k in ("status", "focused_terms", "branch_queries")}
            result["terms"] = lexical.get("terms", [])
            result["compiled_query"] = lexical.get("compiled_query")
        if self.config.enable_embeddings:
            t = time.perf_counter()
            try:
                vector = self.encoder.encode([question], query=True)[0]
            except ValueError:
                return {**result, "status": "error", "reason": "query_embedding_failed"}
            scores = self.vectors @ vector
            # Search the entire dense corpus, independent of lexical matches.
            for unit, score in zip(self.dense_units, scores, strict=True):
                if document_id is None or unit["document_id"] == document_id:
                    cid = unit["chunk_id"]
                    dense_scores[cid] = max(float(score), dense_scores.get(cid, -float("inf")))
            paths["embeddings"] = sorted(dense_scores, key=lambda cid: (-dense_scores[cid], cid))[:limit]
            timings["embeddings"] = time.perf_counter() - t
            result["embedding_identity"] = self.encoder.identity
        ids, scores, ranks = fuse(paths)
        result.update(
            status="ok" if ids else "no_matches", branches=paths, path_seconds=timings,
            hits=[{
                **self.resolve(cid), "rank": rank, "origin": "direct", "rrf_score": scores[cid],
                "score_direction": "higher_is_better", "branch_ranks": ranks[cid],
                "dense_score": dense_scores.get(cid),
            } for rank, cid in enumerate(ids[:top_k], 1)],
            search_seconds=time.perf_counter() - start,
        )
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build a local BGE index from an existing lexical bundle")
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    print(build_dense(args.index, args.output_root))
