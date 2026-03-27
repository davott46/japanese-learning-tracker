import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta, timezone

from db import get_supabase
from db import load_data

from progress_statistics import plot_study_heatmap
from progress_statistics import plot_study_progress_bar
# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="Japanese Learning Tracker", layout="wide")

supabase = get_supabase()

# -----------------------------
# BUTTON CSS
# -----------------------------
st.markdown("""
<style>
div.stButton > button {
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# UI HELPERS
# -----------------------------
def add_task_view(df, sb):
    st.subheader("Add Custom Task")

    task_name = st.text_input("Task name")
    duration = st.number_input("Duration (hours)", min_value=0.0, step=0.25)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Add Task"):
            if task_name:
                today = pd.to_datetime(date.today())
                today_tasks = df[df["date"] == today]

                # get day_id
                first_row = today_tasks.iloc[0]
                day_number = first_row.get("day_number")

                day_lookup = sb.table("days") \
                    .select("id") \
                    .eq("day_number", int(day_number)) \
                    .limit(1) \
                    .execute()

                day_id = day_lookup.data[0]["id"]

                # insert custom task
                res = sb.table("custom_tasks").insert({
                    "name": task_name,
                    "duration": float(duration)
                }).execute()

                custom_task_id = res.data[0]["id"]

                # determine position
                max_position = today_tasks["position"].max()
                next_position = int(max_position) + 1 if pd.notna(max_position) else 1

                # insert into day_tasks
                sb.table("day_tasks").insert({
                    "day_id": day_id,
                    "task_template_id": None,
                    "custom_task_id": custom_task_id,
                    "completed": False,
                    "position": next_position
                }).execute()

                # go back
                st.session_state["view"] = "main"
                st.rerun()

    with col2:
        if st.button("Cancel"):
            st.session_state["view"] = "main"
            st.rerun()


def today_view(df, sb):
    today = pd.to_datetime(date.today())

    today_tasks = df[df["date"] == today]

    if today_tasks.empty:
        st.info("No tasks scheduled for today.")
        return
    
    first_row = today_tasks.iloc[0]

    lesson = first_row.get("lesson")

    if lesson:
        st.info(f"📘 Lesson: {lesson}")
    else:
        st.info(f"📘 No Lesson today")
    
    goal = first_row.get("goal")
    st.caption(f"Goal: {goal}")

    day_number = first_row.get("day_number")
    week = first_row.get("week")
    st.caption(f"Day {day_number} • Week {week}")

    st.markdown("---")
    # column headers
    col1, col2, col3 = st.columns([0.7, 0.15, 0.15])

    with col1:
        header_text, header_btn = st.columns([0.10, 0.90])

        with header_text:
            st.markdown("<div style='text-align:center; font-size:20px; font-weight:600;'>Task</div>",unsafe_allow_html=True)
        with header_btn:
            if st.button("+", key="open_add_task", help="Add task"):
                st.session_state["view"] = "add_task"
                st.rerun()

    with col2:
        st.markdown("<div style='text-align:center; font-size:20px; font-weight:600;'>Done</div>",unsafe_allow_html=True)

    with col3:
        st.markdown("<div style='text-align:center; font-size:20px; font-weight:600;'>Delete</div>",unsafe_allow_html=True)
    # loop over todays tasks
    for idx, row in today_tasks.iterrows():
        col1, col2, col3 = st.columns([0.7, 0.15, 0.15])
        # task / durration
        with col1:
            duration = row.get("duration", None)
            task_name = row.get("task", "Unknown")

            if duration:
                st.write(f"- {task_name} ({duration}h)")
            else:
                st.write(f"- {task_name}")

        with col2:
            task_id = int(row["id"])
            c1, c2, c3 = st.columns([1, 1, 1])

            with c2:
                done = st.checkbox(
                    "Done",
                    value=row["completed"],
                    key=f"done_{task_id}",
                    label_visibility="collapsed"
                )

            if done != row["completed"]:
                # 1. Update only this task
                sb.table("day_tasks") \
                    .update({"completed": done}) \
                    .eq("id", task_id) \
                    .execute()

                if done:
                    # 2a. Insert log
                    sb.table("study_logs").insert({
                        "day_task_id": task_id,
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                        "duration_spent": float(row.get("duration") or 0)
                    }).execute()
                else:
                    # 2b. Delete log
                    sb.table("study_logs") \
                        .delete() \
                        .eq("day_task_id", task_id) \
                        .execute()

                # update streamlit state
                df.loc[df["id"] == task_id, "completed"] = done
                today_tasks = df[df["date"] == today]
        with col3:
            c1, c2, c3 = st.columns([1, 1, 1])

            with c2:
                delete_clicked = st.button("x", key=f"delete_{task_id}")
            if delete_clicked:
                # 1. delete from DB (this will also delete study_logs via FK cascade)
                sb.table("day_tasks") \
                    .delete() \
                    .eq("id", task_id) \
                    .execute()
                # 2. remove from dataframe (optional but clean)
                df.drop(df[df["id"] == task_id].index, inplace=True)
                today_tasks = df[df["date"] == today]
                st.rerun()

    # Progress bar UI
    total_time_today = float(today_tasks["duration"].fillna(0).sum())
    completed_time_today = float(
        today_tasks.loc[today_tasks["completed"], "duration"].fillna(0).sum()
    )

    progress = completed_time_today / total_time_today if total_time_today > 0 else 0
    progress = min(progress, 1.0)

    st.markdown("---")
    st.progress(progress)

    st.caption(
        f"{round(completed_time_today,1)}h / {round(total_time_today,1)}h"
    )

def calendar_view(df):
    st.subheader("Calendar")

    if df.empty:
        st.info("No tasks yet.")
        return

    grouped = df.groupby("date").agg({"task": list, "completed": "mean"}).reset_index()

    for _, row in grouped.iterrows():
        completion_rate = int(row["completed"] * 100)
        with st.expander(f"{row['date'].date()} — {completion_rate}% done"):
            for task in row["task"]:
                st.write(f"• {task}")


def stats_view(df):
    st.subheader("Statistics")

    if df.empty:
        st.info("No data yet.")
        return

    streak = calculate_streak(df)

    st.caption(f"🔥 {streak}")


    res = (
        df.assign(duration_completed=df["duration"].where(df["completed"], 0))
        .groupby(df["date"].dt.date)["duration_completed"]
        .sum()
        .reset_index()
    )    

    fig = plot_study_heatmap(res, date_col="date", value_col="duration_completed")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
    plot_study_progress_bar(df)


def calculate_streak(df):
    df = df.sort_values("date")
    today = pd.to_datetime(date.today())

    streak = 0
    current_day = today

    while True:
        day_tasks = df[df["date"] == current_day]
        if day_tasks.empty or not day_tasks["completed"].all():
            break
        streak += 1
        current_day -= timedelta(days=1)

    return streak


# -----------------------------
# MAIN APP
# -----------------------------
def main():
    if "view" not in st.session_state:
        st.session_state["view"] = "main"
    st.title("🇯🇵 Japanese Learning Tracker")

    df = load_data(supabase)

    tab1, tab2, tab3 = st.tabs(["Today", "Calendar", "Stats"])

    with tab1:
        if st.session_state["view"] == "main":
            today_view(df, supabase)
        elif st.session_state["view"] == "add_task":
            add_task_view(df, supabase)

    with tab2:
        calendar_view(df)

    with tab3:
        stats_view(df)


if __name__ == "__main__":
    main()