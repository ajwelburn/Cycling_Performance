import streamlit as st
import pandas as pd
from datetime import timedelta
import altair as alt # For chart visualization

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
    /* Main Streamlit Theme Tweak - White background */
    .stApp {
        background-color: #ffffff; /* Pure White background */
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
    /* Zone colors in table and chart - using hex codes directly for Altair and CSS */
    .zone-active-recovery { background-color: #9ca3af; color: white; } /* Gray */
    .zone-endurance { background-color: #10b981; color: white; } /* Green */
    .zone-aerobic-intervals { background-color: #f59e0b; color: black; } /* Amber */
    .zone-threshold { background-color: #f97316; color: white; } /* Orange */
    .zone-vo2-max { background-color: #ef4444; color: white; } /* Red */
    .zone-anaerobic-intervals { background-color: #9333ea; color: white; } /* Purple */
    .zone-neuromuscular { background-color: #ec4899; color: white; } /* Pink */
</style>
""", unsafe_allow_html=True)


# Training Zone Definitions with Hex Colors for Altair
ZONE_MAP = [
    {"name": "Active Recovery", "min": 0, "max": 55, "class": "zone-active-recovery", "color": "#9ca3af"},
    {"name": "Endurance", "min": 56, "max": 75, "class": "zone-endurance", "color": "#10b981"},
    {"name": "Aerobic Intervals", "min": 76, "max": 90, "class": "zone-aerobic-intervals", "color": "#f59e0b"},
    {"name": "Threshold", "min": 91, "max": 105, "class": "zone-threshold", "color": "#f97316"},
    {"name": "VO2 Max", "min": 106, "max": 130, "class": "zone-vo2-max", "color": "#ef4444"},
    {"name": "Anaerobic Intervals", "min": 131, "max": 180, "class": "zone-anaerobic-intervals", "color": "#9333ea"},
    {"name": "Neuromuscular", "min": 181, "max": 500, "class": "zone-neuromuscular", "color": "#ec4899"}
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
    if seconds <= 0 or pd.isna(seconds):
        return "00:00:00"
    return str(timedelta(seconds=round(seconds)))


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

# --- 4. KJ TIME CALCULATOR (HH:MM:SS) ---
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
        st.metric("Required Time", format_time_duration(time_2000)) 

    with calc_cols[2]:
        st.markdown("##### Time for 3000 kJ")
        st.metric("Required Time", format_time_duration(time_3000))

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

# --- 6. SESSION BREAKDOWN (List & Visualization) ---
with session_cols[0]:
    st.subheader("Session Breakdown")
    
    if not st.session_state.session_steps:
        st.info("Use the controls above to start building your workout.")
    else:
        step_data_for_display = [] # For the dataframe
        chart_data = [] # For Altair chart
        current_time_offset = 0

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

            # Determine zone for chart color
            percent_cp_actual = (power_w / cp) * 100 if cp > 0 else 0
            zone_info = next((z for z in ZONE_MAP if percent_cp_actual >= z['min'] and percent_cp_actual <= z['max']), None)
            zone_name = zone_info['name'] if zone_info else "Unknown"
            zone_color = zone_info['color'] if zone_info else "#cccccc" # Default gray

            step_data_for_display.append({
                "#": i + 1,
                "Duration": format_time_duration(step['duration']),
                "Target": power_display,
                "Zone": zone_name,
                "Action": st.button("Remove", key=f"remove_{step['id']}", on_click=remove_step, args=(i,)),
            })

            # Prepare data for chart
            chart_data.append({
                "start_time_s": current_time_offset,
                "end_time_s": current_time_offset + step['duration'],
                "duration_s": step['duration'],
                "power_w": power_w,
                "zone_color": zone_color,
                "zone_name": zone_name
            })
            current_time_offset += step['duration']


        df_steps_display = pd.DataFrame(step_data_for_display)
        st.dataframe(df_steps_display, hide_index=True, use_container_width=True)

        # --- Workout Visualization ---
        st.subheader("Workout Visualization")
        if chart_data:
            df_chart = pd.DataFrame(chart_data)

            # Create the Altair chart
            chart = alt.Chart(df_chart).mark_bar().encode(
                x=alt.X('start_time_s', title='Time (s)', axis=alt.Axis(format='m', title='Time (Minutes)')),
                x2='end_time_s',
                y=alt.Y('power_w', title='Power (Watts)', scale=alt.Scale(domain=[0, df_chart['power_w'].max() * 1.2])),
                color=alt.Color('zone_name', 
                                title='Zone',
                                scale=alt.Scale(domain=[z['name'] for z in ZONE_MAP], range=[z['color'] for z in ZONE_MAP])) # Use defined colors
            ).properties(
                title='Workout Power Profile',
                height=300
            ).interactive() # Enable zooming and panning

            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Add steps to visualize your workout.")


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
    total_kj_per_kg = total_work_kj / effective_weight if effective_weight > 0 else 0
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
