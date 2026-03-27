from supabase import create_client
from datetime import datetime, timezone
import streamlit as st
import pandas as pd

from utils import get_day_date

DEBUG = False
DEBUG_TARGET = "streamlit" # streamlit or console

# -----------------------------
# SUPABASE CONNECTION
# -----------------------------

@st.cache_resource
def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )

def load_data(sb, debug=DEBUG, debug_target=DEBUG_TARGET):
    """
    loads table with the cols:
    (id, completed, position,
    task_template_name, task_template_duration,
    day_number)

    :param sb: superbase client instance
    """
    # base task fields
    # + join task_templates (name, duration)
    # + join days (day_number)
    response = sb.table("day_tasks") \
        .select("""
            id,
            completed,
            position,
            task_templates(name, duration),
            custom_tasks(name, duration),
            days(day_number,week, lessons(name, goal))
        """) \
        .order("position") \
        .execute()

    data = response.data if response.data else []

    rows = []
    for row in data:
        # Debugging logic
        if debug:
            if debug_target == "streamlit":
                st.write("DEBUG ROW:", row)
            else:
                print("DEBUG ROW:", row)

        day_info = row.get("days") or {}
        day_number = day_info.get("day_number")
        lesson = day_info.get("lessons") or {}
        week = day_info.get("week")
        task_date = get_day_date(day_number)

        lesson_name = lesson.get("name")
        lesson_goal = lesson.get("goal")

        tt = row.get("task_templates")
        ct = row.get("custom_tasks")

        if tt:
            task_name = tt["name"]
            duration = tt["duration"]
        elif ct:
            task_name = ct["name"]
            duration = ct["duration"]
        else:
            raise Exception("Task neither tt nor ct?")

        rows.append({
            "id": row["id"],
            "position": row["position"],
            "date": pd.to_datetime(task_date),
            "task": task_name,
            "duration": duration,
            "completed": row["completed"],
            "lesson": lesson_name,
            "goal": lesson_goal,
            "day_number": day_number,
            "week": week
        })

    return pd.DataFrame(rows)