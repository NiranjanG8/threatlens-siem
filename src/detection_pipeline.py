from anomaly_detector import detect_anomalies
from normalizer import normalize
from parser import collect_logs
from rules import detect_bruteforce, detect_suspicious_activity


def collect_events_and_alerts():
    raw_logs = collect_logs()
    normalized_logs = normalize(raw_logs)

    alerts = []
    alerts += detect_bruteforce(normalized_logs)
    alerts += detect_suspicious_activity(normalized_logs)
    alerts += detect_anomalies(normalized_logs)

    return normalized_logs, alerts
