import json
import urllib.error
from copy import deepcopy

import pytest
from test_retrieval import bundle  # noqa: F401

from mobile_rag.answer_generation import MODEL, GenerationConfig, generate_answer, make_request
from mobile_rag.context_preparation import prepare_context
from mobile_rag.retrieval import Retriever, build_index


@pytest.fixture
def package(bundle):  # noqa: F811
    root, folder = bundle
    with Retriever(build_index(folder, root / "indexes")) as retriever:
        return prepare_context(retriever, retriever.search("uniquealpha"))


def response(citations=None, status="answered", reason="Supported by the fixture", finish="stop"):
    return {
        "model": MODEL,
        "provider": "DeepInfra",
        "id": "test-only",
        "usage": {"prompt_tokens": 105},
        "choices": [
            {
                "finish_reason": finish,
                "message": {
                    "content": json.dumps(
                        {
                            "status": status,
                            "answer": "Fixture text" if status == "answered" else "",
                            "citations": citations if citations is not None else ["S1"],
                            "reason": reason,
                        }
                    )
                },
            }
        ],
    }


def test_request_gates_and_context_integrity(package, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr("mobile_rag.answer_generation.openrouter_api_key", lambda: None)
    assert generate_answer(package, live=True)["status"] == "credentials_required"
    dry = generate_answer(
        package,
    )
    assert dry["status"] == "dry_run" and not dry["live_request_sent"]
    assert dry["request"]["model"] == MODEL
    assert dry["request"]["provider"]["allow_fallbacks"] is False
    for status in ("empty", "budget_blocked", "invalid_evidence"):
        bad = {**package, "status": status}
        assert generate_answer(bad, live=True)["status"] in {"insufficient_evidence", "invalid_context"}
    bad = deepcopy(package)
    bad["context_text"] += " invented"
    assert generate_answer(bad)["status"] == "invalid_context"
    bad = deepcopy(package)
    bad["citation_map"]["S1"]["chunk_id"] = "other"
    assert generate_answer(bad)["status"] == "invalid_context"
    assert "reference_answer" not in make_request(package, GenerationConfig())["messages"][0]["content"]


def test_success_abstention_and_response_rejection(package):
    def call(payload):
        return generate_answer(package, live=True, api_key="test-only", transport=lambda *_: payload)

    good = call(response())
    assert good["status"] == "answered" and good["citation_validation"] == "passed"
    assert good["support_validation"] == "not_performed"
    assert good["usage"]["prompt_tokens"] == 105
    assert not good["live_request_sent"]
    assert call(response([], "insufficient_evidence", "Missing support"))["status"] == "insufficient_evidence"
    for labels in ([], ["S999"], [1]):
        assert call(response(labels))["status"] == "invalid_response"
    assert call(response(finish="length"))["status"] == "incomplete_response"
    assert call({"error": {"message": "secret body"}})["status"] == "api_error"
    assert call({**response(), "model": "other"})["status"] == "invalid_response"
    assert call({"choices": []})["status"] == "invalid_response"


def test_http_failures_not_retried_or_exposed(package):
    calls = []

    def failure(*args):
        calls.append(1)
        raise urllib.error.HTTPError("https://openrouter.ai", 429, "sensitive body", {}, None)

    result = generate_answer(package, api_key="secret-key", live=True, transport=failure)
    assert result["status"] == "api_error" and result["http_status"] == 429
    assert calls == [1]
    assert "secret-key" not in json.dumps(result) and "sensitive body" not in json.dumps(result)
