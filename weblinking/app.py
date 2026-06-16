from flask import Flask, render_template, request, Response, send_file
import pyautogui
import os
import platform
import psutil
import datetime
from functools import wraps
from pyngrok import ngrok

# LIVE VIEW
import cv2
import numpy as np
import mss

# EMAIL
import smtplib
from email.mime.text import MIMEText

# ================= APP =================
app = Flask(__name__)

# ================= CONFIG =================
USERNAME = "admin"
PASSWORD = "1234"   # CHANGE THIS

EMAIL_SENDER = "pittu.gowthamkumar@gmail.com"
EMAIL_PASSWORD = "kxlwntxqfjqjzciz"   # Gmail App Password
EMAIL_RECEIVER = "pittu.gowthamkumar@gmail.com"

SCREENSHOT_FOLDER = "screenshots"
os.makedirs(SCREENSHOT_FOLDER, exist_ok=True)

PUBLIC_URL = None

# ================= AUTH =================
def check_auth(username, password):
    return username == USERNAME and password == PASSWORD

def authenticate():
    return Response("Login Required", 401,
                    {"WWW-Authenticate": 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# ================= EMAIL =================
def send_email(link):
    try:
        msg = MIMEText(f"Your laptop control link:\n\n{link}")
        msg["Subject"] = "🌍 Remote Control Link"
        msg["From"] = EMAIL_SENDER
        msg["To"] = EMAIL_RECEIVER

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()

        print("✅ Email sent")

    except Exception as e:
        print("❌ Email error:", e)

# ================= NGROK =================
def start_ngrok():
    global PUBLIC_URL
    tunnel = ngrok.connect(5000)
    PUBLIC_URL = tunnel.public_url

    print("🌍 Public URL:", PUBLIC_URL)

    # SEND MAIL
    send_email(PUBLIC_URL)

# ================= LIVE SCREEN =================
def generate_screen():
    with mss.mss() as sct:
        monitor = sct.monitors[1]

        while True:
            img = np.array(sct.grab(monitor))
            frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

            _, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# ================= ROUTES =================

@app.route("/")
@requires_auth
def home():
    return render_template("index.html")

@app.route("/live")
@requires_auth
def live():
    return Response(generate_screen(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/screenshot", methods=["POST"])
@requires_auth
def screenshot():
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{SCREENSHOT_FOLDER}/shot_{now}.png"
    pyautogui.screenshot(path)
    return "✅ Screenshot saved"

@app.route("/view_screenshot")
@requires_auth
def view_screenshot():
    files = os.listdir(SCREENSHOT_FOLDER)
    if not files:
        return "No screenshots"
    latest = sorted(files)[-1]
    return send_file(os.path.join(SCREENSHOT_FOLDER, latest))

@app.route("/status")
@requires_auth
def status():
    battery = psutil.sensors_battery()
    uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time())

    return f"""
    CPU: {psutil.cpu_percent()}% <br>
    RAM: {psutil.virtual_memory().percent}% <br>
    Battery: {battery.percent if battery else 'N/A'}% <br>
    Uptime: {str(uptime).split('.')[0]}
    """

# ================= POWER =================

@app.route("/shutdown", methods=["POST"])
@requires_auth
def shutdown():
    if platform.system() == "Windows":
        os.system("shutdown /s /t 5")
    return "Shutdown started"

@app.route("/restart", methods=["POST"])
@requires_auth
def restart():
    if platform.system() == "Windows":
        os.system("shutdown /r /t 5")
    return "Restart started"

@app.route("/sleep", methods=["POST"])
@requires_auth
def sleep():
    if platform.system() == "Windows":
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
    return "Sleep triggered"

@app.route("/hibernate", methods=["POST"])
@requires_auth
def hibernate():
    if platform.system() == "Windows":
        os.system("shutdown /h")
    return "Hibernate started"

@app.route("/lock", methods=["POST"])
@requires_auth
def lock():
    if platform.system() == "Windows":
        os.system("rundll32.exe user32.dll,LockWorkStation")
    return "Locked"

@app.route("/logout_user", methods=["POST"])
@requires_auth
def logout_user():
    if platform.system() == "Windows":
        os.system("shutdown -l")
    return "Logged out"

# ================= MAIN =================
if __name__ == "__main__":
    start_ngrok()
    app.run(host="0.0.0.0", port=5000)