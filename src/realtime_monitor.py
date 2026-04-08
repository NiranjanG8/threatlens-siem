import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from parser import parse_logs
from normalizer import normalize
from rules import detect_bruteforce
from anomaly_detector import detect_anomalies
from alert_manager import print_alerts

class Handler(FileSystemEventHandler):
    def on_modified(self, event):
        if "sample_logs.log" in event.src_path:
            logs = parse_logs("data/sample_logs.log")
            norm = normalize(logs)

            alerts = detect_bruteforce(norm) + detect_anomalies(norm)
            print_alerts(alerts)

observer = Observer()
observer.schedule(Handler(), path="data", recursive=False)
observer.start()

print("Monitoring logs...")

try:
    while True:
        time.sleep(2)
except KeyboardInterrupt:
    observer.stop()
observer.join()
