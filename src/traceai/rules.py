"""Explainable, deterministic requirement-quality rules for Day 1."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Protocol

from traceai.models import Finding, Requirement, Severity


class QualityRule(Protocol):
    """Contract implemented by every independently testable quality rule."""

    rule_id: str

    def evaluate(self, requirement: Requirement) -> list[Finding]:
        """Return zero or more findings for one requirement."""
        ...


class AmbiguousLanguageRule:
    """Identify vague terms that prevent objective verification."""

    rule_id = "RQ-AMB-001"
    _terms: tuple[str, ...] = (
        "as soon as possible",
        "appropriately",
        "adequate",
        "easy to use",
        "normally",
        "quickly",
        "sufficient",
        "too hot",
        "user-friendly",
    )

    def evaluate(self, requirement: Requirement) -> list[Finding]:
        text = requirement.text.casefold()
        matches = [term for term in self._terms if re.search(rf"\b{re.escape(term)}\b", text)]
        if not matches:
            return []
        return [
            Finding(
                rule_id=self.rule_id,
                severity=Severity.HIGH,
                message="Requirement contains language that is not objectively measurable.",
                evidence=", ".join(matches),
                recommendation=(
                    "Replace vague terms with a controlled parameter, measurable threshold, "
                    "or a referenced engineering definition."
                ),
            )
        ]


class NormativeLanguageRule:
    """Require an explicit, binding modal verb for product requirements."""

    rule_id = "RQ-MOD-001"
    _weak_modals = re.compile(r"\b(should|may|might|could|will)\b", re.IGNORECASE)

    def evaluate(self, requirement: Requirement) -> list[Finding]:
        match = self._weak_modals.search(requirement.text)
        if not match:
            return []
        return [
            Finding(
                rule_id=self.rule_id,
                severity=Severity.HIGH,
                message="Requirement uses non-binding or predictive language.",
                evidence=match.group(0),
                recommendation=(
                    "Confirm that the statement is mandatory and use 'shall'; otherwise move it "
                    "to rationale, guidance, or an assumption."
                ),
            )
        ]


class AtomicityRule:
    """Flag statements that express more than one independently verifiable obligation."""

    rule_id = "RQ-ATM-001"
    _shall = re.compile(r"\bshall\b", re.IGNORECASE)

    def evaluate(self, requirement: Requirement) -> list[Finding]:
        count = len(self._shall.findall(requirement.text))
        if count < 2:
            return []
        return [
            Finding(
                rule_id=self.rule_id,
                severity=Severity.MEDIUM,
                message="Requirement appears to contain multiple obligations.",
                evidence=f"{count} occurrences of 'shall'",
                recommendation=(
                    "Split the statement into atomic requirements with separate identifiers and "
                    "verification evidence."
                ),
            )
        ]


class ClearSubjectRule:
    """Detect pronouns that make ownership of the required behavior unclear."""

    rule_id = "RQ-SUB-001"
    _unclear_start = re.compile(r"^\s*(it|this|they)\b", re.IGNORECASE)

    def evaluate(self, requirement: Requirement) -> list[Finding]:
        match = self._unclear_start.search(requirement.text)
        if not match:
            return []
        return [
            Finding(
                rule_id=self.rule_id,
                severity=Severity.MEDIUM,
                message="The responsible system or component is not explicit.",
                evidence=match.group(0).strip(),
                recommendation="Name the component that owns the required behavior.",
            )
        ]


class VerificationMethodRule:
    """Ensure every requirement has a planned verification method."""

    rule_id = "RQ-VER-001"

    def evaluate(self, requirement: Requirement) -> list[Finding]:
        if requirement.verification_method is not None:
            return []
        return [
            Finding(
                rule_id=self.rule_id,
                severity=Severity.MEDIUM,
                message="Requirement has no assigned verification method.",
                recommendation=(
                    "Assign TEST, ANALYSIS, INSPECTION, or DEMONSTRATION and define the detailed "
                    "verification criteria."
                ),
            )
        ]


class TerminalPunctuationRule:
    """Apply a small consistency check that is useful for controlled exports."""

    rule_id = "RQ-STY-001"

    def evaluate(self, requirement: Requirement) -> list[Finding]:
        if requirement.text.endswith((".", "!", "?")):
            return []
        return [
            Finding(
                rule_id=self.rule_id,
                severity=Severity.LOW,
                message="Requirement does not end with terminal punctuation.",
                recommendation="End the controlled statement with a full stop.",
            )
        ]


def default_rules() -> Sequence[QualityRule]:
    """Return the versioned Day 1 ruleset in deterministic execution order."""
    return (
        AmbiguousLanguageRule(),
        NormativeLanguageRule(),
        AtomicityRule(),
        ClearSubjectRule(),
        VerificationMethodRule(),
        TerminalPunctuationRule(),
    )
