import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import math as m
import pandas as pd

# --- App Title ---
st.title("W'bal Model Calculator")
st.markdown("Adjust the parameters in the sidebar to model W' balance over repeated intervals.")

# --- Sidebar for User Inputs ---
st.sidebar.header("Model Inputs")
# Use number_input for type-in boxes
reps = st.sidebar.number_input("Number of Reps", min_value=1, max_value=50, value=5, step=1)
CP = st.sidebar.number_input("Critical Power (CP)", min_value=100, max_value=500, value=300, step=1)
WP = st.sidebar.number_input("W' Prime (W'P)", min_value=10000, max_value=50000, value=20000, step=100)
duration = st.sidebar.number_input("Work Interval Duration (s)", min_value=10, max_value=1200, value=180, step=1)
work_power = st.sidebar.number_input("Work Interval Power (W)", min_value=100, max_value=1000, value=360, step=1)
recovery = st.sidebar.number_input("Recovery Interval Duration (s)", min_value=10, max_value=1200, value=180, step=1)
recovery_power = st.sidebar.number_input("Recovery Interval Power (W)", min_value=0, max_value=500, value=200, step=1)

st.sidebar.header("Advanced Parameters")
# Keep sliders for A and B
A = st.sidebar.slider("Tau Constant (A)", 1000, 10000, 5184)
B = st.sidebar.slider("Tau Exponent (B)", -1.0, -0.1, -0.60, step=0.01)


# --- Calculation Logic ---
# Initialize variables
Wbal = WP
Wexp = 0
time = []
W_bal = []
power = []
end_time = 0

# Variables for suggestions
negative_wbal_detected = False
suggested_duration = None
suggested_recovery = None
prev_Wexp_start_recovery = 0 # Store the W'exp at the start of the previous recovery

for i in range(reps):
    # --- Work phase ---
    Wbal_start_work = Wbal # W'bal at the beginning of the work interval
    
    for t in range(duration):
        P1 = work_power
        expenditure = P1 - CP
        
        # Allow Wbal to go negative for detection, but don't clamp it here yet
        if expenditure > 0:
            Wbal -= expenditure
        
        # Detect if W'bal goes negative for the first time
        if Wbal < 0 and not negative_wbal_detected:
            negative_wbal_detected = True
            
            # --- Suggestion 1: Adjust Work Interval Duration ---
            # Calculate the max duration possible with the starting W'bal
            expenditure_rate = work_power - CP
            if expenditure_rate > 0:
                # Floor the result to get a whole number of seconds that is safe
                suggested_duration = m.floor(Wbal_start_work / expenditure_rate)

            # --- Suggestion 2: Adjust Recovery Interval Duration ---
            # Calculate the recovery time needed in the *previous* interval
            # to avoid depletion in the *current* interval.
            Wbal_needed_for_work = (work_power - CP) * duration
            DCP_prev = CP - recovery_power
            
            if DCP_prev > 0 and prev_Wexp_start_recovery > 0 and Wbal_needed_for_work < WP:
                Tau_prev = A * (DCP_prev ** B)
                # Argument for the natural logarithm
                log_arg = (WP - Wbal_needed_for_work) / prev_Wexp_start_recovery
                if log_arg > 0:
                    # Ceil the result to ensure full recovery
                    suggested_recovery = m.ceil(-Tau_prev * m.log(log_arg))

        Wexp = WP - Wbal
        time.append(t + end_time)
        W_bal.append(Wbal)
        power.append(P1)

    # --- Recovery phase ---
    Wexp_start_recovery = Wexp
    
    for t in range(recovery):
        P2 = recovery_power
        DCP = CP - P2
        
        if DCP <= 0:
            Tau = float('inf') # Effectively no recovery
        else:
            Tau = A * (DCP ** B)
        
        # Mono-exponential recovery model
        Wbal = WP - (Wexp_start_recovery * m.exp(-(t + 1) / Tau))
        Wbal = min(WP, Wbal) # W'bal cannot exceed W'P
        
        time.append(end_time + duration + t)
        W_bal.append(Wbal)
        power.append(P2)
    
    # Update Wexp and store the starting W'exp for the next loop's suggestion calculation
    Wexp = WP - Wbal
    prev_Wexp_start_recovery = Wexp_start_recovery
    end_time = (i + 1) * (duration + recovery)

# --- Display Results ---

# Display pop-up message if W'bal went negative
if negative_wbal_detected:
    st.error("⚠️ W'bal Depleted!")
    st.markdown(
        "Your W' balance dropped below zero, which is not physiologically possible. "
        "This indicates the work interval is too long or intense for the given recovery."
    )
    st.markdown("**Here are some suggestions to make the session sustainable:**")
    
    col1, col2 = st.columns(2)
    with col1:
        if suggested_duration is not None and suggested_duration > 0:
            st.info(f"**Option 1: Adjust Work Duration**\n\n"
                    f"Reduce the work interval duration to **{suggested_duration} seconds**.")
        else:
            st.warning("**Option 1: Adjust Work Duration**\n\n"
                       "Cannot be calculated. The work power might be too high "
                       "or the starting W'bal was already zero.")
    with col2:
        if suggested_recovery is not None and suggested_recovery > 0:
            st.info(f"**Option 2: Adjust Recovery Duration**\n\n"
                    f"Increase the recovery interval duration to **{suggested_recovery} seconds**.")
        else:
            st.warning("**Option 2: Adjust Recovery Duration**\n\n"
                       "Cannot be calculated. The required W'bal might be higher than W' Prime, "
                       "or recovery from the previous interval was not possible.")


# Check if data was generated before trying to plot
if time:
    # Display the plot
    st.header("W'bal vs. Time")
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot the W'bal line
    ax.plot(time, np.array(W_bal) / 1000, label="W'bal", color='dodgerblue', linewidth=2)
    
    # Shade the area under the curve
    ax.fill_between(time, np.array(W_bal) / 1000, color='dodgerblue', alpha=0.2)
    
    # Formatting
    ax.set_xlabel('Time (s)', fontsize=12)
    ax.set_ylabel("W'bal (kJ)", fontsize=12)
    ax.set_title("W'bal vs Time", fontsize=14, fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.6)
    
    # Add horizontal lines for WP and zero, extending to the max time
    ax.hlines(WP / 1000, 0, max(time), colors='grey', linestyles='--', label="W' Prime")
    ax.hlines(0, 0, max(time), colors='red', linestyles='--', label='Depletion (0 kJ)')
    
    # Set y-axis limits to ensure visibility below zero
    min_wbal_kj = min(W_bal) / 1000
    max_wbal_kj = WP / 1000
    ax.set_ylim(min(min_wbal_kj * 1.1, -1), max_wbal_kj * 1.1)
    
    ax.legend()
    st.pyplot(fig)

else:
    st.warning("No data generated. Increase the number of reps to at least 1.")
