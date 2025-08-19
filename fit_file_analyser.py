import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import math as m
import pandas as pd
from io import BytesIO

# --- App Title ---
st.title("W'bal Model Calculator")
st.markdown("Adjust the parameters in the sidebar to model W' balance over repeated intervals.")

# --- Sidebar for User Inputs ---
st.sidebar.header("Model Inputs")
reps = st.sidebar.slider("Number of Reps", 1, 20, 5)
CP = st.sidebar.slider("Critical Power (CP)", 100, 500, 300)
WP = st.sidebar.slider("W' Prime (W'P)", 10000, 30000, 20000)
duration = st.sidebar.slider("Work Interval Duration (s)", 30, 600, 180)
work_power = st.sidebar.slider("Work Interval Power (W)", 200, 800, 360)
recovery = st.sidebar.slider("Recovery Interval Duration (s)", 30, 600, 180)
recovery_power = st.sidebar.slider("Recovery Interval Power (W)", 50, 250, 200)

st.sidebar.header("Advanced Parameters")
A = st.sidebar.slider("Tau Constant (A)", 1000, 10000, 5184)
B = st.sidebar.slider("Tau Exponent (B)", -1.0, -0.1, -0.60)


# --- Calculation Logic ---
# This part is the same as your original script, but uses the slider values

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

# 1. Display the plot
st.header("W'bal vs. Time")
fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(time, W_bal)
ax.set_xlabel('Time (s)')
ax.set_ylabel('W′bal (J)')
ax.set_title('W′bal vs Time')
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

# 3. Create a download button for the data
# Function to convert DataFrame to Excel in memory
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Wbal_Output')
    processed_data = output.getvalue()
    return processed_data

excel_data = to_excel(df)

st.download_button(
    label="📥 Download Data as Excel",
    data=excel_data,
    file_name="Wbal_output.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

