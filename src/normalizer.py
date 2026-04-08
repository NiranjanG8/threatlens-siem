def normalize(logs):
    normalized = []

    for log in logs:
        if "Failed login" in log:
            ip = log.split()[-1]
            normalized.append({"event": "failed_login", "ip": ip})

        elif "Successful login" in log:
            ip = log.split()[-1]
            normalized.append({"event": "success_login", "ip": ip})

    return normalized
