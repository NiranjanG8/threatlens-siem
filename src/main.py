from parser import collect_logs
from normalizer import normalize
from rules import detect_bruteforce, detect_suspicious_activity
from anomaly_detector import detect_anomalies
from alert_manager import print_alerts, save_alerts

def run():
    raw = collect_logs()
    norm = normalize(raw)

    alerts = []
    alerts += detect_bruteforce(norm)
    alerts += detect_suspicious_activity(norm)
    alerts += detect_anomalies(norm)

    print_alerts(alerts)
    save_alerts(alerts)

if __name__ == "__main__":
    run()
