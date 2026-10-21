"""실행: python -m streamlit run app.py"""
from __future__ import annotations

from pathlib import Path
import math

import pandas as pd
import streamlit as st

from analytics import (
    STATIONS, load_data, select_data, counts, summary, daytype_comparison,
    extrema, format_number as fmt, csv_bytes,
)
from charts import daily_chart, comparison_chart, ranking_chart
from report_content import (
    REPORT_TITLE, REPORT_FILENAME, REPORT_PERIOD, REPORT_DATE,
    HEADLINE, STATION_TEXT, COMPARISON_TEXT, OPERATIONS, LIMITATIONS, CONCLUSION,
)

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="역별 승하차 | 결과 해석", page_icon="🚉", layout="wide")
st.markdown("""
<style>
.block-container {max-width:1450px; padding-top:2.2rem; padding-bottom:3rem;}
h1,h2,h3 {letter-spacing:-0.04em; word-break:keep-all;}
[data-testid="stMetricValue"] {letter-spacing:-0.04em;}
.hero-label {font-size:0.75rem; font-weight:700; letter-spacing:0.15em;
             color:#0F766E; margin-bottom:0.55rem;}
.scope-note {border-left:4px solid #0F766E; padding:0.75rem 1rem;
             background:#F3F6FA; border-radius:0 8px 8px 0; margin:0.8rem 0 1.2rem;}
@media (max-width:700px) {
 .block-container {padding-left:1rem; padding-right:1rem;}
 h1 {font-size:1.8rem;}
}
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def read_source() -> pd.DataFrame:
    return load_data(ROOT / "data/station_daily_usage.csv", verify_source=True)


def show_frame(frame: pd.DataFrame, formatters: dict | None = None):
    styled = frame.style.format(formatters or {}, na_rep="—")
    st.dataframe(styled, hide_index=True, width="stretch")


def show_figure(fig, key: str):
    st.plotly_chart(
        fig, width="stretch", key=key,
        config={"displaylogo": False, "scrollZoom": False,
                "toImageButtonOptions": {"format": "png", "scale": 2}},
    )


def reset_filters():
    st.session_state["station_filter"] = STATIONS.copy()
    st.session_state["period_filter"] = (raw["일자"].min().date(), raw["일자"].max().date())


try:
    raw = read_source()
except (OSError, ValueError, pd.errors.ParserError) as exc:
    st.error(f"데이터를 불러오지 못했습니다. {exc}")
    st.stop()

available = [name for name in STATIONS if name in set(raw["역명"])]
min_day, max_day = raw["일자"].min().date(), raw["일자"].max().date()

with st.sidebar:
    st.markdown("### 조회 조건")
    st.caption("기본값은 원본 보고서의 전체 분석 범위입니다.")
    selected = st.multiselect("역 선택", available, default=available, key="station_filter")
    period = st.date_input(
        "조회 기간", value=(min_day, max_day), min_value=min_day, max_value=max_day,
        format="YYYY/MM/DD", key="period_filter",
    )
    st.button("전체 기간·역으로 초기화", on_click=reset_filters, width="stretch")
    fixed_scale = st.toggle("역별 그래프 세로축 통일", value=True, key="fixed_scale")
    st.caption("승차·하차 그래프를 역 간 같은 척도로 비교합니다.")
    st.divider()
    st.markdown("**데이터 안내**")
    st.caption("원본: station_daily_usage.csv\n\n단위: 승차·하차 건수\n\n민원건수는 승하차 분석에 포함하지 않습니다.")
    st.caption("‘종합 해석’과 원본 보고서는 전체 14일 기준으로 고정됩니다.")

st.markdown('<div class="hero-label">STATION INSIGHT · 결과 해석 대시보드</div>', unsafe_allow_html=True)
st.title(REPORT_TITLE)
st.caption(f"보고서 작성일 {REPORT_DATE} · 원본 분석 기간 {REPORT_PERIOD}")
if not selected:
    st.info("왼쪽에서 한 개 이상의 역을 선택해 주세요.")
    st.stop()
if not isinstance(period, (tuple, list)) or len(period) != 2:
    st.info("조회 기간의 시작일과 종료일을 모두 선택해 주세요.")
    st.stop()

try:
    filtered = select_data(raw, selected, period[0], period[1])
except ValueError as exc:
    st.warning(str(exc))
    st.stop()
if filtered.empty:
    st.warning("선택한 조건에 해당하는 기록이 없습니다.")
    st.stop()

n = counts(filtered)
stats = summary(filtered)
comparison = daytype_comparison(filtered)
all_row = comparison.loc[comparison["역명"].eq("선택 역 전체")].iloc[0]
full_scope = set(selected) == set(available) and tuple(period) == (min_day, max_day)
st.markdown(
    f'<div class="scope-note"><b>현재 집계</b> &nbsp; {period[0]:%Y.%m.%d} - {period[1]:%Y.%m.%d}'
    f' &nbsp; | &nbsp; {n["stations"]}개 역 · {n["days"]}일'
    f' &nbsp; | &nbsp; 평일 {n["weekdays"]}일 / 주말 {n["weekends"]}일</div>',
    unsafe_allow_html=True,
)
if not full_scope:
    st.caption("필터 적용 중: 수치·표·그래프는 선택 범위로 재계산됩니다. 원본 보고서의 고정 해석은 별도 표시합니다.")

kpis = st.columns(4)
kpis[0].metric("승하차 합계", f'{n["total"]:,}건', border=True)
kpis[1].metric("승차", f'{n["boarding"]:,}건', border=True)
kpis[2].metric("하차", f'{n["alighting"]:,}건', border=True)
kpis[3].metric("선택 역 전체 일평균", f'{fmt(n["daily"])}건/일', border=True)
st.caption("승하차 합계는 고유 이용자 수가 아닙니다. 같은 사람의 반복 이용과 승차·하차가 포함될 수 있습니다.")

overview, weekday_tab, detail, interpretation, data_tab = st.tabs(
    ["한눈에 보기", "평일·주말 비교", "역별 추이", "종합 해석", "데이터·보고서"]
)

with overview:
    st.subheader("평일과 주말, 역마다 방향이 다릅니다." if full_scope else "선택 범위의 역별 요일 차이")
    if full_scope:
        st.write(HEADLINE)
    cols = st.columns(len(stats))
    for col, station in zip(cols, stats["역명"]):
        row = comparison.loc[comparison["역명"].eq(station)].iloc[0]
        rate = row["증감률_pct"]
        with col, st.container(border=True):
            st.caption(station)
            st.metric("평일 대비 주말", f"{fmt(rate, signed=True)}%" if pd.notna(rate) else "비교 불가")
            if pd.isna(rate):
                st.caption("평일·주말을 모두 포함하고 평일 평균이 0보다 커야 합니다.")
            else:
                direction = "증가" if rate > 0 else "감소" if rate < 0 else "동일"
                st.caption(f"주말 {direction} · 일평균 기준")
            st.caption(f'평일 {fmt(row["평일_일평균"])} → 주말 {fmt(row["주말_일평균"])}건/일')
    if pd.notna(all_row["증감률_pct"]):
        st.info(f'선택 역 전체의 주말 일평균은 평일 대비 {fmt(all_row["증감률_pct"], signed=True)}%입니다. '
                "역별 반대 방향의 변화를 전체 합계만으로 판단하지 마세요.")
    else:
        st.info("선택 범위에는 비교 가능한 평일·주말 쌍이 없어 증감률을 계산하지 않았습니다.")
    left, right = st.columns([1, 1.25], gap="large")
    with left:
        st.markdown("#### 기간 이용 규모")
        show_figure(ranking_chart(stats), "ranking")
    with right:
        st.markdown("#### 역별 집계")
        table = stats[["역명", "승차건수", "하차건수", "승하차합계", "일평균", "비중_pct"]].rename(
            columns={"승차건수": "승차 (건)", "하차건수": "하차 (건)", "승하차합계": "합계 (건)",
                     "일평균": "일평균 (건/일)", "비중_pct": "비중 (%)"})
        show_frame(table, {
            "승차 (건)": lambda x: fmt(x, 0), "하차 (건)": lambda x: fmt(x, 0),
            "합계 (건)": lambda x: fmt(x, 0), "일평균 (건/일)": fmt, "비중 (%)": fmt,
        })
        st.caption("비중의 분모는 현재 선택한 역·기간의 승하차 합계입니다.")

with weekday_tab:
    st.subheader("관측 일수가 다르므로 일평균으로 비교합니다.")
    st.caption("주말은 토·일요일입니다. 증감률 = (주말 일평균 ÷ 평일 일평균 - 1) × 100")
    if n["weekdays"] == 0 or n["weekends"] == 0:
        st.warning("평일 또는 주말 기록이 없는 기간입니다. 없는 유형의 평균과 증감률은 ‘—’로 표시합니다.")
    show_figure(comparison_chart(comparison), "daytype")
    ctable = comparison.rename(columns={
        "평일_일수": "평일 (일)", "주말_일수": "주말 (일)",
        "평일_일평균": "평일 평균 (건/일)", "주말_일평균": "주말 평균 (건/일)",
        "차이": "차이 (건/일)", "증감률_pct": "주말 증감률 (%)",
    })
    show_frame(ctable, {
        "평일 평균 (건/일)": fmt, "주말 평균 (건/일)": fmt,
        "차이 (건/일)": lambda x: fmt(x, signed=True),
        "주말 증감률 (%)": lambda x: fmt(x, signed=True),
    })
    st.caption("차이와 증감률은 반올림 전 평균에서 계산합니다. 마지막 행은 선택 역의 일별 합계를 기준으로 계산합니다.")
    with st.expander("원본 보고서의 비교 해석 | 전체 4개 역·14일 기준", expanded=full_scope):
        for heading, body in COMPARISON_TEXT:
            st.markdown(f"**{heading}**")
            st.write(body)

with detail:
    st.subheader("날짜별 흐름과 최대·최소일")
    select_col, mode_col = st.columns([1, 1.5])
    with select_col:
        station = st.selectbox("상세 분석 역", stats["역명"].tolist(), key="detail_station")
    with mode_col:
        mode = st.radio("표시 지표", ["승차·하차", "승하차 합계"], horizontal=True, key="chart_mode")
    part = filtered.loc[filtered["역명"].eq(station)].copy()
    ext = extrema(part)
    row = comparison.loc[comparison["역명"].eq(station)].iloc[0]
    detail_cols = st.columns(3)
    detail_cols[0].metric("평일 대비 주말 일평균", f'{fmt(row["증감률_pct"], signed=True)}%' if pd.notna(row["증감률_pct"]) else "비교 불가", border=True)
    detail_cols[1].metric("최대 일별 합계", f'{ext["max"]:,}건', border=True)
    detail_cols[1].caption("해당 날짜 " + ", ".join(ext["max_dates"]))
    detail_cols[2].metric("최소 일별 합계", f'{ext["min"]:,}건', border=True)
    detail_cols[2].caption("해당 날짜 " + ", ".join(ext["min_dates"]))
    ymax = None
    if fixed_scale:
        source_max = raw[["승차건수", "하차건수"]].to_numpy().max() if mode == "승차·하차" else raw["승하차합계"].max()
        ymax = math.ceil(float(source_max) * 1.10 / 100) * 100
    show_figure(daily_chart(part, mode, ymax), "daily_station")
    st.caption("음영은 주말입니다. 승차는 실선·원, 하차는 점선·사각형입니다. 최대·최소는 승차와 하차를 더한 일별 합계입니다.")
    if fixed_scale:
        st.caption(f"세로축: 0~{ymax:,}건. 모든 역에 같은 원본 전체 범위를 적용합니다.")
    with st.expander(f"원본 보고서의 {station} 해석 | {REPORT_PERIOD}", expanded=True):
        st.caption("아래 설명은 원본 전체 기간의 해석이며, 현재 필터 범위의 해석이 아닙니다.")
        narrative = STATION_TEXT[station]
        st.markdown(f'**{narrative["title"]}**')
        st.markdown("**관찰 결과**")
        st.write(narrative["observed"])
        st.markdown("**해석**")
        st.write(narrative["meaning"])
    with st.expander("선택 역의 일별 숫자 보기"):
        show_frame(part[["일자", "요일구분", "승차건수", "하차건수", "승하차합계"]].assign(
            일자=part["일자"].dt.strftime("%Y-%m-%d")))

with interpretation:
    st.subheader("종합 판단과 결과의 활용 범위")
    st.info(f"이 탭은 원본 보고서의 전체 4개 역·14일({REPORT_PERIOD}) 기준입니다. 왼쪽 필터와 무관하게 고정됩니다.")
    st.markdown("#### 승차와 하차의 차이")
    original_stats = summary(raw)
    imbalance = original_stats[["역명", "승차_하차차이", "차이비율_pct"]].rename(
        columns={"승차_하차차이": "승차 - 하차 (건)", "차이비율_pct": "차이 ÷ 승하차 합계 (%)"})
    show_frame(imbalance, {
        "승차 - 하차 (건)": lambda x: fmt(x, 0, signed=True),
        "차이 ÷ 승하차 합계 (%)": lambda x: fmt(x, signed=True),
    })
    st.caption("양수는 승차 우세, 음수는 하차 우세입니다. 이용 기록 차이이지 순유입 인구가 아닙니다.")
    st.markdown("#### 데이터에 근거한 운영 검토 방향")
    st.table(pd.DataFrame(OPERATIONS))
    st.write("모든 역에 동일한 운영 기준을 적용하기보다 역별·요일별 관측 결과를 구분해 검토할 필요가 있습니다. "
             "이는 운영 변경의 확정안이 아니라 추가 확인의 우선순위입니다.")
    st.markdown("#### 결과 해석 시 주의사항")
    for heading, body in LIMITATIONS:
        with st.expander(heading, expanded=True):
            st.write(body)
    st.markdown("#### 결론")
    st.write(CONCLUSION)
    st.caption(f"해석 출처: {REPORT_FILENAME}의 02~05절. 원문의 관찰·해석·한계를 유지했습니다.")

with data_tab:
    st.subheader("데이터 확인과 보고서 내려받기")
    st.markdown("#### 원본 데이터 품질")
    audit = st.columns(4)
    audit[0].metric("결측값", int(raw.isna().sum().sum()), border=True)
    audit[1].metric("일자·역명 중복", int(raw.duplicated(["일자", "역명"]).sum()), border=True)
    audit[2].metric("음수 건수 값", int((raw[["승차건수", "하차건수", "민원건수"]] < 0).sum().sum()), border=True)
    audit[3].metric("날짜·요일 일치", "전체 일치", border=True)
    st.caption("원본 56행·6열. 삭제·대체·보간 없이 사용하며 원본 파일의 체크섬도 확인합니다.")
    st.markdown("#### 현재 선택 범위의 데이터")
    visible = filtered[["일자", "역명", "요일구분", "승차건수", "하차건수", "승하차합계", "민원건수"]].copy()
    visible["일자"] = visible["일자"].dt.strftime("%Y-%m-%d")
    st.dataframe(visible, hide_index=True, width="stretch")
    st.caption("민원건수는 원본 확인을 위해 표시하며, 위의 승하차 지표·해석에는 사용하지 않습니다.")
    d1, d2, d3 = st.columns(3)
    d1.download_button("선택 데이터 CSV", csv_bytes(filtered), "station_filtered.csv", "text/csv", width="stretch")
    d2.download_button("역별 집계 CSV", csv_bytes(stats), "station_summary.csv", "text/csv", width="stretch")
    d3.download_button("평일·주말 비교 CSV", csv_bytes(comparison), "station_daytype_comparison.csv", "text/csv", width="stretch")
    st.markdown("#### 원본 보고서")
    report = ROOT / "assets/station_report.docx"
    if report.is_file():
        st.download_button(
            "가독성 개선 보고서 받기 · Word", report.read_bytes(), REPORT_FILENAME,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            width="stretch",
        )
    else:
        st.warning("assets/station_report.docx가 없습니다. 배포 시 보고서 파일도 함께 포함해 주세요.")
    st.caption("Word 파일은 전체 14일 기준의 기존 보고서입니다. 필터 조건에 맞춰 새로 생성되는 보고서가 아닙니다.")
    with st.expander("집계 기준과 재현 정보"):
        st.markdown("""
승하차 합계는 **승차건수 + 하차건수**입니다. 일평균은 해당 범위의 합계를 실제 관측 일수로 나눕니다.
원본 전체 기간은 14일(평일 10일, 주말 4일)입니다.

주말 증감률은 **(주말 일평균 ÷ 평일 일평균 - 1) × 100**입니다.
비교할 요일 유형이 없거나 평일 평균이 0인 경우 증감률을 계산하지 않습니다.

소수점 첫째 자리 표시는 반올림하며, 증감률과 차이는 반올림 전 값으로 계산합니다.
비중은 현재 선택한 역·기간의 승하차 합계를 분모로 사용합니다.

원본 데이터: `data/station_daily_usage.csv`  
원본 보고서: `assets/station_report.docx`  
자동으로 갱신되는 실시간 데이터가 아니라 고정된 분석 자료입니다.
""")

st.divider()
st.caption("자료: station_daily_usage.csv · 해석: 역별_승하차_결과해석_보고서_가독성개선.docx · 단위: 건")
