"""Page 2 — Route Map."""
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="Route Map", page_icon="🗺️", layout="wide")
st.title("🗺️ Route Map")

PORT_COORDS = {
    "Chennai":      (13.0827, 80.2707),
    "NSICT Mumbai": (18.9548, 72.8352),
    "Jebel Ali":    (25.0130, 55.0555),
    "Abu Dhabi":    (24.4664, 54.3773),
    "Delhi ICD":    (28.5355, 77.3910),
}

result = st.session_state.get("last_result")
if not result:
    st.info("Submit a shipment brief on the **Submit Shipment** page first.")
    st.stop()

routes = result.get("all_options", [])
selected_strategy = result.get("selected_strategy", "")
selected = next((r for r in routes if r["strategy"] == selected_strategy), None)
if not selected:
    st.warning("No route data available.")
    st.stop()

# Extract origin/destination from task metadata (stored in session via result)
# Fall back to showing all port coordinates
lats, lons, labels = [], [], []
for port, (lat, lon) in PORT_COORDS.items():
    lats.append(lat)
    lons.append(lon)
    labels.append(port)

fig = go.Figure()

# Port markers
fig.add_trace(go.Scattermapbox(
    lat=lats, lon=lons,
    mode="markers+text",
    marker=dict(size=14, color="#00D2FF"),
    text=labels,
    textposition="top right",
    name="Ports",
))

fig.update_layout(
    mapbox=dict(style="open-street-map", zoom=3, center=dict(lat=20, lon=65)),
    margin=dict(l=0, r=0, t=0, b=0),
    height=500,
    paper_bgcolor="#0e1117",
    plot_bgcolor="#0e1117",
)

st.plotly_chart(fig, use_container_width=True)

col1, col2, col3 = st.columns(3)
col1.metric("Strategy", result["selected_strategy"])
col2.metric("Cost", f"${result['selected_cost_usd']:,.0f}")
col3.metric("Reduction", f"{result['cost_reduction_pct']:.1f}%")
