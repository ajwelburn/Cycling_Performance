import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- App Title ---
st.title("⚡ CP and W' Calculator")
st.markdown("Enter your 3-minute and 12-minute maximal power, and your weight, to calculate your Critical Power and W'.")

# --- Sidebar for User Inputs ---
st.sidebar.header("User Inputs")
p3 = st.sidebar.number_input("3-Minute Power (W)", min_value=100, max_value=1000, value=350, step=1)
p12 = st.sidebar.number_input("12-Minute Power (W)", min_value=100, max_value=1000, value=300, step=1)
weight = st.sidebar.number_input("Weight (kg)", min_value=40.0, max_value=150.0, value=70.0, step=0.1)

# --- Calculation Logic ---
# Check for valid inputs to prevent illogical results
if p3 <= p12:
    st.error("Error: 3-minute power must be greater than 12-minute power. Please check your inputs.")
else:
    # Calculate CP and W' using the Power vs. 1/Time linear model
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
    
    # Predict VO2max
    vo2max_pred = (0.01095 * cp_w_kg + 0.02388) * weight

    # --- Display Results in Data Boxes ---
    st.header("📈 Your Calculated Metrics")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Critical Power (CP)", f"{CP:.0f} W")
    col2.metric("W' (Work Capacity)", f"{W_prime_kj:.1f} kJ")
    col3.metric("CP (Relative)", f"{cp_w_kg:.2f} W/kg")
    col4.metric("W' (Relative)", f"{w_prime_j_kg:.1f} J/kg")

    st.markdown("---") # Visual separator
    
    col5, col6 = st.columns(2)
    col5.metric("Estimated LT1 (±9%)", f"{lt1_lower:.0f} - {lt1_upper:.0f} W")
    col6.metric("Predicted VO₂max", f"{vo2max_pred:.2f} L/min")


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
        title="Power-Duration Curve",
        xaxis_title="Time (s)",
        yaxis_title="Power (W)",
        legend_title="Legend",
        template="plotly_white", # Use a clean template
        xaxis_range=[0, max(time_curve) + 50], # Start x-axis at 0
        yaxis_range=[100, max(power_curve) + 50],  # Start y-axis at 100
        font=dict(color="black") # Set all font to black
    )
    
    # Add solid axis lines, inside ticks, and remove gridlines for a cleaner look
    fig_pd.update_xaxes(showline=True, linewidth=2, linecolor='black', ticks='inside', showgrid=False)
    fig_pd.update_yaxes(showline=True, linewidth=2, linecolor='black', ticks='inside', showgrid=False)

    st.plotly_chart(fig_pd, use_container_width=True)
    
    # --- Linear Power vs. 1/Time Graph ---
    with st.expander("Show Linear Model (Power vs. 1/Time)"):
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
        # The line is P = W'*(1/t) + CP
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

    # --- Comparison Section ---
    with st.expander("Compare To Previous Results"):
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
            
            # Use st.metric's delta feature for visualization
            comp_col1, comp_col2 = st.columns(2)
            comp_col1.metric("Critical Power (CP)", f"{CP:.0f} W", f"{delta_cp:+.0f} W")
            comp_col2.metric("W' (Work Capacity)", f"{W_prime_kj:.1f} kJ", f"{delta_w_prime_kj:+.1f} kJ")
        elif prev_p3 > 0 and prev_p12 > 0 and prev_p3 <= prev_p12:
            st.warning("Previous 3-min power must be greater than previous 12-min power for a valid comparison.")


    # --- Maximal Sustainable Power Calculator ---
    with st.expander("Calculate Maximal Sustainable Power for a Custom Duration"):
        duration_input_min = st.number_input("Enter duration (minutes)", min_value=3, max_value=15, value=5, step=1, key="msp_input")
        
        duration_input_sec = duration_input_min * 60
        msp = (W_prime / duration_input_sec) + CP
        
        st.metric(f"Predicted Max Power for {duration_input_min} minutes", f"{msp:.0f} W")

