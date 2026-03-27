from datetime import date, timedelta

START_DATE = date(2026, 3, 27)

def get_day_date(day_number: int):
    return START_DATE + timedelta(days=day_number - 1)
