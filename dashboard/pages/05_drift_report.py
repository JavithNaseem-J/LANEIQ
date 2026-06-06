"""Page 5 — Drift Report."""
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Drift Report", page_icon="📈", layout="wide")
st.title("📈 Feature Drift Report")
st.caption("Evidently AI report — shipment feature distribution vs reference dataset.")

REPORT_PATH = Path("data/processed/drift_report.html")

if REPORT_PATH.exists():
    html = REPORT_PATH.read_text(encoding="utf-8")
    components.html(html, height=800, scrolling=True)
else:
    st.info(
        "No drift report found yet. Run the DVC monitor stage to generate it:\n\n"
        "```bash\ndvc repro pipelines/dvc.yaml:monitor\n```"
    )
    st.markdown(
        """
        ### What this page will show
        - **Data Drift Preset** — detects shifts in cargo weight, distance, mode distribution
        - **Data Quality Preset** — missing values, type errors, outliers
        - **Drift threshold** — alert when >30% of features show statistically significant drift
        """
    )
