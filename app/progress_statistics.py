import pandas as pd
import numpy as np
import plotly.graph_objects as go

import streamlit as st



def plot_study_heatmap(df, date_col="date", value_col="minutes"):
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])

    # --- Full continuous range ---
    end = pd.Timestamp.today().normalize()
    start = end - pd.Timedelta(days=365)
    start = start - pd.Timedelta(days=start.weekday())
    end = end + pd.Timedelta(days=(6 - end.weekday()))

    full_range = pd.date_range(start, end, freq="D")

    df = (
        df.set_index(date_col)
        .reindex(full_range)
        .fillna(0)
        .rename_axis(date_col)
        .reset_index()
    )

    # --- Calendar features ---
    df["weekday"] = df[date_col].dt.weekday
    df["week_index"] = ((df[date_col] - start).dt.days // 7)

    heatmap_data = df.pivot(index="weekday", columns="week_index", values=value_col)
    date_matrix = df.pivot(index="weekday", columns="week_index", values=date_col)

    n_weeks = heatmap_data.shape[1]

    # =========================
    # 🎨 FIXED COLOR SCALE
    # =========================

    MAX_MINUTES = 5

    values = heatmap_data.values.astype(float)
    clipped = np.clip(values, 0, MAX_MINUTES)
    norm_values = clipped / MAX_MINUTES  # always 0 → 1

    BLUE = (0, 122, 255)  # iOS / Streamlit-like blue
    colorscale = [
        [0.0, "rgba(60,60,60,1)"],        # zero → dark gray
        [0.00001, "rgba(60,60,60,1)"],

        # very low → barely blue (close to gray)
        [0.15, "rgba(30, 80, 160, 0.35)"],

        # low-mid → noticeable blue
        [0.35, "rgba(0, 120, 255, 0.55)"],

        # mid-high → strong blue
        [0.6, "rgba(40, 160, 255, 0.75)"],

        # high → bright blue (big jump!)
        [0.85, "rgba(120, 200, 255, 0.90)"],

        # max → very bright, almost glowing
        [1.0, "rgba(180, 220, 255, 1.0)"]
    ]

    # =========================
    # 🔥 Heatmap
    # =========================

    fig = go.Figure(
        data=go.Heatmap(
            z=norm_values,
            zmin=0,   # 🔥 CRITICAL FIX
            zmax=1,   # 🔥 CRITICAL FIX
            x=list(range(n_weeks)),
            y=list(range(7)),
            customdata=np.stack((values, date_matrix.values.astype(str)), axis=-1),
            colorscale=colorscale,
            showscale=False,
            xgap=3,
            ygap=3,
            hovertemplate=(
                "Day: %{customdata[1]}<br>"
                "Minutes: %{customdata[0]}<extra></extra>"
            ),
        )
    )

    # --- Square cells ---
    fig.update_yaxes(
        scaleanchor="x",
        scaleratio=1,
        tickmode="array",
        tickvals=list(range(7)),
        ticktext=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],
        showgrid=False,
        zeroline=False,
        color="white",
    )

    fig.update_xaxes(
        showticklabels=False,
        showgrid=False,
        zeroline=False,
    )

    # --- Layout ---
    cell_size = 20
    fig.update_layout(
        height=cell_size * 7 + 60,
        margin=dict(t=30, b=10, l=40, r=10),
        plot_bgcolor="black",
        paper_bgcolor="black",
    )

    # =========================
    # 📅 Month labels
    # =========================

    target_months = [1, 4, 8, 12]
    month_names = {1: "Jan", 4: "Apr", 8: "Aug", 12: "Dec"}

    annotations = []

    for date in pd.date_range(start, end, freq="MS"):
        if date.month not in target_months:
            continue

        week_idx = ((date - start).days // 7)

        annotations.append(
            dict(
                x=week_idx,
                y=7.5,
                text=month_names[date.month],
                showarrow=False,
                font=dict(color="white", size=12),
                xanchor="left",
            )
        )

    fig.update_layout(annotations=annotations)

    return fig


def plot_study_progress_bar(df):
    completed_time = df.loc[df["completed"], "duration"].fillna(0).sum()
    total_time = df["duration"].fillna(0).sum()


    progress = completed_time / total_time if total_time > 0 else 0
    progress = min(progress, 1.0)

    st.markdown("---")
    st.progress(progress)

    st.caption(
        f"{round(completed_time,1)}h / {round(total_time,1)}h"
    )