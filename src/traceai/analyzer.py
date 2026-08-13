"""Requirements quality analysis service."""

from __future__ import annotations

from collections.abc import Sequence

from traceai.models import (
    Finding,
    QualityStatus,
    Requirement,
    RequirementAnalysis,
    Severity,
)
from traceai.rules import QualityRule, default_rules

SCORE_DEDUCTION = {
    Severity.HIGH: 25,
    Severity.MEDIUM: 12,
    Severity.LOW: 5,
}


class RequirementQualityAnalyzer:
    """Run a configurable ruleset and produce stable, explainable scores."""

    def __init__(self, rules: Sequence[QualityRule] | None = None) -> None:
        self._rules = tuple(rules if rules is not None else default_rules())

    def analyze(self, requirement: Requirement) -> RequirementAnalysis:
        """Analyze one requirement without mutating the source artifact."""
        findings: list[Finding] = []
        for rule in self._rules:
            findings.extend(rule.evaluate(requirement))

        score = max(0, 100 - sum(SCORE_DEDUCTION[item.severity] for item in findings))
        return RequirementAnalysis(
            requirement_id=requirement.requirement_id,
            quality_score=score,
            quality_status=_status_from_score(score),
            findings=findings,
        )

    def analyze_many(self, requirements: Sequence[Requirement]) -> list[RequirementAnalysis]:
        """Analyze requirements in source order for reproducible reports."""
        return [self.analyze(requirement) for requirement in requirements]


def _status_from_score(score: int) -> QualityStatus:
    if score >= 85:
        return QualityStatus.PASS
    if score >= 60:
        return QualityStatus.REVIEW
    return QualityStatus.FAIL
