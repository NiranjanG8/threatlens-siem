from flask import Flask, jsonify
from parser import parse_logs
from normalizer import normalize
from rules import detect_bruteforce
from anomaly_detector import detect_anomalies

app = Flask(__name__)

@app.route("/analyze")
def analyze():
    logs = parse_logs("data/sample_logs.log")
    norm = normalize(logs)

    alerts = detect_bruteforce(norm) + detect_anomalies(norm)
    return jsonify(alerts)

@app.route("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    app.run()
