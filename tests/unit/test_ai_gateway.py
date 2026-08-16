"""Tests for offline and real-provider adapter boundaries without making API calls."""

from types import SimpleNamespace
from typing import Any

import pytest

from traceai.ai_gateway import OpenAIModelGateway, SyntheticDemoGateway, cosine_similarity
from traceai.ai_models import RequirementQualityDraft
from traceai.exceptions import AIProviderError


class FakeResponses:
    def __init__(self, parsed: RequirementQualityDraft) -> None:
        self.parsed = parsed
        self.calls: list[dict[str, Any]] = []

    def parse(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(output_parsed=self.parsed)


class FakeEmbeddings:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(
            data=[
                SimpleNamespace(index=1, embedding=[0.0, 1.0]),
                SimpleNamespace(index=0, embedding=[1.0, 0.0]),
            ]
        )


def _quality_draft() -> RequirementQualityDraft:
    return RequirementQualityDraft.model_validate(
        {
            "summary": "Needs measurable wording.",
            "rewritten_requirement": "The controller shall respond within 100 ms.",
            "findings": [],
            "verification_notes": ["Measure at the boundary."],
            "evidence_ids": ["SWE-REQ-031"],
        }
    )


def test_openai_gateway_uses_responses_parse_and_embedding_models() -> None:
    client = SimpleNamespace(responses=FakeResponses(_quality_draft()), embeddings=FakeEmbeddings())
    gateway = OpenAIModelGateway(
        generation_model="gpt-test",
        embedding_model="embedding-test",
        client=client,
    )

    result = gateway.generate_structured(
        RequirementQualityDraft,
        system_prompt="system",
        user_payload={"allowed_evidence_ids": ["SWE-REQ-031"]},
    )
    vectors = gateway.embed(["one", "two"])

    assert result.summary == "Needs measurable wording."
    assert client.responses.calls[0]["model"] == "gpt-test"
    assert client.responses.calls[0]["text_format"] is RequirementQualityDraft
    assert client.embeddings.calls[0]["model"] == "embedding-test"
    assert vectors == [[1.0, 0.0], [0.0, 1.0]]


def test_demo_gateway_is_explicitly_not_a_live_ai_model() -> None:
    gateway = SyntheticDemoGateway()

    assert gateway.live_model_used is False
    assert gateway.provider_name == "synthetic-demo"


def test_cosine_similarity_is_bounded_and_rejects_bad_dimensions() -> None:
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    with pytest.raises(AIProviderError, match="equal non-zero"):
        cosine_similarity([1.0], [1.0, 0.0])
