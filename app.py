from flask import Flask, render_template, request, session
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "supersecretkey"

BASE_RATE = 41.02
SHIFT_LOADING_15 = 1.15
SHIFT_LOADING_30 = 1.30
TIME_AND_HALF = 1.5
DOUBLE_TIME = 2.0
SUPERANNUATION_RATE = 0.11
TAX_RATE = 0.20
DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def calculate_shift_pay(start_time, finish_time, day_index):
    if not start_time or not finish_time:
        return None
    
    # Use fixed date for consistent day calculations
    base_date = datetime(2000, 1, 1)
    start_dt = datetime.strptime(start_time, "%H:%M").replace(
        year=base_date.year, month=base_date.month, day=base_date.day)
    finish_dt = datetime.strptime(finish_time, "%H:%M").replace(
        year=base_date.year, month=base_date.month, day=base_date.day)

    # Handle overnight shifts
    if finish_dt < start_dt:
        finish_dt += timedelta(days=1)

    total_hours = (finish_dt - start_dt).total_seconds() / 3600
    original_date = start_dt.date()

    # Initialize tracking variables
    standard_pay = shift_15_pay = shift_30_pay = 0.0
    saturday_pay = sunday_pay = 0.0
    standard_hours = shift_15_hours = shift_30_hours = 0.0
    saturday_hours = sunday_hours = 0.0

    while start_dt < finish_dt:
        current_date = start_dt.date()
        current_day_index = day_index if current_date == original_date else (day_index + 1) % 7
        current_hour = start_dt.hour + start_dt.minute / 60.0
        minute_fraction = 1 / 60  # Value for 1 minute

        # Calculate rates based on day and time
        if current_day_index == 6:  # Sunday
            pay = BASE_RATE * DOUBLE_TIME * minute_fraction
            sunday_pay += pay
            sunday_hours += minute_fraction
        elif current_day_index == 5:  # Saturday
            pay = BASE_RATE * TIME_AND_HALF * minute_fraction
            saturday_pay += pay
            saturday_hours += minute_fraction
        elif current_day_index == 4:  # Friday
            if 18 <= current_hour < 24:
                pay = BASE_RATE * SHIFT_LOADING_15 * minute_fraction
                shift_15_pay += pay
                shift_15_hours += minute_fraction
            elif 0 <= current_hour < 6:
                pay = BASE_RATE * TIME_AND_HALF * minute_fraction
                saturday_pay += pay
                saturday_hours += minute_fraction
            else:
                pay = BASE_RATE * minute_fraction
                standard_pay += pay
                standard_hours += minute_fraction
        elif current_day_index < 4:  # Monday-Thursday
            if 18 <= current_hour < 24:
                pay = BASE_RATE * SHIFT_LOADING_15 * minute_fraction
                shift_15_pay += pay
                shift_15_hours += minute_fraction
            elif 0 <= current_hour < 6:
                pay = BASE_RATE * SHIFT_LOADING_30 * minute_fraction
                shift_30_pay += pay
                shift_30_hours += minute_fraction
            else:
                pay = BASE_RATE * minute_fraction
                standard_pay += pay
                standard_hours += minute_fraction
        else:
            pay = BASE_RATE * minute_fraction
            standard_pay += pay
            standard_hours += minute_fraction

        start_dt += timedelta(minutes=1)

    # Calculate totals
    total_pay = sum([
        standard_pay,
        shift_15_pay,
        shift_30_pay,
        saturday_pay,
        sunday_pay
    ])

    # Round values
    totals = {
        'total_hours': round(total_hours, 2),
        'standard_hours': round(standard_hours, 2),
        'shift_15_hours': round(shift_15_hours, 2),
        'shift_30_hours': round(shift_30_hours, 2),
        'saturday_hours': round(saturday_hours, 2),
        'sunday_hours': round(sunday_hours, 2),
        'standard_pay': round(standard_pay, 2),
        'shift_15_pay': round(shift_15_pay, 2),
        'shift_30_pay': round(shift_30_pay, 2),
        'saturday_pay': round(saturday_pay, 2),
        'sunday_pay': round(sunday_pay, 2),
        'total_pay': round(total_pay, 2)
    }

    # Calculate deductions
    totals['superannuation'] = round(totals['total_pay'] * SUPERANNUATION_RATE, 2)
    totals['tax'] = round(totals['total_pay'] * TAX_RATE, 2)
    totals['net_pay'] = round(totals['total_pay'] - totals['tax'], 2)

    return totals

@app.route("/", methods=["GET", "POST"])
def home():
    if "shift_data" not in session:
        session["shift_data"] = {f"start_time_{i}": "" for i in range(14)}
        session["shift_data"].update({f"finish_time_{i}": "" for i in range(14)})
    
    total_summary = {
        "total_hours": 0.0,
        "standard_hours": 0.0,
        "shift_15_hours": 0.0,
        "shift_30_hours": 0.0,
        "saturday_hours": 0.0,
        "sunday_hours": 0.0,
        "standard_pay": 0.0,
        "shift_15_pay": 0.0,
        "shift_30_pay": 0.0,
        "saturday_pay": 0.0,
        "sunday_pay": 0.0,
        "total_pay": 0.0,
        "superannuation": 0.0,
        "tax": 0.0,
        "net_pay": 0.0,
    }
    
    if request.method == "POST":
        shift_data = {}
        for i in range(14):
            start_time = request.form.get(f"start_time_{i}")
            finish_time = request.form.get(f"finish_time_{i}")
            shift_data[f"start_time_{i}"] = start_time
            shift_data[f"finish_time_{i}"] = finish_time
            day_index = i % 7
            
            if start_time and finish_time:
                pay_details = calculate_shift_pay(start_time, finish_time, day_index)
                if pay_details:
                    for key in total_summary:
                        if key in pay_details:
                            total_summary[key] += pay_details[key]
        
        session["shift_data"] = shift_data
    
    return render_template("index.html", 
                         total_summary=total_summary, 
                         days=DAYS_OF_WEEK, 
                         shift_data=session["shift_data"])

if __name__ == "__main__":
    app.run(debug=True)