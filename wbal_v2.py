import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import math as m

st.set_page_config(layout="wide")

# ==============================================================================
# --- App State Initialization ---
# ==============================================================================
# Use session state to manage the dynamic number of efforts
if 'num_efforts' not in st.session_state:
    st.session_state.num_efforts = 1

# ==============================================================================
# --- Core Functions ---
# ==============================================================================

def calculate_tau(model_type, DCP, WP, custom_A, custom_B):
    """Calculates the time constant for W' reconstitution."""
    if DCP <= 0:
        return float('inf')  # Infinite tau, no recovery
    if model_type == 'BART': return 2287.2 * (DCP ** -0.688)
    elif model_type == 'REG': return 5184 * (DCP ** -0.70)
    elif model_type == 'Skiba2': return WP / DCP
    else: return custom_A * (DCP ** custom_B)

def run_wbal_simulation(workout_structure, CP, WP, tau_model, tau_A, tau_B, power_modifier=1.0):
    """
    Runs the W'bal simulation based on a structured workout plan.
    The power_modifier allows running scenarios (e.g., 5% less power).
    """
    Wbal = WP
    time, W_bal, power_profile = [0], [WP], []
    
    total_time = 0
    depletion_time = None
    negative_wbal_detected = False

    for segment in workout_structure:
        segment_duration = segment['duration']
        segment_power = segment['power']

        # Apply the power modifier ONLY to work intervals
        if segment['type'] == 'work':
            modified_power = segment_power * power_modifier
        else:
            modified_power = segment_power

        expenditure_rate = modified_power - CP
        
        if expenditure_rate > 0:  # W' is being expended
            for t in range(1, segment_duration + 1):
                Wbal -= expenditure_rate
                time.append(total_time + t)
                W_bal.append(Wbal)
                power_profile.append(modified_power)
                if Wbal < 0 and not negative_wbal_detected:
                    negative_wbal_detected = True
                    # Calculate the exact time to depletion
                    time_to_deplete = (W_bal[-2] / expenditure_rate) if expenditure_rate > 0 else 0
                    depletion_time = total_time + time_to_deplete
        
        else:  # W' is being reconstituted
            DCP = CP - modified_power
            tau = calculate_tau(tau_model, DCP, WP, tau_A, tau_B)
            Wexp_start_recovery = WP - Wbal
            
            for t in range(1, segment_duration + 1):
                Wbal = WP - (Wexp_start_recovery * m.exp(-t / tau)) if tau != float('inf') else Wbal
                Wbal = min(WP, Wbal)
                time.append(total_time + t)
                W_bal.append(Wbal)
                power_profile.append(modified_power)

        total_time += segment_duration

    # Ensure power_profile aligns with time axis (excluding time=0)
    if total_time > 0 and len(power_profile) > 0:
        power_profile = np.interp(np.arange(1, total_time + 1), time[1:], power_profile)

    return time, W_bal, list(power_profile), negative_wbal_detected, depletion_time


# ==============================================================================
# --- UI: Sidebar for Global Inputs ---
# ==============================================================================

st.sidebar.header("Athlete Parameters")
CP = st.sidebar.number_input("Critical Power (CP)", min_value=100, max_value=500, value=300, step=1)
WP = st.sidebar.number_input("W' Prime (W'P)", min_value=10000, max_value=50000, value=20000, step=100)

st.sidebar.header("Advanced Tau Model")
tau_option = st.sidebar.selectbox("Select Tau Model", ("Custom", "BART", "REG", "Skiba2"))

if tau_option == "Custom":
    A = st.sidebar.slider("Tau Constant (A)", 1000, 10000, 5184)
    B = st.sidebar.slider("Tau Exponent (B)", -1.0, -0.1, -0.60, step=0.01)
else:
    A, B = 5184, -0.60 # Default non-user-facing values

# ==============================================================================
# --- UI: Main App Layout ---
# ==============================================================================

st.title("Advanced W'bal Interval Designer & Simulator")
st.markdown("""
<small>Based on research by: Welburn, A.J., Pugh, C.F., Bailey, S.J. et al. W′ reconstitution modelling during intermittent exercise performed to task failure. Eur J Appl Physiol (2025). <a href="https://doi.org/10.1007/s00421-025-05912-0" target="_blank">https://doi.org/10.1007/s00421-025-05912-0</a></small>
""", unsafe_allow_html=True)

designer_tab, analysis_tab = st.tabs(["Workout Designer", "Simulation & Analysis"])

# --- Workout Designer Tab ---
with designer_tab:
    st.header("Design Your Interval Session")
    workout_structure = []

    # --- Step 1: Define the Efforts within a Block ---
    st.subheader("Step 1: Define the Efforts within a Block")
    st.session_state.num_efforts = st.number_input("How many different efforts per block?", min_value=1, max_value=10, step=1)
    
    efforts = []
    cols = st.columns(st.session_state.num_efforts)
    for i in range(st.session_state.num_efforts):
        with cols[i]:
            st.markdown(f"**Effort {i+1}**")
            duration = st.number_input(f"Duration (s) [{i+1}]", min_value=1, value=180, key=f"d_{i}")
            unit = st.radio(f"Power Unit [{i+1}]", ["Watts", "% of CP"], key=f"u_{i}")
            if unit == "Watts":
                power = st.number_input(f"Power (W) [{i+1}]", min_value=0, value=360, key=f"p_{i}")
            else:
                percent_cp = st.number_input(f"Power (% CP) [{i+1}]", min_value=0, value=120, key=f"pcp_{i}")
                power = CP * (percent_cp / 100)
            efforts.append({'type': 'work', 'power': power, 'duration': duration})

    # --- Step 2: Define Repetitions and Recovery ---
    st.subheader("Step 2: Define Repetitions & Recovery")
    reps_in_block = st.number_input("How many times to repeat this block?", min_value=1, value=5)
    
    rec_unit = st.radio("Block Recovery Power Unit", ["Watts", "% of CP"], key="rec_unit")
    if rec_unit == "Watts":
        recovery_power = st.number_input("Block Recovery Power (W)", min_value=0, value=200)
    else:
        rec_percent_cp = st.number_input("Block Recovery Power (% CP)", min_value=0, value=60)
        recovery_power = CP * (rec_percent_cp / 100)
    recovery_duration = st.number_input("Block Recovery Duration (s)", min_value=0, value=180)

    # --- Step 3: Structure as Sets (Optional) ---
    st.subheader("Step 3: Structure as Sets (Optional)")
    is_sets = st.checkbox("Structure workout into sets?")
    if is_sets:
        num_sets = st.number_input("How many sets?", min_value=1, value=3)
        set_rec_unit = st.radio("Set Recovery Power Unit", ["Watts", "% of CP"], key="set_rec_unit")
        if set_rec_unit == "Watts":
            set_recovery_power = st.number_input("Set Recovery Power (W)", min_value=0, value=150)
        else:
            set_rec_percent_cp = st.number_input("Set Recovery Power (% CP)", min_value=0, value=50)
            set_recovery_power = CP * (set_rec_percent_cp / 100)
        set_recovery_duration = st.number_input("Set Recovery Duration (s)", min_value=0, value=300)
    else:
        num_sets = 1
        set_recovery_power = 0
        set_recovery_duration = 0

    # --- Generate the final workout structure ---
    for s in range(num_sets):
        for r in range(reps_in_block):
            # Add the entire block of efforts back-to-back
            for effort in efforts:
                workout_structure.append(effort)
            
            # Add recovery between blocks, but not after the last block in a set
            if r < reps_in_block - 1:
                workout_structure.append({'type': 'recovery', 'power': recovery_power, 'duration': recovery_duration})
        
        # Add recovery between sets, but not after the final set
        if s < num_sets - 1:
            workout_structure.append({'type': 'recovery', 'power': set_recovery_power, 'duration': set_recovery_duration})
    
    st.success("Workout structure generated! Switch to the 'Simulation & Analysis' tab to see the results.")

# --- Analysis Tab ---
with analysis_tab:
    if not workout_structure:
        st.warning("Please design a workout in the 'Workout Designer' tab first.")
    else:
        # --- Run Simulations ---
        # Main simulation
        main_time, main_W_bal, main_power, main_negative, depletion_time = run_wbal_simulation(workout_structure, CP, WP, tau_option, A, B)
        # Scenario simulation (5% less power)
        scen_time, scen_W_bal, _, _, _ = run_wbal_simulation(workout_structure, CP, WP, tau_option, A, B, power_modifier=0.95)

        st.header("Simulation Results")
        if main_negative:
            st.error(f"⚠️ W'bal Depleted! Estimated time to depletion: {depletion_time:.0f} seconds.")
        else:
            st.success("✅ W'bal was not depleted during this session.")

        # --- W'bal Graph ---
        if main_time and len(main_time) > 1:
            st.subheader("W' Balance vs. Time")
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Plot 5% lower scenario first (background)
            ax.plot(scen_time, np.array(scen_W_bal) / 1000, color='gray', linewidth=2.5, alpha=0.8, linestyle='--', label="W'bal (at 95% intensity)")
            ax.fill_between(scen_time, np.array(scen_W_bal) / 1000, color='gray', alpha=0.1)

            # Plot main simulation
            ax.plot(main_time, np.array(main_W_bal) / 1000, color='dodgerblue', linewidth=2.5, label="W'bal (at 100% intensity)")
            ax.fill_between(main_time, np.array(main_W_bal) / 1000, color='dodgerblue', alpha=0.2)
            
            ax.set_xlabel('Time (s)', fontsize=12)
            ax.set_ylabel("W'bal (kJ)", fontsize=12)
            ax.grid(True, linestyle='--', alpha=0.6)
            ax.hlines(WP / 1000, 0, max(main_time), colors='grey', linestyles='--', label="W'")
            ax.hlines(0, 0, max(main_time), colors='red', linestyles='--', label='Depletion (0 kJ)')
            min_wbal_kj = min(main_W_bal) / 1000 if main_W_bal else 0
            max_wbal_kj = WP / 1000
            ax.set_ylim(min(min_wbal_kj * 1.1, -1), max_wbal_kj * 1.1)
            ax.legend()
            st.pyplot(fig)

            # --- Power Graph ---
            st.subheader("Power Profile vs. Time")
            fig_pow, ax_pow = plt.subplots(figsize=(12, 6))
            ax_pow.plot(main_time[1:], main_power, label="Power", color='coral', linewidth=2)
            ax_pow.set_xlabel('Time (s)', fontsize=12)
            ax_pow.set_ylabel("Power (W)", fontsize=12)
            ax_pow.grid(True, linestyle='--', alpha=0.6)
            if depletion_time is not None:
                ax_pow.axvspan(depletion_time, max(main_time), color='red', alpha=0.2, label='Post-Depletion')
            ax_pow.legend()
            st.pyplot(fig_pow)
        else:
            st.warning("Simulation did not produce data to plot. Please check your workout structure (e.g., ensure durations are > 0).")






