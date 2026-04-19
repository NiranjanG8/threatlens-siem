import time

from parser import collect_logs
from normalizer import normalize
from rules import detect_bruteforce, detect_suspicious_activity
from anomaly_detector import detect_anomalies
from alert_manager import print_alerts

print("Monitoring configured log sources...")

last_alerts = None

try:
    while True:
        logs = collect_logs()
        norm = normalize(logs)
        alerts = detect_bruteforce(norm) + detect_suspicious_activity(norm) + detect_anomalies(norm)

        if alerts != last_alerts:
            print_alerts(alerts)
            last_alerts = alerts

        time.sleep(10)
except KeyboardInterrupt:
    pass
