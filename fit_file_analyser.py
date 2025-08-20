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
reps = st.sidebar.number_input("Number of Reps", min_value=1, max_value=50, value=5, step=1)
CP = st.sidebar.number_input("Critical Power (CP)", min_value=100, max_value=500, value=300, step=1)
WP = st.sidebar.number_input("W' Prime (W'P)", min_value=10000, max_value=50000, value=20000, step=100)
duration = st.sidebar.number_input("Work Interval Duration (s)", min_value=10, max_value=1200, value=180, step=1)
work_power = st.sidebar.number_input("Work Interval Power (W)", min_value=100, max_value=1000, value=360, step=1)
recovery = st.sidebar.number_input("Recovery Interval Duration (s)", min_value=10, max_value=1200, value=180, step=1)
recovery_power = st.sidebar.number_input("Recovery Interval Power (W)", min_value=0, max_value=500, value=200, step=1)

st.sidebar.header("Advanced Parameters")
tau_option = st.sidebar.selectbox(
    "Select Tau Model",
    ("Custom", "BART", "REG", "Skiba2")
)

# Conditionally show A and B sliders only for the "Custom" option
if tau_option == "Custom":
    A = st.sidebar.slider("Tau Constant (A)", 1000, 10000, 5184)
    B = st.sidebar.slider("Tau Exponent (B)", -1.0, -0.1, -0.60, step=0.01)
else:
    # Set default values for A and B when not in use, they won't be used in calculations
    A = 5184
    B = -0.60

# --- Calculation Function ---
def run_wbal_simulation(model_type, custom_A=None, custom_B=None):
    """
    Runs the W'bal simulation for a given model type.
    Returns time, W_bal, and depletion information.
    """
    Wbal = WP
    Wexp = 0
    time = []
    W_bal = []
    end_time = 0
    negative_wbal_detected = False
    suggested_duration = None
    suggested_recovery = None
    prev_Wexp_start_recovery = 0

    for i in range(reps):
        Wbal_start_work = Wbal
        for t in range(duration):
            P1 = work_power
            expenditure = P1 - CP
            if expenditure > 0:
                Wbal -= expenditure
            
            if Wbal < 0 and not negative_wbal_detected:
                negative_wbal_detected = True
                expenditure_rate = work_power - CP
                if expenditure_rate > 0:
                    suggested_duration = m.floor(Wbal_start_work / expenditure_rate)
                
                Wbal_needed_for_work = (work_power - CP) * duration
                DCP_prev = CP - recovery_power
                if DCP_prev > 0 and prev_Wexp_start_recovery > 0 and Wbal_needed_for_work < WP:
                    if model_type == 'BART':
                        Tau_prev = 2287.2 * (DCP_prev ** -0.688)
                    elif model_type == 'REG':
                        Tau_prev = 5184 * (DCP_prev ** -0.70)
                    elif model_type == 'Skiba2':
                        Tau_prev = WP / DCP_prev
                    else: # Custom
                        Tau_prev = custom_A * (DCP_prev ** custom_B)
                    
                    log_arg = (WP - Wbal_needed_for_work) / prev_Wexp_start_recovery
                    if log_arg > 0:
                        suggested_recovery = m.ceil(-Tau_prev * m.log(log_arg))
            
            Wexp = WP - Wbal
            time.append(t + end_time)
            W_bal.append(Wbal)

        Wexp_start_recovery = Wexp
        for t in range(recovery):
            P2 = recovery_power
            DCP = CP - P2
            
            if DCP <= 0:
                Tau = float('inf')
            else:
                if model_type == 'BART':
                    Tau = 2287.2 * (DCP ** -0.688)
                elif model_type == 'REG':
                    Tau = 5184 * (DCP ** -0.70)
                elif model_type == 'Skiba2':
                    Tau = WP / DCP
                else: # Custom
                    Tau = custom_A * (DCP ** custom_B)
            
            Wbal = WP - (Wexp_start_recovery * m.exp(-(t + 1) / Tau))
            Wbal = min(WP, Wbal)
            time.append(end_time + duration + t)
            W_bal.append(Wbal)
        
        Wexp = WP - Wbal
        prev_Wexp_start_recovery = Wexp_start_recovery
        end_time = (i + 1) * (duration + recovery)
        
    return time, W_bal, negative_wbal_detected, suggested_duration, suggested_recovery

# --- Run Main Simulation for User's Selection ---
main_time, main_W_bal, main_negative, main_sugg_dur, main_sugg_rec = run_wbal_simulation(tau_option, A, B)

# --- Display Main Results ---
st.header(f"Results for: {tau_option} Model")

if main_negative:
    st.error("⚠️ W'bal Depleted!")
    st.markdown("Your W' balance dropped below zero, this suggest the session may not be possiable.")
    st.markdown("**Here are some suggestions to make the session sustainable:**")
    col1, col2 = st.columns(2)
    with col1:
        if main_sugg_dur is not None and main_sugg_dur > 0:
            st.info(f"**Option 1: Adjust Work Duration**\n\nReduce to **{main_sugg_dur} seconds**.")
        else:
            st.warning("**Option 1: Adjust Work Duration**\n\nCannot be calculated.")
    with col2:
        if main_sugg_rec is not None and main_sugg_rec > 0:
            st.info(f"**Option 2: Adjust Recovery Duration**\n\nIncrease to **{main_sugg_rec} seconds**.")
        else:
            st.warning("**Option 2: Adjust Recovery Duration**\n\nCannot be calculated.")

if main_time:
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(main_time, np.array(main_W_bal) / 1000, label="W'bal", color='dodgerblue', linewidth=2)
    ax.fill_between(main_time, np.array(main_W_bal) / 1000, color='dodgerblue', alpha=0.2)
    ax.set_xlabel('Time (s)', fontsize=12)
    ax.set_ylabel("W'bal (kJ)", fontsize=12)
    ax.set_title("W'bal vs Time", fontsize=14, fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.hlines(WP / 1000, 0, max(main_time), colors='grey', linestyles='--', label="W' Prime")
    ax.hlines(0, 0, max(main_time), colors='red', linestyles='--', label='Depletion (0 kJ)')
    min_wbal_kj = min(main_W_bal) / 1000
    max_wbal_kj = WP / 1000
    ax.set_ylim(min(min_wbal_kj * 1.1, -1), max_wbal_kj * 1.1)
    ax.legend()
    st.pyplot(fig)
else:
    st.warning("No data generated. Increase the number of reps to at least 1.")

# --- Comparison Graph ---
st.header("Tau Model Comparison")
st.markdown("This graph compares the W'bal kinetics of different Tau models using your current settings.")

if main_time:
    fig_comp, ax_comp = plt.subplots(figsize=(10, 6))
    
    models_to_compare = ["BART", "REG", "Skiba2", "Custom"]
    colors = {'BART': 'orange', 'REG': 'green', 'Skiba2': 'purple', 'Custom': 'dodgerblue'}

    for model in models_to_compare:
        # For the custom model, use the user's selected A and B
        if model == "Custom":
            comp_A, comp_B = A, B
            label = f"Custom (A={A}, B={B})" if tau_option == "Custom" else "Custom (User Selected)"
        else:
            comp_A, comp_B = None, None # Not needed for preset models
            label = model
            
        time_comp, W_bal_comp, _, _, _ = run_wbal_simulation(model, comp_A, comp_B)
        
        if time_comp:
            ax_comp.plot(time_comp, np.array(W_bal_comp) / 1000, label=label, color=colors[model], linewidth=2)

    ax_comp.set_xlabel('Time (s)', fontsize=12)
    ax_comp.set_ylabel("W'bal (kJ)", fontsize=12)
    ax_comp.set_title("W'bal Model Comparison", fontsize=14, fontweight='bold')
    ax_comp.grid(True, linestyle='--', alpha=0.6)
    ax_comp.hlines(WP / 1000, 0, max(main_time), colors='grey', linestyles='--')
    ax_comp.hlines(0, 0, max(main_time), colors='red', linestyles='--')
    ax_comp.legend()
    st.pyplot(fig_comp)
