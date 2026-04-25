from flask import Flask, jsonify, request

from alert_store import append_alert_note, list_alerts, update_alert, upsert_detected_alerts
from detection_pipeline import collect_events_and_alerts

app = Flask(__name__)

@app.route("/analyze")
def analyze():
    _, detected_alerts = collect_events_and_alerts()
    return jsonify(upsert_detected_alerts(detected_alerts))


@app.route("/alerts")
def alerts():
    return jsonify(list_alerts())


@app.route("/alerts/<alert_id>", methods=["PATCH"])
def patch_alert(alert_id):
    payload = request.get_json(silent=True) or {}
    try:
        alert = update_alert(
            alert_id,
            status=payload.get("status"),
            assigned_to=payload.get("assigned_to"),
        )
    except KeyError:
        return jsonify({"error": "Alert not found"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(alert)


@app.route("/alerts/<alert_id>/notes", methods=["POST"])
def add_alert_note(alert_id):
    payload = request.get_json(silent=True) or {}
    try:
        alert = append_alert_note(
            alert_id,
            payload.get("note"),
            author=payload.get("author", "Analyst"),
        )
    except KeyError:
        return jsonify({"error": "Alert not found"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(alert), 201

@app.route("/events")
def events():
    normalized_logs, _ = collect_events_and_alerts()
    return jsonify(normalized_logs)

@app.route("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    app.run()
