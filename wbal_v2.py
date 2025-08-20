import streamlit as st
import plotly.graph_objects as go
import numpy as np
import math as m

st.set_page_config(layout="wide", page_title="W'bal Simulator")

# ==============================================================================
# --- App State Initialization ---
# ==============================================================================
if 'num_efforts' not in st.session_state:
    st.session_state.num_efforts = 1

# ==============================================================================
# --- Core Functions ---
# ==============================================================================

def calculate_tau(model_type, DCP, W_prime, custom_A, custom_B):
    if DCP <= 0: return float('inf')
    if model_type == 'BART': return 2287.2 * (DCP ** -0.688)
    elif model_type == 'REG': return 5184 * (DCP ** -0.70)
    elif model_type == 'Skiba2': return W_prime / DCP
    else: return custom_A * (DCP ** custom_B)

def run_wbal_simulation(workout_structure, CP, W_prime, tau_model, tau_A, tau_B):
    Wbal = W_prime
    time, W_bal_data, power_profile = [0], [W_prime], []
    
    total_time = 0
    depletion_time = None
    negative_wbal_detected = False

    for segment in workout_structure:
        segment_duration = segment['duration']
        power = segment['power']
        expenditure_rate = power - CP
        
        if expenditure_rate > 0:
            for t in range(1, segment_duration + 1):
                Wbal -= expenditure_rate
                time.append(total_time + t)
                W_bal_data.append(Wbal)
                power_profile.append(power)
                if Wbal < 0 and not negative_wbal_detected:
                    negative_wbal_detected = True
                    time_to_deplete = (W_bal_data[-2] / expenditure_rate) if expenditure_rate > 0 else 0
                    depletion_time = total_time + time_to_deplete
        else:
            DCP = CP - power
            tau = calculate_tau(tau_model, DCP, W_prime, tau_A, tau_B)
            Wexp_start_recovery = W_prime - Wbal
            for t in range(1, segment_duration + 1):
                Wbal = W_prime - (Wexp_start_recovery * m.exp(-t / tau)) if tau != float('inf') else Wbal
                Wbal = min(W_prime, Wbal)
                time.append(total_time + t)
                W_bal_data.append(Wbal)
                power_profile.append(power)
        total_time += segment_duration

    if total_time > 0 and len(power_profile) > 0:
        power_profile_interp = np.interp(np.arange(1, total_time + 1), time[1:], power_profile)

    return time, W_bal_data, list(power_profile_interp), negative_wbal_detected, depletion_time

# ==============================================================================
# --- Charting Functions ---
# ==============================================================================

def create_wbal_chart(time, W_bal_data, W_prime):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=time, y=np.array(W_bal_data) / 1000,
        fill='tozeroy', mode='lines', line_color='#08F7FE', name="W'bal"
    ))
    fig.add_hline(y=W_prime / 1000, line_dash="dash", line_color="grey", annotation_text="W'")
    fig.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="Depletion")
    fig.update_layout(
        title_text="<b>W' Balance vs. Time</b>", template='plotly_dark',
        xaxis_title="Time (s)", yaxis_title="W'bal (kJ)",
        height=500
    )
    return fig

def create_power_chart(time, power_profile, CP, depletion_time):
    fig = go.Figure()

    # Base power profile (filled area)
    fig.add_trace(go.Scatter(
        x=time, y=power_profile,
        fill='tozeroy', mode='lines', line_color='grey', name='Power < CP',
        fillcolor='rgba(128, 128, 128, 0.2)'
    ))

    # Highlight segments above CP
    above_cp_indices = np.where(np.array(power_profile) > CP)[0]
    start = -1
    for i in range(len(above_cp_indices)):
        if i == 0 or above_cp_indices[i] != above_cp_indices[i-1] + 1:
            start = above_cp_indices[i]
        if i == len(above_cp_indices) - 1 or above_cp_indices[i] != above_cp_indices[i+1] - 1:
            end = above_cp_indices[i]
            fig.add_trace(go.Scatter(
                x=time[start:end+2], y=power_profile[start:end+1],
                mode='lines', line_color='#FFAF42', name='Power > CP',
                fill='tozeroy', fillcolor='rgba(255, 175, 66, 0.3)'
            ))

    fig.add_hline(y=CP, line_dash="dash", line_color="white", annotation_text="CP")
    
    if depletion_time:
        fig.add_vrect(x0=depletion_time, x1=max(time), fillcolor="red", opacity=0.2, layer="below", line_width=0, annotation_text="Depletion")

    fig.update_layout(
        title_text="<b>Power Profile vs. Time</b>", template='plotly_dark',
        xaxis_title="Time (s)", yaxis_title="Power (W)",
        height=500, showlegend=False
    )
    return fig

# ==============================================================================
# --- UI: Sidebar for Global Inputs ---
# ==============================================================================

st.sidebar.header("Athlete Parameters")
CP = st.sidebar.number_input("Critical Power (CP)", 100, 500, 300, 1)
W_prime = st.sidebar.number_input("W' (Joules)", 10000, 50000, 20000, 100)

st.sidebar.header("Advanced Tau Model")
tau_option = st.sidebar.selectbox("Select Tau Model", ("Custom", "BART", "REG", "Skiba2"))
if tau_option == "Custom":
    A = st.sidebar.slider("Tau Constant (A)", 1000, 10000, 5184)
    B = st.sidebar.slider("Tau Exponent (B)", -1.0, -0.1, -0.60, 0.01)
else:
    A, B = 5184, -0.60

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

    st.subheader("Step 1: Define the Efforts within a single Block")
    st.session_state.num_efforts = st.number_input("How many different efforts per block?", 1, 10, 1)
    
    efforts = []
    cols = st.columns(st.session_state.num_efforts)
    for i in range(st.session_state.num_efforts):
        with cols[i]:
            st.markdown(f"**Effort {i+1}**")
            duration = st.number_input(f"Duration (s) [{i+1}]", 1, value=180, key=f"d_{i}")
            unit = st.radio(f"Power Unit [{i+1}]", ["Watts", "% of CP"], key=f"u_{i}")
            if unit == "Watts":
                power = st.number_input(f"Power (W) [{i+1}]", 0, value=360, key=f"p_{i}")
            else:
                percent_cp = st.number_input(f"Power (% CP) [{i+1}]", 0, value=120, key=f"pcp_{i}")
                power = CP * (percent_cp / 100)
            efforts.append({'type': 'work', 'power': power, 'duration': duration})

    st.subheader("Step 2: Define Repetitions per Set")
    reps_per_set = st.number_input("How many times to repeat the block of efforts?", 1, value=5)
    
    st.subheader("Step 3: Define Sets & Recovery")
    num_sets = st.number_input("How many sets?", 1, value=1)
    
    if num_sets > 1:
        set_rec_unit = st.radio("Power Unit between Sets", ["Watts", "% of CP"], key="set_rec_unit")
        if set_rec_unit == "Watts":
            set_recovery_power = st.number_input("Power between Sets (W)", 0, value=150)
        else:
            set_rec_percent_cp = st.number_input("Power between Sets (% CP)", 0, value=50)
            set_recovery_power = CP * (set_rec_percent_cp / 100)
        set_recovery_duration = st.number_input("Duration between Sets (s)", 0, value=300)
    else:
        set_recovery_power, set_recovery_duration = 0, 0

    for s in range(num_sets):
        for r in range(reps_per_set):
            workout_structure.extend(efforts)
        if s < num_sets - 1:
            workout_structure.append({'type': 'recovery', 'power': set_recovery_power, 'duration': set_recovery_duration})
    
    st.success("Workout structure generated! Switch to the 'Simulation & Analysis' tab to see the results.")

# --- Analysis Tab ---
with analysis_tab:
    if not workout_structure:
        st.warning("Please design a workout in the 'Workout Designer' tab first.")
    else:
        main_time, main_W_bal, main_power, main_negative, depletion_time = run_wbal_simulation(workout_structure, CP, W_prime, tau_option, A, B)

        st.header("Simulation Results")
        
        # --- Summary Metrics ---
        total_duration_seconds = sum(s['duration'] for s in workout_structure)
        total_duration_minutes = total_duration_seconds / 60
        weighted_avg_power = sum(s['power'] * s['duration'] for s in workout_structure) / total_duration_seconds if total_duration_seconds > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Duration", f"{total_duration_minutes:.1f} min")
        with col2:
            st.metric("Average Power", f"{weighted_avg_power:.0f} W")
        with col3:
            if main_negative:
                st.metric("Session Status", "🔴 Depleted", help=f"Estimated depletion at {depletion_time:.0f}s")
            else:
                st.metric("Session Status", "🟢 Sustainable")
        
        st.divider()

        # --- Charts ---
        if main_time and len(main_time) > 1:
            st.plotly_chart(create_wbal_chart(main_time, main_W_bal, W_prime), use_container_width=True)
            st.plotly_chart(create_power_chart(main_time[1:], main_power, CP, depletion_time), use_container_width=True)
        else:
            st.warning("Simulation did not produce data to plot. Check your workout structure.")

