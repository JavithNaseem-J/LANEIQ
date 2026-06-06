"""Page 4 — Exception Monitor."""
import streamlit as st

st.set_page_config(page_title="Exception Monitor", page_icon="⚠️", layout="wide")
st.title("⚠️ Exception Monitor")

result = st.session_state.get("last_result")
if not result:
    st.info("Submit a shipment brief on the **Submit Shipment** page first.")
    st.stop()

exceptions = result.get("exception_summaries", [])
count = result.get("exceptions_detected", 0)

if count == 0:
    st.success("✅ No exceptions detected for this shipment.")
else:
    st.error(f"🚨 {count} exception(s) detected and resolved.")

    for exc in exceptions:
        severity = "🔴 HIGH" if exc["delay_hours"] > 48 else "🟡 MEDIUM"
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            col1.markdown(f"**{exc['shipment_id']}** — {exc['exception_type'].replace('_', ' ').title()}")
            col2.markdown(f"**Delay:** {exc['delay_hours']}h")
            col3.markdown(f"**Re-routed:** {exc['original_mode']} → {exc['new_mode']}")
            col4.markdown(f"**Severity:** {severity}")
            st.caption(f"New cost: ${exc['new_cost']:,.2f}")

# Always show the raw list for transparency
with st.expander("Raw exception data"):
    st.json(exceptions)
