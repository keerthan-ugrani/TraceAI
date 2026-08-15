"""Unit tests for scoring and orchestration."""

from traceai.analyzer import RequirementQualityAnalyzer
from traceai.models import Finding, QualityStatus, Requirement, Severity


class StubRule:
    rule_id = "STUB-001"

    def __init__(self, severity: Severity) -> None:
        self.severity = severity

    def evaluate(self, requirement: Requirement) -> list[Finding]:
        return [
            Finding(
                rule_id=self.rule_id,
                severity=self.severity,
                message="Synthetic test finding",
                recommendation="Resolve it",
            )
        ]


def test_valid_requirement_passes_with_full_score(valid_requirement: Requirement) -> None:
    result = RequirementQualityAnalyzer().analyze(valid_requirement)

    assert result.quality_score == 100
    assert result.quality_status is QualityStatus.PASS
    assert result.findings == []


def test_score_deductions_map_to_review_status(valid_requirement: Requirement) -> None:
    analyzer = RequirementQualityAnalyzer(
        [StubRule(Severity.HIGH), StubRule(Severity.MEDIUM), StubRule(Severity.LOW)]
    )

    result = analyzer.analyze(valid_requirement)

    assert result.quality_score == 58
    assert result.quality_status is QualityStatus.FAIL


def test_score_does_not_become_negative(valid_requirement: Requirement) -> None:
    analyzer = RequirementQualityAnalyzer([StubRule(Severity.HIGH)] * 5)

    result = analyzer.analyze(valid_requirement)

    assert result.quality_score == 0
    assert result.quality_status is QualityStatus.FAIL


def test_analyze_many_preserves_input_order(valid_requirement_data: dict[str, object]) -> None:
    second_data = dict(valid_requirement_data)
    second_data["requirement_id"] = "REQ-998"
    requirements = [
        Requirement.model_validate(valid_requirement_data),
        Requirement.model_validate(second_data),
    ]

    results = RequirementQualityAnalyzer().analyze_many(requirements)

    assert [result.requirement_id for result in results] == ["REQ-999", "REQ-998"]
