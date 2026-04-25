import json
from pathlib import Path

from alert_store import upsert_detected_alerts

def print_alerts(alerts):
    for a in alerts:
        print(f"[{a['severity']}] {a['message']}")

def save_alerts(alerts, path="reports/alerts.json"):
    persisted_alerts = upsert_detected_alerts(alerts)
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        json.dump(persisted_alerts, f, indent=4)
