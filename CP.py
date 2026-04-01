import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- Page Config ---
st.set_page_config(page_title="Elite CP & W' Analytics", layout="wide")

# --- Custom CSS ---
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
CP, W_prime, r_squared = 0, 0, 0
valid_data = []

if input_mode == "Effort Based":
    raw_data = [{"d": 180, "p": p3, "l": "3m"}, {"d": 300, "p": p5, "l": "5m"}, 
                {"d": 720, "p": p12, "l": "12m"}, {"d": 900, "p": p15, "l": "15m"}]
    valid_data = sorted([d for d in raw_data if d["p"] > 0], key=lambda x: x["d"])
    
    if len(valid_data) >= 2:
        t_sec = np.array([d["d"] for d in valid_data])
        p_vals = np.array([d["p"] for d in valid_data])
        x_reg = 1/t_sec
        slope, intercept = np.polyfit(x_reg, p_vals, 1)
        W_prime, CP = slope, intercept
        r_squared = np.corrcoef(x_reg, p_vals)[0, 1]**2
else:
    CP, W_prime = m_cp, m_w * 1000

# --- Main App ---
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
    with c4: 
        # Using HTML <sub> for the 2 to avoid dollar signs
        vo2_label = "VO<sub>2</sub> Max"
        custom_metric(vo2_label, f"{vo2_rel:.1f}", "ml/kg/min")

    # --- Power-Duration Curve with Gradient & Data Points ---
    st.header("📊 Power-Duration Profile")
    t_curve = np.arange(20, 1501, 5)
    p_curve = (W_prime / t_curve) + CP
    fig = go.Figure()

    # Gradient Layers
    for i in range(1, 13):
        fig.add_trace(go.Scatter(x=t_curve, y=p_curve, fill='tozeroy', 
                                 fillcolor=f'rgba(0, 122, 204, {i*0.01})', 
                                 line=dict(color='rgba(0,0,0,0)'), showlegend=False, hoverinfo='skip'))

    fig.add_trace(go.Scatter(x=t_curve, y=p_curve, line=dict(color='#007ACC', width=4), name="Model Curve"))

    # RESTORED: Data Points
    if input_mode == "Effort Based":
        fig.add_trace(go.Scatter(
            x=[d["d"] for d in valid_data], 
            y=[d["p"] for d in valid_data],
            mode='markers', name="Efforts", 
            marker=dict(size=12, color='#1e293b', line=dict(width=2, color='white'))
        ))

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
        # FIXED: Removed dollar signs, used plain text
        custom_metric("Required Power", f"{p_req:.0f}", "W", f"Total W' used: {w_used_kj:.1f} kJ")

    # --- RESTORED: TTE & Linear Graph ---
    st.markdown("---")
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("⏱️ TTE Calculator")
        tte_p = st.number_input("Enter Target Power (W)", int(CP+5), 2000, int(CP+50))
        tte_sec = W_prime / (tte_p - CP)
        st.info(f"**Predicted Time to Exhaustion:** {int(tte_sec // 60)}m {int(tte_sec % 60)}s")

    with col_right:
        st.subheader("📈 Linear Regression")
        if input_mode == "Effort Based":
            fig_lin = go.Figure()
            xr = 1/np.array([d["d"] for d in valid_data])
            yr = [d["p"] for d in valid_data]
            fig_lin.add_trace(go.Scatter(x=xr, y=yr, mode='markers', name="Actual"))
            fig_lin.add_trace(go.Scatter(x=[0, max(xr)*1.1], y=[CP, W_prime*(max(xr)*1.1)+CP], mode='lines', name="Fit"))
            fig_lin.update_layout(template="plotly_white", xaxis_title="1/Time", yaxis_title="Power", height=300)
            st.plotly_chart(fig_lin, use_container_width=True)
            st.caption(f"Model Fit (R²): {r_squared:.4f}")
        else:
            st.write("Regression data is available in 'Effort Based' mode.")
