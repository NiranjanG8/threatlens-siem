import streamlit as st
import json
import pandas as pd

st.title("ThreatLens Dashboard")

with open("../reports/alerts.json") as f:
    alerts = json.load(f)

df = pd.DataFrame(alerts)
st.dataframe(df)

if not df.empty:
    st.bar_chart(df["severity"].value_counts())
