"""Integration tests for the complete six-enhancement CLI workflow."""

import json
from pathlib import Path

import pytest

from traceai.cli import main


@pytest.mark.integration
def test_ai_suite_demo_writes_all_six_reports(
    ai_knowledge_path: Path,
    engineering_data_path: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "ai-suite.json"

    main(
        [
            "ai",
            "suite",
            "SWE-REQ-014",
            "--provider",
            "demo",
            "--knowledge",
            str(ai_knowledge_path),
            "--engineering-data",
            str(engineering_data_path),
            "--output",
            str(output),
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert set(payload) == {
        "root_cause",
        "trace_links",
        "requirement_quality",
        "log_analysis",
        "similar_defects",
        "test_generation",
    }
    assert payload["test_generation"]["plan"]["test_cases"][0]["review_decision"] == "PROPOSED"
    assert "Live model used: False" in capsys.readouterr().out


@pytest.mark.integration
def test_openai_mode_requires_api_key(
    ai_knowledge_path: Path,
    engineering_data_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(SystemExit) as raised:
        main(
            [
                "ai",
                "rca",
                "SWE-REQ-014",
                "--provider",
                "openai",
                "--knowledge",
                str(ai_knowledge_path),
                "--engineering-data",
                str(engineering_data_path),
            ]
        )

    assert raised.value.code == 1
    assert "OPENAI_API_KEY is not set" in capsys.readouterr().err
