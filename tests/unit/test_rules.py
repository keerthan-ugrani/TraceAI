"""Unit tests establish observable behavior for each explainable rule."""

from copy import deepcopy

import pytest

from traceai.models import Requirement, Severity
from traceai.rules import (
    AmbiguousLanguageRule,
    AtomicityRule,
    ClearSubjectRule,
    NormativeLanguageRule,
    TerminalPunctuationRule,
    VerificationMethodRule,
)


@pytest.mark.parametrize("term", ["quickly", "appropriately", "sufficient", "too hot"])
def test_ambiguous_language_rule_detects_seeded_terms(
    valid_requirement_data: dict[str, object], term: str
) -> None:
    data = deepcopy(valid_requirement_data)
    data["text"] = f"The controller shall respond {term}."

    findings = AmbiguousLanguageRule().evaluate(Requirement.model_validate(data))

    assert len(findings) == 1
    assert findings[0].severity is Severity.HIGH
    assert term in findings[0].evidence


def test_ambiguous_language_rule_allows_measurable_requirement(
    valid_requirement: Requirement,
) -> None:
    assert AmbiguousLanguageRule().evaluate(valid_requirement) == []


@pytest.mark.parametrize("modal", ["should", "may", "will"])
def test_normative_rule_detects_weak_modal(
    valid_requirement_data: dict[str, object], modal: str
) -> None:
    valid_requirement_data["text"] = f"The controller {modal} prevent power transfer."

    findings = NormativeLanguageRule().evaluate(Requirement.model_validate(valid_requirement_data))

    assert findings[0].rule_id == "RQ-MOD-001"
    assert findings[0].evidence == modal


def test_atomicity_rule_detects_multiple_obligations(
    valid_requirement_data: dict[str, object],
) -> None:
    valid_requirement_data["text"] = (
        "The controller shall stop charging and the logger shall record an event."
    )

    findings = AtomicityRule().evaluate(Requirement.model_validate(valid_requirement_data))

    assert findings[0].severity is Severity.MEDIUM
    assert findings[0].evidence == "2 occurrences of 'shall'"


def test_clear_subject_rule_detects_pronoun(valid_requirement_data: dict[str, object]) -> None:
    valid_requirement_data["text"] = "It shall operate during rain."

    findings = ClearSubjectRule().evaluate(Requirement.model_validate(valid_requirement_data))

    assert findings[0].rule_id == "RQ-SUB-001"


def test_verification_rule_detects_missing_method(
    valid_requirement_data: dict[str, object],
) -> None:
    valid_requirement_data["verification_method"] = None

    findings = VerificationMethodRule().evaluate(Requirement.model_validate(valid_requirement_data))

    assert findings[0].rule_id == "RQ-VER-001"


def test_punctuation_rule_detects_missing_full_stop(
    valid_requirement_data: dict[str, object],
) -> None:
    valid_requirement_data["text"] = "The controller shall prevent power transfer"

    findings = TerminalPunctuationRule().evaluate(
        Requirement.model_validate(valid_requirement_data)
    )

    assert findings[0].severity is Severity.LOW


@pytest.mark.parametrize(
    "rule",
    [
        NormativeLanguageRule(),
        AtomicityRule(),
        ClearSubjectRule(),
        VerificationMethodRule(),
        TerminalPunctuationRule(),
    ],
)
def test_rules_return_no_finding_for_valid_requirement(
    rule: object, valid_requirement: Requirement
) -> None:
    assert rule.evaluate(valid_requirement) == []  # type: ignore[attr-defined]
