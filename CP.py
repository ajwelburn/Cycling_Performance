import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- Page Config ---
st.set_page_config(page_title="Elite CP & W' Analytics", layout="wide")

# --- Custom CSS for modern metric styling ---
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
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
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
    font-weight: 500;
}
</style>
""", unsafe_allow_html=True)

def custom_metric(label, value, unit, subtext=None):
    subtext_html = f'<div class="metric-subtext">{subtext}</div>' if subtext else ""
    html_str = f'''
    <div class="metric-container">
        <div class="metric-label">{label}</div>
        <div class="metric-value-container">
            <span class="metric-value">{value}</span>
            <span class="metric-unit">{unit}</span>
        </div>
        {subtext_html}
    </div>
    '''
    st.markdown(html_str, unsafe_allow_html=True)

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

# --- Calculation Logic ---
CP, W_prime, r_squared = 0, 0, 0
valid_data = []

if input_mode == "Effort Based":
    raw_data = [
        {"duration": 180, "power": p3, "label": "3-min"},
        {"duration": 300, "power": p5, "label": "5-min"},
        {"duration": 720, "power": p12, "label": "12-min"},
        {"duration": 900, "power": p15, "label": "15-min"}
    ]
    valid_data = sorted([d for d in raw_data if d["power"] > 0], key=lambda x: x["duration"])
    
    if len(valid_data) >= 2:
        t_sec = np.array([d["duration"] for d in valid_data])
        p_vals = np.array([d["power"] for d in valid_data])
        slope, intercept = np.polyfit(1/t_sec, p_vals, 1)
        W_prime, CP = slope, intercept
        r_squared = np.corrcoef(1/t_sec, p_vals)[0, 1]**2
else:
    CP, W_prime = m_cp, m_w * 1000
    r_squared = 1.0

# --- App Display ---
st.title("⚡ Multi-Point CP & W' Analytics")

if input_mode == "Effort Based" and len(valid_data) < 2:
    st.error("⚠️ Please enter power values for at least two different durations.")
else:
    # Derived Metrics
    lt1_est = (0.8572 * CP) - 30.45
    MAP = (W_prime / 220) + CP
    vo2_abs = (0.01095 * MAP) + 0.02388
    vo2_rel = (vo2_abs * 1000) / weight

    # Header Metrics
    st.header("📈 Core Metrics")
    col1, col2, col3, col4 = st.columns(4)
    with col1: custom_metric("Critical Power", f"{CP:.0f}", "W", f"{(CP/weight):.2f} W/kg")
    with col2: custom_metric("W' Capacity", f"{(W_prime/1000):.1f}", "kJ", f"{(W_prime/weight):.0f} J/kg")
    with col3: custom_metric("Est. LT1", f"{lt1_est:.0f}", "W", f"Range: {lt1_est*0.91:.0f}-{lt1_est*1.09:.0f} W")
    with col4: 
        fit_txt = f"Model R²: {r_squared:.4f}" if input_mode == "Effort Based" else "Fixed Input"
        custom_metric(r"$VO_2 \text{ Max}$", f"{vo2_rel:.1f}", "ml/kg/min", fit_txt)

    # Power Duration Curve with Gradient
    st.header("📊 Power-Duration Profile")
    t_curve = np.arange(20, 1201, 2)
    p_curve = (W_prime / t_curve) + CP

    fig_pd = go.Figure()

    # Create Gradient: Stack 15 layers with increasing opacity
    for i in range(1, 16):
        fig_pd.add_trace(go.Scatter(
            x=t_curve, y=p_curve, fill='tozeroy',
            fillcolor=f'rgba(0, 122, 204, {i*0.01})',
            line=dict(color='rgba(0,0,0,0)'), showlegend=False, hoverinfo='skip'
        ))

    fig_pd.add_trace(go.Scatter(x=t_curve, y=p_curve, name="Model Curve", line=dict(color='#007ACC', width=4)))
    
    if input_mode == "Effort Based":
        fig_pd.add_trace(go.Scatter(
            x=[d["duration"] for d in valid_data], y=[d["power"] for d in valid_data],
            mode='markers', name="Efforts", marker=dict(size=12, color='#1e293b', line=dict(width=2, color='white'))
        ))

    fig_pd.update_layout(template="simple_white", xaxis_title="Time (s)", yaxis_title="Power (W)", margin=dict(t=20))
    st.plotly_chart(fig_pd, use_container_width=True)

    # --- Feature: W' Planner ---
    st.markdown("---")
    st.header("🎯 W' Planner")
    c1, c2, c3 = st.columns([2, 2, 3])
    with c1:
        w_perc = st.slider("W' Depletion (%)", 1, 100, 80)
    with c2:
        target_min = st.number_input("Target Duration (min)", 0.5, 120.0, 10.0)
    with c3:
        w_used_kj = (w_perc / 100) * (W_prime / 1000)
        p_req = ((w_perc/100 * W_prime) / (target_min * 60)) + CP
        custom_metric(f"Required Power ({target_min}m)", f"{p_req:.0f}", "W", f"Total $W'$ used: {w_used_kj:.1f} kJ")

    # --- Original Features: TTE & Regression ---
    col_a, col_b = st.columns(2)
    with col_a:
        with st.expander("⏱️ Time to Exhaustion (TTE)"):
            tte_p = st.number_input("Enter Power (W)", int(CP+1), 2000, int(CP+50))
            tte_sec = W_prime / (tte_p - CP)
            st.subheader(f"TTE: {int(tte_sec // 60)}m {int(tte_sec % 60)}s")
    
    with col_b:
        with st.expander("📉 Linear Regression Model"):
            if input_mode == "Effort Based":
                fig_lin = go.Figure()
                xr = 1/np.array([d["duration"] for d in valid_data])
                fig_lin.add_trace(go.Scatter(x=xr, y=[d["power"] for d in valid_data], mode='markers', name="Data"))
                fig_lin.add_trace(go.Scatter(x=[0, max(xr)*1.1], y=[CP, W_prime*(max(xr)*1.1)+CP], mode='lines', name="Fit"))
                st.plotly_chart(fig_lin, use_container_width=True)
            else:
                st.write("Regression data is hidden in Manual Entry mode.")
