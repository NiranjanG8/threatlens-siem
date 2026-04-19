import streamlit as st
import json
import pandas as pd
from pathlib import Path

st.title("ThreatLens Dashboard")

alerts_path = Path(__file__).resolve().parents[1] / "reports" / "alerts.json"

with alerts_path.open() as f:
    alerts = json.load(f)

df = pd.DataFrame(alerts)
st.dataframe(df)

if not df.empty:
    st.bar_chart(df["severity"].value_counts())
