import streamlit as st
import pandas as pd
from datetime import timedelta
import altair as alt
import re # For regular expression for time parsing

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
    hours, remainder = divmod(round(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

def parse_hhmmss_to_seconds(hhmmss_str):
    """Parses HH:MM:SS string to total seconds."""
    if not hhmmss_str:
        return 0
    
    # Regex to match H:M:S, HH:MM:SS, M:S, MM:SS formats
    match = re.match(r'^(?:(\d+):)?(\d{1,2}):(\d{1,2})$', hhmmss_str)
    if not match:
        return None # Indicate invalid format

    parts = match.groups()
    hours = int(parts[0]) if parts[0] else 0
    minutes = int(parts[1])
    seconds = int(parts[2])

    if minutes >= 60 or seconds >= 60:
        return None # Invalid minutes/seconds values

    return hours * 3600 + minutes * 60 + seconds

def get_carbs_recommendation(total_time_s):
    """Provides carbohydrate intake recommendations based on total duration (seconds)."""
    
    total_time_hours = total_time_s / 3600
    
    if total_time_hours <= 0:
        # FIX: Ensure a tuple of two items is always returned for unpacking to work.
        return "No session defined.", 0
    elif total_time_hours < 1:
        # Less than 1 hour, fueling is usually not required unless high intensity
        rate = "0–30 g/h (Focus on water/electrolytes)"
        total_g = 0
    elif total_time_hours <= 2.5:
        # 1 to 2.5 hours
        rate = "30–60 g/h"
        # Calculate for a mid-range of 45 g/h
        total_g = round(total_time_hours * 45)
    else:
        # Over 2.5 hours
        rate = "60–90 g/h (Up to 120 g/h for elite/specialized)"
        # Calculate for a mid-range of 75 g/h
        total_g = round(total_time_hours * 75)
    
    return rate, total_g


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

# --- Custom input for duration in HH:MM:SS ---
duration_str = st.text_input("Duration (HH:MM:SS)", value="00:05:00", key='new_duration_str',
                             help="Enter duration in HH:MM:SS, MM:SS, or M:S format. E.g., 00:05:00, 5:00, 1:30")

# Parse and validate duration
new_duration_seconds = parse_hhmmss_to_seconds(duration_str)
if new_duration_seconds is None:
    st.error("Invalid duration format. Please use HH:MM:SS (e.g., 00:05:00) or MM:SS (e.g., 05:00).")
    # Set a placeholder value if invalid to prevent errors downstream, but block add step
    new_duration_seconds = 0 


def add_step_callback():
    """Callback for adding a new step."""
    if new_duration_seconds > 0: # Only add if duration is valid and > 0
        st.session_state.session_steps.append({
            'duration': new_duration_seconds,
            'type': st.session_state.new_power_type,
            'value': st.session_state.new_power_value,
            'id': pd.Timestamp.now().value # Use a unique ID based on timestamp
        })
        st.toast("Workout step added!", icon="✅")
    else:
        st.warning("Cannot add step with invalid or zero duration.")

def copy_step_callback(step_data):
    """Callback for copying an existing step."""
    st.session_state.session_steps.append({
        'duration': step_data['duration'],
        'type': step_data['type'],
        'value': step_data['value'],
        'id': pd.Timestamp.now().value + 1 # New unique ID (ensure unique even if timestamp is same)
    })
    st.toast("Workout step copied!", icon="📋")

def remove_step(index):
    """Removes a step by its index in the list."""
    if 0 <= index < len(st.session_state.session_steps):
        st.session_state.session_steps.pop(index)
        st.toast("Workout step removed!", icon="🗑️")

# Input controls for adding steps
input_cols = st.columns([2, 1, 1, 1])
with input_cols[0]: # This column now implicitly handles the duration_str text input above
    pass # Duration input is already defined
with input_cols[1]:
    st.selectbox("Power Type", ('% CP', 'W'), key='new_power_type')
with input_cols[2]:
    st.number_input("Value", min_value=1, value=70, step=1, key='new_power_value')
with input_cols[3]:
    st.markdown("<br>", unsafe_allow_html=True) # Space to align button
    st.button("➕ Add Step", on_click=add_step_callback, use_container_width=True, 
              disabled=(new_duration_seconds == 0)) # Disable if duration is invalid or zero


session_cols = st.columns([2, 1])

# --- 6. SESSION BREAKDOWN (List & Visualization) ---
with session_cols[0]:
    st.subheader("Session Breakdown")
    
    if not st.session_state.session_steps:
        st.info("Use the controls above to start building your workout.")
    else:
        chart_data = [] # For Altair chart
        current_time_offset = 0

        max_power_in_session = 0 # To determine dynamic y-axis scale
        
        # Custom display for steps with action buttons
        st.markdown("**Current Steps:**")
        st.markdown(
            """
            | # | Duration | Target | Zone |
            |---|---|---|---|
            """, unsafe_allow_html=True
        )

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

            max_power_in_session = max(max_power_in_session, power_w)

            # Determine zone name for color display
            percent_cp_actual = (power_w / cp) * 100 if cp > 0 else 0
            zone_info = next((z for z in ZONE_MAP if percent_cp_actual >= z['min'] and percent_cp_actual <= z['max']), None)
            zone_name = zone_info['name'] if zone_info else "Unknown"
            
            # --- Rendering the row data in Markdown table format ---
            st.markdown(f"| {i+1} | {format_time_duration(step['duration'])} | {power_display} | {zone_name} |", unsafe_allow_html=True)
            
            # --- Action buttons for this row (FIXED LOCATION) ---
            # These buttons must be rendered *outside* of the markdown table string
            # We use columns to align them horizontally beneath the table row
            col_d, col_r, _ = st.columns([0.2, 0.2, 0.6])
            with col_d:
                # FIX: Ensure unique key for copy button
                st.button("Copy 📋", key=f"copy_{step['id']}", on_click=copy_step_callback, args=(step,), use_container_width=True)
            with col_r:
                # FIX: Ensure unique key for remove button
                st.button("Remove 🗑️", key=f"remove_{step['id']}", on_click=remove_step, args=(i,), use_container_width=True)
            st.markdown("---")
            
            # Prepare data for chart
            chart_data.append({
                "start_time_s": current_time_offset,
                "end_time_s": current_time_offset + step['duration'],
                "duration_s": step['duration'],
                "power_w": power_w,
                "zone_color": zone_color,
                "zone_name": zone_name,
                "step_index": i + 1, # Add step index for better tooltips
            })
            current_time_offset += step['duration']
            

        # --- Workout Visualization ---
        st.subheader("Workout Visualization")
        if chart_data:
            df_chart = pd.DataFrame(chart_data)

            # Determine y-axis scale based on highest power
            y_max_scale = 1000 # Default max
            if max_power_in_session > 1000:
                y_max_scale = max_power_in_session * 1.5 # 50% above highest if it exceeds 1000W
            
            # Create the Altair chart using mark_bar for solid blocks
            chart = alt.Chart(df_chart).mark_bar(
                strokeWidth=0, # Remove stroke for contiguous solid blocks (solid area fill)
            ).encode(
                x=alt.X('start_time_s', 
                        title='Time (s)', 
                        axis=alt.Axis(format='m', title='Time (Minutes)'), # Format axis to show minutes
                        scale=alt.Scale(domain=[0, df_chart['end_time_s'].max()])),
                x2='end_time_s',
                y=alt.Y('power_w', 
                        title='Power (Watts)', 
                        scale=alt.Scale(domain=[0, y_max_scale])), # Dynamic Y-axis scale
                color=alt.Color('zone_name', 
                                title='Zone',
                                scale=alt.Scale(domain=[z['name'] for z in ZONE_MAP], range=[z['color'] for z in ZONE_MAP]),
                                legend=None), 
                tooltip=[
                    alt.Tooltip('step_index', title='Step'),
                    alt.Tooltip('duration_s', title='Duration (s)'),
                    alt.Tooltip('power_w', title='Power (W)'),
                    alt.Tooltip('zone_name', title='Zone')
                ]
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
    # Removed decimals on Total Work (kJ)
    col_metrics[1].metric("Total Work (kJ)", f"{total_work_kj:.0f} kJ") 
    
    col_metrics[0].metric("kJ Above CP", f"{total_work_above_cp_kj:.1f} kJ")
    col_metrics[1].metric("kJ/kg", f"{total_kj_per_kg:.2f}")

    col_metrics[0].metric("Avg Power (W)", f"{avg_power_w:.0f} W")
    # Removed decimals on Total kJ/hour
    col_metrics[1].metric("Total kJ/hour", f"{total_kj_per_hour:.0f} kJ/h")
    
    st.markdown("---")
    
    # --- 8. FUELING RECOMMENDATIONS ---
    # Changed water drop (💧) to fuel pump (⛽) emoji
    st.subheader("⛽ Fueling Recommendation") 
    
    carbs_rate_str, total_carbs_g = get_carbs_recommendation(total_time_s)
    
    if total_time_s > 3600:
        st.metric(f"Estimated Total Carbs Needed", f"{total_carbs_g} g")

    st.markdown(f"""
        <div style="background-color: #f0f8ff; padding: 10px; border-radius: 8px; border: 1px solid #3b82f6;">
            <p style="font-weight: 700; color: #3b82f6;">Target Intake Rate (g/hr):</p>
            <p style="font-size: 1.1em; margin: 0;">{carbs_rate_str}</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.caption("These guidelines are based on current sports nutrition research for endurance cycling.")
