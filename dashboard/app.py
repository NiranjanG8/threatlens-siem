import json
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


def fetch_json(endpoint):
    with urlopen(f"{API_BASE_URL}{endpoint}", timeout=5) as response:
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


st.set_page_config(page_title="ThreatLens Dashboard", layout="wide")
st.title("ThreatLens Dashboard")
st.caption("Live view of ingested events and detections from configured file and Windows log sources.")

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

config = load_source_config()

enabled_files = [source["source"] for source in config["file_sources"] if source.get("enabled", True)]
enabled_windows = [source["name"] for source in config["windows_event_sources"] if source.get("enabled", True)]
source_col1, source_col2 = st.columns(2)
with source_col1:
    st.subheader("File Sources")
    st.write(enabled_files or ["No enabled file sources"])

with source_col2:
    st.subheader("Windows Event Logs")
    st.write(enabled_windows or ["No enabled Windows logs"])

header_col1, header_col2 = st.columns([6, 1])
with header_col2:
    manual_refresh = st.button("Refresh now", use_container_width=True, key="main_refresh")


def render_live_data():
    try:
        alerts = fetch_json("/analyze")
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
        events_df["message_preview"] = events_df.apply(build_event_overview, axis=1)
        events_df = events_df.drop(columns=["parsed_timestamp"])

    alerts_col, events_col = st.columns(2)

    with alerts_col:
        st.subheader("Alerts")
        if alerts_df.empty:
            st.info("No alerts returned by the API.")
        else:
            st.dataframe(alerts_df, use_container_width=True)
            st.bar_chart(alerts_df["severity"].value_counts())

    with events_col:
        st.subheader("Normalized Events")
        if events_df.empty:
            st.info("No normalized events available yet.")
        else:
            visible_columns = [
                column
                for column in [
                    "display_timestamp",
                    "event",
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
                events_df[visible_columns],
                use_container_width=True,
                key="events_table",
                on_select="rerun",
                selection_mode="single-row",
                hide_index=True,
                column_config={
                    "display_timestamp": "Timestamp",
                    "event": "Event",
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
                selected_event = events_df.iloc[selected_rows[0]].to_dict()
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

    if not events_df.empty and "source" in events_df.columns:
        st.subheader("Events by Source")
        st.bar_chart(events_df["source"].value_counts())

refresh_interval = f"{refresh_seconds}s" if auto_refresh else None


@st.fragment(run_every=refresh_interval)
def live_fragment():
    render_live_data()


live_fragment()

if manual_refresh:
    st.rerun()
