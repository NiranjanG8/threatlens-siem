from alert_manager import print_alerts, save_alerts
from detection_pipeline import collect_events_and_alerts

def run():
    _, alerts = collect_events_and_alerts()
    print_alerts(alerts)
    save_alerts(alerts)

if __name__ == "__main__":
    run()
