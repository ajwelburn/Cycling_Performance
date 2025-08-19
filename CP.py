iimport streamlit as st
import numpy as np
import matplotlib.pyplot as plt

# --- App Title ---
st.title("CP and W' Calculator")
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
    # Calculate CP and W'
    # Time in seconds
    t1 = 180  # 3 minutes
    t2 = 720  # 12 minutes
    
    work1 = p3 * t1
    work2 = p12 * t2
    
    CP = (work2 - work1) / (t2 - t1)
    W_prime = (p3 - CP) * t1
    
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
    st.header("Your Calculated Metrics")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Critical Power (CP)", f"{CP:.0f} W")
    col2.metric("W' (Work Capacity)", f"{W_prime_kj:.1f} kJ")
    col3.metric("CP (Relative)", f"{cp_w_kg:.2f} W/kg")
    col4.metric("W' (Relative)", f"{w_prime_j_kg:.1f} J/kg")

    st.markdown("---") # Visual separator
    
    col5, col6 = st.columns(2)
    col5.metric("Estimated LT1 (±9%)", f"{lt1_lower:.0f} - {lt1_upper:.0f} W")
    col6.metric("Predicted VO2max", f"{vo2max_pred:.2f} L/min")


    # --- Power-Duration Curve ---
    st.header("Your Power-Duration Curve")
    
    # Generate time data from 10s to 900s
    time_curve = np.arange(10, 901)
    
    # Calculate power using the formula P = (W' / t) + CP
    power_curve = (W_prime / time_curve) + CP
    
    # Create the plot with modern colors
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(time_curve, power_curve, label="Power-Duration Curve", color="#007ACC", linewidth=2)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel("Power (W)")
    ax.set_title("Power-Duration Curve")
    ax.grid(True, linestyle='--', alpha=0.6)
    
    # Add markers for the input powers
    ax.plot(t1, p3, marker='o', color='#FF5733', markersize=8, linestyle='None', label=f'3-min Power ({p3}W)')
    ax.plot(t2, p12, marker='o', color='#33C1FF', markersize=8, linestyle='None', label=f'12-min Power ({p12}W)')
    ax.legend()

    st.pyplot(fig)
    
    # --- Maximal Sustainable Power Calculator ---
    st.header("Maximal Sustainable Power Calculator")
    duration_input_min = st.number_input("Enter duration (minutes)", min_value=3, max_value=15, value=5, step=1)
    
    duration_input_sec = duration_input_min * 60
    msp = (W_prime / duration_input_sec) + CP
    
    st.metric(f"Predicted Max Power for {duration_input_min} minutes", f"{msp:.0f} W")
