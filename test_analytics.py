from pathlib import Path
import io
import pandas as pd
import pytest

from analytics import (
    STATIONS, REQUIRED, load_data, validate_data, counts, summary,
    daytype_comparison, select_data, extrema, format_number, csv_bytes,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def data():
    return load_data(ROOT / "data/station_daily_usage.csv", verify_source=True)


def test_report_overall(data):
    c = counts(data)
    assert c["total"] == 63955
    assert (c["boarding"], c["alighting"]) == (32593, 31362)
    assert (c["rows"], c["days"], c["weekdays"], c["weekends"]) == (56, 14, 10, 4)
    assert format_number(c["daily"]) == "4,568.2"


@pytest.mark.parametrize("station,boarding,alighting,total,balance", [
    ("가람역", 11575, 10556, 22131, 1019),
    ("누리역", 8497, 8146, 16643, 351),
    ("해솔역", 7511, 7452, 14963, 59),
    ("한빛역", 5010, 5208, 10218, -198),
])
def test_station_totals(data, station, boarding, alighting, total, balance):
    r = summary(data).set_index("역명").loc[station]
    assert [r["승차건수"], r["하차건수"], r["승하차합계"], r["승차_하차차이"]] == [
        boarding, alighting, total, balance]


@pytest.mark.parametrize("station,weekday,weekend,change,rate", [
    ("가람역", "1,739.8", "1,183.3", "-556.6", "-32.0"),
    ("누리역", "1,260.8", "1,008.8", "-252.1", "-20.0"),
    ("해솔역", "836.2", "1,650.3", "+814.1", "+97.4"),
    ("한빛역", "682.1", "849.3", "+167.2", "+24.5"),
    ("선택 역 전체", "4,518.9", "4,691.5", "+172.6", "+3.8"),
])
def test_report_weekday_means(data, station, weekday, weekend, change, rate):
    r = daytype_comparison(data).set_index("역명").loc[station]
    assert format_number(r["평일_일평균"]) == weekday
    assert format_number(r["주말_일평균"]) == weekend
    assert format_number(r["차이"], signed=True) == change
    assert format_number(r["증감률_pct"], signed=True) == rate


@pytest.mark.parametrize("station,high,highdate,low,lowdate", [
    ("가람역", 1892, "09/15", 1169, "09/19"),
    ("누리역", 1443, "09/08", 881, "09/12"),
    ("해솔역", 1695, "09/20", 724, "09/08"),
    ("한빛역", 984, "09/19", 565, "09/10"),
])
def test_report_extrema(data, station, high, highdate, low, lowdate):
    e = extrema(data[data["역명"].eq(station)])
    assert e == {"max": high, "min": low, "max_dates": [highdate], "min_dates": [lowdate]}


@pytest.mark.parametrize("value,expected", [
    (1183.25, "1,183.3"), (1008.75, "1,008.8"), (814.05, "814.1"),
    (-556.549999999999, "-556.6"), (167.15, "167.2"), (float("nan"), "—"),
])
def test_rounding(value, expected):
    assert format_number(value) == expected


def test_one_station_filter(data):
    part = select_data(data, ["해솔역"], "2026-09-07", "2026-09-20")
    assert len(part) == 14
    assert counts(part)["total"] == 14963
    assert summary(part).iloc[0]["비중_pct"] == 100
    comp = daytype_comparison(part)
    assert comp.iloc[0]["주말_일평균"] == comp.iloc[1]["주말_일평균"]


@pytest.mark.parametrize("start,end,days,weekend_days", [
    ("2026-09-07", "2026-09-11", 5, 0),
    ("2026-09-12", "2026-09-13", 2, 2),
    ("2026-09-12", "2026-09-12", 1, 1),
])
def test_one_daytype_filter(data, start, end, days, weekend_days):
    part = select_data(data, STATIONS, start, end)
    assert counts(part)["days"] == days
    assert counts(part)["weekends"] == weekend_days
    assert daytype_comparison(part)["증감률_pct"].isna().all()


def test_empty_selection(data):
    part = select_data(data, [], "2026-09-07", "2026-09-20")
    assert part.empty
    assert counts(part)["total"] == 0
    assert daytype_comparison(part).empty


def test_reversed_dates(data):
    with pytest.raises(ValueError):
        select_data(data, STATIONS, "2026-09-20", "2026-09-07")


@pytest.mark.parametrize("problem", [
    "duplicate", "negative", "null", "wrong_daytype", "missing_column",
    "fraction", "missing_day", "invalid_date", "blank_station", "infinite",
])
def test_invalid_data_rejected(data, problem):
    frame = data[REQUIRED].copy()
    if problem == "duplicate":
        frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    elif problem == "negative":
        frame.loc[0, "승차건수"] = -1
    elif problem == "null":
        frame.loc[0, "역명"] = None
    elif problem == "wrong_daytype":
        frame.loc[0, "요일구분"] = "주말"
    elif problem == "missing_column":
        frame = frame.drop(columns="승차건수")
    elif problem == "fraction":
        frame["승차건수"] = frame["승차건수"].astype(float)
        frame.loc[0, "승차건수"] = 0.5
    elif problem == "missing_day":
        frame = frame.iloc[1:].copy()
    elif problem == "invalid_date":
        frame["일자"] = frame["일자"].astype(str)
        frame.loc[0, "일자"] = "bad-date"
    elif problem == "blank_station":
        frame.loc[0, "역명"] = " "
    elif problem == "infinite":
        frame["승차건수"] = frame["승차건수"].astype(float)
        frame.loc[0, "승차건수"] = float("inf")
    with pytest.raises((ValueError, TypeError)):
        validate_data(frame)


def test_source_checksum_guard(tmp_path):
    path = tmp_path / "changed.csv"
    path.write_text("bad data\n", encoding="utf-8")
    with pytest.raises(ValueError, match="CSV"):
        load_data(path, verify_source=True)


def test_tied_extrema_are_preserved(data):
    part = data[data["역명"].eq("가람역")].iloc[:2].copy()
    part["승하차합계"] = 100
    e = extrema(part)
    assert len(e["max_dates"]) == 2
    assert len(e["min_dates"]) == 2


def test_csv_export_keeps_korean_and_rows(data):
    exported = csv_bytes(data)
    assert exported.startswith(b"\xef\xbb\xbf")
    restored = pd.read_csv(io.BytesIO(exported), encoding="utf-8-sig")
    assert len(restored) == len(data)
    assert restored["승차건수"].sum() == 32593


def test_zero_weekday_does_not_divide_by_zero(data):
    changed = data.copy()
    changed.loc[changed["요일구분"].eq("평일"), ["승차건수", "하차건수", "승하차합계"]] = 0
    assert daytype_comparison(changed)["증감률_pct"].isna().all()
