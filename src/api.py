from flask import Flask, jsonify
from parser import collect_logs
from normalizer import normalize
from rules import detect_bruteforce, detect_suspicious_activity
from anomaly_detector import detect_anomalies

app = Flask(__name__)

@app.route("/analyze")
def analyze():
    logs = collect_logs()
    norm = normalize(logs)

    alerts = detect_bruteforce(norm) + detect_suspicious_activity(norm) + detect_anomalies(norm)
    return jsonify(alerts)

@app.route("/events")
def events():
    logs = collect_logs()
    return jsonify(normalize(logs))

@app.route("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    app.run()
