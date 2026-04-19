import json
from pathlib import Path
from datetime import datetime
from urllib.error import URLError
from urllib.request import urlopen

import pandas as pd
import streamlit as st


API_BASE_URL = "http://127.0.0.1:5000"
CONFIG_PATH = Path(__file__).resolve().parents[1] / "data" / "log_sources.json"


def fetch_json(endpoint):
    with urlopen(f"{API_BASE_URL}{endpoint}", timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def load_source_config():
    with CONFIG_PATH.open() as config_file:
        return json.load(config_file)


st.set_page_config(page_title="ThreatLens Dashboard", layout="wide")
st.title("ThreatLens Dashboard")
st.caption("Live view of ingested events and detections from configured file and Windows log sources.")

with st.sidebar:
    st.header("Live Mode")
    auto_refresh = st.toggle("Auto refresh", value=True)
    refresh_seconds = st.slider("Refresh every (seconds)", min_value=2, max_value=30, value=5)
    manual_refresh = st.button("Refresh now", use_container_width=True)

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

def render_live_data():
    try:
        alerts = fetch_json("/analyze")
        events = fetch_json("/events")
        api_online = True
    except URLError:
        alerts = []
        events = []
        api_online = False

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("API Status", "Online" if api_online else "Offline")
    metric_col2.metric("Alerts", len(alerts))
    metric_col3.metric("Normalized Events", len(events))
    metric_col4.metric("Enabled Sources", len(enabled_files) + len(enabled_windows))
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    alerts_df = pd.DataFrame(alerts)
    events_df = pd.DataFrame(events)

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
                for column in ["event", "ip", "source", "timestamp", "event_id", "provider", "level", "raw_message"]
                if column in events_df.columns
            ]
            st.dataframe(events_df[visible_columns], use_container_width=True)

    if not events_df.empty and "source" in events_df.columns:
        st.subheader("Events by Source")
        st.bar_chart(events_df["source"].value_counts())


if auto_refresh:
    @st.fragment(run_every=f"{refresh_seconds}s")
    def live_fragment():
        render_live_data()

    live_fragment()
else:
    render_live_data()

if manual_refresh:
    st.rerun()
