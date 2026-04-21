from collections import defaultdict

def detect_bruteforce(logs):
    counts = defaultdict(int)

    for log in logs:
        if log["event"] == "failed_login" and log.get("ip"):
            counts[log["ip"]] += 1

    return [
        {
            "type": "Brute Force",
            "ip": ip,
            "severity": "HIGH",
            "message": f"Brute force attack from {ip}"
        }
        for ip, count in counts.items() if count >= 3
    ]


def detect_suspicious_activity(logs):
    counts = defaultdict(int)

    for log in logs:
        if not log.get("ip"):
            continue
        counts[log["ip"]] += 1

    return [
        {
            "type": "Suspicious Activity",
            "ip": ip,
            "severity": "MEDIUM",
            "message": f"High activity from {ip}"
        }
        for ip, count in counts.items() if count >= 5
    ]
