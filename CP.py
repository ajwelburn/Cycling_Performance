import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- Page Config ---
st.set_page_config(page_title="Pro Cycling Analytics", layout="wide")

# --- Modern UI Styling ---
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    .metric-container {
        display: flex;
        flex-direction: column;
        padding: 1.5rem;
        border-radius: 12px;
        background-color: white;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
    }
    .metric-label { font-size: 0.8rem; font-weight: 700; color: #64748b; text-transform: uppercase; }
    .metric-value-container { display: flex; align-items: baseline; margin-top: 0.5rem; }
    .metric-value { font-size: 1.8rem; font-weight: 800; color: #0f172a; }
    .metric-unit { font-size: 1rem; margin-left: 4px; color: #94a3b8; }
    .metric-subtext { font-size: 0.85rem; color: #3b82f6; margin-top: 0.5rem; font-weight: 500; }
</style>
""", unsafe_allow_html=True)

def custom_metric(label, value, unit, subtext=None):
    sub_html = f'<div class="metric-subtext">{subtext}</div>' if subtext else ""
    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-label">{label}</div>
        <div class="metric-value-container">
            <span class="metric-value">{value}</span>
            <span class="metric-unit">{unit}</span>
        </div>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)

# --- Sidebar Inputs ---
with st.sidebar:
    st.header("⚙️ Configuration")
    input_mode = st.radio("Input Method", ["Calculate from Efforts", "Manual Entry"])
    
    if input_mode == "Calculate from Efforts":
        p3 = st.number_input("3-Min Power (W)", 0, 2000, 350)
        p5 = st.number_input("5-Min Power (W)", 0, 2000, 0)
        p12 = st.number_input("12-Min Power (W)", 0, 2000, 300)
        p15 = st.number_input("15-Min Power (W)", 0, 2000, 0)
    else:
        manual_cp = st.number_input("Manual CP (W)", 50, 600, 250)
        manual_w_kj = st.number_input("Manual W' (kJ)", 1.0, 50.0, 15.0)
        
    weight = st.number_input("Weight (kg)", 30.0, 200.0, 75.0)

# --- Logic & Processing ---
W_prime = 0
CP = 0
r_squared = 1.0
valid_data = []

if input_mode == "Calculate from Efforts":
    raw_data = [
        {"duration": 180, "power": p3, "label": "3-min"},
        {"duration": 300, "power": p5, "label": "5-min"},
        {"duration": 720, "power": p12, "label": "12-min"},
        {"duration": 900, "power": p15, "label": "15-min"}
    ]
    valid_data = sorted([d for d in raw_data if d["power"] > 0], key=lambda x: x["duration"])
    
    if len(valid_data) >= 2:
        t_seconds = np.array([d["duration"] for d in valid_data])
        powers = np.array([d["power"] for d in valid_data])
        x_reg = 1 / t_seconds
        slope, intercept = np.polyfit(x_reg, powers, 1)
        W_prime, CP = slope, intercept
        correlation_matrix = np.corrcoef(x_reg, powers)
        r_squared = correlation_matrix[0, 1]**2
else:
    CP = manual_cp
    W_prime = manual_w_kj * 1000

# --- UI Display ---
if (input_mode == "Calculate from Efforts" and len(valid_data) < 2):
    st.info("👋 Enter at least two power values in the sidebar to generate your profile.")
else:
    # Calculations
    lt1_est = (0.8572 * CP) - 30.45
    MAP = (W_prime / 220) + CP
    vo2max_ml_kg = (((0.01095 * MAP) + 0.02388) * 1000) / weight

    st.title("⚡ Performance Dashboard")
    
    # Primary Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1: custom_metric("Critical Power", f"{CP:.0f}", "W", f"{(CP/weight):.2f} W/kg")
    with col2: custom_metric("W' Capacity", f"{(W_prime/1000):.1f}", "kJ", f"{(W_prime/weight):.0f} J/kg")
    with col3: custom_metric("Estimated LT1", f"{lt1_est:.0f}", "W", f"Range: {lt1_est*0.91:.0f}-{lt1_est*1.09:.0f}W")
    with col4: custom_metric("$VO_2$ Max Est.", f"{vo2max_ml_kg:.1f}", "ml/kg/min", f"R²: {r_squared:.4f}" if input_mode == "Calculate" else "Manual Mode")

    # --- Gradient Power Curve Plot ---
    st.subheader("📊 Power-Duration Profile")
    time_curve = np.arange(20, 1500, 2)
    power_curve = (W_prime / time_curve) + CP

    fig_pd = go.Figure()

    # Gradient Stack
    for i in range(1, 15):
        fig_pd.add_trace(go.Scatter(
            x=time_curve, y=power_curve,
            fill='tozeroy',
            fillcolor=f'rgba(37, 99, 235, {i*0.008})', 
            line=dict(color='rgba(0,0,0,0)'),
            showlegend=False, hoverinfo='skip'
        ))

    fig_pd.add_trace(go.Scatter(
        x=time_curve, y=power_curve,
        name="Model Curve", line=dict(color='#2563eb', width=4)
    ))

    if input_mode == "Calculate from Efforts":
        fig_pd.add_trace(go.Scatter(
            x=[d["duration"] for d in valid_data],
            y=[d["power"] for d in valid_data],
            mode='markers', marker=dict(size=12, color='#1e293b', line=dict(width=2, color='white')),
            name="Test Efforts"
        ))

    fig_pd.update_layout(
        template="plotly_white", margin=dict(t=10),
        xaxis=dict(title="Time (s)", showgrid=False),
        yaxis=dict(title="Power (W)", gridcolor="#f1f5f9"),
        legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="right", x=1)
    )
    st.plotly_chart(fig_pd, use_container_width=True)

    # --- Target Intent Calculator ---
    st.markdown("---")
    st.header("🎯 Target Intent Calculator")
    
    c1, c2, c3 = st.columns([2, 2, 3])
    with c1:
        w_perc = st.slider("Target W' Depletion (%)", 10, 100, 80)
    with c2:
        dur_min = st.number_input("Target Duration (min)", 0.5, 120.0, 5.0)
    with c3:
        target_p = ((w_perc/100 * W_prime) / (dur_min * 60)) + CP
        custom_metric(f"Target Power Output ({dur_min}m)", f"{target_p:.0f}", "Watts", 
                      subtext=f"Total $W'$ used: {(w_perc/100 * W_prime/1000):.1f} kJ")

    # --- Technical Expansion ---
    if input_mode == "Calculate from Efforts":
        with st.expander("Show Regression Data (Power vs 1/t)"):
            fig_lin = go.Figure()
            x_line = np.array([0, max(x_reg) * 1.1])
            y_line = W_prime * x_line + CP
            fig_lin.add_trace(go.Scatter(x=x_line, y=y_line, mode='lines', name='Fit', line=dict(color='#94a3b8', dash='dash')))
            fig_lin.add_trace(go.Scatter(x=x_reg, y=powers, mode='markers', marker=dict(color='#ef4444')))
            st.plotly_chart(fig_lin, use_container_width=True)
