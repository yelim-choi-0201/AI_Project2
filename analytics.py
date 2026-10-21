"""보고서 집계 기준을 재현하는 순수 계산 함수. 네트워크 접근 없음."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import hashlib
import math

import pandas as pd

STATIONS = ["가람역", "누리역", "해솔역", "한빛역"]
REQUIRED = ["일자", "역명", "요일구분", "승차건수", "하차건수", "민원건수"]
SOURCE_SHA256 = "bf9a1ed866500e31c40ad7ca0e7f2456166838b7a25a55ac31fb3bd9b31e8d2a"


def load_data(path: str | Path, verify_source: bool = False) -> pd.DataFrame:
    """입력 오류를 임의 보정하지 않는다. 보고서 기준 원본 여부도 확인 가능."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"데이터 파일을 찾을 수 없습니다: {path.name}")
    if verify_source and hashlib.sha256(path.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError(
            "CSV가 원본 보고서의 데이터와 다릅니다. 원본 CSV를 복원하거나 "
            "보고서 해석과 데이터 검증 기준을 함께 갱신해 주세요."
        )
    return validate_data(pd.read_csv(path, encoding="utf-8-sig"))


def validate_data(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    missing = sorted(set(REQUIRED) - set(df.columns))
    if missing:
        raise ValueError("필수 열이 없습니다: " + ", ".join(missing))
    if df.empty:
        raise ValueError("데이터가 비어 있습니다.")
    if df[REQUIRED].isna().any().any():
        raise ValueError("결측값이 있습니다. 자동 대체하지 않았습니다.")
    df["일자"] = pd.to_datetime(df["일자"], format="%Y-%m-%d", errors="raise")
    if (df["일자"] != df["일자"].dt.normalize()).any():
        raise ValueError("일자 열에는 시간 없이 날짜만 있어야 합니다.")
    if (df["역명"].astype(str).str.strip() == "").any():
        raise ValueError("역명이 비어 있습니다.")
    if df.duplicated(["일자", "역명"]).any():
        raise ValueError("동일 일자·역명 중복이 있습니다. 자동 합산하지 않았습니다.")
    for col in ["승차건수", "하차건수", "민원건수"]:
        values = pd.to_numeric(df[col], errors="raise")
        if (~values.map(math.isfinite)).any() or (values < 0).any():
            raise ValueError(f"{col}에는 유한한 0 이상의 숫자가 필요합니다.")
        if (values % 1 != 0).any():
            raise ValueError(f"{col}에 정수가 아닌 값이 있습니다.")
        df[col] = values.astype("int64")
    expected = df["일자"].dt.dayofweek.map(lambda day: "주말" if day >= 5 else "평일")
    if not df["요일구분"].eq(expected).all():
        raise ValueError("요일구분과 실제 날짜가 일치하지 않습니다.")
    all_dates = pd.date_range(df["일자"].min(), df["일자"].max(), freq="D")
    for station, part in df.groupby("역명", sort=False):
        if len(part) != len(all_dates) or set(part["일자"]) != set(all_dates):
            raise ValueError(f"{station}에 날짜별 기록이 누락되었습니다. 0건으로 채우지 않았습니다.")
    df["승하차합계"] = df["승차건수"] + df["하차건수"]
    return df.sort_values(["일자", "역명"]).reset_index(drop=True)


def select_data(df: pd.DataFrame, stations: list[str], start, end) -> pd.DataFrame:
    start, end = pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize()
    if start > end:
        raise ValueError("시작일은 종료일보다 늦을 수 없습니다.")
    return df.loc[df["역명"].isin(stations) & df["일자"].between(start, end)].copy()


def format_number(value, digits: int = 1, signed: bool = False) -> str:
    """보고서와 동일하게 소수점 반올림(half-up). 부동소수점 끝자리 잡음 제거."""
    if value is None or pd.isna(value):
        return "—"
    number = Decimal(str(round(float(value), 8))).quantize(
        Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP
    )
    return format(number, f"{'+' if signed else ''},.{digits}f")


def counts(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"stations": 0, "days": 0, "weekdays": 0, "weekends": 0,
                "rows": 0, "boarding": 0, "alighting": 0, "total": 0, "daily": float("nan")}
    unique_dates = df[["일자", "요일구분"]].drop_duplicates()
    days = len(unique_dates)
    return {
        "stations": df["역명"].nunique(), "days": days, "rows": len(df),
        "weekdays": int(unique_dates["요일구분"].eq("평일").sum()),
        "weekends": int(unique_dates["요일구분"].eq("주말").sum()),
        "boarding": int(df["승차건수"].sum()), "alighting": int(df["하차건수"].sum()),
        "total": int(df["승하차합계"].sum()), "daily": df["승하차합계"].sum() / days,
    }


def summary(df: pd.DataFrame) -> pd.DataFrame:
    result = df.groupby("역명", sort=False).agg(
        승차건수=("승차건수", "sum"), 하차건수=("하차건수", "sum"),
        승하차합계=("승하차합계", "sum"), 관측일수=("일자", "nunique"),
    )
    result["일평균"] = result["승하차합계"] / result["관측일수"]
    result["비중_pct"] = result["승하차합계"] / result["승하차합계"].sum() * 100
    result["승차_하차차이"] = result["승차건수"] - result["하차건수"]
    result["차이비율_pct"] = result["승차_하차차이"] / result["승하차합계"].replace(0, float("nan")) * 100
    ordered = [s for s in STATIONS if s in result.index]
    ordered += [s for s in result.index if s not in ordered]
    return result.reindex(ordered).reset_index()


def daytype_comparison(df: pd.DataFrame, include_total: bool = True) -> pd.DataFrame:
    """합계/관측 일수. 한 요일 유형이 없거나 평일 평균이 0이면 비율은 NaN."""
    rows = []
    names = [s for s in STATIONS if s in set(df["역명"])]
    names += [s for s in df["역명"].unique() if s not in names]
    for name in names + (["선택 역 전체"] if include_total and not df.empty else []):
        part = df if name == "선택 역 전체" else df.loc[df["역명"].eq(name)]
        by_date = part.groupby(["일자", "요일구분"], as_index=False)["승하차합계"].sum()
        weekday = by_date.loc[by_date["요일구분"].eq("평일"), "승하차합계"]
        weekend = by_date.loc[by_date["요일구분"].eq("주말"), "승하차합계"]
        wd, we = weekday.mean(), weekend.mean()
        change = (we / wd - 1) * 100 if pd.notna(wd) and pd.notna(we) and wd != 0 else float("nan")
        rows.append({
            "역명": name, "평일_일수": len(weekday), "주말_일수": len(weekend),
            "평일_일평균": wd, "주말_일평균": we,
            "차이": we - wd, "증감률_pct": change,
        })
    return pd.DataFrame(rows, columns=[
        "역명", "평일_일수", "주말_일수", "평일_일평균", "주말_일평균", "차이", "증감률_pct"
    ])


def extrema(df: pd.DataFrame) -> dict:
    """동률 최대·최소일을 모두 보존."""
    if df.empty:
        raise ValueError("최대·최소를 계산할 데이터가 없습니다.")
    high, low = int(df["승하차합계"].max()), int(df["승하차합계"].min())
    return {
        "max": high, "min": low,
        "max_dates": df.loc[df["승하차합계"].eq(high), "일자"].dt.strftime("%m/%d").tolist(),
        "min_dates": df.loc[df["승하차합계"].eq(low), "일자"].dt.strftime("%m/%d").tolist(),
    }


def csv_bytes(df: pd.DataFrame) -> bytes:
    """Excel에서 한글을 읽을 수 있도록 UTF-8 BOM을 포함."""
    out = df.copy()
    for col in out.select_dtypes(include=["datetime"]).columns:
        out[col] = out[col].dt.strftime("%Y-%m-%d")
    return out.to_csv(index=False).encode("utf-8-sig")
