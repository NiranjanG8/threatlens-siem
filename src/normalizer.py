import re


IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def normalize(logs):
    normalized = []

    for log in logs:
        if isinstance(log, str):
            entry = _normalize_text_log(log, source="file")
        else:
            entry = _normalize_structured_log(log)

        if entry:
            normalized.append(entry)

    return normalized


def _normalize_structured_log(log):
    message = log.get("raw", "")
    entry = _normalize_text_log(message, source=log.get("source", "unknown"))
    if not entry:
        entry = {
            "event": _detect_structured_event_type(log, message),
            "ip": None,
            "source": log.get("source", "unknown"),
            "raw_message": message,
        }

    entry["timestamp"] = log.get("timestamp")
    entry["provider"] = log.get("provider")
    entry["event_id"] = log.get("event_id")
    entry["level"] = log.get("level")
    entry["host"] = log.get("host")
    return entry


def _normalize_text_log(message, source):
    ip_match = IP_PATTERN.search(message)
    if not ip_match:
        return None

    event = _detect_event_type(message)
    if not event:
        return None

    return {
        "event": event,
        "ip": ip_match.group(0),
        "source": source,
        "raw_message": message,
    }


def _detect_event_type(message):
    lowered = message.lower()

    if "failed login" in lowered or "failure" in lowered or "4625" in lowered:
        return "failed_login"

    if "successful login" in lowered or "logon success" in lowered or "4624" in lowered:
        return "success_login"

    if "denied" in lowered or "blocked" in lowered:
        return "access_denied"

    return None


def _detect_structured_event_type(log, message):
    event_id = log.get("event_id")
    provider = (log.get("provider") or "").lower()
    lowered = message.lower()

    if event_id == 4625 or "4625" in lowered:
        return "failed_login"

    if event_id == 4624 or "4624" in lowered:
        return "success_login"

    if "defender" in provider:
        return "defender_event"

    if "service control manager" in provider:
        return "service_event"

    if "powershell" in provider:
        return "powershell_event"

    if "error" in (log.get("level") or "").lower():
        return "system_error"

    if "warning" in (log.get("level") or "").lower():
        return "system_warning"

    return "system_event"
