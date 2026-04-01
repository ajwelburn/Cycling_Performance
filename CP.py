import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- Page Config ---
st.set_page_config(page_title="Elite CP & W' Analytics", layout="wide")

# --- Refined CSS ---
st.markdown("""
<style>
.metric-container {
    display: flex;
    flex-direction: column;
    padding: 15px;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    margin-bottom: 10px;
    background-color: #ffffff;
}
.metric-label {
    font-size: 0.85rem;
    font-weight: 600;
    color: #64748b;
    margin-bottom: 4px;
    text-transform: uppercase;
}
.metric-value-container {
    display: flex;
    align-items: baseline;
}
.metric-value {
    font-size: 1.8rem;
    font-weight: 800;
    color: #1e293b;
}
.metric-unit {
    font-size: 1rem;
    margin-left: 0.3rem;
    color: #94a3b8;
}
.metric-subtext {
    font-size: 0.85rem;
    color: #3b82f6;
    margin-top: 5px;
}
</style>
""", unsafe_allow_html=True)

def custom_metric(label, value, unit, subtext=None):
    subtext_html = f'<div class="metric-subtext">{subtext}</div>' if subtext else ""
    st.markdown(f'''
    <div class="metric-container">
        <div class="metric-label">{label}</div>
        <div class="metric-value-container">
            <span class="metric-value">{value}</span>
            <span class="metric-unit">{unit}</span>
        </div>
        {subtext_html}
    </div>
    ''', unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.header("⚡ User Inputs")
    input_mode = st.radio("Calculation Mode", ["Effort Based", "Manual Entry"])
    
    if input_mode == "Effort Based":
        p3 = st.number_input("3-Minute Power (W)", 0, 2000, 350)
        p5 = st.number_input("5-Minute Power (W)", 0, 2000, 0)
        p12 = st.number_input("12-Minute Power (W)", 0, 2000, 300)
        p15 = st.number_input("15-Minute Power (W)", 0, 2000, 0)
    else:
        m_cp = st.number_input("Known CP (W)", 50, 600, 250)
        m_w = st.number_input("Known W' (kJ)", 1.0, 50.0, 15.0)

    weight = st.number_input("Weight (kg)", 30.0, 200.0, 70.0)

# --- Logic ---
CP, W_prime = 0, 0
valid_data = []

if input_mode == "Effort Based":
    raw_data = [{"d": 180, "p": p3, "l": "3m"}, {"d": 300, "p": p5, "l": "5m"}, 
                {"d": 720, "p": p12, "l": "12m"}, {"d": 900, "p": p15, "l": "15m"}]
    valid_data = sorted([d for d in raw_data if d["p"] > 0], key=lambda x: x["d"])
    
    if len(valid_data) >= 2:
        t_sec = np.array([d["d"] for d in valid_data])
        p_vals = np.array([d["p"] for d in valid_data])
        slope, intercept = np.polyfit(1/t_sec, p_vals, 1)
        W_prime, CP = slope, intercept
else:
    CP, W_prime = m_cp, m_w * 1000

# --- Display ---
if input_mode == "Effort Based" and len(valid_data) < 2:
    st.info("Please enter at least two power values.")
else:
    lt1 = (0.8572 * CP) - 30.45
    map_val = (W_prime / 220) + CP
    vo2_rel = (((0.01095 * map_val) + 0.02388) * 1000) / weight

    st.header("📈 Core Metrics")
    c1, c2, c3, c4 = st.columns(4)
    with c1: custom_metric("Critical Power", f"{CP:.0f}", "W", f"{(CP/weight):.2f} W/kg")
    with c2: custom_metric("W' Capacity", f"{(W_prime/1000):.1f}", "kJ", f"{(W_prime/weight):.0f} J/kg")
    with c3: custom_metric("Est. LT1", f"{lt1:.0f}", "W", f"Range: {lt1*0.91:.0f}-{lt1*1.09:.0f} W")
    with c4: custom_metric(r"$VO_2 \text{ Max}$", f"{vo2_rel:.1f}", "ml/kg/min")

    # Gradient Chart
    st.header("📊 Power-Duration Profile")
    t_curve = np.arange(20, 1201, 2)
    p_curve = (W_prime / t_curve) + CP
    fig = go.Figure()

    # Opacity Layers
    for i in range(1, 12):
        fig.add_trace(go.Scatter(x=t_curve, y=p_curve, fill='tozeroy', 
                                 fillcolor=f'rgba(0, 122, 204, {i*0.01})', 
                                 line=dict(color='rgba(0,0,0,0)'), showlegend=False))

    fig.add_trace(go.Scatter(x=t_curve, y=p_curve, line=dict(color='#007ACC', width=4), name="Curve"))
    fig.update_layout(template="simple_white", xaxis_title="Time (s)", yaxis_title="Power (W)")
    st.plotly_chart(fig, use_container_width=True)

    # --- W' Planner ---
    st.markdown("---")
    st.header("🎯 W' Planner")
    p1, p2, p3 = st.columns([2, 2, 3])
    with p1: w_perc = st.slider("W' Depletion (%)", 1, 100, 80)
    with p2: target_min = st.number_input("Target Duration (min)", 0.5, 120.0, 10.0)
    with p3:
        w_used_kj = (w_perc / 100) * (W_prime / 1000)
        p_req = ((w_perc/100 * W_prime) / (target_min * 60)) + CP
        # Subtext formatted exactly as requested
        custom_metric("Required Power", f"{p_req:.0f}", "W", f"Total $W'$ used: {w_used_kj:.1f} kJ")

    # --- Other Original Features ---
    with st.expander("Additional Tools (TTE & Regression)"):
        ta, tb = st.columns(2)
        with ta:
            tte_p = st.number_input("Calculate TTE for Power (W)", int(CP+1), 2000, int(CP+50))
            tte_s = W_prime / (tte_p - CP)
            st.write(f"**Predicted TTE:** {int(tte_s // 60)}m {int(tte_s % 60)}s")
        with tb:
            if input_mode == "Effort Based":
                st.write("**Model Accuracy:** Linear Regression of Power vs 1/t")
