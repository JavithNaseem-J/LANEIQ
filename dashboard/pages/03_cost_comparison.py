"""Page 3 — Cost Comparison."""
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="Cost Comparison", page_icon="📊", layout="wide")
st.title("📊 Cost Comparison")

result = st.session_state.get("last_result")
if not result:
    st.info("Submit a shipment brief on the **Submit Shipment** page first.")
    st.stop()

options = result.get("all_options", [])
if not options:
    st.warning("No route options in result.")
    st.stop()

strategies = [o["strategy"] for o in options]
costs = [o["total_cost"] for o in options]
selected = result["selected_strategy"]
colors = ["#00D2FF" if s == selected else "#444" for s in strategies]

# Bar chart
fig = go.Figure(go.Bar(
    x=strategies,
    y=costs,
    marker_color=colors,
    text=[f"${c:,.0f}" for c in costs],
    textposition="outside",
))
fig.update_layout(
    title="Strategy Cost Comparison (USD)",
    yaxis_title="Total Cost (USD)",
    paper_bgcolor="#0e1117",
    plot_bgcolor="#0e1117",
    font_color="#ffffff",
    height=400,
)
st.plotly_chart(fig, use_container_width=True)

# Metric cards
col1, col2, col3 = st.columns(3)
baseline = next((o["total_cost"] for o in options if "baseline" in o["strategy"]), 0)
vrp = next((o["total_cost"] for o in options if "vrp" in o["strategy"]), 0)
saving = baseline - result["selected_cost_usd"]

col1.metric("Greedy Baseline", f"${baseline:,.0f}")
col2.metric("Selected Cost", f"${result['selected_cost_usd']:,.0f}", delta=f"-${saving:,.0f}")
col3.metric("Cost Reduction", f"{result['cost_reduction_pct']:.1f}%")
