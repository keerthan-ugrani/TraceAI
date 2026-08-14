"""Unit tests for CLI exit behavior."""

from pathlib import Path

import pytest

from traceai.cli import main


def test_cli_returns_error_for_missing_input(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as raised:
        main(["analyze", "--input", str(tmp_path / "missing.csv")])

    assert raised.value.code == 1
    assert "does not exist" in capsys.readouterr().err


def test_cli_can_enforce_high_severity_gate(
    sample_data_path: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as raised:
        main(
            [
                "analyze",
                "--input",
                str(sample_data_path),
                "--output-dir",
                str(tmp_path),
                "--fail-on-high",
            ]
        )

    assert raised.value.code == 2
    assert "HIGH_FINDINGS=" in capsys.readouterr().out
