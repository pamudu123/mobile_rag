import json

import pytest
from pydantic import ValidationError

from mobile_rag.answer_generation import validate_answer
from mobile_rag.answer_schema import GroundedAnswer, answer_json_schema


@pytest.mark.parametrize(
    "patch",
    [
        {"extra": True},
        {"reason": None},
        {"reason": ""},
        {"reason": " "},
        {"answer": 42},
        {"answer": " "},
        {"citations": [1]},
        {"citations": ["S2"]},
        {"citations": []},
        {"claims": []},
        {"status": "categorical"},
        {"status": "insufficient_evidence"},
    ],
)
def test_strict_schema_rejects_invalid_answers(patch):
    answer = {"status": "answered", "answer": "Answer", "reason": "Supported by source", "citations": ["S1"]}
    with pytest.raises(ValidationError):
        validate_answer(json.dumps({**answer, **patch}), {"S1": {}})


def test_schema_and_roundtrip():
    schema = answer_json_schema(["S1", "S2"])
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"status", "answer", "reason", "citations"}
    assert schema["properties"]["citations"]["items"]["enum"] == ["S1", "S2"]
    assert "enum" not in GroundedAnswer.model_json_schema()["properties"]["citations"]["items"]
    for answer in [
        {"status": "insufficient_evidence", "answer": "", "citations": [], "reason": "No support"},
        {"status": "answered", "answer": "Answer", "citations": ["S1"], "reason": "Source supports this answer"},
    ]:
        assert validate_answer(json.dumps(answer), {"S1": {}}) == answer
