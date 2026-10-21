"""Streamlit이 설치된 환경에서만 실제 앱 스모크 테스트를 실행."""
from pathlib import Path
from datetime import date

import pytest
pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_app_initial_view():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not app.exception
    assert any(m.label == "승하차 합계" and m.value == "63,955건" for m in app.metric)
    assert len(app.tabs) == 5


def test_app_empty_station_selection():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    app.multiselect(key="station_filter").set_value([]).run()
    assert not app.exception
    assert any("한 개 이상" in e.value for e in app.info)


def test_app_weekend_only_and_single_station():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    app.multiselect(key="station_filter").set_value(["해솔역"]).run()
    app.date_input(key="period_filter").set_value((date(2026, 9, 12), date(2026, 9, 13))).run()
    assert not app.exception
    assert any(m.label == "승하차 합계" and m.value == "3,237건" for m in app.metric)
    assert any("평일 또는 주말" in e.value for e in app.warning)
