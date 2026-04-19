from sklearn.ensemble import IsolationForest
import numpy as np

def detect_anomalies(logs):
    ip_counts = {}

    for log in logs:
        ip = log["ip"]
        ip_counts[ip] = ip_counts.get(ip, 0) + 1

    ips = list(ip_counts.keys())
    if len(ips) < 2:
        return []

    values = np.array(list(ip_counts.values())).reshape(-1, 1)

    model = IsolationForest(contamination=0.2)
    model.fit(values)

    preds = model.predict(values)

    alerts = []
    for i, pred in enumerate(preds):
        if pred == -1:
            alerts.append({
                "type": "Anomaly",
                "ip": ips[i],
                "severity": "HIGH",
                "message": f"Anomalous activity from {ips[i]}"
            })

    return alerts
