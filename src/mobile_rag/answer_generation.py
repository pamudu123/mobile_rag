"""Evidence-only generation through OpenRouter with fail-closed validation."""

import hashlib
import json
import math
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

from mobile_rag.answer_schema import GroundedAnswer, answer_json_schema
from mobile_rag.environment import openrouter_api_key

# MODEL = "google/gemma-3-4b-it"
MODEL = "qwen/qwen3.5-9b"
PROMPT_VERSION = "evidence-answer/v6"
PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "answer_generation.md"
INSTRUCTIONS = PROMPT_PATH.read_text(encoding="utf-8").rstrip()
PROMPT_SHA256 = hashlib.sha256(INSTRUCTIONS.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class GenerationConfig:
    max_output_tokens: int = 1024 * 2 * 2 * 2
    timeout_seconds: int = 120
    model: str = MODEL
    temperature: float = 0.0
    max_retries: int = 2
    retry_delay_seconds: float = 0.5

    def validate(self):
        for value in (self.max_output_tokens, self.timeout_seconds):
            if type(value) is not int or value <= 0:
                raise ValueError("Generation limits must be positive integers")
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("Model must be a nonblank identifier")
        if (type(self.temperature) not in (int, float) or not math.isfinite(self.temperature)
                or not 0 <= self.temperature <= 2):
            raise ValueError("Temperature must be between 0 and 2")
        if type(self.max_retries) is not int or not 0 <= self.max_retries <= 3:
            raise ValueError("max_retries must be between 0 and 3")
        if (type(self.retry_delay_seconds) not in (int, float) or not math.isfinite(self.retry_delay_seconds)
                or not 0 <= self.retry_delay_seconds <= 10):
            raise ValueError("Retry delay must be between 0 and 10 seconds")


def generation_identity(config):
    """Identity of the loaded request implementation, not mutable prompt bytes on disk."""
    config.validate()
    return {
        "config": asdict(config),
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": PROMPT_SHA256,
        "schema_sha256": hashlib.sha256(json.dumps(answer_json_schema(["S1"]), sort_keys=True).encode()).hexdigest(),
        "adapter_version": "openrouter-grounded/v3",
    }


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
    config.validate()
    validate_package(package)
    return render_request(package["question"], [json.loads(line) for line in package["context_text"].split("\n")], config)


def render_request(question, evidence, config):
    """Render the full wire payload for generation and context budget accounting."""
    schema = answer_json_schema([group["label"] for group in evidence])
    content = (
        INSTRUCTIONS
        + "\n\nINPUT DATA:\n"
        + json.dumps(
            {
                "question": question,
                "evidence": evidence,
            },
            ensure_ascii=False,
        )
    )
    # A single user turn avoids relying on provider-specific system-role rewriting.
    return {
        "model": config.model,
        "messages": [{"role": "user", "content": content}],
        "temperature": config.temperature,
        "max_tokens": config.max_output_tokens,
        "stream": False,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "grounded_answer", "strict": True, "schema": schema},
        },
    }


def validate_answer(content, citation_map):
    payload = json.loads(content)
    if isinstance(payload, dict) and "reason" not in payload:
        citations = [label for label in payload.get("citations") or [] if isinstance(label, str) and label.strip()]
        if payload.get("status") == "answered":
            payload["reason"] = "Supported by " + (", ".join(citations) if citations else "the cited evidence") + "."
        elif payload.get("status") == "insufficient_evidence":
            payload["reason"] = "The supplied evidence does not fully support the requested fact."
        content = json.dumps(payload, ensure_ascii=False)
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


def _failure(status, reason, **extra):
    error = {"status": status, "reason": reason}
    error.update({key: value for key, value in extra.items() if value is not None})
    payload = {"status": status, "reason": reason, "error": error}
    if "http_status" in extra:
        payload["http_status"] = extra["http_status"]
    return payload


def generate_answer(package, *, config=None, api_key=None, live=False, transport=None):
    config = config or GenerationConfig()
    config.validate()
    output = {
        "status": "invalid_context",
        "model": config.model,
        "prompt_version": PROMPT_VERSION,
        "config": asdict(config),
        "generation_identity": generation_identity(config),
        "answer": None,
        "usage": None,
        "latency_ms": None,
        "live_request_sent": False,
        "citation_validation": "not_run",
        "support_validation": "not_performed",
        "abstention_origin": None,
        "attempts": [],
    }
    if package.get("status") in {"empty", "budget_blocked"}:
        return {**output, "status": "insufficient_evidence", "reason": "context_" + package["status"],
                "abstention_origin": "context"}
    try:
        payload = make_request(package, config)
    except (KeyError, TypeError, ValueError) as exc:
        return {**output, **_failure("invalid_context", str(exc), type=type(exc).__name__)}
    output["request_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    output["citation_map"] = package["citation_map"]
    output["bundle_identity"] = package["bundle_identity"]
    budget = package.get("budget", {})
    request_chars = len(json.dumps(payload, ensure_ascii=False))
    output["request_budget"] = {"serialized_request_chars": request_chars, "counting_method": "characters_not_tokens"}
    if request_chars + budget.get("answer_reserve", 0) > budget.get("total_chars", 20000):
        return {**output, **_failure("request_budget_exceeded", "Rendered request exceeds character budget")}
    if not live:
        return {**output, "status": "dry_run", "request": payload}
    api_key = api_key or openrouter_api_key()
    if not api_key:
        return {**output, **_failure("credentials_required", "OPENROUTER_API_KEY is missing")}
    start = time.perf_counter()
    output["live_request_sent"] = transport is None
    output["transport"] = "openrouter" if transport is None else "injected_test_transport"
    base_content = payload["messages"][0]["content"]
    retry_feedback = None
    try:
        for attempt in range(config.max_retries + 1):
            if retry_feedback:
                payload = {**payload, "messages": [{
                    "role": "user", "content": base_content + "\n\n## Retry feedback\n" + retry_feedback,
                }]}
            request_chars = len(json.dumps(payload, ensure_ascii=False))
            if request_chars + budget.get("answer_reserve", 0) > budget.get("total_chars", 20000):
                output.update(_failure("request_budget_exceeded", "Retry request exceeds character budget"))
                return output
            record = {
                "attempt": attempt + 1,
                "request_sha256": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
                "serialized_request_chars": request_chars,
            }
            if retry_feedback:
                record["retry_feedback"] = retry_feedback
            output["attempts"].append(record)
            try:
                response = (transport or post_openrouter)(payload, api_key, config.timeout_seconds)
                record["status"] = "response_received"
            except urllib.error.HTTPError as exc:
                retryable = exc.code == 429 or 500 <= exc.code <= 599
                record.update(status="http_error", http_status=exc.code)
                exc.close()
                if not retryable or attempt == config.max_retries:
                    raise
                time.sleep(config.retry_delay_seconds * (2 ** attempt))
                continue
            if not isinstance(response, dict):
                raise TypeError("Response must be an object")
            if "error" in response:
                output.update(_failure("api_error", "Provider returned an error payload", type="ProviderError"))
                return output
            choice = response["choices"][0]
            record.update(usage=response.get("usage"), finish_reason=choice.get("finish_reason"))
            output.update(
                usage=response.get("usage"),
                provider=response.get("provider"),
                response_id=response.get("id"),
                finish_reason=choice.get("finish_reason"),
                returned_model=response.get("model"),
            )
            if response.get("model") != config.model:
                output.update(_failure(
                    "invalid_response", "Unexpected model", type="UnexpectedModel",
                    expected_model=config.model, returned_model=response.get("model"),
                ))
                return output
            failure = None
            if choice.get("finish_reason") != "stop":
                failure = _failure(
                    "incomplete_response", "Completion did not finish normally",
                    type="IncompleteCompletion", finish_reason=choice.get("finish_reason"),
                )
                # Other finish reasons can represent filtering/refusal and are terminal.
                retryable = choice.get("finish_reason") == "length"
                retry_feedback = (
                    'Error: incomplete_response / IncompleteCompletion: Completion did not finish normally '
                    '(finish_reason="length"). Retry from the beginning with a concise, complete JSON object. '
                    'Return status, answer, reason, and citations only. Avoid lengthy explanations; '
                    'preserve necessary clinical qualifiers and cite only supplied evidence. '
                    'Do not continue the truncated response or output reasoning traces.'
                )
            else:
                try:
                    answer = validate_answer(choice["message"]["content"], package["citation_map"])
                except (KeyError, TypeError, ValueError):
                    failure = _failure(
                        "invalid_response", "Response schema or citation validation failed", type="InvalidAnswer",
                    )
                    retryable = True
                    retry_feedback = (
                        'Error: invalid_response: Response schema or citation validation failed. '
                        'Retry with one complete JSON object containing exactly status, answer, reason, and citations. '
                        'Use the required types, a nonblank reason, and only unique supplied citation labels. '
                        'For insufficient_evidence use an empty answer and empty citations. '
                        'Return no Markdown or extra text; ground every clinical claim in the supplied evidence.'
                    )
            if failure:
                record.update(status=failure["status"], error=failure["error"])
                if not retryable or attempt == config.max_retries:
                    output.update(failure)
                    return output
                time.sleep(config.retry_delay_seconds * (2 ** attempt))
                continue
            output.update(status=answer["status"], answer=answer, citation_validation="passed")
            if answer["status"] == "insufficient_evidence":
                output["abstention_origin"] = "model"
            return output
    except urllib.error.HTTPError as exc:
        output.update(_failure(
            "api_error",
            "HTTP request failed; response body omitted",
            type="HTTPError",
            http_status=exc.code,
        ))
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        output.update(_failure(
            "api_error",
            "Network failure or timeout; not automatically retried",
            type=type(exc).__name__,
        ))
    except (AttributeError, KeyError, IndexError, TypeError, ValueError) as exc:
        output.update(answer=None, **_failure(
            "invalid_response",
            "Response schema or citation validation failed",
            type=type(exc).__name__,
            message=str(exc),
        ))
    finally:
        output["latency_ms"] = (time.perf_counter() - start) * 1000
    return output
