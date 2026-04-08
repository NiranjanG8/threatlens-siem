import json

def print_alerts(alerts):
    for a in alerts:
        print(f"[{a['severity']}] {a['message']}")

def save_alerts(alerts, path="reports/alerts.json"):
    with open(path, "w") as f:
        json.dump(alerts, f, indent=4)
