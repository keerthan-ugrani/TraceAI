"""Headless UI integration test for the hero Requirement-ID workflow."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


@pytest.mark.integration
def test_streamlit_hero_analysis_renders_engineering_intelligence() -> None:
    app_path = Path(__file__).parents[2] / "app.py"
    app = AppTest.from_file(str(app_path), default_timeout=10).run()

    app.text_input[0].input("SWE-REQ-014")
    app.button[0].click().run()

    assert list(app.exception) == []
    assert app.title[0].value == "Engineering Intelligence Copilot"
    assert app.metric[0].label == "Overall Health"
    assert app.metric[0].value == "BLOCKED"
    assert app.metric[5].label == "Release"
    assert app.metric[5].value == "BLOCKED"
    assert any(item.value == "Failure Analysis" for item in app.subheader)
    assert any(item.value == "AI Root-Cause Analysis" for item in app.subheader)
