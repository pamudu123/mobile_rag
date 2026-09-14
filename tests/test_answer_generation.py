import json
import urllib.error
from copy import deepcopy

import pytest
from test_retrieval import bundle  # noqa: F401

from mobile_rag.answer_generation import MODEL, GenerationConfig, generate_answer, load_generation_config, make_request
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
    assert "provider" not in dry["request"]
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
    assert call({"choices": []})["error"]["status"] == "invalid_response"
    assert call({"choices": []})["error"]["message"]
    missing_reason = json.loads(response()["choices"][0]["message"]["content"])
    del missing_reason["reason"]
    filled = call({**response(), "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(missing_reason)}}]})
    assert filled["status"] == "answered"
    assert filled["answer"]["reason"].startswith("Supported by")


def test_http_failures_bounded_and_not_exposed(package, monkeypatch):
    monkeypatch.setattr("mobile_rag.answer_generation.time.sleep", lambda _: None)
    calls = []

    def failure(*args):
        calls.append(1)
        raise urllib.error.HTTPError("https://openrouter.ai", 429, "sensitive body", {}, None)

    result = generate_answer(package, api_key="secret-key", live=True, transport=failure)
    assert result["status"] == "api_error" and result["http_status"] == 429
    assert calls == [1, 1, 1]
    assert len(result["attempts"]) == 3
    assert "secret-key" not in json.dumps(result) and "sensitive body" not in json.dumps(result)


def test_transient_recovery_and_terminal_errors(package, monkeypatch):
    monkeypatch.setattr("mobile_rag.answer_generation.time.sleep", lambda _: None)
    calls = []

    def recover(*_):
        calls.append(1)
        if len(calls) == 1:
            raise urllib.error.HTTPError("url", 503, "private", {}, None)
        return response()

    result = generate_answer(package, live=True, api_key="fixture", transport=recover)
    assert result["status"] == "answered" and len(result["attempts"]) == 2

    def terminal(*_):
        raise urllib.error.HTTPError("url", 400, "private", {}, None)

    result = generate_answer(package, live=True, api_key="fixture", transport=terminal)
    assert result["status"] == "api_error" and len(result["attempts"]) == 1


def test_thinking_flag_loads_presets_and_request_reasoning(package):
    thinking = load_generation_config(True)
    non_thinking = load_generation_config(False)
    assert thinking.thinking and thinking.max_output_tokens == 8192 and thinking.timeout_seconds == 120
    assert not non_thinking.thinking and non_thinking.max_output_tokens == 2048 and non_thinking.timeout_seconds == 60
    assert make_request(package, thinking)["reasoning"] == {"enabled": True, "exclude": True}
    assert make_request(package, non_thinking)["reasoning"] == {"enabled": False}
    assert generate_answer(package, thinking=True)["request"]["reasoning"] == {"enabled": True, "exclude": True}
    assert generate_answer(package, thinking=False)["request"]["reasoning"] == {"enabled": False}
    with pytest.raises(ValueError, match="config or thinking"):
        generate_answer(package, config=GenerationConfig(), thinking=False)
    with pytest.raises(ValueError, match="thinking"):
        load_generation_config("thinking")
    with pytest.raises(ValueError, match="thinking"):
        GenerationConfig(thinking=1).validate()


def test_configured_model_and_request_budget(package):
    config = GenerationConfig(model="test/model", temperature=0.3)
    request = make_request(package, config)
    assert request["model"] == "test/model" and request["temperature"] == 0.3
    assert request["reasoning"] == {"enabled": True, "exclude": True}
    payload = {**response(), "model": "test/model"}
    assert generate_answer(package, config=config, live=True, api_key="fixture",
                           transport=lambda *_: payload)["status"] == "answered"
    tiny = deepcopy(package)
    tiny["budget"]["total_chars"] = 10
    result = generate_answer(tiny, live=True, api_key="fixture", transport=lambda *_: pytest.fail("Must not call"))
    assert result["status"] == "request_budget_exceeded" and not result["live_request_sent"]


@pytest.mark.parametrize("first", [response(finish="length"), response(["S999"])])
def test_completion_retry_feedback_and_recovery(package, monkeypatch, first):
    monkeypatch.setattr("mobile_rag.answer_generation.time.sleep", lambda _: None)
    requests = []

    def recover(payload, *_):
        requests.append(deepcopy(payload))
        return first if len(requests) == 1 else response()

    result = generate_answer(package, live=True, api_key="fixture", transport=recover)
    assert result["status"] == "answered" and "error" not in result
    assert len(requests) == 2
    assert "Retry feedback" in requests[1]["messages"][0]["content"]
    assert "Error:" in requests[1]["messages"][0]["content"]
    assert requests[1]["messages"][0]["content"].startswith(requests[0]["messages"][0]["content"])
    assert requests[1]["max_tokens"] == requests[0]["max_tokens"]
    assert result["attempts"][0]["error"]
    assert result["attempts"][0]["request_sha256"] != result["attempts"][1]["request_sha256"]


def test_completion_retry_limits_and_terminal_finish(package, monkeypatch):
    monkeypatch.setattr("mobile_rag.answer_generation.time.sleep", lambda _: None)
    for retries, finish, expected in [(2, "length", 3), (0, "length", 1), (2, "content_filter", 1)]:
        result = generate_answer(package, config=GenerationConfig(max_retries=retries),
                                 live=True, api_key="fixture", transport=lambda *_, finish=finish: response(finish=finish))
        assert result["status"] == "incomplete_response"
        assert result["answer"] is None
        assert len(result["attempts"]) == expected


def test_retry_feedback_respects_request_budget(package, monkeypatch):
    monkeypatch.setattr("mobile_rag.answer_generation.time.sleep", lambda _: None)
    package = deepcopy(package)
    config = GenerationConfig()
    size = len(json.dumps(make_request(package, config), ensure_ascii=False))
    package["budget"]["total_chars"] = size + package["budget"]["answer_reserve"]
    calls = []

    def truncated(*_):
        calls.append(1)
        return response(finish="length")

    result = generate_answer(package, live=True, api_key="fixture", transport=truncated)
    assert result["status"] == "request_budget_exceeded"
    assert len(calls) == 1
    assert result["attempts"][0]["finish_reason"] == "length"

