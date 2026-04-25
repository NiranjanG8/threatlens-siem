import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
STORE_PATH = BASE_DIR / "reports" / "alert_state.json"
DEFAULT_STATUS = "NEW"
VALID_STATUSES = {
    "NEW",
    "INVESTIGATING",
    "TRUE_POSITIVE",
    "FALSE_POSITIVE",
    "RESOLVED",
}


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _load_store():
    if not STORE_PATH.exists():
        return []
    with STORE_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def _save_store(alerts):
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with STORE_PATH.open("w", encoding="utf-8") as file:
        json.dump(alerts, file, indent=4)


def initialize_db():
    if not STORE_PATH.exists():
        _save_store([])


def build_alert_id(alert):
    fingerprint = "|".join(
        [
            str(alert.get("type", "")),
            str(alert.get("ip", "")),
            str(alert.get("message", "")),
        ]
    )
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:16]


def _normalize_status(status):
    normalized = str(status or DEFAULT_STATUS).strip().upper()
    if normalized not in VALID_STATUSES:
        raise ValueError(f"Invalid alert status: {status}")
    return normalized


def _sort_alerts(alerts):
    order = {
        "NEW": 1,
        "INVESTIGATING": 2,
        "TRUE_POSITIVE": 3,
        "FALSE_POSITIVE": 4,
        "RESOLVED": 5,
    }
    return sorted(
        alerts,
        key=lambda alert: (order.get(alert.get("status", DEFAULT_STATUS), 99), alert.get("last_seen_at", "")),
        reverse=False,
    )[::-1]


def upsert_detected_alerts(alerts):
    initialize_db()
    stored_alerts = _load_store()
    indexed_alerts = {alert["alert_id"]: alert for alert in stored_alerts}
    now = _utc_now()
    current_alerts = []

    for alert in alerts:
        alert_id = build_alert_id(alert)
        existing = indexed_alerts.get(alert_id)

        if existing:
            existing["severity"] = alert.get("severity", existing.get("severity", "MEDIUM"))
            existing["message"] = alert.get("message", existing.get("message", ""))
            existing["source"] = alert.get("source", existing.get("source"))
            existing["updated_at"] = now
            existing["last_seen_at"] = now
            existing["occurrence_count"] = int(existing.get("occurrence_count", 0)) + 1
            current_alerts.append(existing)
            continue

        created = {
            "alert_id": alert_id,
            "type": alert.get("type", "Unknown"),
            "ip": alert.get("ip"),
            "severity": alert.get("severity", "MEDIUM"),
            "message": alert.get("message", ""),
            "source": alert.get("source"),
            "status": DEFAULT_STATUS,
            "assigned_to": "",
            "notes": [],
            "created_at": now,
            "updated_at": now,
            "last_seen_at": now,
            "occurrence_count": 1,
        }
        indexed_alerts[alert_id] = created
        current_alerts.append(created)

    _save_store(_sort_alerts(list(indexed_alerts.values())))
    return current_alerts


def list_alerts():
    initialize_db()
    return _sort_alerts(_load_store())


def update_alert(alert_id, *, status=None, assigned_to=None):
    initialize_db()
    alerts = _load_store()
    now = _utc_now()

    for alert in alerts:
        if alert["alert_id"] != alert_id:
            continue

        if status is not None:
            alert["status"] = _normalize_status(status)
        if assigned_to is not None:
            alert["assigned_to"] = str(assigned_to).strip()
        alert["updated_at"] = now
        _save_store(_sort_alerts(alerts))
        return alert

    raise KeyError(f"Alert not found: {alert_id}")


def append_alert_note(alert_id, note, author="Analyst"):
    initialize_db()
    note_text = str(note or "").strip()
    if not note_text:
        raise ValueError("Note cannot be empty")

    alerts = _load_store()
    for alert in alerts:
        if alert["alert_id"] != alert_id:
            continue

        alert.setdefault("notes", []).append(
            {
                "author": str(author or "Analyst").strip() or "Analyst",
                "note": note_text,
                "created_at": _utc_now(),
            }
        )
        alert["updated_at"] = _utc_now()
        _save_store(_sort_alerts(alerts))
        return alert

    raise KeyError(f"Alert not found: {alert_id}")
