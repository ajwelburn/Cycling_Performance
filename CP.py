import streamlit as st
import numpy as np
import plotly.graph_objects as go
from scipy.stats import linregress

# --- Custom CSS for metric styling ---
st.markdown("""
<style>
.metric-container {
    display: flex;
    flex-direction: column;
    padding: 10px;
    border: 1px solid #ddd;
    border-radius: 5px;
    margin-bottom: 10px;
    background-color: #fafafa;
}
.metric-label {
    font-size: 0.9rem;
    color: #808495;
    margin-bottom: 2px;
}
.metric-value-container {
    display: flex;
    align-items: baseline;
}
.metric-value {
    font-size: 1.75rem;
    font-weight: bold;
    color: #31333F;
}
.metric-unit {
    font-size: 1rem;
    margin-left: 0.3rem;
    color: #555;
}
.metric-delta {
    font-size: 0.9rem;
    margin-left: 0.5rem;
}
.metric-subtext {
    font-size: 0.85rem;
    color: #666;
    margin-top: 2px;
    font-style: italic;
}
</style>
""", unsafe_allow_html=True)


# --- Helper function to create custom metric with optional subtext ---
def custom_metric(label, value, unit, delta=None, delta_unit="", subtext=None):
    delta_html = ""
    if delta is not None:
        delta_color = "green" if delta >= 0 else "red"
        delta_sign = "+" if delta >= 0 else ""
        delta_html = f'<span class="metric-delta" style="color: {delta_color};">{delta_sign}{delta:.1f}{delta_unit}</span>'
    
    subtext_html = ""
    if subtext:
        subtext_html = f'<div class="metric-subtext">{subtext}</div>'

    st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">{label}</div>
            <div class="metric-value-container">
                <span class="metric-value">{value}</span>
                <span class="metric-unit">{unit}</span>
                {delta_html}
            </div>
            {subtext_html}
        </div>
    """, unsafe_allow_html=True)


# --- App Title ---
st.title("⚡ Multi-Point CP & W' Calculator")
st.markdown("""
Enter your maximal power for 3, 5, 12, or 15 minutes. 
**You must provide at least two durations** for the calculation to work. 
Set a value to **0** to exclude it from the calculation.
""")

# --- Sidebar for User Inputs ---
st.sidebar.header("User Inputs")

# Using 0 as default for optional fields so logic implies "not used"
p3 = st.sidebar.number_input("3-Minute Power (W)", min_value=0, max_value=2000, value=350, step=1)
p5 = st.sidebar.number_input("5-Minute Power (W)", min_value=0, max_value=2000, value=0, step=1)
p12 = st.sidebar.number_input("12-Minute Power (W)", min_value=0, max_value=2000, value=300, step=1)
p15 = st.sidebar.number_input("15-Minute Power (W)", min_value=0, max_value=2000, value=0, step=1)
weight = st.sidebar.number_input("Weight (kg)", min_value=30.0, max_value=200.0, value=70.0, step=0.1)

# --- Data Preparation Logic ---
# 1. Aggregate inputs into lists
raw_data = [
    {"duration": 180, "power": p3, "label": "3-min"},
    {"duration": 300, "power": p5, "label": "5-min"},
    {"duration": 720, "power": p12, "label": "12-min"},
    {"duration": 900, "power": p15, "label": "15-min"}
]

# 2. Filter out valid inputs (Power > 0)
valid_data = [d for d in raw_data if d["power"] > 0]

# 3. Validation Flag
is_valid = True
error_msg = ""

if len(valid_data) < 2:
    is_valid = False
    error_msg = "Please enter power values for at least two different durations."
else:
    # Sort by duration to check for logical consistency (shorter duration should have higher power)
    valid_data.sort(key=lambda x: x["duration"])
    
    # Check that power decreases as duration increases
    for i in range(len(valid_data) - 1):
        if valid_data[i]["power"] <= valid_data[i+1]["power"]:
            is_valid = False
            error_msg = f"Data Error: {valid_data[i]['label']} power must be higher than {valid_data[i+1]['label']} power."
            break

# --- Calculation & Display ---
if not is_valid:
    st.error(f"⚠️ {error_msg}")
else:
    # Extract arrays for calculation
    # Model: Power = W' * (1/time) + CP
    # y = mx + c  ->  Power = W' * (1/t) + CP
    
    t_seconds = np.array([d["duration"] for d in valid_data])
    powers = np.array([d["power"] for d in valid_data])
    
    # x axis for regression is 1/time
    x_reg = 1 / t_seconds
    y_reg = powers

    # Perform Linear Regression
    # slope = W', intercept = CP
    slope, intercept, r_value, p_value, std_err = linregress(x_reg, y_reg)
    
    W_prime = slope
    CP = intercept
    r_squared = r_value**2

    # --- Derived Metrics ---
    W_prime_kj = W_prime / 1000
    cp_w_kg = CP / weight
    w_prime_j_kg = W_prime / weight
    
    # Estimate LT1 and its range
    lt1_est = (0.8572 * CP) - 30.45
    lt1_lower = lt1_est * 0.91
    lt1_upper = lt1_est * 1.09
    
    # Predict VO2max using the new MAP formula
    MAP = (W_prime / 220) + CP
    vo2max_l_min = (0.01095 * MAP) + 0.02388
    vo2max_ml_kg_min = (vo2max_l_min * 1000) / weight

    # --- Display Results in Data Boxes ---
    st.header("📈 Your Calculated Metrics")
    
    # Show how many points were used and the fit quality
    st.caption(f"Calculated using {len(valid_data)} data points. Model Fit (R²): {r_squared:.4f}")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        custom_metric("Critical Power (CP)", f"{CP:.0f}", "W")
    with col2:
        custom_metric("W' (Work Capacity)", f"{W_prime_kj:.1f}", "kJ")
    with col3:
        custom_metric("CP (Relative)", f"{cp_w_kg:.2f}", "W/kg")
    with col4:
        custom_metric("W' (Relative)", f"{w_prime_j_kg:.1f}", "J/kg")

    st.markdown("---") # Visual separator
    
    col5, col6, col7 = st.columns(3)
    with col5:
        # UPDATED: LT1 with range underneath
        range_text = f"Range: {lt1_lower:.0f} - {lt1_upper:.0f} W"
        custom_metric("Estimated LT1", f"{lt1_est:.0f}", "W", subtext=range_text)
    with col6:
        custom_metric("Predicted VO₂max (abs)", f"{vo2max_l_min:.2f}", "L/min")
    with col7:
        custom_metric("Predicted VO₂max (rel)", f"{vo2max_ml_kg_min:.1f}", "ml/min/kg")


    # --- Power-Duration Curve ---
    st.header("📊 Your Power-Duration Curve")
    
    # Generate time data from 20s to 1200s (20 mins) for the curve
    time_curve = np.arange(20, 1201)
    power_curve = (W_prime / time_curve) + CP

    # Create the plot with Plotly
    fig_pd = go.Figure()

    # Add the CP line first (for shading reference)
    fig_pd.add_trace(go.Scatter(
        x=time_curve,
        y=[CP] * len(time_curve),
        mode='lines',
        name='Critical Power (CP)',
        line=dict(color='grey', dash='dot', width=2)
    ))

    # Add the main power curve with shading
    fig_pd.add_trace(go.Scatter(
        x=time_curve, 
        y=power_curve, 
        mode='lines', 
        name='Model Curve',
        line=dict(color='#007ACC', width=3),
        fill='tonexty', 
        fillcolor='rgba(255, 182, 193, 0.3)' 
    ))

    # Add markers for the input powers (Dynamic based on valid_data)
    for point in valid_data:
        fig_pd.add_trace(go.Scatter(
            x=[point["duration"]], 
            y=[point["power"]], 
            mode='markers', 
            name=f'{point["label"]} ({point["power"]}W)',
            marker=dict(size=10, symbol='circle', line=dict(width=2, color='DarkSlateGrey'))
        ))

    # Update layout
    fig_pd.update_layout(
        title="", 
        xaxis_title="Time (s)",
        yaxis_title="Power (W)",
        template="simple_white", 
        xaxis_range=[0, 1250], 
        yaxis_range=[100, max(power_curve) + 50],  
        font=dict(color="black", family="Arial, sans-serif"),
        legend=dict(
            yanchor="top",
            y=0.98,
            xanchor="right",
            x=0.98,
            bgcolor="rgba(255,255,255,0.6)"
        )
    )
    
    fig_pd.update_xaxes(showline=True, linewidth=1, linecolor='black', ticks='inside')
    fig_pd.update_yaxes(showline=True, linewidth=1, linecolor='black', ticks='inside')

    st.plotly_chart(fig_pd, use_container_width=True)
    
    # --- Linear Power vs. 1/Time Graph ---
    with st.expander("Show Linear Regression Model (Power vs. 1/Time)"):
        fig_linear = go.Figure()

        # Add the test points used
        fig_linear.add_trace(go.Scatter(
            x=x_reg,
            y=y_reg,
            mode='markers',
            name='User Inputs',
            marker=dict(color='red', size=12)
        ))

        # Add the regression line
        # Create 2 points to draw the line (0 and max 1/t)
        x_line = np.array([0, max(x_reg) * 1.1])
        y_line = W_prime * x_line + CP
        
        fig_linear.add_trace(go.Scatter(
            x=x_line,
            y=y_line,
            mode='lines',
            name='Linear Fit',
            line=dict(color='blue', dash='dash')
        ))
        
        fig_linear.update_layout(
            title="Linear Regression: Power vs. 1/Time",
            xaxis_title="1 / Time (s⁻¹)",
            yaxis_title="Power (W)",
            template="plotly_white",
            font=dict(color="black")
        )
        fig_linear.update_xaxes(showline=True, linewidth=2, linecolor='black', ticks='inside', showgrid=False)
        fig_linear.update_yaxes(showline=True, linewidth=2, linecolor='black', ticks='inside', showgrid=False)
        
        st.plotly_chart(fig_linear, use_container_width=True)
        st.markdown(f"**Slope (W')**: {W_prime_kj:.1f} kJ | **Intercept (CP)**: {CP:.1f} W")

    # --- Maximal Sustainable Power Calculator ---
    with st.expander("Calculate Predicted Max Power for Custom Duration"):
        duration_input_min = st.number_input("Enter duration (minutes)", min_value=1, max_value=120, value=20, step=1, key="msp_input")
        
        duration_input_sec = duration_input_min * 60
        msp = (W_prime / duration_input_sec) + CP
        
        custom_metric(f"Predicted Power for {duration_input_min} min", f"{msp:.0f}", "W")
