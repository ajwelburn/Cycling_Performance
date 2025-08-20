import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import math as m
import pandas as pd

# --- App Title ---
st.title("W'bal Model Calculator")
st.markdown("Adjust the parameters in the sidebar to model W' balance over repeated intervals.")
st.markdown("""
<small>Based on research by: Welburn, A.J., Pugh, C.F., Bailey, S.J. et al. W′ reconstitution modelling during intermittent exercise performed to task failure. Eur J Appl Physiol (2025). <a href="https://doi.org/10.1007/s00421-025-05912-0" target="_blank">https://doi.org/10.1007/s00421-025-05912-0</a></small>
""", unsafe_allow_html=True)


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
    # Set default values for A and B when not in use
    A = 5184
    B = -0.60

# --- Helper Function to Calculate Tau ---
def calculate_tau(model_type, DCP, WP, custom_A, custom_B):
    if DCP <= 0:
        return float('inf')
    if model_type == 'BART': return 2287.2 * (DCP ** -0.688)
    elif model_type == 'REG': return 5184 * (DCP ** -0.70)
    elif model_type == 'Skiba2': return WP / DCP
    else: return custom_A * (DCP ** custom_B)

# --- Proactive Session Viability Analysis (runs on every input change) ---
with st.expander("Show Session Viability Analysis", expanded=True):
    expenditure_rate = work_power - CP
    DCP = CP - recovery_power
    tau = calculate_tau(tau_option, DCP, WP, A, B)
    
    # Calculate the maximum possible expenditure (E_max) for the given recovery duration
    E_max = WP * (1 - m.exp(-recovery / tau)) if tau != float('inf') else 0
    
    # Calculate the required expenditure (E) for the given work duration
    E_req = expenditure_rate * duration

    # Check if the session is sustainable in a steady state
    sustainable = E_req <= E_max and expenditure_rate > 0

    if sustainable:
        st.success("✅ This session appears sustainable from a W'bal perspective.")
    else:
        st.warning("⚠️ This session may not be sustainable.")
        st.markdown("**Here are some suggestions to achieve a sustainable steady-state:**")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            # Suggest new work duration
            sugg_dur = m.floor(E_max / expenditure_rate) if expenditure_rate > 0 else None
            if sugg_dur is not None and sugg_dur > 0:
                st.info(f"**Hint 1: Adjust Work Duration**\n\nReduce to **≤ {sugg_dur} seconds**.")
            else:
                st.error("**Hint 1: Adjust Work Duration**\n\nCannot be sustained. Recovery is too short or recovery power is too high.")
        
        with col2:
            # Suggest new recovery duration
            sugg_rec = None
            if E_req < WP and E_req > 0:
                log_arg = 1 - (E_req / WP)
                if log_arg > 0:
                    sugg_rec = m.ceil(-tau * m.log(log_arg))
            
            if sugg_rec is not None and sugg_rec > 0:
                st.info(f"**Hint 2: Adjust Recovery Duration**\n\nIncrease to **≥ {sugg_rec} seconds**.")
            else:
                st.error("**Hint 2: Adjust Recovery Duration**\n\nCannot be sustained. Work interval is too demanding (requires >100% W').")
        
        with col3:
            st.info(f"**Hint 3: Reduce Repetitions**\n\nConsider reducing the number of repetitions to complete the session before depletion.")
        
        with col4:
            if tau_option == "Custom":
                st.info("**Hint 4: Adjust Tau Factors**\n\n- **A (scaling factor):** Increase for slower recovery.\n- **B (rate of decay):** Make less negative (e.g., -0.6 -> -0.5) for slower recovery.")

    st.caption("Remember, the W'bal model is a powerful tool to help make better informed decisions about session structure, not the absolute determinant of exercise performance.")


# --- Simulation Function ---
def run_wbal_simulation(model_type, custom_A=None, custom_B=None):
    Wbal = WP
    time, W_bal, power = [], [], []
    end_time = 0
    negative_wbal_detected = False
    depletion_time = None

    for i in range(reps):
        # Work Phase
        for t in range(duration):
            P1 = work_power
            expenditure = P1 - CP
            if expenditure > 0: Wbal -= expenditure
            if Wbal < 0 and not negative_wbal_detected:
                negative_wbal_detected = True
                depletion_time = t + end_time
            time.append(t + end_time)
            W_bal.append(Wbal)
            power.append(P1)

        # Recovery Phase
        Wexp_start_recovery = WP - Wbal
        for t in range(recovery):
            P2 = recovery_power
            DCP = CP - P2
            Tau = calculate_tau(model_type, DCP, WP, custom_A, custom_B)
            Wbal = WP - (Wexp_start_recovery * m.exp(-(t + 1) / Tau))
            Wbal = min(WP, Wbal)
            time.append(end_time + duration + t)
            W_bal.append(Wbal)
            power.append(P2)
        
        end_time = (i + 1) * (duration + recovery)
        
    return time, W_bal, power, negative_wbal_detected, depletion_time

# --- Run Main Simulation and Display Graphs ---
main_time, main_W_bal, main_power, main_negative, depletion_time = run_wbal_simulation(tau_option, A, B)

st.header(f"Simulation Results for: {tau_option} Model")
if main_negative:
    st.error("⚠️ W'bal Depleted during simulation!")

if main_time:
    # --- W'bal Graph ---
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

    # --- Power Graph ---
    fig_pow, ax_pow = plt.subplots(figsize=(10, 6))
    ax_pow.plot(main_time, main_power, label="Power", color='coral', linewidth=2)
    ax_pow.set_xlabel('Time (s)', fontsize=12)
    ax_pow.set_ylabel("Power (W)", fontsize=12)
    ax_pow.set_title("Power vs Time", fontsize=14, fontweight='bold')
    ax_pow.grid(True, linestyle='--', alpha=0.6)
    if depletion_time is not None:
        ax_pow.axvspan(depletion_time, max(main_time), color='red', alpha=0.2, label='Post-Depletion')
    ax_pow.legend()
    st.pyplot(fig_pow)
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
        if model == "Custom":
            comp_A, comp_B = A, B
            label = f"Custom (A={A}, B={B})" if tau_option == "Custom" else "Custom (User Selected)"
        else:
            comp_A, comp_B = None, None
            label = model
        time_comp, W_bal_comp, _, _, _ = run_wbal_simulation(model, comp_A, comp_B)
        if time_comp:
            ax_comp.plot(time_comp, np.array(W_bal_comp) / 1000, label=label, color=colors[model], linewidth=2)

    ax_comp.set_xlabel('Time (s)', fontsize=12)
    ax_comp.set_ylabel("W'bal (kJ)", fontsize=12)
    ax_comp.set_title("W'bal Model Comparison", fontsize=14, fontweight='bold')
    ax_comp.grid(True, linestyle='--', alpha=0.6)
    ax_comp.hlines(WP / 1000, 0, max(main_time), colors='grey', linestyles='--', label="W' Prime")
    ax_comp.hlines(0, 0, max(main_time), colors='red', linestyles='--', label='Depletion (0 kJ)')
    ax_comp.legend()
    st.pyplot(fig_comp)
