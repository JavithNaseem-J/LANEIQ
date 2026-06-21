"""Page 1 — Submit Shipment Brief."""

import streamlit as st

from dashboard.utils.api_client import poll_status, submit_optimization

st.set_page_config(page_title="Submit Shipment", page_icon="📦", layout="wide")
st.title("📦 Submit Shipment Brief")
st.caption("Describe your shipment in plain English — the agent will extract and optimise it.")

EXAMPLES = [
    "Ship 500 kg of electronics from Chennai to Jebel Ali by June 20, 2026. Prefer air freight.",
    "Move 2000 kg of textiles from NSICT Mumbai to Abu Dhabi by July 5, 2026. Sea freight.",
    "Urgent: 150 kg of perishables from Delhi ICD to Jebel Ali, must arrive by June 15, 2026.",
]

with st.expander("💡 Example briefs"):
    for ex in EXAMPLES:
        if st.button(ex[:60] + "…", key=ex):
            st.session_state["brief_input"] = ex

brief = st.text_area(
    "Shipment Brief",
    value=st.session_state.get("brief_input", ""),
    height=120,
    max_chars=500,
    placeholder="e.g. Ship 500 kg of electronics from Chennai to Jebel Ali by June 20, 2026…",
)
char_count = len(brief)
st.caption(f"{char_count}/500 characters")

if st.button("🚀 Optimise Route", type="primary", disabled=(char_count < 10)):
    with st.spinner("Submitting to agent pipeline…"):
        try:
            task_id = submit_optimization(brief)
            st.info(f"Task queued: `{task_id}`")
            st.session_state["last_task_id"] = task_id
        except Exception as e:
            st.error(f"Submission failed: {e}")
            st.stop()

    with st.spinner("Running Planner → Route → Exception → Report…"):
        try:
            data = poll_status(task_id)
        except TimeoutError:
            st.error("Timed out waiting for result. Check /status endpoint.")
            st.stop()

    if data["state"] == "success":
        result = data["result"]
        st.session_state["last_result"] = result
        st.success("Optimisation complete!")

        col1, col2, col3 = st.columns(3)
        col1.metric("Strategy", result.get("selected_strategy", "—"))
        col2.metric("Total Cost", f"${result.get('selected_cost_usd', 0):,.0f}")
        col3.metric("Cost Reduction", f"{result.get('cost_reduction_pct', 0):.1f}%")

        if result.get("exceptions_detected", 0) > 0:
            st.warning(f"⚠️ {result['exceptions_detected']} exception(s) detected — see Exception Monitor page.")

        with st.expander("📄 Full Report"):
            st.markdown(result.get("final_report", "No report generated."))

        with st.expander("🔍 Raw JSON"):
            st.json(result)
    else:
        st.error(f"Pipeline error: {data['result']}")
