import json
from pathlib import Path

def print_alerts(alerts):
    for a in alerts:
        print(f"[{a['severity']}] {a['message']}")

def save_alerts(alerts, path="reports/alerts.json"):
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        json.dump(alerts, f, indent=4)
