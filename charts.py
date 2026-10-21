"""Plotly 대화형 그래프. 색상은 라이브러리 기본값을 사용."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from analytics import format_number


def polish(fig: go.Figure, height: int = 400) -> go.Figure:
    fig.update_layout(
        height=height,
        font=dict(family="Arial, 'Noto Sans CJK KR', 'Malgun Gothic', sans-serif", size=13),
        margin=dict(l=24, r=28, t=44, b=45),
        legend=dict(orientation="h", yanchor="bottom", y=1.03, x=0),
        hoverlabel=dict(namelength=-1),
    )
    fig.update_xaxes(automargin=True)
    fig.update_yaxes(automargin=True)
    return fig


def daily_chart(part: pd.DataFrame, mode: str = "승차·하차", y_max: float | None = None) -> go.Figure:
    part = part.sort_values("일자")
    fig = go.Figure()
    items = [("승차건수", "승차", "solid", "circle"), ("하차건수", "하차", "dash", "square")]
    if mode == "승하차 합계":
        items = [("승하차합계", "승하차 합계", "solid", "circle")]
    for column, label, dash, symbol in items:
        fig.add_trace(go.Scatter(
            x=part["일자"], y=part[column], name=label, mode="lines+markers",
            line=dict(width=2.5, dash=dash), marker=dict(size=7, symbol=symbol),
            customdata=part[["요일구분"]],
            hovertemplate=label + " %{y:,}건 (%{customdata[0]})<extra></extra>",
        ))
    for day in part.loc[part["요일구분"].eq("주말"), "일자"].unique():
        day = pd.Timestamp(day)
        fig.add_vrect(
            x0=day - pd.Timedelta(hours=12), x1=day + pd.Timedelta(hours=12),
            fillcolor=fig.layout.template.layout.font.color,
            opacity=0.10, line_width=0, layer="below",
        )
    fig.update_layout(hovermode="x unified")
    fig.update_xaxes(
        title="일자", tickformat="%m/%d", dtick=86400000,
        range=[part["일자"].min() - pd.Timedelta(hours=12),
               part["일자"].max() + pd.Timedelta(hours=12)],
    )
    fig.update_yaxes(title="승하차 건수 (건)", rangemode="tozero")
    if y_max is not None:
        fig.update_yaxes(range=[0, y_max])
    return polish(fig, 420)


def comparison_chart(table: pd.DataFrame) -> go.Figure:
    table = table.loc[table["역명"] != "선택 역 전체"]
    fig = go.Figure()
    for column, label in [("평일_일평균", "평일"), ("주말_일평균", "주말")]:
        fig.add_trace(go.Bar(
            x=table["역명"], y=table[column], name=label,
            text=table[column].map(lambda x: format_number(x, 1)),
            textposition="outside", cliponaxis=False,
            customdata=table[column].map(lambda x: format_number(x, 1)),
            hovertemplate="%{x}<br>" + label + " %{customdata}건/일<extra></extra>",
        ))
    fig.update_layout(barmode="group", hovermode="x unified")
    fig.update_yaxes(title="일평균 승하차 합계 (건/일)", rangemode="tozero")
    fig.update_xaxes(title=None)
    return polish(fig, 410)


def ranking_chart(table: pd.DataFrame) -> go.Figure:
    table = table.sort_values("승하차합계", ascending=True)
    fig = go.Figure(go.Bar(
        y=table["역명"], x=table["승하차합계"], orientation="h",
        text=table["승하차합계"].map(lambda n: f"{n:,}건"), textposition="outside",
        cliponaxis=False, hovertemplate="%{y}<br>승하차 합계 %{x:,}건<extra></extra>",
    ))
    fig.update_xaxes(title="기간 승하차 합계 (건)", range=[0, table["승하차합계"].max() * 1.26])
    fig.update_yaxes(title=None)
    return polish(fig, 310)
