"""Evidence-only generation through OpenRouter with fail-closed validation."""

import hashlib
import json
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

from mobile_rag.answer_schema import GroundedAnswer, answer_json_schema
from mobile_rag.environment import openrouter_api_key

# MODEL = "google/gemma-3-4b-it"
MODEL = "qwen/qwen3-14b"
PROMPT_VERSION = "evidence-answer/v3"
PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "answer_generation.md"
INSTRUCTIONS = PROMPT_PATH.read_text(encoding="utf-8").rstrip()


@dataclass(frozen=True)
class GenerationConfig:
    max_output_tokens: int = 1024
    timeout_seconds: int = 60
    provider: str = "DeepInfra"

    def validate(self):
        for value in (self.max_output_tokens, self.timeout_seconds):
            if type(value) is not int or value <= 0:
                raise ValueError("Generation limits must be positive integers")
        if self.provider != "DeepInfra":
            raise ValueError("This adapter currently pins DeepInfra")


def validate_package(package):
    """Check package consistency; source authenticity is established upstream."""
    if package.get("status") != "ready" or not package.get("question"):
        raise ValueError("Context is not ready")
    groups = package["evidence_groups"]
    citations = package["citation_map"]
    lines = package["context_text"].split("\n")
    if not groups or len(lines) != len(groups) or len(citations) != len(groups):
        raise ValueError("Inconsistent evidence groups")
    owners = {}
    for number, (group, line) in enumerate(zip(groups, lines, strict=True), 1):
        label = f"S{number}"
        if group["label"] != label or label not in citations:
            raise ValueError("Inconsistent citation labels")
        rendered = {k: group[k] for k in ("label", "document_id", "chunk_id", "source_passages", "page_status")}
        if json.loads(line) != rendered:
            raise ValueError("Rendered context differs from evidence")
        citation = citations[label]
        if any(citation[k] != group[k] for k in ("document_id", "chunk_id")):
            raise ValueError("Citation targets another group")
        if citation["source_passage_ids"] != [p["passage_id"] for p in group["source_passages"]]:
            raise ValueError("Citation passage mismatch")
        for passage in group["source_passages"]:
            key = (group["document_id"], passage["passage_id"])
            if "text" in passage:
                if not isinstance(passage["text"], str) or key in owners or "reference" in passage:
                    raise ValueError("Invalid source passage")
                owners[key] = label
            elif passage.get("reference") != owners.get(key) or key not in owners:
                raise ValueError("Unresolved passage reference")


def make_request(package, config):
    validate_package(package)
    schema = answer_json_schema(list(package["citation_map"]))
    content = (
        INSTRUCTIONS
        + "\n\nINPUT DATA:\n"
        + json.dumps(
            {
                "question": package["question"],
                "evidence": [json.loads(line) for line in package["context_text"].split("\n")],
            },
            ensure_ascii=False,
        )
    )
    # A single user turn avoids relying on provider-specific system-role rewriting.
    return {
        "model": MODEL,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0,
        "max_tokens": config.max_output_tokens,
        "stream": False,
        "provider": {"only": [config.provider], "allow_fallbacks": False, "require_parameters": True},
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "grounded_answer", "strict": True, "schema": schema},
        },
    }


def validate_answer(content, citation_map):
    return GroundedAnswer.model_validate_json(content, context={"citation_map": citation_map}).model_dump()


def post_openrouter(payload, api_key, timeout):
    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("Response too large")
        return json.loads(raw)


def generate_answer(package, *, config=None, api_key=None, live=False, transport=None):
    config = config or GenerationConfig()
    config.validate()
    output = {
        "status": "invalid_context",
        "model": MODEL,
        "prompt_version": PROMPT_VERSION,
        "config": asdict(config),
        "answer": None,
        "usage": None,
        "latency_ms": None,
        "live_request_sent": False,
        "citation_validation": "not_run",
        "support_validation": "not_performed",
    }
    if package.get("status") in {"empty", "budget_blocked"}:
        return {**output, "status": "insufficient_evidence", "reason": "context_" + package["status"]}
    try:
        payload = make_request(package, config)
    except (KeyError, TypeError, ValueError) as exc:
        return {**output, "reason": str(exc)}
    output["request_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    output["citation_map"] = package["citation_map"]
    output["bundle_identity"] = package["bundle_identity"]
    if not live:
        return {**output, "status": "dry_run", "request": payload}
    api_key = api_key or openrouter_api_key()
    if not api_key:
        return {**output, "status": "credentials_required"}
    start = time.perf_counter()
    output["live_request_sent"] = transport is None
    output["transport"] = "openrouter" if transport is None else "injected_test_transport"
    try:
        response = (transport or post_openrouter)(payload, api_key, config.timeout_seconds)
        if not isinstance(response, dict):
            raise TypeError("Response must be an object")
        if "error" in response:
            output.update(status="api_error", reason="Provider returned an error payload")
            return output
        choice = response["choices"][0]
        output.update(
            usage=response.get("usage"),
            provider=response.get("provider"),
            response_id=response.get("id"),
            finish_reason=choice.get("finish_reason"),
            returned_model=response.get("model"),
        )
        if response.get("model") != MODEL:
            output.update(status="invalid_response", reason="Unexpected model")
            return output
        if choice.get("finish_reason") != "stop":
            output.update(status="incomplete_response", reason="Completion did not finish normally")
            return output
        answer = validate_answer(choice["message"]["content"], package["citation_map"])
        output.update(status=answer["status"], answer=answer, citation_validation="passed")
    except urllib.error.HTTPError as exc:
        output.update(status="api_error", http_status=exc.code, reason="HTTP request failed; response body omitted")
    except (urllib.error.URLError, TimeoutError, OSError):
        output.update(status="api_error", reason="Network failure or timeout; not automatically retried")
    except (AttributeError, KeyError, IndexError, TypeError, ValueError):
        output.update(status="invalid_response", answer=None, reason="Response schema or citation validation failed")
    finally:
        output["latency_ms"] = (time.perf_counter() - start) * 1000
    return output
