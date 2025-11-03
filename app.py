from flask import Flask, jsonify, render_template, send_file
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import requests
import csv
import os
import pytz

app = Flask(__name__)

# ==== Configuration ====
TARGET_URL = "https://unique-5.onrender.com"  # your target website
ping_count = 0
last_ping = None
uptime_start = None
pinger_running = False

# Timezone for India
IST = pytz.timezone("Asia/Kolkata")

scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
scheduler.start()

LOG_FILE = "ping_logs.csv"

# ==== Initialize CSV if not exists ====
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Ping Count", "Date", "Time", "Status Code", "Duration (ms)"])

# ==== Ping Function ====
def ping_website():
    global ping_count, last_ping
    try:
        start_time = datetime.now(IST)
        response = requests.get(TARGET_URL, timeout=10)
        duration_ms = int((datetime.now(IST) - start_time).total_seconds() * 1000)

        ping_count += 1
        now = datetime.now(IST)
        date_str = now.strftime("%d-%m-%Y")
        time_str = now.strftime("%I:%M:%S %p")  # 12-hour format
        last_ping = f"{date_str} {time_str}"

        # Save to CSV
        with open(LOG_FILE, "a", newline="") as f:
            csv.writer(f).writerow([ping_count, date_str, time_str, response.status_code, duration_ms])

        print(f"✅ Ping {ping_count}: {TARGET_URL} - {response.status_code} at {last_ping}")

    except Exception as e:
        now = datetime.now(IST)
        date_str = now.strftime("%d-%m-%Y")
        time_str = now.strftime("%I:%M:%S %p")
        with open(LOG_FILE, "a", newline="") as f:
            csv.writer(f).writerow([ping_count, date_str, time_str, "Error", "0"])
        print(f"❌ Ping failed at {date_str} {time_str}: {e}")

# ==== Routes ====
@app.route("/")
def index():
    return render_template("index.html", target_url=TARGET_URL)

@app.route("/start", methods=["POST"])
def start_pinger():
    global pinger_running, uptime_start
    if not pinger_running:
        pinger_running = True
        uptime_start = datetime.now(IST)
        ping_website()
        scheduler.add_job(ping_website, "interval", minutes=5, id="auto_pinger", replace_existing=True)
    return jsonify({"status": "started", "message": "Pinger started successfully."})

@app.route("/stop", methods=["POST"])
def stop_pinger():
    global pinger_running
    pinger_running = False
    try:
        scheduler.remove_job("auto_pinger")
    except:
        pass
    return jsonify({"status": "stopped"})

@app.route("/status")
def get_status():
    uptime = "00:00:00"
    if pinger_running and uptime_start:
        # Ensure both are timezone-aware
        now_ist = datetime.now(IST)
        uptime_seconds = (now_ist - uptime_start).total_seconds()
        hrs, rem = divmod(uptime_seconds, 3600)
        mins, secs = divmod(rem, 60)
        uptime = f"{int(hrs):02}:{int(mins):02}:{int(secs):02}"

    return jsonify({
        "status": "Running" if pinger_running else "Stopped",
        "ping_count": ping_count,
        "last_ping": last_ping if last_ping else "-",
        "uptime": uptime
    })

@app.route("/download")
def download_logs():
    return send_file(LOG_FILE, as_attachment=True)

# ==== Run App ====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
