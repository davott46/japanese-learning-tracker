import streamlit as st
import pandas as pd
from datetime import date, timedelta

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="Japanese Learning Tracker", layout="wide")

DATA_FILE = "schedule.csv"

# -----------------------------
# DATA HELPERS
# -----------------------------
def load_data():
    try:
        df = pd.read_csv(DATA_FILE, parse_dates=["date"])
    except FileNotFoundError:
        df = pd.DataFrame(columns=["date", "task", "completed"])
    return df


def save_data(df):
    df.to_csv(DATA_FILE, index=False)


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
            new_row = pd.DataFrame([
                {"date": task_date, "task": task_text, "completed": False}
            ])
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df)
            st.success("Task added!")
            st.rerun()


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
            st.write(f"- {row['task']}")
        with col2:
            done = st.checkbox("Done", value=row["completed"], key=f"done_{idx}")
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
