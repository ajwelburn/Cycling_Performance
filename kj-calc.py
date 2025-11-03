import streamlit as st
import pandas as pd
from datetime import timedelta

# --- 1. CONFIGURATION AND UTILITIES ---

# Set up the app to use a simple, clean layout with the "steam lit" blue theme
st.set_page_config(
    page_title="CP Cycling Session Planner",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom style for the 'Steam Lit' aesthetic
st.markdown("""
<style>
    /* Main Streamlit Theme Tweak - White/Light Blue */
    .stApp {
        background-color: #eff6ff; /* Light blue background */
    }
    /* Header/Title */
    .st-emotion-cache-18ni7ap { /* Class for st.title container */
        background: linear-gradient(90deg, #60a5fa, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem; 
        font-weight: 800;
        text-align: center;
        padding-bottom: 20px;
    }
    /* Card Styling (for inputs and outputs) */
    .st-emotion-cache-1l0l2a9, .st-emotion-cache-16cq8s0, .st-emotion-cache-13bkzjm { /* Targeting column and container elements */
        background-color: white !important;
        border-radius: 1rem;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.2), 0 2px 4px -2px rgba(59, 130, 246, 0.1);
        border: 1px solid rgba(59, 130, 246, 0.2);
        margin-bottom: 15px;
    }
    /* Buttons */
    .stButton>button {
        background-color: #3b82f6;
        color: white;
        border-radius: 0.75rem;
        transition: background-color 0.2s;
        border: none;
    }
    .stButton>button:hover {
        background-color: #2563eb;
    }
    /* Zone colors in table */
    .zone-active-recovery { background-color: #9ca3af; color: white; }
    .zone-endurance { background-color: #10b981; color: white; }
    .zone-aerobic-intervals { background-color: #f59e0b; color: black; }
    .zone-threshold { background-color: #f97316; color: white; }
    .zone-vo2-max { background-color: #ef4444; color: white; }
    .zone-anaerobic-intervals { background-color: #9333ea; color: white; }
    .zone-neuromuscular { background-color: #ec4899; color: white; }
</style>
""", unsafe_allow_html=True)


# Training Zone Definitions
ZONE_MAP = [
    {"name": "Active Recovery", "min": 0, "max": 55, "class": "zone-active-recovery"},
    {"name": "Endurance", "min": 56, "max": 75, "class": "zone-endurance"},
    {"name": "Aerobic Intervals", "min": 76, "max": 90, "class": "zone-aerobic-intervals"},
    {"name": "Threshold", "min": 91, "max": 105, "class": "zone-threshold"},
    {"name": "VO2 Max", "min": 106, "max": 130, "class": "zone-vo2-max"},
    {"name": "Anaerobic Intervals", "min": 131, "max": 180, "class": "zone-anaerobic-intervals"},
    {"name": "Neuromuscular", "min": 181, "max": 500, "class": "zone-neuromuscular"}
]

# Initialize session state for the workout steps list
if 'session_steps' not in st.session_state:
    st.session_state.session_steps = []

def calculate_time_for_work(kj, power_w):
    """Calculates time (seconds) needed to complete a kJ work load."""
    if not power_w or power_w <= 0:
        return 0
    work_j = kj * 1000
    time_seconds = work_j / power_w
    return time_seconds

def format_time_duration(seconds):
    """Formats seconds into HH:MM:SS string."""
    if seconds <= 0:
        return "00:00:00"
    return str(timedelta(seconds=round(seconds)))

def format_time_min_sec(seconds):
    """Formats seconds into MM:SS string."""
    if seconds <= 0 or pd.isna(seconds):
        return "--:--"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"

# --- 2. LAYOUT AND INPUTS ---

st.title("CP Cycling Session Planner")

# Sidebar for Athlete Profile (Inputs)
with st.sidebar:
    st.header("🚴 Athlete Profile")
    cp = st.number_input(
        "Critical Power (CP) (Watts)",
        min_value=50,
        value=280,
        step=5,
        key='cp'
    )
    weight = st.number_input(
        "Weight (kg)",
        min_value=30.0,
        value=75.0,
        step=1.0,
        key='weight'
    )

# Main container for the app
main_cols = st.columns([1, 2])

# --- 3. TRAINING ZONES DISPLAY ---
with main_cols[0]:
    st.subheader("Training Zones")
    
    zone_data = []
    if cp > 0:
        for zone in ZONE_MAP:
            min_w = round(cp * zone['min'] / 100)
            max_w = round(cp * zone['max'] / 100)
            zone_data.append({
                "Zone": f"<span class='{zone['class']} px-2 py-1 rounded'>{zone['name']}</span>",
                "% CP": f"{zone['min']}% – {zone['max']}%",
                "Watts": f"{min_w} W – {max_w} W"
            })
    
    if zone_data:
        df_zones = pd.DataFrame(zone_data)
        st.markdown(df_zones.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.info("Enter CP to calculate training zones.")

# --- 4. KJ TIME CALCULATOR ---
with main_cols[1]:
    st.subheader("⏳ Work-Time Calculator (2000 kJ & 3000 kJ)")
    
    calc_cols = st.columns(3)
    
    # Input group for target power
    with calc_cols[0]:
        st.markdown("##### Target Power")
        power_type = st.radio(
            "Select Input Type",
            ('W', '% CP'),
            key='calc_power_type',
            horizontal=True
        )
        
        target_input = st.number_input(
            "Value",
            min_value=1,
            value=200 if power_type == 'W' else 70,
            step=1,
            key='calc_power_value'
        )
        
        target_watts = 0
        if power_type == 'W':
            target_watts = target_input
        elif cp > 0:
            target_watts = cp * target_input / 100

    # Calculation results
    time_2000 = calculate_time_for_work(2000, target_watts)
    time_3000 = calculate_time_for_work(3000, target_watts)

    with calc_cols[1]:
        st.markdown("##### Time for 2000 kJ")
        st.metric("Required Time", format_time_min_sec(time_2000))

    with calc_cols[2]:
        st.markdown("##### Time for 3000 kJ")
        st.metric("Required Time", format_time_min_sec(time_3000))

st.markdown("---")

# --- 5. SESSION BUILDER ---
st.header("📝 Workout Builder")

def add_step():
    """Adds a new step to the session state list."""
    duration = st.session_state.new_duration * 60 # Convert minutes to seconds
    power_type = st.session_state.new_power_type
    value = st.session_state.new_power_value
    
    if duration > 0 and value > 0:
        st.session_state.session_steps.append({
            'duration': duration,
            'type': power_type,
            'value': value,
            'id': len(st.session_state.session_steps) # Simple ID
        })
        st.toast("Workout step added!", icon="✅")

def remove_step(index):
    """Removes a step by its index in the list."""
    if 0 <= index < len(st.session_state.session_steps):
        st.session_state.session_steps.pop(index)
        st.toast("Workout step removed!", icon="🗑️")

# Input controls for adding steps
input_cols = st.columns([2, 1, 1, 1])
with input_cols[0]:
    st.number_input("Duration (Minutes)", min_value=1, value=5, key='new_duration')
with input_cols[1]:
    st.selectbox("Power Type", ('% CP', 'W'), key='new_power_type')
with input_cols[2]:
    st.number_input("Value", min_value=1, value=70, step=1, key='new_power_value')
with input_cols[3]:
    st.markdown("<br>", unsafe_allow_html=True) # Space to align button
    st.button("➕ Add Step", on_click=add_step, use_container_width=True)


session_cols = st.columns([2, 1])

# --- 6. SESSION BREAKDOWN (List) ---
with session_cols[0]:
    st.subheader("Session Breakdown")
    
    if not st.session_state.session_steps:
        st.info("Use the controls above to start building your workout.")
    else:
        step_data = []
        for i, step in enumerate(st.session_state.session_steps):
            power_w = 0
            
            if step['type'] == '% CP' and cp > 0:
                power_w = cp * step['value'] / 100
                power_display = f"{step['value']}% CP ({power_w:.0f} W)"
            elif step['type'] == 'W':
                power_w = step['value']
                percent = (power_w / cp) * 100 if cp > 0 else 0
                power_display = f"{power_w:.0f} W ({percent:.1f}% CP)"
            else:
                power_w = step['value']
                power_display = f"{power_w:.0f} W (CP required)"

            step_data.append({
                "#": i + 1,
                "Duration": format_time_min_sec(step['duration']),
                "Target": power_display,
                "Action": st.button("Remove", key=f"remove_{step['id']}", on_click=remove_step, args=(i,)),
            })

        df_steps = pd.DataFrame(step_data)
        st.dataframe(df_steps, hide_index=True, use_container_width=True)

# --- 7. TOTAL METRICS (Calculations) ---
with session_cols[1]:
    st.subheader("Total Metrics")
    
    total_time_s = 0
    total_work_kj = 0
    total_work_above_cp_kj = 0
    
    for step in st.session_state.session_steps:
        duration_s = step['duration']
        power_w = 0
        
        if step['type'] == '% CP' and cp > 0:
            power_w = cp * step['value'] / 100
        elif step['type'] == 'W':
            power_w = step['value']

        # Work calculation (J = W * s)
        work_j = power_w * duration_s
        work_kj = work_j / 1000

        total_time_s += duration_s
        total_work_kj += work_kj

        # Work above CP calculation (if power is above CP)
        if cp > 0 and power_w > cp:
            power_above_cp = power_w - cp
            work_above_cp_j = power_above_cp * duration_s
            total_work_above_cp_kj += work_above_cp_j / 1000

    # Final calculations
    effective_weight = weight if weight > 0 else 75
    total_kj_per_kg = total_work_kj / effective_weight if total_work_kj > 0 else 0
    avg_power_w = (total_work_kj * 1000) / total_time_s if total_time_s > 0 else 0
    total_kj_per_hour = (total_work_kj / total_time_s) * 3600 if total_time_s > 0 else 0

    
    # Display Metrics using st.metric
    col_metrics = st.columns(2)
    
    col_metrics[0].metric("Total Duration", format_time_duration(total_time_s))
    col_metrics[1].metric("Total Work (kJ)", f"{total_work_kj:.1f} kJ")
    
    col_metrics[0].metric("kJ Above CP", f"{total_work_above_cp_kj:.1f} kJ")
    col_metrics[1].metric("kJ/kg", f"{total_kj_per_kg:.2f}")

    col_metrics[0].metric("Avg Power (W)", f"{avg_power_w:.0f} W")
    col_metrics[1].metric("Total kJ/hour", f"{total_kj_per_hour:.1f} kJ/h")
