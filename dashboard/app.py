"""LANEIQ Streamlit Dashboard — main entry point."""
import streamlit as st

st.set_page_config(
    page_title="LANEIQ — Freight Routing",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)

from dashboard.utils.api_client import check_health  # noqa: E402

# Sidebar status
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/container-ship.png", width=64)
    st.title("LANEIQ")
    st.caption("AI Freight Routing · LangGraph + OR-Tools")
    st.divider()
    if check_health():
        st.success("API online", icon="✅")
    else:
        st.error("API offline", icon="🔴")

st.title("🚢 LANEIQ — Intelligent Freight Routing")
st.markdown(
    """
    **LANEIQ** uses a 4-node LangGraph agent pipeline to convert free-text shipment briefs
    into cost-optimised routing plans with real-time exception monitoring.

    **Navigate using the sidebar** to:
    - 📦 Submit a new shipment brief
    - 🗺️ View route maps
    - 📊 Compare routing costs
    - ⚠️ Monitor exceptions
    - 📈 View drift reports
    """
)
