import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- Page Config & Modern Styling ---
st.set_page_config(page_title="W' & CP Analytics", layout="wide")

st.markdown("""
<style>
    /* Modern Background and Font */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* Modernized Metric Containers */
    .metric-container {
        display: flex;
        flex-direction: column;
        padding: 20px;
        border: none;
        border-radius: 12px;
        margin-bottom: 10px;
        background-color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        transition: transform 0.2s;
    }
    .metric-container:hover {
        transform: translateY(-2px);
    }
    .metric-label {
        font-size: 0.85rem;
        font-weight: 600;
        color: #6c757d;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-value-container {
        display: flex;
        align-items: baseline;
        margin-top: 5px;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 800;
        color: #1e293b;
    }
    .metric-unit {
        font-size: 1rem;
        margin-left: 5px;
        color: #94a3b8;
    }
    .metric-subtext {
        font-size: 0.8rem;
        color: #64748b;
        margin-top: 8px;
        padding-top: 8px;
        border-top: 1px solid #f1f5f9;
    }
</style>
""", unsafe_allow_html=True)

def custom_metric(label, value, unit, subtext=None):
    subtext_html = f'<div class="metric-subtext">{subtext}</div>' if subtext else ""
    html_str = f"""
    <div class="metric-container">
        <div class="metric-label">{label}</div>
        <div class="metric-value-container">
            <span class="metric-value">{value}</span>
            <span class="metric-unit">{unit}</span>
        </div>
        {subtext_html}
    </div>
    """
    st.markdown(html_str, unsafe_allow_html=True)

# --- Sidebar Inputs ---
with st.sidebar:
    st.header("⚡ Input Parameters")
    p3 = st.number_input("3-Min Power (W)", 0, 2000, 350)
    p5 = st.number_input("5-Min Power (W)", 0, 2000, 0)
    p12 = st.number_input("12-Min Power (W)", 0, 2000, 300)
    p15 = st.number_input("15-Min Power (W)", 0, 2000, 0)
    weight = st.number_input("Body Weight (kg)", 30.0, 200.0, 75.0)
    
    st.markdown("---")
    st.caption("Developed for High-Performance Analytics")

# --- Logic & Calculations ---
raw_data = [
    {"duration": 180, "power": p3, "label": "3-min"},
    {"duration": 300, "power": p5, "label": "5-min"},
    {"duration": 720, "power": p12, "label": "12-min"},
    {"duration": 900, "power": p15, "label": "15-min"}
]
valid_data = [d for d in raw_data if d["power"] > 0]

if len(valid_data) < 2:
    st.warning("Please enter at least two power values in the sidebar to generate the model.")
else:
    # Regression
    t_seconds = np.array([d["duration"] for d in valid_data])
    powers = np.array([d["power"] for d in valid_data])
    slope, intercept = np.polyfit(1/t_seconds, powers, 1)
    
    W_prime = slope
    CP = intercept
    
    # Hero Metrics
    st.title("Performance Profile")
    m1, m2, m3, m4 = st.columns(4)
    with m1: custom_metric("Critical Power", f"{CP:.0f}", "W", f"{(CP/weight):.2f} W/kg")
    with m2: custom_metric("W' Capacity", f"{(W_prime/1000):.1f}", "kJ", f"{(W_prime/weight):.0f} J/kg")
    with m3: custom_metric("Est. LT1", f"{(0.85*CP-30):.0f}", "W", "Zone 2 Upper Bound")
    with m4: custom_metric("VO2Max Est.", f"{((0.011*((W_prime/220)+CP)+0.024)*1000/weight):.1f}", "ml/kg")

    # --- Plotly Power-Duration Curve with Gradient ---
    st.subheader("Power-Duration Curve")
    time_curve = np.arange(20, 1500, 2)
    power_curve = (W_prime / time_curve) + CP

    fig = go.Figure()

    # 1. Simulate Gradient Fill (Stacking layers)
    # We create 10 layers of the fill area with decreasing opacity
    num_steps = 12
    for i in range(num_steps):
        opacity = (i + 1) / num_steps * 0.15  # Increases as it goes down
        # Each layer fills a portion of the Y axis to simulate the fade
        fig.add_trace(go.Scatter(
            x=time_curve,
            y=power_curve,
            fill='tozeroy',
            fillcolor=f'rgba(0, 122, 255, {opacity/2})',
            line=dict(color='rgba(0,0,0,0)'),
            showlegend=False,
            hoverinfo='skip'
        ))

    # 2. Add main Curve Line
    fig.add_trace(go.Scatter(
        x=time_curve, y=power_curve,
        name="Model Curve",
        line=dict(color='#007AFF', width=4)
    ))

    # 3. Add Critical Power baseline
    fig.add_hline(y=CP, line_dash="dot", line_color="#94a3b8", 
                 annotation_text="CP Baseline", annotation_position="bottom right")

    # 4. Add User Data Points
    fig.add_trace(go.Scatter(
        x=[d["duration"] for d in valid_data],
        y=[d["power"] for d in valid_data],
        mode='markers',
        marker=dict(size=12, color='#1e293b', line=dict(width=2, color='white')),
        name="Field Tests"
    ))

    fig.update_layout(
        template="plotly_white",
        hovermode="x unified",
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(title="Duration (seconds)", showgrid=False),
        yaxis=dict(title="Power (Watts)", showgrid=True, gridcolor="#f1f5f9"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- New Feature: W' Target Calculator ---
    st.markdown("---")
    st.header("🎯 Target Intent Calculator")
    st.markdown("Calculate exactly how much power you need to hold to deplete a specific % of your W' over a set duration.")
    
    c1, c2 = st.columns(2)
    with c1:
        w_percent = st.slider("Target W' Depletion (%)", 10, 100, 80)
        target_duration_min = st.number_input("Target Duration (minutes)", 1.0, 60.0, 5.0)
    
    with c2:
        # Math: Power = (W'_used / time) + CP
        target_seconds = target_duration_min * 60
        w_used = (w_percent / 100) * W_prime
        target_power = (w_used / target_seconds) + CP
        
        st.write("##") # Spacer
        custom_metric(
            f"Target Power for {target_duration_min}m", 
            f"{target_power:.0f}", "Watts", 
            subtext=f"Uses {w_percent}% of your total {W_prime/1000:.1f}kJ capacity"
        )

    # --- Cleanup UI Footer ---
    with st.expander("Model Technical Details"):
        st.write(f"**Regression Slope:** {W_prime:.2f} (W')")
        st.write(f"**Regression Intercept:** {CP:.2f} (CP)")
        st.write("This model uses the linear $P = W' \cdot (1/t) + CP$ relationship.")
