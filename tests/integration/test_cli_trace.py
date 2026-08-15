"""Integration test for the Requirement-ID command-line workflow."""

from pathlib import Path

import pytest

from traceai.cli import main


@pytest.mark.integration
def test_cli_generates_blocked_hero_report(
    engineering_data_path: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "engineering-report.json"

    main(
        [
            "trace",
            "SWE-REQ-014",
            "--data",
            str(engineering_data_path),
            "--release-id",
            "REL-1.4.0",
            "--change-request-id",
            "CR-091",
            "--output",
            str(output),
        ]
    )

    captured = capsys.readouterr().out
    assert "Overall: BLOCKED" in captured
    assert "First failure: IT-045" in captured
    assert "Release REL-1.4.0: BLOCKED" in captured
    assert output.exists()
