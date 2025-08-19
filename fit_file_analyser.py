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

for i in range(reps):
    # Work phase
    for t in range(duration):
        P1 = work_power
        # W'bal cannot go below zero
        expenditure = P1 - CP
        if expenditure > 0:
            Wbal = max(0, Wbal - expenditure)
        
        Wexp = WP - Wbal
        time.append(t + end_time)
        W_bal.append(Wbal)
        power.append(P1)

    # Recovery phase
    for t in range(recovery):
        P2 = recovery_power
        DCP = CP - P2
        # Avoid math errors if recovery power is at or above CP
        if DCP <= 0:
            Tau = float('inf') # Effectively no recovery
        else:
            Tau = A * (DCP ** B)
        
        # Calculate new W'bal during recovery
        Wbal = WP - (Wexp * m.exp(-(t+1) / Tau))
        Wbal = min(WP, Wbal) # W'bal cannot exceed W'P
        
        Wexp = WP - Wbal
        time.append(end_time + duration + t)
        W_bal.append(Wbal)
        power.append(P2)

    end_time = (i + 1) * (duration + recovery)

# --- Display Results ---

# Check if data was generated before trying to plot or display
if time:
    # 1. Display the plot
    st.header("W'bal vs. Time")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(time, W_bal)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel("W'bal (J)")
    ax.set_title("W'bal vs Time")
    ax.grid(True)
    ax.hlines(WP, 0, max(time), colors='grey', linestyles='--')
    ax.hlines(0, 0, max(time), colors='grey', linestyles='--')
    st.pyplot(fig)

    # 2. Display the data in a table
    st.header("Output Data")
    df = pd.DataFrame({
        'Time (s)': time,
        'Power (W)': power,
        'W′bal (J)': W_bal
    })
    st.dataframe(df)
else:
    st.warning("No data generated. Increase the number of reps to at least 1.")
