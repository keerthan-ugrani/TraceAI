"""Model gateways for real OpenAI inference and a clearly labelled offline demo mode."""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

from traceai.ai_models import (
    ConfidenceLevel,
    FindingLevel,
    GeneratedTestCase,
    LogAnalysisDraft,
    RequirementQualityDraft,
    RequirementQualityFinding,
    RootCauseDraft,
    RootCauseHypothesis,
    TestGenerationDraft,
    VerificationLevel,
)
from traceai.engineering_models import ReviewDecision
from traceai.exceptions import AIProviderError

TModel = TypeVar("TModel", bound=BaseModel)


class AIModelGateway(Protocol):
    """Narrow boundary shared by structured generation and semantic embeddings."""

    provider_name: str
    generation_model: str
    embedding_model: str
    live_model_used: bool

    def generate_structured(
        self,
        output_type: type[TModel],
        *,
        system_prompt: str,
        user_payload: dict[str, Any],
    ) -> TModel: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class OpenAIModelGateway:
    """Real OpenAI Responses API and embeddings adapter.

    The import is intentionally lazy: the base deterministic TraceAI application remains
    installable without the optional ``ai`` dependency.
    """

    provider_name = "openai"
    live_model_used = True

    def __init__(
        self,
        *,
        generation_model: str = "gpt-5.6",
        embedding_model: str = "text-embedding-3-small",
        client: Any | None = None,
    ) -> None:
        self.generation_model = generation_model
        self.embedding_model = embedding_model
        if client is not None:
            self._client = client
            return
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise AIProviderError(
                "OpenAI support is not installed. Run: uv sync --extra dev --extra ai"
            ) from exc
        self._client = OpenAI(timeout=45.0, max_retries=2)

    def generate_structured(
        self,
        output_type: type[TModel],
        *,
        system_prompt: str,
        user_payload: dict[str, Any],
    ) -> TModel:
        try:
            response = self._client.responses.parse(
                model=self.generation_model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": json.dumps(user_payload, sort_keys=True),
                    },
                ],
                text_format=output_type,
            )
        except Exception as exc:  # SDK error classes are optional with the SDK itself.
            raise AIProviderError(f"OpenAI structured generation failed: {exc}") from exc
        parsed = response.output_parsed
        if parsed is None:
            raise AIProviderError("OpenAI returned no parsed structured output")
        if not isinstance(parsed, output_type):
            raise AIProviderError(
                f"OpenAI returned {type(parsed).__name__}; expected {output_type.__name__}"
            )
        return parsed

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts or any(not text.strip() for text in texts):
            raise AIProviderError("Embedding input must contain non-empty text")
        try:
            response = self._client.embeddings.create(
                model=self.embedding_model,
                input=texts,
                encoding_format="float",
            )
        except Exception as exc:  # See optional-SDK explanation above.
            raise AIProviderError(f"OpenAI embedding request failed: {exc}") from exc
        ordered = sorted(response.data, key=lambda item: item.index)
        vectors = [list(item.embedding) for item in ordered]
        if len(vectors) != len(texts):
            raise AIProviderError("OpenAI returned an unexpected number of embeddings")
        return vectors


class SyntheticDemoGateway:
    """Offline, non-AI substitute for tutorials, tests, and interview backup demos."""

    provider_name = "synthetic-demo"
    generation_model = "deterministic-template-v2"
    embedding_model = "deterministic-token-hash-v1"
    live_model_used = False

    def generate_structured(
        self,
        output_type: type[TModel],
        *,
        system_prompt: str,
        user_payload: dict[str, Any],
    ) -> TModel:
        del system_prompt
        payload = self._draft_payload(output_type, user_payload)
        return output_type.model_validate(payload)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [_token_hash_embedding(text) for text in texts]

    def _draft_payload(
        self, output_type: type[BaseModel], user_payload: dict[str, Any]
    ) -> dict[str, Any]:
        evidence_ids = list(user_payload["allowed_evidence_ids"])
        if output_type is RootCauseDraft:
            return RootCauseDraft(
                summary=(
                    "The integration failure is consistent with an interface enumeration "
                    "contract mismatch; this is an advisory hypothesis requiring review."
                ),
                hypotheses=[
                    RootCauseHypothesis(
                        title="Interface enumeration mismatch",
                        explanation=(
                            "The upstream component publishes VALID while the downstream "
                            "component expects ALIGNED at the first failing integration stage."
                        ),
                        confidence=ConfidenceLevel.HIGH,
                        evidence_ids=_preferred(evidence_ids, ["IT-045", "ARCH-IF-006"]),
                    )
                ],
                recommended_checks=[
                    "Compare the v2.0 and v2.1 interface enumeration definitions.",
                    "Re-run IT-045 after baselining one shared interface contract.",
                ],
                evidence_ids=evidence_ids,
            ).model_dump()
        if output_type is RequirementQualityDraft:
            requirement_id = str(user_payload["requirement_id"])
            return RequirementQualityDraft(
                summary="The requirement is ambiguous and not objectively verifiable.",
                rewritten_requirement=(
                    "When measured alignment exceeds 5 mm during charging preparation, the "
                    "controller shall disable power-transfer authorization within 100 ms."
                ),
                findings=[
                    RequirementQualityFinding(
                        category="AMBIGUOUS_TERM",
                        severity=FindingLevel.MAJOR,
                        message="The terms 'quickly' and 'not good' are not measurable.",
                        suggested_change="Add alignment and response-time thresholds.",
                        evidence_ids=[requirement_id],
                    )
                ],
                verification_notes=[
                    "Measure authorization state transition at 99 ms, 100 ms, and 101 ms."
                ],
                evidence_ids=[requirement_id],
            ).model_dump()
        if output_type is LogAnalysisDraft:
            log_id = str(user_payload["log_id"])
            return LogAnalysisDraft(
                summary=(
                    "The failure begins when incompatible alignment states cross the interface."
                ),
                timeline=[
                    "AlignmentController publishes VALID.",
                    "ChargingStateMachine rejects VALID because it expects ALIGNED.",
                    "Power-transfer authorization remains false and IT-045 fails.",
                ],
                anomalies=["Published and accepted enumeration values differ at ARCH-IF-006."],
                hypotheses=[
                    RootCauseHypothesis(
                        title="Runtime interface contract mismatch",
                        explanation="The connected components use different status enumerations.",
                        confidence=ConfidenceLevel.HIGH,
                        evidence_ids=_preferred(evidence_ids, [log_id, "ARCH-IF-006", "IT-045"]),
                    )
                ],
                recommended_checks=["Inspect the deployed interface version on both components."],
                evidence_ids=evidence_ids,
            ).model_dump()
        if output_type is TestGenerationDraft:
            requirement_id = str(user_payload["requirement_id"])
            core_evidence = _preferred(evidence_ids, [requirement_id, "ARCH-IF-006", "DD-018"])
            return TestGenerationDraft(
                coverage_summary=(
                    "Proposed boundary, negative, integration, and SWE.6 acceptance coverage."
                ),
                test_cases=[
                    GeneratedTestCase(
                        test_id="AI-TC-014-01",
                        title="Reject misalignment above threshold",
                        verification_level=VerificationLevel.UNIT,
                        objective="Verify deterministic authorization rejection above 5 mm.",
                        preconditions=["Controller is in CHARGING_PREPARATION."],
                        steps=["Inject alignment error of 5.1 mm.", "Advance the clock by 100 ms."],
                        expected_result="Power-transfer authorization is false within 100 ms.",
                        test_data=["alignment_error_mm=5.1", "elapsed_ms=100"],
                        requirement_ids=[requirement_id],
                        evidence_ids=core_evidence,
                        review_decision=ReviewDecision.PROPOSED,
                    ),
                    GeneratedTestCase(
                        test_id="AI-TC-014-02",
                        title="Accept aligned interface state",
                        verification_level=VerificationLevel.COMPONENT,
                        objective="Verify the normal aligned path remains available.",
                        preconditions=["Interface contract version 2.1 is baselined."],
                        steps=["Publish ALIGNED with 5.0 mm error.", "Request authorization."],
                        expected_result="Authorization follows the approved state transition.",
                        test_data=["alignment_error_mm=5.0", "state=ALIGNED"],
                        requirement_ids=[requirement_id],
                        evidence_ids=core_evidence,
                        review_decision=ReviewDecision.PROPOSED,
                    ),
                    GeneratedTestCase(
                        test_id="AI-TC-014-03",
                        title="Detect incompatible enumeration contract",
                        verification_level=VerificationLevel.INTEGRATION,
                        objective="Expose v2.0 to v2.1 enumeration incompatibility.",
                        preconditions=["Two controlled interface versions are available."],
                        steps=["Publish VALID from the v2.0 producer.", "Consume with v2.1."],
                        expected_result="The mismatch is detected and authorization stays false.",
                        test_data=["producer=v2.0", "consumer=v2.1"],
                        requirement_ids=[requirement_id],
                        evidence_ids=core_evidence,
                        review_decision=ReviewDecision.PROPOSED,
                    ),
                    GeneratedTestCase(
                        test_id="AI-TC-014-04",
                        title="Verify end-to-end response-time boundary",
                        verification_level=VerificationLevel.SOFTWARE,
                        objective="Confirm the controlled 100 ms response-time requirement.",
                        preconditions=["Software candidate is deployed on the test bench."],
                        steps=["Inject misalignment.", "Measure authorization output latency."],
                        expected_result="Authorization is false no later than 100 ms.",
                        test_data=["boundary_ms=[99,100,101]"],
                        requirement_ids=[requirement_id],
                        evidence_ids=core_evidence,
                        review_decision=ReviewDecision.PROPOSED,
                    ),
                ],
                uncovered_risks=[
                    "Hardware timing jitter requires confirmation on the representative target."
                ],
                evidence_ids=evidence_ids,
            ).model_dump()
        raise AIProviderError(f"Synthetic demo cannot generate {output_type.__name__}")


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        raise AIProviderError("Embedding vectors must have equal non-zero dimensions")
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)


def _token_hash_embedding(text: str, dimensions: int = 128) -> list[float]:
    vector = [0.0] * dimensions
    for token in re.findall(r"[a-z0-9_.-]+", text.lower()):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        vector[index] += 1.0
    return vector


def _preferred(available: list[str], desired: list[str]) -> list[str]:
    selected = [item for item in desired if item in available]
    return selected or available[:1]
