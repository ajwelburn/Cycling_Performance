import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.set_page_config(layout="wide")

st.title("⚡ CP and W' Calculator")
st.markdown("Enter your 3-minute and 12-minute maximal power, and your weight, to calculate your Critical Power and W'.")

# --- Helper Function for Calculations ---
def calculate_power_metrics(p3, p12, weight_kg):
    """Calculates Critical Power, W', and other derived metrics."""
    if p3 <= p12:
        return None # Return None to indicate an error condition

    t1, t2 = 180, 720  # 3 and 12 minutes in seconds
    inv_t1, inv_t2 = 1 / t1, 1 / t2

    # Core calculations
    w_prime = (p3 - p12) / (inv_t1 - inv_t2)
    cp = p12 - (w_prime * inv_t2)

    # Derived metrics
    metrics = {
        "cp": cp,
        "w_prime_kj": w_prime / 1000,
        "cp_w_kg": cp / weight_kg,
        "w_prime_j_kg": w_prime / weight_kg,
        "map": (w_prime / 220) + cp
    }
    
    # Estimated LT1 and VO2max
    lt1_est = (0.8572 * cp) - 30.45
    metrics["lt1_range"] = f"{lt1_est * 0.91:.0f} - {lt1_est * 1.09:.0f}"
    vo2max_l_min = (0.01095 * metrics["map"]) + 0.02388
    metrics["vo2max_l_min"] = vo2max_l_min
    metrics["vo2max_ml_kg_min"] = (vo2max_l_min * 1000) / weight_kg
    
    return metrics

# --- Main Layout ---
input_col, results_col = st.columns([1, 3])

with input_col:
    st.header("⚙️ Your Test Data")
    p3 = st.number_input("3-Minute Power (W)", min_value=100, max_value=1000, value=350, step=1)
    p12 = st.number_input("12-Minute Power (W)", min_value=100, max_value=1000, value=300, step=1)
    weight = st.number_input("Weight (kg)", min_value=40.0, max_value=150.0, value=70.0, step=0.1)

    analyse_button = st.button("Analyse", use_container_width=True, type="primary")

# --- Results and Visualization ---
if analyse_button:
    metrics = calculate_power_metrics(p3, p12, weight)
    
    with results_col:
        if metrics is None:
            st.error("Error: 3-minute power must be greater than 12-minute power. Please check your inputs.")
        else:
            st.header("📈 Your Calculated Metrics")
            # Display primary metrics
            cols = st.columns(4)
            cols[0].metric("Critical Power (CP)", f"{metrics['cp']:.0f} W")
            cols[1].metric("W' (Work Capacity)", f"{metrics['w_prime_kj']:.1f} kJ")
            cols[2].metric("CP (Relative)", f"{metrics['cp_w_kg']:.2f} W/kg")
            cols[3].metric("W' (Relative)", f"{metrics['w_prime_j_kg']:.1f} J/kg")
            
            st.markdown("---")
            
            # Display secondary metrics
            cols = st.columns(3)
            cols[0].metric("Estimated LT1 (±9%)", f"{metrics['lt1_range']} W")
            cols[1].metric("Predicted VO₂max (abs)", f"{metrics['vo2max_l_min']:.2f} L/min")
            cols[2].metric("Predicted VO₂max (rel)", f"{metrics['vo2max_ml_kg_min']:.1f} ml/min/kg")

            # --- Power-Duration Curve ---
            st.header("📊 Your Power-Duration Curve")
            time_curve = np.arange(20, 901)
            power_curve = (metrics['cp'] * time_curve + (metrics['w_prime_kj'] * 1000)) / time_curve

            fig_pd = go.Figure()
            # CP Line
            fig_pd.add_trace(go.Scatter(x=time_curve, y=[metrics['cp']] * len(time_curve), mode='lines', name='Critical Power', line=dict(color='grey', dash='dot')))
            # Power Curve
            fig_pd.add_trace(go.Scatter(x=time_curve, y=power_curve, mode='lines', name='Power Curve', line=dict(color='#007ACC'), fill='tonexty', fillcolor='rgba(0, 122, 204, 0.2)'))
            # Test data points
            fig_pd.add_trace(go.Scatter(x=[180], y=[p3], mode='markers', name=f'3-min Power ({p3}W)', marker=dict(color='#FF5733', size=10)))
            fig_pd.add_trace(go.Scatter(x=[720], y=[p12], mode='markers', name=f'12-min Power ({p12}W)', marker=dict(color='#33C1FF', size=10)))

            fig_pd.update_layout(
                xaxis_title="Time (s)", yaxis_title="Power (W)",
                template="simple_white",
                yaxis_range=[min(power_curve) * 0.8, max(power_curve) * 1.1],
                legend=dict(yanchor="top", y=0.98, xanchor="right", x=0.98, bgcolor="rgba(255,255,255,0.7)"),
                margin=dict(l=20, r=20, t=20, b=20)
            )
            st.plotly_chart(fig_pd, use_container_width=True)

            # --- Expanders for additional info ---
            with st.expander("🔍 Show the Linear Model Calculation"):
                inv_t1, inv_t2 = 1/180, 1/720
                fig_linear = go.Figure()
                fig_linear.add_trace(go.Scatter(x=[inv_t1, inv_t2], y=[p3, p12], mode='markers', name='Test Efforts', marker=dict(color='red', size=10)))
                x_vals = np.array([0, inv_t1])
                y_vals = (metrics['w_prime_kj'] * 1000) * x_vals + metrics['cp']
                fig_linear.add_trace(go.Scatter(x=x_vals, y=y_vals, mode='lines', name='Linear Model', line=dict(color='blue', dash='dash')))
                fig_linear.update_layout(title="Linear Model: Power vs. 1/Time", xaxis_title="1 / Time (s⁻¹)", yaxis_title="Power (W)", template="simple_white")
                st.plotly_chart(fig_linear, use_container_width=True)
                st.markdown(f"The slope of the line is your **W' ({metrics['w_prime_kj']:.1f} kJ)**, and the y-intercept is your **Critical Power ({metrics['cp']:.1f} W)**.")

            with st.expander("🔄 Compare to a Previous Test"):
                st.write("Enter your previous test results to see the change.")
                prev_p3 = st.number_input("Previous 3-Min Power (W)", value=0, step=1, key="prev_p3")
                prev_p12 = st.number_input("Previous 12-Min Power (W)", value=0, step=1, key="prev_p12")
                
                if prev_p3 > 0 and prev_p12 > 0:
                    prev_metrics = calculate_power_metrics(prev_p3, prev_p12, weight)
                    if prev_metrics:
                        delta_cp = metrics['cp'] - prev_metrics['cp']
                        delta_w_prime_kj = metrics['w_prime_kj'] - prev_metrics['w_prime_kj']
                        
                        comp_cols = st.columns(2)
                        comp_cols[0].metric("Critical Power (CP)", f"{metrics['cp']:.0f} W", delta=f"{delta_cp:.1f} W")
                        comp_cols[1].metric("W' (Work Capacity)", f"{metrics['w_prime_kj']:.1f} kJ", delta=f"{delta_w_prime_kj:.1f} kJ")
                    else:
                        st.warning("Previous 3-min power must be greater than previous 12-min power for a valid comparison.")

            with st.expander("⏱️ Predict Max Power for a Custom Duration"):
                duration_min = st.number_input("Enter duration (minutes)", min_value=1, max_value=60, value=5, step=1)
                duration_sec = duration_min * 60
                predicted_power = (metrics['w_prime_kj'] * 1000 / duration_sec) + metrics['cp']
                st.metric(f"Predicted Max Power for {duration_min} min", f"{predicted_power:.0f} W")
