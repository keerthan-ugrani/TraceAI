"""One-to-one acceptance evidence for governed AI Enhancements 1 through 6."""

import pytest

from traceai.ai_services import AIEngineeringCopilot


@pytest.mark.verification
def test_poc_ai_001_real_llm_boundary_is_grounded(
    ai_copilot: AIEngineeringCopilot,
) -> None:
    report = ai_copilot.analyze_root_cause("SWE-REQ-014")

    assert report.first_failure_id == "IT-045"
    assert {"IT-045", "ARCH-IF-006"} <= set(report.provenance.evidence_ids)
    assert report.provenance.review_decision == "PROPOSED"


@pytest.mark.verification
def test_poc_ai_002_embedding_trace_links_are_proposals(
    ai_copilot: AIEngineeringCopilot,
) -> None:
    report = ai_copilot.recommend_trace_links("SWE-REQ-014", top_k=3)

    assert len(report.recommendations) == 3
    assert all(item.review_decision == "PROPOSED" for item in report.recommendations)


@pytest.mark.verification
def test_poc_ai_003_semantic_requirement_review_is_measurable(
    ai_copilot: AIEngineeringCopilot,
) -> None:
    report = ai_copilot.review_requirement("SWE-REQ-031")

    assert report.review.findings
    assert "100 ms" in report.review.rewritten_requirement


@pytest.mark.verification
def test_poc_ai_004_log_analysis_separates_timeline_and_hypothesis(
    ai_copilot: AIEngineeringCopilot,
) -> None:
    report = ai_copilot.analyze_log("LOG-IT-045")

    assert report.analysis.timeline
    assert report.analysis.hypotheses
    assert "ARCH-IF-006" in report.provenance.evidence_ids


@pytest.mark.verification
def test_poc_ai_005_similar_defects_retrieve_controlled_history(
    ai_copilot: AIEngineeringCopilot,
) -> None:
    report = ai_copilot.retrieve_similar_defects("LOG-IT-045", top_k=3)

    assert "DEFECT-023" in {match.defect_id for match in report.matches}
    assert all(match.evidence_ids for match in report.matches)


@pytest.mark.verification
def test_poc_ai_006_generated_tests_remain_proposed_and_traced(
    ai_copilot: AIEngineeringCopilot,
) -> None:
    report = ai_copilot.generate_tests("SWE-REQ-014")

    assert report.plan.test_cases
    assert all(test.test_id.startswith("AI-TC-") for test in report.plan.test_cases)
    assert all(test.review_decision == "PROPOSED" for test in report.plan.test_cases)
    assert all("SWE-REQ-014" in test.requirement_ids for test in report.plan.test_cases)
