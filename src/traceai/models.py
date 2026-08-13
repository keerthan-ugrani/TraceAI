"""Validated domain models for requirements-quality analysis."""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Classification(StrEnum):
    """Requirement classification used by the synthetic engineering dataset."""

    SAFETY = "SAFETY"
    FUNCTIONAL = "FUNCTIONAL"
    CYBERSECURITY = "CYBERSECURITY"
    DIAGNOSTIC = "DIAGNOSTIC"


class RequirementStatus(StrEnum):
    """Simplified lifecycle state for the PoC."""

    DRAFT = "DRAFT"
    APPROVED = "APPROVED"


class VerificationMethod(StrEnum):
    """Common verification methods used by engineering teams."""

    TEST = "TEST"
    ANALYSIS = "ANALYSIS"
    INSPECTION = "INSPECTION"
    DEMONSTRATION = "DEMONSTRATION"


class Severity(StrEnum):
    """Finding severity and its effect on the quality score."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class QualityStatus(StrEnum):
    """Human-readable outcome for a requirement."""

    PASS = "PASS"
    REVIEW = "REVIEW"
    FAIL = "FAIL"


class Requirement(BaseModel):
    """A single controlled engineering requirement."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    requirement_id: str
    title: str = Field(min_length=3, max_length=120)
    text: str = Field(min_length=10, max_length=1000)
    component: str = Field(min_length=2, max_length=120)
    classification: Classification
    status: RequirementStatus
    verification_method: VerificationMethod | None = None
    source: str = Field(min_length=2, max_length=120)
    revision: int = Field(ge=1)

    @field_validator("requirement_id")
    @classmethod
    def validate_requirement_id(cls, value: str) -> str:
        """Require stable IDs so findings and future trace links are addressable."""
        if not re.fullmatch(r"REQ-\d{3,6}", value):
            raise ValueError("requirement_id must match REQ- followed by 3 to 6 digits")
        return value

    @field_validator("verification_method", mode="before")
    @classmethod
    def empty_verification_method_is_none(cls, value: object) -> object:
        """CSV files represent a missing optional verification method as an empty cell."""
        return None if value == "" else value


class Finding(BaseModel):
    """An explainable quality issue produced by one deterministic rule."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    severity: Severity
    message: str
    evidence: str | None = None
    recommendation: str


class RequirementAnalysis(BaseModel):
    """Quality result for one requirement."""

    requirement_id: str
    quality_score: int = Field(ge=0, le=100)
    quality_status: QualityStatus
    findings: list[Finding]


class ReportSummary(BaseModel):
    """Aggregated counts suitable for a dashboard or CI output."""

    total_requirements: int = Field(ge=0)
    passed: int = Field(ge=0)
    review_required: int = Field(ge=0)
    failed: int = Field(ge=0)
    requirements_with_findings: int = Field(ge=0)
    high_severity_findings: int = Field(ge=0)
    medium_severity_findings: int = Field(ge=0)
    low_severity_findings: int = Field(ge=0)


class ReportMetadata(BaseModel):
    """Provenance needed to reproduce an analysis run."""

    analyzer_version: str
    source_file: str
    generated_at: datetime


class AnalysisReport(BaseModel):
    """Versioned output contract for the Day 1 pipeline."""

    metadata: ReportMetadata
    summary: ReportSummary
    results: list[RequirementAnalysis]
