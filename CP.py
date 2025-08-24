import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- Page Configuration ---
st.set_page_config(layout="wide")

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
}
.metric-label {
    font-size: 1rem;
    color: #808495;
}
.metric-value-container {
    display: flex;
    align-items: baseline;
}
.metric-value {
    font-size: 2rem;
    font-weight: bold;
}
.metric-unit {
    font-size: 1.1rem;
    margin-left: 0.3rem;
}
.metric-delta {
    font-size: 0.9rem;
    margin-left: 0.5rem;
}
</style>
""", unsafe_allow_html=True)


# --- Helper function to create custom metric ---
def custom_metric(label, value, unit, delta=None, delta_unit=""):
    delta_html = ""
    if delta is not None:
        delta_color = "green" if delta >= 0 else "red"
        delta_sign = "+" if delta >= 0 else ""
        delta_html = f'<span class="metric-delta" style="color: {delta_color};">{delta_sign}{delta:.1f}{delta_unit}</span>'

    st.markdown(f"""
        <div class="metric-label">{label}</div>
        <div class="metric-value-container">
            <span class="metric-value">{value}</span>
            <span class="metric-unit">{unit}</span>
            {delta_html}
        </div>
    """, unsafe_allow_html=True)


# --- App Title ---
st.title("⚡ CP and W' Calculator")
st.markdown("Enter your 3-minute and 12-minute maximal power, and your weight, to calculate your Critical Power and W'.")

# --- Main Layout ---
# Create two columns: one for inputs and one for the results.
input_col, results_col = st.columns([1, 2])

# --- Column for User Inputs ---
with input_col:
    st.header("⚙️ Your Test Data")
    p3 = st.number_input("3-Minute Power (W)", min_value=100, max_value=1000, value=350, step=1)
    p12 = st.number_input("12-Minute Power (W)", min_value=100, max_value=1000, value=300, step=1)
    weight = st.number_input("Weight (kg)", min_value=40.0, max_value=150.0, value=70.0, step=0.1)

    # The "Analyse" button to trigger calculations
    analyse_button = st.button("Analyse", use_container_width=True)


# --- Column for Results ---
# The analysis will only run when the button is clicked.
if analyse_button:
    with results_col:
        # --- Calculation Logic ---
        # Check for valid inputs to prevent illogical results
        if p3 <= p12:
            st.error("Error: 3-minute power must be greater than 12-minute power. Please check your inputs.")
        else:
            # Time in seconds
            t1 = 180  # 3 minutes
            t2 = 720  # 12 minutes
            
            inv_t1 = 1 / t1
            inv_t2 = 1 / t2
            
            # W' is the slope of the Power vs. 1/Time relationship
            W_prime = (p3 - p12) / (inv_t1 - inv_t2)
            
            # CP is the y-intercept of the Power vs. 1/Time relationship
            CP = p12 - (W_prime * inv_t2)
            
            # Calculate derived metrics
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
                custom_metric("Estimated LT1 (±9%)", f"{lt1_lower:.0f} - {lt1_upper:.0f}", "W")
            with col6:
                custom_metric("Predicted VO₂max (abs)", f"{vo2max_l_min:.2f}", "L/min")
            with col7:
                custom_metric("Predicted VO₂max (rel)", f"{vo2max_ml_kg_min:.1f}", "ml/min/kg")


            # --- Power-Duration Curve ---
            st.header("📊 Your Power-Duration Curve")
            
            # Generate time data from 20s to 900s
            time_curve = np.arange(20, 901)
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
                name='Power-Duration Curve',
                line=dict(color='#007ACC', width=3),
                fill='tonexty', # Shade the area down to the next trace (the CP line)
                fillcolor='rgba(255, 182, 193, 0.3)' # Light pink with transparency
            ))

            # Add markers for the input powers
            fig_pd.add_trace(go.Scatter(
                x=[t1], 
                y=[p3], 
                mode='markers', 
                name=f'3-min Power ({p3}W)',
                marker=dict(color='#FF5733', size=10, symbol='circle')
            ))
            fig_pd.add_trace(go.Scatter(
                x=[t2], 
                y=[p12], 
                mode='markers', 
                name=f'12-min Power ({p12}W)',
                marker=dict(color='#33C1FF', size=10, symbol='circle')
            ))

            # Update layout for a modern look and set axis ranges
            fig_pd.update_layout(
                title="", # Remove title from here to place it outside
                xaxis_title="Time (s)",
                yaxis_title="Power (W)",
                template="simple_white", # Use a clean template that removes top/right axes
                xaxis_range=[0, max(time_curve) + 50], # Start x-axis at 0
                yaxis_range=[100, max(power_curve) + 50],  # Start y-axis at 100
                font=dict(color="black", family="Arial, sans-serif"), # Set all font to black and sans-serif
                legend=dict(
                    yanchor="top",
                    y=0.98,
                    xanchor="right",
                    x=0.98,
                    bgcolor="rgba(255,255,255,0.6)" # Semi-transparent background for legend
                )
            )
            
            # Add solid axis lines and more prominent inside ticks
            fig_pd.update_xaxes(showline=True, linewidth=1, linecolor='black', ticks='inside', ticklen=6, tickwidth=1)
            fig_pd.update_yaxes(showline=True, linewidth=1, linecolor='black', ticks='inside', ticklen=6, tickwidth=1)

            st.plotly_chart(fig_pd, use_container_width=True)
            
            # --- Expandable Sections ---
            with st.expander("🔍 Show the Linear Model Calculation"):
                fig_linear = go.Figure()

                # Add the two test points
                fig_linear.add_trace(go.Scatter(
                    x=[inv_t1, inv_t2],
                    y=[p3, p12],
                    mode='markers',
                    name='Test Efforts',
                    marker=dict(color='red', size=10)
                ))

                # Add the line connecting the points and extending to the y-axis
                x_vals = np.array([0, inv_t1])
                y_vals = W_prime * x_vals + CP
                fig_linear.add_trace(go.Scatter(
                    x=x_vals,
                    y=y_vals,
                    mode='lines',
                    name='Linear Relationship',
                    line=dict(color='blue', dash='dash')
                ))
                
                fig_linear.update_layout(
                    title="Linear Model: Power vs. 1/Time",
                    xaxis_title="1 / Time (s⁻¹)",
                    yaxis_title="Power (W)",
                    template="plotly_white",
                    font=dict(color="black")
                )
                fig_linear.update_xaxes(showline=True, linewidth=2, linecolor='black', ticks='inside', showgrid=False)
                fig_linear.update_yaxes(showline=True, linewidth=2, linecolor='black', ticks='inside', showgrid=False)
                
                st.plotly_chart(fig_linear, use_container_width=True)
                st.markdown(f"The slope of the line is your **W' ({W_prime_kj:.1f} kJ)**, and the y-intercept is your **Critical Power ({CP:.1f} W)**.")

            with st.expander("🔄 Compare to a Previous Test"):
                st.write("Enter your previous test results to see the change.")
                prev_p3 = st.number_input("Previous 3-Min Power (W)", value=0, step=1, key="prev_p3")
                prev_p12 = st.number_input("Previous 12-Min Power (W)", value=0, step=1, key="prev_p12")

                if prev_p3 > 0 and prev_p12 > 0 and prev_p3 > prev_p12:
                    # Recalculate previous CP and W'
                    prev_W_prime = (prev_p3 - prev_p12) / (inv_t1 - inv_t2)
                    prev_CP = prev_p12 - (prev_W_prime * inv_t2)
                    prev_W_prime_kj = prev_W_prime / 1000

                    st.subheader("Comparison")
                    delta_cp = CP - prev_CP
                    delta_w_prime_kj = W_prime_kj - prev_W_prime_kj
                    
                    comp_col1, comp_col2 = st.columns(2)
                    with comp_col1:
                        custom_metric("Critical Power (CP)", f"{CP:.0f}", "W", delta=delta_cp, delta_unit=" W")
                    with comp_col2:
                        custom_metric("W' (Work Capacity)", f"{W_prime_kj:.1f}", "kJ", delta=delta_w_prime_kj, delta_unit=" kJ")

                elif prev_p3 > 0 and prev_p12 > 0 and prev_p3 <= prev_p12:
                    st.warning("Previous 3-min power must be greater than previous 12-min power for a valid comparison.")

            with st.expander("⏱️ Predict Max Power for a Custom Duration"):
                duration_input_min = st.number_input("Enter duration (minutes)", min_value=3, max_value=15, value=5, step=1, key="msp_input")
                
                duration_input_sec = duration_input_min * 60
                msp = (W_prime / duration_input_sec) + CP
                
                custom_metric(f"Predicted Max Power for {duration_input_min} minutes", f"{msp:.0f}", "W")
