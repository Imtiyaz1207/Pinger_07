from flask import Flask, jsonify, render_template, send_file
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import requests
import csv
import os
import pytz
import threading

app = Flask(__name__)

# ==== Configuration ====
TARGET_URLS = [
    "https://unique-5.onrender.com",
    "https://unique-07.onrender.com"
]

ping_data = {}  # Store status per URL
uptime_start = None
scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
scheduler.start()
LOG_FILE = "ping_logs.csv"
IST = pytz.timezone("Asia/Kolkata")
pinger_running = False

# Initialize ping_data
for url in TARGET_URLS:
    ping_data[url] = {"status": "Not started", "ping_count": 0, "last_ping": "-"}

# Initialize CSV if not exists
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["URL", "Ping Count", "Date", "Time", "Status Code", "Duration (ms)"])

# ==== Ping Function ====
def ping_website(url):
    try:
        start_time = datetime.now(IST)
        response = requests.get(url, timeout=20)
        duration_ms = int((datetime.now(IST) - start_time).total_seconds() * 1000)

        ping_data[url]["ping_count"] += 1
        now = datetime.now(IST)
        date_str = now.strftime("%d-%m-%Y")
        time_str = now.strftime("%I:%M:%S %p")
        ping_data[url]["last_ping"] = f"{date_str} {time_str}"
        ping_data[url]["status"] = response.status_code

        # Save to CSV
        with open(LOG_FILE, "a", newline="") as f:
            csv.writer(f).writerow([url, ping_data[url]["ping_count"], date_str, time_str, response.status_code, duration_ms])

        print(f"✅ {url} - {response.status_code} at {ping_data[url]['last_ping']}")
    except Exception as e:
        now = datetime.now(IST)
        date_str = now.strftime("%d-%m-%Y")
        time_str = now.strftime("%I:%M:%S %p")
        ping_data[url]["status"] = "Error"
        with open(LOG_FILE, "a", newline="") as f:
            csv.writer(f).writerow([url, ping_data[url]["ping_count"], date_str, time_str, "Error", 0])
        print(f"❌ Ping failed for {url} at {date_str} {time_str}: {e}")

# ==== Start / Stop Pinger ====
def start_pinger():
    global uptime_start, pinger_running
    if not pinger_running:
        uptime_start = datetime.now(IST)
        for url in TARGET_URLS:
            ping_website(url)  # immediate first ping
            scheduler.add_job(ping_website, "interval", args=[url], minutes=5, id=f"ping_{url}", replace_existing=True)
        pinger_running = True
        print("🚀 Pinger started")

def stop_pinger():
    global pinger_running
    for url in TARGET_URLS:
        try:
            scheduler.remove_job(f"ping_{url}")
        except:
            pass
    pinger_running = False
    print("🛑 Pinger stopped")

# Auto-start on server start
threading.Thread(target=start_pinger, daemon=True).start()

# ==== Routes ====
@app.route("/")
def index():
    return render_template("index.html", target_urls=TARGET_URLS)

@app.route("/status_all")
def status_all():
    uptime = "00:00:00"
    if uptime_start and pinger_running:
        uptime_seconds = (datetime.now(IST) - uptime_start).total_seconds()
        hrs, rem = divmod(uptime_seconds, 3600)
        mins, secs = divmod(rem, 60)
        uptime = f"{int(hrs):02}:{int(mins):02}:{int(secs):02}"

    data = {url: ping_data[url] for url in TARGET_URLS}
    data["uptime"] = uptime
    return jsonify(data)

@app.route("/start", methods=["POST"])
def start_route():
    start_pinger()
    return jsonify({"status": "started"})

@app.route("/stop", methods=["POST"])
def stop_route():
    stop_pinger()
    return jsonify({"status": "stopped"})

@app.route("/download")
def download_logs():
    return send_file(LOG_FILE, as_attachment=True)

if __name__ == "__main__":
    print("🌐 Flask Pinger Dashboard running at http://127.0.0.1:5000/")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
