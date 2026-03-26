import streamlit as st
import pandas as pd
from datetime import date, timedelta
from supabase import create_client

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="Japanese Learning Tracker", layout="wide")

# -----------------------------
# SUPABASE CONNECTION
# -----------------------------
@st.cache_resource
def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )

supabase = get_supabase()

# -----------------------------
# DATA HELPERS (DB)
# -----------------------------
START_DATE = date(2026, 3, 26)  # adjust if needed


def get_day_date(day_number: int):
    return START_DATE + timedelta(days=day_number - 1)


def load_data():
    response = supabase.table("day_tasks") \
        .select("""
            id,
            completed,
            position,
            task_templates(name, duration),
            days(day_number)
        """) \
        .order("position") \
        .execute()

    data = response.data if response.data else []

    rows = []
    for row in data:
        day_number = row["days"]["day_number"]
        task_date = get_day_date(day_number)

        rows.append({
            "id": row["id"],
            "date": pd.to_datetime(task_date),
            "task": row["task_templates"]["name"],
            "duration": row["task_templates"]["duration"],
            "completed": row["completed"]
        })

    return pd.DataFrame(rows)


def save_data(df):
    for _, row in df.iterrows():
        supabase.table("day_tasks") \
            .update({"completed": bool(row["completed"])}) \
            .eq("id", int(row["id"])) \
            .execute()

        if row["completed"]:
            supabase.table("study_logs").insert({
                "day_task_id": int(row["id"]),
                "duration_spent": float(row.get("duration", 0))
            }).execute()


# -----------------------------
# UI HELPERS
# -----------------------------
def add_task_ui(df):
    with st.form("add_task"):
        st.subheader("Add Study Task")
        task_date = st.date_input("Date", value=date.today())
        task_text = st.text_input("Task (e.g., Learn 10 Kanji)")
        submitted = st.form_submit_button("Add Task")

        if submitted and task_text:
            st.info("Custom tasks not supported with DB yet.")


def today_view(df):
    st.subheader("Today's Plan")
    today = pd.to_datetime(date.today())

    today_tasks = df[df["date"] == today]

    if today_tasks.empty:
        st.info("No tasks scheduled for today.")
        return

    for idx, row in today_tasks.iterrows():
        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            duration = row.get("duration", None)
            if duration:
                st.write(f"- {row['task']} ({duration}h)")
            else:
                st.write(f"- {row['task']}")

        with col2:
            done = st.checkbox("Done", value=row["completed"], key=f"done_{row['id']}")
            if done != row["completed"]:
                df.at[idx, "completed"] = done
                save_data(df)
                st.rerun()


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

    total = len(df)
    completed = df["completed"].sum()
    streak = calculate_streak(df)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Tasks", total)
    col2.metric("Completed", int(completed))
    col3.metric("Current Streak (days)", streak)


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
    st.title("🇯🇵 Japanese Learning Tracker")

    df = load_data()

    tab1, tab2, tab3 = st.tabs(["Today", "Calendar", "Stats"])

    with tab1:
        today_view(df)
        add_task_ui(df)

    with tab2:
        calendar_view(df)

    with tab3:
        stats_view(df)


if __name__ == "__main__":
    main()