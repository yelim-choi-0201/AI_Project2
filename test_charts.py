from pathlib import Path
import json
import pytest
import pandas as pd
from analytics import STATIONS, load_data, summary, daytype_comparison
from charts import daily_chart, comparison_chart, ranking_chart

DATA = load_data(Path(__file__).resolve().parents[1] / "data/station_daily_usage.csv")


@pytest.mark.parametrize("station", STATIONS)
def test_each_daily_chart(station):
    frame = DATA[DATA["역명"].eq(station)]
    fig = daily_chart(frame, y_max=1100)
    assert len(fig.data) == 2
    assert all(len(trace.x) == 14 for trace in fig.data)
    assert len(fig.layout.shapes) == 4
    assert all(shape.fillcolor for shape in fig.layout.shapes)
    assert list(fig.data[0].y) == frame["승차건수"].tolist()
    assert list(fig.data[1].y) == frame["하차건수"].tolist()
    assert fig.layout.yaxis.range == (0, 1100)
    assert json.loads(fig.to_json())["data"]


def test_total_mode_chart():
    frame = DATA[DATA["역명"].eq("가람역")]
    fig = daily_chart(frame, mode="승하차 합계")
    assert len(fig.data) == 1
    assert list(fig.data[0].y) == frame["승하차합계"].tolist()


def test_one_date_chart():
    frame = DATA[(DATA["역명"] == "가람역") & (DATA["일자"] == pd.Timestamp("2026-09-12"))]
    fig = daily_chart(frame)
    assert len(fig.data[0].x) == 1
    assert len(fig.layout.shapes) == 1
    assert fig.layout.xaxis.range[0] < fig.layout.xaxis.range[1]


def test_comparison_chart():
    frame = daytype_comparison(DATA)
    fig = comparison_chart(frame)
    assert list(fig.data[0].x) == STATIONS
    assert len(fig.data[0].y) == 4
    assert fig.data[1].text[0] == "1,183.3"


def test_ranking_chart():
    fig = ranking_chart(summary(DATA))
    assert list(fig.data[0].x) == [10218, 14963, 16643, 22131]
