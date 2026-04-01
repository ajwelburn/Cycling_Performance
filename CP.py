import streamlit as st
import numpy as np
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
LT1_SLOPE = 0.8572          # Linear coefficient for LT1 estimation from CP
LT1_INTERCEPT = 30.45       # Offset for LT1 estimation (W)
MAP_W_PRIME_DIVISOR = 220   # Divisor converting W' to MAP contribution (s)
VO2_SLOPE = 0.01095         # ml/min/W slope for VO2max estimation
VO2_INTERCEPT = 0.02388     # VO2max intercept term
VO2_ML_CONVERSION = 1000    # Convert L/min → ml/min

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Elite CP & W' Analytics", layout="wide")

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Helper: custom metric card
# ---------------------------------------------------------------------------
def custom_metric(label: str, value: str, unit: str, subtext: str = None) -> None:
    """Render a styled metric card. Label supports basic HTML (e.g. subscripts)."""
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


# ---------------------------------------------------------------------------
# Helper: core calculations (pure function — easy to test independently)
# ---------------------------------------------------------------------------
def calculate_metrics(cp: float, w_prime: float, weight: float) -> dict:
    """
    Derive secondary metrics from CP (W), W' (J), and weight (kg).
    Returns a dict of computed values.
    """
    lt1 = (LT1_SLOPE * cp) - LT1_INTERCEPT
    map_val = (w_prime / MAP_W_PRIME_DIVISOR) + cp
    vo2_rel = (((VO2_SLOPE * map_val) + VO2_INTERCEPT) * VO2_ML_CONVERSION) / weight
    return {
        "lt1": lt1,
        "lt1_low": lt1 * 0.91,
        "lt1_high": lt1 * 1.09,
        "map_val": map_val,
        "vo2_rel": vo2_rel,
        "cp_per_kg": cp / weight,
        "w_prime_kj": w_prime / 1000,
        "w_prime_per_kg": w_prime / weight,
    }


# ---------------------------------------------------------------------------
# Helper: R² colour badge
# ---------------------------------------------------------------------------
def r2_badge(r2: float) -> str:
    if r2 >= 0.99:
        colour = "green"
        label = "Excellent"
    elif r2 >= 0.95:
        colour = "orange"
        label = "Acceptable"
    else:
        colour = "red"
        label = "Poor"
    return f":{colour}[R² = {r2:.4f} — {label} fit]"


# ---------------------------------------------------------------------------
# Sidebar inputs
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚡ User Inputs")
    input_mode = st.radio("Calculation Mode", ["Effort Based", "Manual Entry"])

    if input_mode == "Effort Based":
        p_3min  = st.number_input("3-Minute Power (W)",  0, 2000, 350)
        p_5min  = st.number_input("5-Minute Power (W)",  0, 2000, 0)
        p_12min = st.number_input("12-Minute Power (W)", 0, 2000, 300)
        p_15min = st.number_input("15-Minute Power (W)", 0, 2000, 0)
    else:
        m_cp = st.number_input("Known CP (W)",   50,  600,  250)
        m_w  = st.number_input("Known W' (kJ)", 1.0, 50.0, 15.0)

    weight = st.number_input("Weight (kg)", 30.0, 200.0, 70.0)

# ---------------------------------------------------------------------------
# Input validation: weight
# ---------------------------------------------------------------------------
if weight <= 0:
    st.error("Weight must be greater than 0 kg.")
    st.stop()

# ---------------------------------------------------------------------------
# Derive CP and W' from inputs
# ---------------------------------------------------------------------------
CP: float = 0.0
W_prime: float = 0.0
r_squared: float = 0.0
valid_data: list = []

if input_mode == "Effort Based":
    raw_data = [
        {"d": 180, "p": p_3min,  "l": "3m"},
        {"d": 300, "p": p_5min,  "l": "5m"},
        {"d": 720, "p": p_12min, "l": "12m"},
        {"d": 900, "p": p_15min, "l": "15m"},
    ]
    valid_data = sorted(
        [d for d in raw_data if d["p"] > 0],
        key=lambda x: x["d"]
    )

    if len(valid_data) < 2:
        st.info("Please enter at least two power values to generate a model.")
        st.stop()

    t_sec  = np.array([d["d"] for d in valid_data])
    p_vals = np.array([d["p"] for d in valid_data])
    x_reg  = 1 / t_sec
    slope, intercept = np.polyfit(x_reg, p_vals, 1)
    W_prime, CP = slope, intercept
    r_squared = float(np.corrcoef(x_reg, p_vals)[0, 1] ** 2)

else:
    CP      = float(m_cp)
    W_prime = m_w * 1000  # store internally in Joules

# ---------------------------------------------------------------------------
# Validate derived values before rendering
# ---------------------------------------------------------------------------
if W_prime <= 0:
    st.error("W' must be greater than 0. Please check your inputs.")
    st.stop()

if CP <= 0:
    st.error("Critical Power must be greater than 0. Please check your inputs.")
    st.stop()

# ---------------------------------------------------------------------------
# Calculate secondary metrics
# ---------------------------------------------------------------------------
metrics = calculate_metrics(CP, W_prime, weight)

# ---------------------------------------------------------------------------
# Section: Core Metrics
# ---------------------------------------------------------------------------
st.header("📈 Core Metrics")

if input_mode == "Effort Based" and len(valid_data) == 2:
    st.warning(
        "Only 2 data points used — the model fits perfectly by definition but may not "
        "generalise. Add a third effort for a more reliable estimate."
    )

col_a, col_b, col_c, col_d = st.columns(4)
with col_a:
    custom_metric("Critical Power", f"{CP:.0f}", "W", f"{metrics['cp_per_kg']:.2f} W/kg")
with col_b:
    custom_metric("W' Capacity", f"{metrics['w_prime_kj']:.1f}", "kJ",
                  f"{metrics['w_prime_per_kg']:.0f} J/kg")
with col_c:
    custom_metric("Est. LT1", f"{metrics['lt1']:.0f}", "W",
                  f"Range: {metrics['lt1_low']:.0f}–{metrics['lt1_high']:.0f} W")
with col_d:
    custom_metric("VO<sub>2</sub> Max", f"{metrics['vo2_rel']:.1f}", "ml/kg/min")

# ---------------------------------------------------------------------------
# Section: Power-Duration Curve
# ---------------------------------------------------------------------------
st.header("📊 Power-Duration Profile")

t_curve = np.arange(20, 1501, 5)
p_curve = (W_prime / t_curve) + CP

fig = go.Figure()

# Gradient fill layers
for i in range(1, 13):
    fig.add_trace(go.Scatter(
        x=t_curve, y=p_curve,
        fill='tozeroy',
        fillcolor=f'rgba(0, 122, 204, {i * 0.01})',
        line=dict(color='rgba(0,0,0,0)'),
        showlegend=False, hoverinfo='skip'
    ))

fig.add_trace(go.Scatter(
    x=t_curve, y=p_curve,
    line=dict(color='#007ACC', width=4),
    name="Model Curve"
))

# Data point overlay (Effort Based only)
if input_mode == "Effort Based":
    fig.add_trace(go.Scatter(
        x=[d["d"] for d in valid_data],
        y=[d["p"] for d in valid_data],
        mode='markers',
        name="Efforts",
        marker=dict(size=12, color='#1e293b', line=dict(width=2, color='white'))
    ))

# Format x-axis as mm:ss
tick_vals = list(range(0, 1501, 120))
tick_text = [f"{v // 60}:{v % 60:02d}" for v in tick_vals]

fig.update_layout(
    template="simple_white",
    xaxis=dict(title="Time (mm:ss)", tickvals=tick_vals, ticktext=tick_text),
    yaxis_title="Power (W)"
)
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Section: W' Planner
# ---------------------------------------------------------------------------
st.markdown("---")
st.header("🎯 W' Planner")

plan_col_a, plan_col_b, plan_col_c = st.columns([2, 2, 3])
with plan_col_a:
    w_perc = st.slider("W' Depletion (%)", 1, 100, 80)
with plan_col_b:
    target_min = st.number_input("Target Duration (min)", 0.5, 120.0, 10.0)
with plan_col_c:
    w_used_kj = (w_perc / 100) * metrics["w_prime_kj"]
    p_req = ((w_perc / 100 * W_prime) / (target_min * 60)) + CP
    custom_metric("Required Power", f"{p_req:.0f}", "W",
                  f"Total W' used: {w_used_kj:.1f} kJ")

# ---------------------------------------------------------------------------
# Section: TTE Calculator & Linear Regression
# ---------------------------------------------------------------------------
st.markdown("---")
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("⏱️ TTE Calculator")
    tte_p = st.number_input(
        "Enter Target Power (W)",
        min_value=int(CP) + 1,
        max_value=2000,
        value=int(CP) + 50,
        help="Power must be above Critical Power for TTE to be finite."
    )
    if tte_p <= CP:
        st.warning("Target power must be above Critical Power for a finite TTE.")
    else:
        tte_sec = W_prime / (tte_p - CP)
        st.info(f"**Predicted Time to Exhaustion:** {int(tte_sec // 60)}m {int(tte_sec % 60)}s")

with col_right:
    st.subheader("📈 Linear Regression")
    if input_mode == "Effort Based":
        xr = 1 / np.array([d["d"] for d in valid_data])
        yr = [d["p"] for d in valid_data]
        fig_lin = go.Figure()
        fig_lin.add_trace(go.Scatter(x=xr, y=yr, mode='markers', name="Actual"))
        fig_lin.add_trace(go.Scatter(
            x=[0, max(xr) * 1.1],
            y=[CP, W_prime * (max(xr) * 1.1) + CP],
            mode='lines', name="Fit"
        ))
        fig_lin.update_layout(
            template="plotly_white",
            xaxis_title="1/Time (s⁻¹)",
            yaxis_title="Power (W)",
            height=300
        )
        st.plotly_chart(fig_lin, use_container_width=True)
        st.caption(r2_badge(r_squared))
    else:
        st.write("Regression data is available in 'Effort Based' mode.")
