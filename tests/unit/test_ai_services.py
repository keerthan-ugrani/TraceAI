"""Unit tests for governed AI Enhancements 1 through 6."""

from datetime import UTC, datetime
from typing import Any, TypeVar

import pytest
from pydantic import BaseModel

from traceai.ai_gateway import SyntheticDemoGateway
from traceai.ai_models import (
    AIKnowledgeDataset,
    ConfidenceLevel,
    DataClassification,
    RootCauseDraft,
    RootCauseHypothesis,
)
from traceai.ai_services import AIEngineeringCopilot
from traceai.engineering_graph import EngineeringGraph
from traceai.exceptions import AIGovernanceError

TIMESTAMP = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)
TModel = TypeVar("TModel", bound=BaseModel)


class FakeLiveGateway(SyntheticDemoGateway):
    live_model_used = True


class UngroundedGateway(SyntheticDemoGateway):
    def generate_structured(
        self,
        output_type: type[TModel],
        *,
        system_prompt: str,
        user_payload: dict[str, Any],
    ) -> TModel:
        if output_type is RootCauseDraft:
            return output_type.model_validate(
                RootCauseDraft(
                    summary="Ungrounded output",
                    hypotheses=[
                        RootCauseHypothesis(
                            title="Invented evidence",
                            explanation="This citation was not retrieved.",
                            confidence=ConfidenceLevel.HIGH,
                            evidence_ids=["INVENTED-999"],
                        )
                    ],
                    recommended_checks=["Review."],
                    evidence_ids=["INVENTED-999"],
                ).model_dump()
            )
        return super().generate_structured(
            output_type, system_prompt=system_prompt, user_payload=user_payload
        )


def test_enhancement_1_grounded_root_cause(ai_copilot: AIEngineeringCopilot) -> None:
    report = ai_copilot.analyze_root_cause("SWE-REQ-014", generated_at=TIMESTAMP)

    assert report.first_failure_id == "IT-045"
    assert {"IT-045", "ARCH-IF-006"} <= set(report.provenance.evidence_ids)
    assert report.provenance.review_decision == "PROPOSED"
    assert report.provenance.live_model_used is False


def test_enhancement_2_semantic_trace_recommendations(
    ai_copilot: AIEngineeringCopilot,
) -> None:
    report = ai_copilot.recommend_trace_links("SWE-REQ-014", top_k=3, generated_at=TIMESTAMP)

    assert len(report.recommendations) == 3
    assert all(item.review_decision == "PROPOSED" for item in report.recommendations)
    assert "ARCH-IF-006" not in {item.artifact_id for item in report.recommendations}
    assert all(0 <= item.similarity_score <= 1 for item in report.recommendations)


def test_enhancement_3_requirement_quality_review(
    ai_copilot: AIEngineeringCopilot,
) -> None:
    report = ai_copilot.review_requirement("SWE-REQ-031", generated_at=TIMESTAMP)

    assert report.review.findings[0].category == "AMBIGUOUS_TERM"
    assert "100 ms" in report.review.rewritten_requirement
    assert report.provenance.evidence_ids == ["SWE-REQ-031"]


def test_enhancement_4_log_analysis(ai_copilot: AIEngineeringCopilot) -> None:
    report = ai_copilot.analyze_log("LOG-IT-045", generated_at=TIMESTAMP)

    assert len(report.analysis.timeline) == 3
    assert "ARCH-IF-006" in report.provenance.evidence_ids
    assert report.analysis.hypotheses[0].confidence == "High"


def test_enhancement_5_similar_defect_retrieval(
    ai_copilot: AIEngineeringCopilot,
) -> None:
    report = ai_copilot.retrieve_similar_defects("LOG-IT-045", top_k=3, generated_at=TIMESTAMP)

    assert len(report.matches) == 3
    assert "DEFECT-023" in {item.defect_id for item in report.matches}
    assert report.matches[0].similarity_score >= report.matches[-1].similarity_score


def test_enhancement_6_generates_proposed_traced_tests(
    ai_copilot: AIEngineeringCopilot,
) -> None:
    report = ai_copilot.generate_tests("SWE-REQ-014", generated_at=TIMESTAMP)

    assert len(report.plan.test_cases) == 4
    assert {item.verification_level for item in report.plan.test_cases} == {
        "UNIT",
        "COMPONENT",
        "INTEGRATION",
        "SOFTWARE",
    }
    assert all(item.review_decision == "PROPOSED" for item in report.plan.test_cases)
    assert all("SWE-REQ-014" in item.requirement_ids for item in report.plan.test_cases)


def test_live_gateway_is_refused_for_non_synthetic_data(
    ai_knowledge: AIKnowledgeDataset, engineering_graph: EngineeringGraph
) -> None:
    internal = ai_knowledge.model_copy(update={"data_classification": DataClassification.INTERNAL})
    with pytest.raises(AIGovernanceError, match="only for the synthetic"):
        AIEngineeringCopilot(internal, engineering_graph, FakeLiveGateway())


def test_model_output_with_invented_evidence_is_rejected(
    ai_knowledge: AIKnowledgeDataset, engineering_graph: EngineeringGraph
) -> None:
    copilot = AIEngineeringCopilot(ai_knowledge, engineering_graph, UngroundedGateway())

    with pytest.raises(AIGovernanceError, match="INVENTED-999"):
        copilot.analyze_root_cause("SWE-REQ-014")
