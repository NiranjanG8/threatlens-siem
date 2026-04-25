import json
import urllib.error
import urllib.request
from pathlib import Path
from datetime import datetime, timedelta
import re
from zoneinfo import ZoneInfo
from urllib.error import URLError
from urllib.request import urlopen

import pandas as pd
import streamlit as st


API_BASE_URL = "http://127.0.0.1:5000"
CONFIG_PATH = Path(__file__).resolve().parents[1] / "data" / "log_sources.json"
WINDOWS_DATE_PATTERN = re.compile(r"/Date\((\d+)\)/")
LOCAL_TIMEZONE = ZoneInfo("Asia/Kolkata")
EVENT_COLOR_MAP = {
    "failed_login": "#ef4444",
    "success_login": "#22c55e",
    "access_denied": "#f97316",
    "defender_event": "#06b6d4",
    "service_event": "#8b5cf6",
    "powershell_event": "#eab308",
    "system_error": "#dc2626",
    "system_warning": "#f59e0b",
    "system_event": "#64748b",
    "Other": "#94a3b8",
    "Unknown": "#94a3b8",
}
EVENT_BADGE_MAP = {
    "failed_login": "🔴",
    "success_login": "🟢",
    "access_denied": "🟠",
    "defender_event": "🔵",
    "service_event": "🟣",
    "powershell_event": "🟡",
    "system_error": "🔺",
    "system_warning": "🟨",
    "system_event": "⚪",
    "Unknown": "⚫",
}
EVENT_LABEL_MAP = {
    "failed_login": "Failed Login",
    "success_login": "Success Login",
    "access_denied": "Access Denied",
    "defender_event": "Defender Event",
    "service_event": "Service Event",
    "powershell_event": "PowerShell Event",
    "system_error": "System Error",
    "system_warning": "System Warning",
    "system_event": "System Event",
    "Other": "Other",
    "Unknown": "Unknown",
}


def fetch_json(endpoint):
    with urlopen(f"{API_BASE_URL}{endpoint}", timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def send_json_request(endpoint, method, payload):
    request = urllib.request.Request(
        f"{API_BASE_URL}{endpoint}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def load_source_config():
    with CONFIG_PATH.open() as config_file:
        return json.load(config_file)


def parse_event_timestamp(value):
    if not value:
        return pd.NaT
    if isinstance(value, str):
        match = WINDOWS_DATE_PATTERN.search(value)
        if match:
            return pd.to_datetime(int(match.group(1)), unit="ms", utc=True).tz_convert(LOCAL_TIMEZONE)
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        return pd.NaT
    return parsed.tz_convert(LOCAL_TIMEZONE)


def format_event_timestamp(value):
    parsed = parse_event_timestamp(value)
    if pd.isna(parsed):
        return "N/A"
    return parsed.strftime("%Y-%m-%d %H:%M:%S %Z")


def build_event_overview(event):
    message = (event.get("raw_message") or "").strip()
    if len(message) > 90:
        message = f"{message[:87]}..."
    return message or "No message"


def format_status_label(status):
    return str(status or "NEW").replace("_", " ").title()


def format_notes_preview(notes):
    if not notes:
        return "No notes"
    latest = notes[-1]
    note_text = latest.get("note", "").strip()
    if len(note_text) > 52:
        note_text = f"{note_text[:49]}..."
    return note_text or "No notes"


def get_date_range_from_preset(preset, now_local):
    today = now_local.date()

    if preset == "All available":
        return None, None
    if preset == "Last 7 days":
        return today - timedelta(days=7), today
    if preset == "Last 30 days":
        return today - timedelta(days=30), today
    if preset == "Last 3 months":
        return today - timedelta(days=90), today
    if preset == "Last year":
        return today - timedelta(days=365), today
    if preset == "This year":
        return today.replace(month=1, day=1), today
    if preset == "Jan to Mar":
        return today.replace(month=1, day=1), today.replace(month=3, day=31)
    return None, None


def apply_time_filter(events_df, preset, start_date, end_date):
    if events_df.empty or "parsed_timestamp" not in events_df.columns:
        return events_df

    filtered_df = events_df.copy()

    if preset != "Custom range":
        start_date, end_date = get_date_range_from_preset(preset, datetime.now(LOCAL_TIMEZONE))

    if start_date:
        filtered_df = filtered_df[
            filtered_df["parsed_timestamp"].isna()
            | (filtered_df["parsed_timestamp"].dt.date >= start_date)
        ]

    if end_date:
        filtered_df = filtered_df[
            filtered_df["parsed_timestamp"].isna()
            | (filtered_df["parsed_timestamp"].dt.date <= end_date)
        ]

    return filtered_df


def build_count_chart_data(series, label):
    counts = series.fillna("Unknown").astype(str).value_counts().reset_index()
    counts.columns = [label, "count"]
    return counts


def get_event_color_scale():
    domain = list(EVENT_COLOR_MAP.keys())
    return {"domain": domain, "range": [EVENT_COLOR_MAP[key] for key in domain]}


def format_event_label(event_name):
    normalized = str(event_name or "Unknown")
    return EVENT_LABEL_MAP.get(normalized, normalized.replace("_", " ").title())


def build_event_badge(event_name):
    normalized = str(event_name or "Unknown")
    badge = EVENT_BADGE_MAP.get(normalized, EVENT_BADGE_MAP["Unknown"])
    return f"{badge} {format_event_label(normalized)}"


def build_event_chart_data(series, top_n=6):
    event_counts = build_count_chart_data(series, "event")
    if event_counts.empty:
        return event_counts

    if len(event_counts) > top_n:
        top_events = event_counts.head(top_n).copy()
        other_count = event_counts.iloc[top_n:]["count"].sum()
        if other_count > 0:
            top_events = pd.concat(
                [top_events, pd.DataFrame([{"event": "Other", "count": other_count}])],
                ignore_index=True,
            )
        event_counts = top_events

    event_counts["event_label"] = event_counts["event"].apply(format_event_label)
    return event_counts


def render_donut_chart(data, category_field, title):
    if data.empty:
        st.info(f"No {title.lower()} available.")
        return

    display_field = category_field
    color_encoding = {
        "field": category_field,
        "type": "nominal",
        "legend": {"title": title, "orient": "bottom", "direction": "horizontal"},
    }
    if category_field == "event":
        color_encoding["scale"] = get_event_color_scale()
        color_encoding["field"] = "event_label"
        display_field = "event_label"

    chart_spec = {
        "height": 320,
        "mark": {"type": "arc", "innerRadius": 82, "outerRadius": 128},
        "encoding": {
            "theta": {"field": "count", "type": "quantitative"},
            "color": color_encoding,
            "tooltip": [
                {"field": display_field, "type": "nominal", "title": title},
                {"field": "count", "type": "quantitative", "title": "Count"},
            ],
        },
    }
    st.vega_lite_chart(data, chart_spec, use_container_width=True)


def render_event_type_chart(data):
    if data.empty:
        st.info("No event types available yet.")
        return

    chart_spec = {
        "height": 320,
        "mark": {"type": "bar", "cornerRadiusEnd": 6},
        "encoding": {
            "y": {
                "field": "event_label",
                "type": "nominal",
                "sort": "-x",
                "title": None,
                "axis": {"labelLimit": 180},
            },
            "x": {"field": "count", "type": "quantitative", "title": "Events"},
            "color": {
                "field": "event",
                "type": "nominal",
                "scale": get_event_color_scale(),
                "legend": None,
            },
            "tooltip": [
                {"field": "event_label", "type": "nominal", "title": "Event Type"},
                {"field": "count", "type": "quantitative", "title": "Count"},
            ],
        },
    }
    st.vega_lite_chart(data, chart_spec, use_container_width=True)


def render_timeline_chart(events_df):
    timeline_df = events_df.dropna(subset=["parsed_timestamp"]).copy()
    if timeline_df.empty:
        st.info("No timestamped events available for a timeline yet.")
        return

    span = timeline_df["parsed_timestamp"].max() - timeline_df["parsed_timestamp"].min()
    bucket = "h" if pd.isna(span) or span <= timedelta(days=3) else "D"
    bucket_label = "hour" if bucket == "h" else "day"

    timeline_df["time_bucket"] = timeline_df["parsed_timestamp"].dt.floor(bucket)
    timeline_counts = (
        timeline_df.groupby("time_bucket")
        .size()
        .rename("events")
        .reset_index()
        .sort_values("time_bucket")
        .set_index("time_bucket")
    )

    st.line_chart(timeline_counts, height=280, use_container_width=True)
    st.caption(f"Event volume grouped by {bucket_label}.")


def render_top_ip_chart(events_df):
    if "ip" not in events_df.columns:
        st.info("No IP data available yet.")
        return

    ip_counts = build_count_chart_data(events_df["ip"], "ip")
    ip_counts = ip_counts[ip_counts["ip"] != "None"].head(8).set_index("ip")
    if ip_counts.empty:
        st.info("No IP-based activity to visualize yet.")
        return

    st.bar_chart(ip_counts, height=280, use_container_width=True)


def render_source_heatmap(events_df):
    if "source" not in events_df.columns or "event" not in events_df.columns:
        st.info("Not enough event metadata for a source heatmap yet.")
        return

    heatmap_df = (
        events_df.assign(
            source=events_df["source"].fillna("Unknown").astype(str),
            event=events_df["event"].fillna("Unknown").astype(str),
        )
        .groupby(["source", "event"])
        .size()
        .rename("count")
        .reset_index()
        .sort_values("count", ascending=False)
        .head(25)
    )

    if heatmap_df.empty:
        st.info("No source and event combinations to visualize yet.")
        return

    chart_spec = {
        "mark": "rect",
        "encoding": {
            "x": {"field": "event", "type": "nominal", "title": "Event Type"},
            "y": {"field": "source", "type": "nominal", "title": "Source"},
            "color": {
                "field": "count",
                "type": "quantitative",
                "title": "Events",
                "scale": {"scheme": "teals"},
            },
            "tooltip": [
                {"field": "source", "type": "nominal", "title": "Source"},
                {"field": "event", "type": "nominal", "title": "Event"},
                {"field": "count", "type": "quantitative", "title": "Count"},
            ],
        },
    }
    st.vega_lite_chart(heatmap_df, chart_spec, use_container_width=True)


st.set_page_config(page_title="ThreatLens Dashboard", layout="wide")
st.title("ThreatLens Dashboard")
st.caption("Live view of ingested events and detections from configured file and Windows log sources.")

config = load_source_config()
enabled_files = [source["source"] for source in config["file_sources"] if source.get("enabled", True)]
enabled_windows = [source["name"] for source in config["windows_event_sources"] if source.get("enabled", True)]

with st.sidebar:
    st.header("Live Mode")
    auto_refresh = st.toggle("Auto refresh", value=True)
    refresh_seconds = st.slider("Refresh every (seconds)", min_value=2, max_value=30, value=5)

st.subheader("Time Filter")
filter_col1, filter_col2, filter_col3 = st.columns([2, 1, 1])
with filter_col1:
    time_preset = st.selectbox(
        "Range",
        [
            "All available",
            "Last 7 days",
            "Last 30 days",
            "Last 3 months",
            "Last year",
            "This year",
            "Jan to Mar",
            "Custom range",
        ],
        index=0,
    )
with filter_col2:
    start_date = st.date_input("Start date", value=None, disabled=time_preset != "Custom range")
with filter_col3:
    end_date = st.date_input("End date", value=None, disabled=time_preset != "Custom range")

source_col1, source_col2 = st.columns(2)
with source_col1:
    st.subheader("File Sources")
    st.write(enabled_files or ["No enabled file sources"])

with source_col2:
    st.subheader("Windows Event Logs")
    st.write(enabled_windows or ["No enabled Windows logs"])

header_col1, header_col2 = st.columns([6, 1])
with header_col2:
    manual_refresh = st.button("Refresh now", width="stretch", key="main_refresh")


def render_live_data():
    try:
        fetch_json("/analyze")
        alerts = fetch_json("/alerts")
        events = fetch_json("/events")
        api_online = True
    except URLError:
        alerts = []
        events = []
        api_online = False

    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if time_preset == "Custom range":
        st.caption(f"Showing events from {start_date or 'beginning'} to {end_date or 'today'}")
    else:
        st.caption(f"Showing: {time_preset}")

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("API Status", "Online" if api_online else "Offline")
    metric_col2.metric("Alerts", len(alerts))
    metric_col3.metric("Normalized Events", len(events))
    metric_col4.metric("Enabled Sources", len(enabled_files) + len(enabled_windows))

    alerts_df = pd.DataFrame(alerts)
    events_df = pd.DataFrame(events)
    if not alerts_df.empty and "timestamp" in alerts_df.columns:
        alerts_df["_sort_timestamp"] = alerts_df["timestamp"].apply(parse_event_timestamp)
        alerts_df = alerts_df.sort_values("_sort_timestamp", ascending=False, na_position="last").drop(
            columns=["_sort_timestamp"]
        )
    if not alerts_df.empty:
        alerts_df["status_label"] = alerts_df["status"].apply(format_status_label)
        alerts_df["notes_preview"] = alerts_df["notes"].apply(format_notes_preview)
        alerts_df["assigned_display"] = alerts_df["assigned_to"].replace("", "Unassigned")
    if not events_df.empty:
        if "timestamp" in events_df.columns:
            events_df["parsed_timestamp"] = events_df["timestamp"].apply(parse_event_timestamp)
        else:
            events_df["parsed_timestamp"] = pd.NaT
        events_df = apply_time_filter(events_df, time_preset, start_date, end_date)
        events_df = events_df.sort_values("parsed_timestamp", ascending=False, na_position="last")
        events_df["display_timestamp"] = events_df["timestamp"].apply(format_event_timestamp)
        events_df["display_event_id"] = events_df["event_id"].apply(
            lambda value: str(int(value)) if pd.notna(value) else "N/A"
        )
        events_df["event_badge"] = events_df["event"].apply(build_event_badge)
        events_df["message_preview"] = events_df.apply(build_event_overview, axis=1)

    alerts_col, events_col = st.columns(2)

    with alerts_col:
        st.subheader("Alerts")
        if alerts_df.empty:
            st.info("No alerts returned by the API.")
        else:
            alert_columns = [
                column
                for column in [
                    "type",
                    "severity",
                    "status_label",
                    "assigned_display",
                    "ip",
                    "occurrence_count",
                    "last_seen_at",
                    "notes_preview",
                ]
                if column in alerts_df.columns
            ]
            alert_selection = st.dataframe(
                alerts_df[alert_columns],
                width="stretch",
                hide_index=True,
                key="alerts_table",
                on_select="rerun",
                selection_mode="single-row",
                column_config={
                    "type": "Type",
                    "severity": "Severity",
                    "status_label": "Status",
                    "assigned_display": "Assigned To",
                    "ip": "IP",
                    "occurrence_count": "Count",
                    "last_seen_at": "Last Seen",
                    "notes_preview": "Latest Note",
                },
            )

            selected_alert_rows = alert_selection.selection.rows
            if selected_alert_rows:
                selected_alert = alerts_df.iloc[selected_alert_rows[0]].to_dict()
                st.markdown("### Alert Triage")

                triage_col1, triage_col2 = st.columns(2)
                with triage_col1:
                    new_status = st.selectbox(
                        "Status",
                        ["NEW", "INVESTIGATING", "TRUE_POSITIVE", "FALSE_POSITIVE", "RESOLVED"],
                        index=["NEW", "INVESTIGATING", "TRUE_POSITIVE", "FALSE_POSITIVE", "RESOLVED"].index(
                            selected_alert.get("status", "NEW")
                        ),
                        key=f"status_{selected_alert['alert_id']}",
                    )
                with triage_col2:
                    assigned_to = st.text_input(
                        "Assigned To",
                        value=selected_alert.get("assigned_to", ""),
                        key=f"assigned_{selected_alert['alert_id']}",
                    )

                update_clicked = st.button(
                    "Update Alert",
                    key=f"update_{selected_alert['alert_id']}",
                    width="stretch",
                )
                if update_clicked:
                    try:
                        send_json_request(
                            f"/alerts/{selected_alert['alert_id']}",
                            "PATCH",
                            {"status": new_status, "assigned_to": assigned_to},
                        )
                        st.success("Alert updated.")
                        st.rerun()
                    except urllib.error.URLError:
                        st.error("Unable to update alert right now.")

                note_text = st.text_area(
                    "Add Investigation Note",
                    key=f"note_{selected_alert['alert_id']}",
                    height=100,
                    placeholder="Document triage steps, findings, and next actions...",
                )
                add_note_clicked = st.button(
                    "Add Note",
                    key=f"add_note_{selected_alert['alert_id']}",
                    width="stretch",
                )
                if add_note_clicked:
                    try:
                        send_json_request(
                            f"/alerts/{selected_alert['alert_id']}/notes",
                            "POST",
                            {"note": note_text, "author": assigned_to or "Analyst"},
                        )
                        st.success("Note added.")
                        st.rerun()
                    except urllib.error.URLError:
                        st.error("Unable to add note right now.")

                st.caption(
                    f"Created: {selected_alert.get('created_at', 'N/A')} | Last seen: {selected_alert.get('last_seen_at', 'N/A')}"
                )
                if selected_alert.get("notes"):
                    with st.expander("Investigation Notes", expanded=True):
                        for note in reversed(selected_alert["notes"]):
                            st.markdown(
                                f"**{note.get('author', 'Analyst')}** · {note.get('created_at', '')}"
                            )
                            st.write(note.get("note", ""))
                else:
                    st.caption("No investigation notes yet.")

    with events_col:
        st.subheader("Normalized Events")
        if events_df.empty:
            st.info("No normalized events available yet.")
        else:
            table_df = events_df.drop(columns=["parsed_timestamp"], errors="ignore")
            visible_columns = [
                column
                for column in [
                    "display_timestamp",
                    "event_badge",
                    "display_event_id",
                    "source",
                    "host",
                    "ip",
                    "level",
                    "provider",
                    "message_preview",
                ]
                if column in events_df.columns
            ]
            event_selection = st.dataframe(
                table_df[visible_columns],
                width="stretch",
                key="events_table",
                on_select="rerun",
                selection_mode="single-row",
                hide_index=True,
                column_config={
                    "display_timestamp": "Timestamp",
                    "event_badge": "Event",
                    "display_event_id": "Event ID",
                    "source": "Source",
                    "host": "Host",
                    "ip": "IP",
                    "level": "Level",
                    "provider": "Provider",
                    "message_preview": "Message",
                },
            )

            selected_rows = event_selection.selection.rows
            if selected_rows:
                selected_event = table_df.iloc[selected_rows[0]].to_dict()
                st.markdown("### Event Details")

                detail_col1, detail_col2 = st.columns(2)
                with detail_col1:
                    st.write(f"**Event Type:** {selected_event.get('event', 'N/A')}")
                    st.write(f"**IP Address:** {selected_event.get('ip') or 'N/A'}")
                    st.write(f"**Host:** {selected_event.get('host') or 'N/A'}")
                    st.write(f"**Source:** {selected_event.get('source', 'N/A')}")
                    st.write(f"**Timestamp:** {selected_event.get('display_timestamp') or 'N/A'}")

                with detail_col2:
                    st.write(f"**Event ID:** {selected_event.get('display_event_id') or 'N/A'}")
                    st.write(f"**Provider:** {selected_event.get('provider') or 'N/A'}")
                    st.write(f"**Level:** {selected_event.get('level') or 'N/A'}")

                st.text_area(
                    "Raw Message",
                    value=selected_event.get("raw_message", ""),
                    height=140,
                    disabled=True,
                )
                with st.expander("Full Event Record"):
                    st.json(selected_event)
            else:
                st.caption("Click an event row to inspect full details.")

    analytics_col1, analytics_col2 = st.columns(2)
    with analytics_col1:
        st.subheader("Alert Severity Mix")
        render_donut_chart(
            build_count_chart_data(alerts_df.get("severity", pd.Series(dtype=str)), "severity"),
            "severity",
            "Severity",
        )

    with analytics_col2:
        st.subheader("Event Type Mix")
        if events_df.empty:
            st.info("No event types available yet.")
        else:
            render_event_type_chart(build_event_chart_data(events_df["event"]))

    st.subheader("Activity Timeline")
    render_timeline_chart(events_df)

    intel_col1, intel_col2 = st.columns(2)
    with intel_col1:
        st.subheader("Top Active IPs")
        render_top_ip_chart(events_df)

    with intel_col2:
        st.subheader("Event Volume by Source")
        if not events_df.empty and "source" in events_df.columns:
            source_counts = build_count_chart_data(events_df["source"], "source").set_index("source")
            st.bar_chart(source_counts, height=280, use_container_width=True)
        else:
            st.info("No source activity available yet.")

    st.subheader("Source vs Event Heatmap")
    render_source_heatmap(events_df)

refresh_interval = f"{refresh_seconds}s" if auto_refresh else None


@st.fragment(run_every=refresh_interval)
def live_fragment():
    render_live_data()


live_fragment()

if manual_refresh:
    st.rerun()
