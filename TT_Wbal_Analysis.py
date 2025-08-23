import streamlit as st
import pandas as pd
import math as m
import numpy as np
import fitdecode
import io
import folium
import branca.colormap as cm
from streamlit_folium import st_folium
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Tuple, List, Dict
from datetime import datetime, time, date
import requests
from folium.features import ColorLine
import plotly.colors

# --- Page Configuration ---
st.set_page_config(
    page_title="W'bal Analysis Tool",
    page_icon="🚴",
    layout="wide"
)

# --- Constants ---
SEMICIRCLES_TO_DEGREES = 180 / (2**31)

# --- 1. ANALYSIS FUNCTIONS (Cached for performance) ---

@st.cache_data
def parse_fit_file(file_content: bytes) -> Tuple[pd.DataFrame, int, datetime]:
    """
    Parses the in-memory .fit file content into a pandas DataFrame.
    Returns the DataFrame, missing power count, and the ride start time.
    """
    records = []
    file_id_time, session_time, first_record_time = None, None, None
    
    try:
        with io.BytesIO(file_content) as fit_file:
            with fitdecode.FitReader(fit_file) as fit:
                for frame in fit:
                    if frame.frame_type == fitdecode.FIT_FRAME_DATA:
                        if frame.name == "file_id" and frame.has_field("time_created"):
                            file_id_time = frame.get_value("time_created")
                        
                        elif frame.name == "session" and frame.has_field("start_time"):
                            session_time = frame.get_value("start_time")

                        elif frame.name == "record":
                            if first_record_time is None and frame.has_field("timestamp"):
                                first_record_time = frame.get_value("timestamp")

                            record_data = {
                                "timestamp": frame.get_value("timestamp", fallback=None),
                                "power": frame.get_value("power", fallback=None),
                                "cadence": frame.get_value("cadence", fallback=None),
                                "altitude": frame.get_value("altitude", fallback=None),
                                "heart_rate": frame.get_value("heart_rate", fallback=None),
                                "speed": frame.get_value("speed", fallback=None),
                                "distance": frame.get_value("distance", fallback=None),
                                "temperature": frame.get_value("temperature", fallback=None),
                                "position_lat": frame.get_value("position_lat", fallback=None),
                                "position_long": frame.get_value("position_long", fallback=None),
                            }
                            if record_data["timestamp"] is not None:
                                records.append(record_data)

    except fitdecode.FitDecodeError as e:
        st.error(f"Error decoding .fit file: {e}")
        return pd.DataFrame(), 0, None

    start_time = file_id_time or session_time or first_record_time

    if not records:
        st.warning("The selected .fit file contains no data records.")
        return pd.DataFrame(), 0, None

    df = pd.DataFrame(records)
    
    if 'position_lat' in df.columns and df['position_lat'].notnull().any():
        df['position_lat'] = df['position_lat'] * SEMICIRCLES_TO_DEGREES
    if 'position_long' in df.columns and df['position_long'].notnull().any():
        df['position_long'] = df['position_long'] * SEMICIRCLES_TO_DEGREES

    if not start_time and not df.empty:
        st.warning("Could not find a reliable start time in the file. Using elapsed time from the first record unless a manual time is set.")
        df['time'] = (df['timestamp'] - df['timestamp'].iloc[0]).dt.total_seconds()
    elif start_time:
        df['time'] = (df['timestamp'] - start_time).dt.total_seconds()
        
    df.drop(columns=['timestamp'], inplace=True, errors='ignore')

    missing_power_count = df['power'].isnull().sum()
    if missing_power_count > 0:
        st.warning(f"Note: Found and replaced {missing_power_count} missing power data point(s) with 0.")
    df['power'] = df['power'].fillna(0)
    
    for col in ['power', 'cadence', 'heart_rate', 'speed', 'distance', 'temperature']:
        if col not in df.columns: df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    if 'altitude' in df.columns: df['altitude'] = df['altitude'].fillna(method='ffill')
    if 'speed' in df.columns: df['speed_kmh'] = df['speed'] * 3.6

    return df, missing_power_count, start_time

@st.cache_data
def get_weather_data(lat: float, lon: float, start_time: datetime) -> Dict:
    """Fetches historical weather data from Open-Meteo API."""
    if lat is None or lon is None or not isinstance(start_time, datetime):
        return None
    
    try:
        date_str = start_time.strftime('%Y-%m-%d')
        url = (
            f"https://archive-api.open-meteo.com/v1/archive?latitude={lat:.4f}&longitude={lon:.4f}"
            f"&start_date={date_str}&end_date={date_str}"
            "&hourly=temperature_2m,relativehumidity_2m,windspeed_10m,winddirection_10m"
        )
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        hour = start_time.hour
        return {
            "temperature": data['hourly']['temperature_2m'][hour],
            "humidity": data['hourly']['relativehumidity_2m'][hour],
            "wind_speed": data['hourly']['windspeed_10m'][hour],
            "wind_direction": data['hourly']['winddirection_10m'][hour],
        }
    except requests.exceptions.RequestException as e:
        st.warning(f"Could not fetch weather data: {e}")
    except (KeyError, IndexError) as e:
        st.warning(f"Error parsing weather data from API response: {e}")
    return None

@st.cache_data
def calculate_power_zones(power_data: pd.Series, cp: int) -> pd.DataFrame:
    """Calculates time spent in 7 power zones based on CP."""
    zones = {
        "Zone 1": (0, 0.55), "Zone 2": (0.55, 0.75), "Zone 3": (0.75, 0.90),
        "Zone 4": (0.90, 1.05), "Zone 5": (1.05, 1.20), "Zone 6": (1.20, 1.50),
        "Zone 7": (1.50, np.inf),
    }
    zone_counts = {name: 0 for name in zones}
    for power in power_data:
        if power <= 0: continue
        for name, (lower, upper) in zones.items():
            if lower * cp < power <= upper * cp:
                zone_counts[name] += 1
                break
    total_seconds = sum(zone_counts.values())
    zone_data = [{"Zone": name, "Time (s)": s, "Percentage": (s / total_seconds) * 100 if total_seconds > 0 else 0} for name, s in zone_counts.items()]
    return pd.DataFrame(zone_data)

@st.cache_data
def calculate_wbal_zones(wbal_percent_data: pd.Series) -> pd.DataFrame:
    """Calculates time spent in W'bal percentage zones."""
    bins = [-1, 10, 30, 50, 70, 101]
    labels = [
        "Danger Zone (0-10%)",
        "Orange (10-30%)",
        "Orange (30-50%)",
        "Yellow (50-70%)",
        "Green (70-100%)",
    ]
    
    df_zones = pd.cut(wbal_percent_data, bins=bins, labels=labels, right=False).value_counts().reset_index()
    df_zones.columns = ['Zone', 'Time (s)']
    
    df_zones['Zone'] = pd.Categorical(df_zones['Zone'], categories=labels[::-1], ordered=True)
    df_zones = df_zones.sort_values('Zone').reset_index(drop=True)
    
    total_seconds = df_zones['Time (s)'].sum()
    df_zones['Percentage'] = (df_zones['Time (s)'] / total_seconds) * 100 if total_seconds > 0 else 0
    
    return df_zones

@st.cache_data
def calculate_mmp_curve(power_data: pd.Series, weight: float) -> pd.DataFrame:
    """Calculates the Mean Maximal Power (MMP) curve in W and W/kg."""
    durations = sorted(list(set([1, 5, 10, 20, 30, 60, 120, 180, 300, 480, 600, 720, 1200, 1800, 3600])))
    mmp_w = {d: power_data.rolling(window=d).mean().max() for d in durations if len(power_data) >= d}
    
    mmp_df = pd.DataFrame(list(mmp_w.items()), columns=["Duration (s)", "Max Power (W)"])
    if weight > 0:
        mmp_df["Max Power (W/kg)"] = mmp_df["Max Power (W)"] / weight
    else:
        mmp_df["Max Power (W/kg)"] = 0
    return mmp_df

@st.cache_data
def find_top_bouts(df: pd.DataFrame, cp: int, buffer_duration: int = 5) -> Tuple[List[Dict], List[Dict]]:
    """Identifies the top 3 longest bouts above and below CP."""
    bouts = []
    current_bout = None
    buffer = 0

    for i in range(len(df)):
        power = df['power'].iloc[i]
        state = 'above' if power > cp else 'below'

        if current_bout is None:
            current_bout = {'state': state, 'start': i, 'end': i, 'duration': 1}
            buffer = 0
        elif state == current_bout['state']:
            current_bout['end'] = i
            current_bout['duration'] += 1
            buffer = 0
        else: # State has changed
            buffer += 1
            if buffer > buffer_duration:
                bouts.append(current_bout)
                current_bout = {'state': state, 'start': i, 'end': i, 'duration': 1}
                buffer = 0
    
    if current_bout:
        bouts.append(current_bout)

    above_bouts = sorted([b for b in bouts if b['state'] == 'above'], key=lambda x: x['duration'], reverse=True)
    below_bouts = sorted([b for b in bouts if b['state'] == 'below'], key=lambda x: x['duration'], reverse=True)

    return above_bouts[:3], below_bouts[:3]

@st.cache_data
def analyze_bouts(df: pd.DataFrame, bouts: List[Dict], bout_type: str, cp: int) -> pd.DataFrame:
    """Analyzes a list of bouts and returns a summary DataFrame."""
    summary = []
    for i, bout in enumerate(bouts):
        bout_df = df.iloc[bout['start']:bout['end']]
        if bout_df.empty: continue
        
        wbal_change = bout_df['Wbal'].iloc[-1] - bout_df['Wbal'].iloc[0]
        
        pedaling_cadence = bout_df['cadence'][bout_df['cadence'] > 0]
        avg_cadence = round(pedaling_cadence.mean()) if not pedaling_cadence.empty else 0

        bout_summary = {
            "Bout": f"{bout_type} Bout {i+1}",
            "Duration (s)": bout['duration'],
            "Avg Power (W)": round(bout_df['power'].mean()),
            "Avg Speed (km/h)": round(bout_df['speed_kmh'].mean(), 1),
            "Avg Cadence (rpm)": avg_cadence,
            "W' Change (kJ)": round(wbal_change / 1000, 2)
        }
        
        if bout_type == "Effort":
            bout_summary["Avg Power > CP (W)"] = round(bout_df['power'].mean() - cp)
        else: # Recovery
            bout_summary["Avg Power < CP (W)"] = round(cp - bout_df['power'].mean())

        summary.append(bout_summary)
        
    return pd.DataFrame(summary)

@st.cache_data
def calculate_matches(df: pd.DataFrame, cp: int, w_prime: float, gap_tolerance: int) -> Tuple[pd.DataFrame, Dict]:
    """Identifies and analyzes 'matches' burned above a threshold."""
    threshold_power = cp * 1.05
    matches = []
    current_match = None
    below_counter = 0

    for i in range(len(df)):
        power = df['power'].iloc[i]
        
        if power > threshold_power:
            if current_match is None:
                current_match = {'start_index': i, 'powers': [power]}
            else:
                current_match['powers'].append(power)
            below_counter = 0
        else:
            if current_match is not None:
                below_counter += 1
                if below_counter > gap_tolerance:
                    if len(current_match['powers']) > 0:
                        matches.append(current_match)
                    current_match = None
    
    if current_match and len(current_match['powers']) > 0:
        matches.append(current_match)

    match_data = []
    for match in matches:
        duration = len(match['powers'])
        avg_power = sum(match['powers']) / duration
        magnitude = (avg_power / cp) * 100
        w_prime_depleted_joules = duration * (avg_power - cp)
        depletion_percent = (w_prime_depleted_joules / w_prime) * 100 if w_prime > 0 else 0
        start_index = match['start_index']

        match_data.append({
            "Start Time (s)": df['time'].iloc[start_index],
            "Start Distance (km)": df['distance'].iloc[start_index] / 1000,
            "Duration (s)": duration, 
            "Magnitude (%CP)": magnitude,
            "Depletion (% W')": depletion_percent,
            "Depletion (kJ)": w_prime_depleted_joules / 1000
        })

    summary = {
        "Total Matches": len(match_data),
        "Avg Duration (s)": np.mean([m["Duration (s)"] for m in match_data]) if match_data else 0,
        "Avg Magnitude (%CP)": np.mean([m["Magnitude (%CP)"] for m in match_data]) if match_data else 0
    }
    
    return pd.DataFrame(match_data), summary

@st.cache_data
def find_w_depletion_bouts(df: pd.DataFrame, w_prime: float, depletion_threshold_percent: int, max_duration_s: int, recovery_tolerance_s: int) -> List[Dict]:
    """Identifies all efforts that deplete W' by a given percentage within a max duration, allowing for short recoveries."""
    bouts = []
    in_bout = False
    bout_start_index = 0
    recovery_counter = 0
    
    df['wbal_delta'] = df['Wbal'].diff()
    
    for i in range(1, len(df)):
        # Start of a depletion phase
        if df['wbal_delta'].iloc[i] < 0:
            if not in_bout:
                in_bout = True
                bout_start_index = i - 1
            recovery_counter = 0 # Reset recovery counter on any depletion
        
        # Potential end of a depletion phase (i.e., recovery)
        elif in_bout:
            recovery_counter += 1
            # End the bout only if recovery is sustained or it's the end of the ride
            if recovery_counter > recovery_tolerance_s or i == len(df) - 1:
                in_bout = False
                # The actual end of the effort was before the recovery period started
                bout_end_index = i - recovery_counter 
                
                duration = bout_end_index - bout_start_index
                
                if duration > 0:
                    wbal_start = df['Wbal'].iloc[bout_start_index]
                    wbal_end = df['Wbal'].iloc[bout_end_index]
                    
                    w_prime_depleted = wbal_start - wbal_end
                    depletion_percent = (w_prime_depleted / w_prime) * 100 if w_prime > 0 else 0
                    
                    if depletion_percent >= depletion_threshold_percent and duration <= max_duration_s:
                        bouts.append({'start': bout_start_index, 'end': bout_end_index, 'depletion': depletion_percent})
                
                recovery_counter = 0 # Reset for the next potential bout
                
    return bouts

def get_time_of_day(hour: int) -> str:
    """Categorizes the hour into Morning, Afternoon, or Evening."""
    if 5 <= hour < 12: return "Morning"
    elif 12 <= hour < 18: return "Afternoon"
    else: return "Evening"
    
def format_seconds_to_hms(seconds: float) -> str:
    """Converts seconds into a 'Xh Ym Zs' format."""
    seconds = round(seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    remaining_seconds = int(seconds % 60)
    return f"{hours}h {minutes:02d}m {remaining_seconds:02d}s"

# --- Main App Interface ---
st.title("🚴 W' Bal: TT and Race  Analysis Tool")
st.markdown("Upload a `.fit` file and set your parameters to generate a detailed performance analysis.")

# --- Sidebar for Inputs ---
with st.sidebar:
    st.header("1. Upload Activity File")
    uploaded_file = st.file_uploader("Choose a .fit file", type="fit")
    st.caption("Note: Created by Alex Welburn Your data is processed in memory and is deleted when you close the browser tab. No data is stored.")
    
    st.header("2. Input Parameters")
    weight = st.number_input('Weight (kg)', value=75.0, min_value=30.0, max_value=200.0, step=0.5, format="%.1f")

    CP = st.number_input('Critical Power (CP) in Watts', value=350, step=1)
    WP_kJ = st.number_input('W\' (W prime) in kJ', value=20.0, step=1.0, format="%.1f")
    
    A = st.number_input('Parameter A', value=5187, step=1)
    B = st.number_input('Parameter B', value=-0.70, format="%.2f")

    st.header("3. Manual Start Time (Optional)")
    manual_time_override = st.checkbox("Manually set start time")
    manual_date, manual_time = None, None
    if manual_time_override:
        manual_date = st.date_input("Select ride date", value=datetime.now())
        manual_time = st.time_input("Select ride start time", value=datetime.now().time())
    
    with st.expander("🧪 Ride Comparison"):
        uploaded_file_2 = st.file_uploader("Choose a second .fit file to compare", type="fit")

    analyze_button = st.button("Analyze Ride", type="primary")

# --- State Management ---
if 'current_file' not in st.session_state:
    st.session_state.current_file = None

if uploaded_file and uploaded_file.name != st.session_state.current_file:
    st.session_state.current_file = uploaded_file.name
    if 'results' in st.session_state:
        del st.session_state['results']

# --- Main Panel Logic ---
if analyze_button:
    if uploaded_file:
        WP = WP_kJ * 1000
        file_content = uploaded_file.getvalue()
        df, missing_power_count, parsed_start_time = parse_fit_file(file_content)

        start_time = parsed_start_time
        if manual_time_override:
            start_time = datetime.combine(manual_date, manual_time)
            st.info(f"Using manual start time: {start_time.strftime('%d %b %Y, %H:%M')}")

        if df.empty:
            st.error("Could not parse the .fit file. It might be empty or corrupted.")
            if 'results' in st.session_state: del st.session_state['results']
        else:
            with st.spinner("Analyzing..."):
                # --- W'bal CALCULATION ---
                Wbal, Wbal_old = float(WP), float(WP)
                wbal_list = [float(WP)]
                power_np = df['power'].to_numpy()
                for i in range(1, len(df)):
                    P = power_np[i]
                    if P > CP:
                        Wbal -= (P - CP)
                    else:
                        DCP2 = CP - P
                        Tau = A * (DCP2 ** B) if DCP2 > 0 else 0
                        Wbal = WP - ((WP - Wbal_old) * m.exp(-1 / (Tau if Tau > 0 else 1e9)))
                    Wbal = min(WP, Wbal)
                    wbal_list.append(Wbal)
                    Wbal_old = Wbal
                df['Wbal'] = wbal_list
                df['wbal_percent'] = (df['Wbal'] / WP) * 100

                # --- VECTORIZED POWER AND CADENCE ANALYSIS ---
                metrics = {}
                df['state'] = np.where(df['power'] > CP, 'above', 'below')
                
                metrics["total_work_kj"] = round(df['power'].sum() / 1000)
                work_above_cp = df['power'][df['power'] > CP] - CP
                metrics["total_work_above_cp_kj"] = round(work_above_cp.sum() / 1000)
                
                if weight > 0:
                    metrics["total_work_kj_per_kg"] = round(metrics["total_work_kj"] / weight, 1)
                    metrics["total_work_above_cp_kj_per_kg"] = round(metrics["total_work_above_cp_kj"] / weight, 1)

                grouped_state = df.groupby('state')
                metrics["total_time_above"] = len(df[df['state'] == 'above'])
                metrics["total_time_below"] = len(df[df['state'] == 'below'])
                metrics["avg_power_overall"] = round(df['power'].mean())
                if weight > 0:
                    metrics["avg_power_w_kg"] = round(metrics["avg_power_overall"] / weight, 2)
                
                metrics["avg_power_above"] = round(df.loc[df['state'] == 'above', 'power'].mean()) if metrics["total_time_above"] > 0 else 0
                metrics["avg_power_below"] = round(df.loc[df['state'] == 'below', 'power'].mean()) if metrics["total_time_below"] > 0 else 0

                bout_starts = df['state'].ne(df['state'].shift())
                metrics["bouts_above"] = bout_starts[df['state'] == 'above'].sum()
                metrics["bouts_below"] = bout_starts[df['state'] == 'below'].sum()

                pedaling_df = df[df['cadence'] > 0]
                metrics["avg_cadence"] = round(pedaling_df['cadence'].mean()) if not pedaling_df.empty else 0
                if not pedaling_df.empty:
                    grouped_cadence = pedaling_df.groupby('state')
                    metrics["avg_cadence_above"] = round(grouped_cadence.get_group('above')['cadence'].mean()) if 'above' in grouped_cadence.groups else 0
                    metrics["avg_cadence_below"] = round(grouped_cadence.get_group('below')['cadence'].mean()) if 'below' in grouped_cadence.groups else 0
                else:
                    metrics["avg_cadence_above"] = 0
                    metrics["avg_cadence_below"] = 0

                metrics["coasting_time"] = (df['cadence'] == 0).sum()
                metrics["coasting_percent"] = round((metrics["coasting_time"] / len(df)) * 100) if len(df) > 0 else 0
                
                metrics["avg_speed_overall"] = round(df['speed_kmh'].mean(), 1) if 'speed_kmh' in df.columns else 0
                metrics["total_distance"] = round(df['distance'].max() / 1000, 2) if 'distance' in df.columns else 0
                
                power_zones_df = calculate_power_zones(df['power'], CP)
                wbal_zones_df = calculate_wbal_zones(df['wbal_percent'])
                mmp_df = calculate_mmp_curve(df['power'], weight)
                top_above_bouts, top_below_bouts = find_top_bouts(df, CP)
                above_bouts_summary = analyze_bouts(df, top_above_bouts, "Effort", CP)
                below_bouts_summary = analyze_bouts(df, top_below_bouts, "Recovery", CP)
                
                first_coord = df[['position_lat', 'position_long']].dropna().iloc[0] if not df[['position_lat', 'position_long']].dropna().empty else None
                weather_data = get_weather_data(first_coord['position_lat'], first_coord['position_long'], start_time) if first_coord is not None else None

                st.session_state.results = {
                    "df": df,
                    "metrics": metrics,
                    "power_profile": {"zones": power_zones_df, "mmp": mmp_df},
                    "wbal_zones": wbal_zones_df,
                    "interval_analysis": {"above_bouts": top_above_bouts, "below_bouts": top_below_bouts, "above_summary": above_bouts_summary, "below_summary": below_bouts_summary},
                    "params": {"CP": CP, "WP": WP, "Weight": weight},
                    "ride_info": {"start_time": start_time, "weather": weather_data}
                }
                
                if uploaded_file_2:
                    file_content_2 = uploaded_file_2.getvalue()
                    df2, _, _ = parse_fit_file(file_content_2)
                    if not df2.empty:
                        st.session_state.results["df2"] = df2

    else:
        st.warning("Please upload a .fit file first.")

# Display results if they exist in the session state
if 'results' in st.session_state:
    results = st.session_state.results
    df = results["df"]
    metrics = results["metrics"]
    params = results["params"]
    power_profile = results["power_profile"]
    ride_info = results["ride_info"]
    interval_analysis = results["interval_analysis"]
    CP, WP, weight = params["CP"], params["WP"], params["Weight"]
    df['wbal_kj'] = df['Wbal'] / 1000

    tab_list = ["📊 Summary", "🏃 Interval Analysis", "🔥 Match Analysis", "📈 Ride Profile", "⚡ Power Profile", "🗺️ Route Maps", "⚙️ Data Explorer", "📋 Raw Data Explorer", "🧪 Beta Features"]
    tabs = st.tabs(tab_list)

    with tabs[0]: # Summary
        st.header("Ride Summary")
        
        st.subheader("About the Model")
        col1, col2 = st.columns([1, 10])
        with col1:
            st.markdown("👨‍🔬")
        with col2:
            st.markdown(
                """
                This tool utilizes a W' balance model based on the research by Alex Welburn, PhD. 
                [Publication](https://link.springer.com/article/10.1007/s00421-025-05912-0) | [ResearchGate](https://www.researchgate.net/profile/Alex-Welburn) | [X (Twitter)](https://twitter.com/xx)
                """
            )
        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Ride Details")
            if ride_info["start_time"] and isinstance(ride_info["start_time"], datetime):
                st.metric("Date", ride_info["start_time"].strftime("%d %b %Y"))
                st.metric("Time of Day", get_time_of_day(ride_info["start_time"].hour))
            else:
                st.info("No start time found in file.")
        with col2:
            st.subheader("Weather Conditions")
            if ride_info["weather"]:
                weather = ride_info["weather"]
                temp = weather.get('temperature')
                if isinstance(temp, (int, float)):
                    thermo_emoji = "🔥" if temp > 25 else "☀️" if temp > 18 else "⛅"
                    st.metric(f"Temperature {thermo_emoji}", f"{temp}°C")
                else:
                    st.metric("Temperature", "N/A")
                st.metric("Wind", f"{weather.get('wind_speed')} km/h ({weather.get('wind_direction')}°)")
            else:
                st.info("No location data found to fetch weather.")

        st.divider()
        st.subheader("Overall Ride Metrics")
        c1, c2, c3 = st.columns(3)
        avg_power_w_kg_val = metrics.get('avg_power_w_kg')
        
        with c1:
            st.metric("Total Distance", f"{metrics.get('total_distance', 'N/A')} km")
        with c2:
            st.metric("Average Power", f"{metrics.get('avg_power_overall', 'N/A')} W")
            if avg_power_w_kg_val is not None:
                st.markdown(f"<p style='color:green; font-size: 0.9em; margin-top: -10px;'>{avg_power_w_kg_val} W/kg</p>", unsafe_allow_html=True)
        with c3:
            st.metric("Average Speed", f"{metrics.get('avg_speed_overall', 'N/A')} km/h")

        c4, c5, c6 = st.columns(3)
        total_work_val = metrics.get('total_work_kj')
        work_above_cp_val = metrics.get('total_work_above_cp_kj')
        total_work_per_kg_val = metrics.get('total_work_kj_per_kg')
        work_above_cp_per_kg_val = metrics.get('total_work_above_cp_kj_per_kg')
        
        with c4:
            st.metric("Total Work", f"{total_work_val} kJ" if total_work_val is not None else "N/A")
            if total_work_per_kg_val is not None:
                st.markdown(f"<p style='color:green; font-size: 0.9em; margin-top: -10px;'>{total_work_per_kg_val} kJ/kg</p>", unsafe_allow_html=True)
        with c5:
            st.metric("Work Above CP", f"{work_above_cp_val} kJ" if work_above_cp_val is not None else "N/A")
            if work_above_cp_per_kg_val is not None:
                st.markdown(f"<p style='color:green; font-size: 0.9em; margin-top: -10px;'>{work_above_cp_per_kg_val} kJ/kg</p>", unsafe_allow_html=True)
        with c6:
            st.metric("Coasting", f"{metrics.get('coasting_percent', 'N/A')}%")
        
        st.divider()
        st.header(f"Power Analysis (Threshold = {int(CP)} W)")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### Above CP")
            st.metric("Total Time", format_seconds_to_hms(metrics.get('total_time_above', 0)))
            st.metric("Avg Power", f"{metrics.get('avg_power_above', 'N/A')} W")
            st.metric("Number of Bouts", f"{metrics.get('bouts_above', 'N/A')}")
        with col2:
            st.markdown("##### Below or At CP")
            st.metric("Total Time", format_seconds_to_hms(metrics.get('total_time_below', 0)))
            st.metric("Avg Power", f"{metrics.get('avg_power_below', 'N/A')} W")
            st.metric("Number of Bouts", f"{metrics.get('bouts_below', 'N/A')}")
        
    with tabs[1]: # Interval Analysis
        st.header("Interval Analysis")
        st.subheader("Top Bouts vs. Power and W'bal")
        fig_intervals = make_subplots(specs=[[{"secondary_y": True}]])
        fig_intervals.add_trace(go.Scatter(x=df['time'], y=df['wbal_kj'], name='W\'bal (kJ)', line=dict(color='#9467bd', width=2)), secondary_y=False)
        fig_intervals.add_trace(go.Scatter(x=df['time'], y=df['power'], name='Power', line=dict(color='grey', width=1)), secondary_y=True)
        
        fig_intervals.add_trace(go.Scatter(x=[None], y=[None], mode='markers', marker=dict(color='rgba(214, 39, 40, 0.4)'), name='Top Effort'))
        fig_intervals.add_trace(go.Scatter(x=[None], y=[None], mode='markers', marker=dict(color='rgba(31, 119, 180, 0.4)'), name='Top Recovery'))

        for bout in interval_analysis['above_bouts']:
            fig_intervals.add_vrect(x0=df['time'].iloc[bout['start']], x1=df['time'].iloc[bout['end']], fillcolor="red", opacity=0.2, layer="below", line_width=0)
        for bout in interval_analysis['below_bouts']:
            fig_intervals.add_vrect(x0=df['time'].iloc[bout['start']], x1=df['time'].iloc[bout['end']], fillcolor="blue", opacity=0.2, layer="below", line_width=0)

        fig_intervals.update_layout(template='plotly_white', font=dict(color="black"), showlegend=True)
        fig_intervals.update_xaxes(showline=True, linewidth=2, linecolor='black', mirror=False)
        fig_intervals.update_yaxes(title_text="W'bal (kJ)", showline=True, linewidth=2, linecolor='black', mirror=False, secondary_y=False)
        fig_intervals.update_yaxes(title_text="Power (W)", showline=True, linewidth=2, linecolor='black', mirror=False, secondary_y=True)
        st.plotly_chart(fig_intervals, use_container_width=True)
        
        st.subheader("W' Balance as a Percentage")
        fig_wbal_percent = go.Figure()
        fig_wbal_percent.add_trace(go.Scatter(x=df['time'], y=df['wbal_percent'], name='W\'bal (%)', line=dict(color='purple', width=2)))
        fig_wbal_percent.add_hrect(y0=70, y1=100.1, line_width=0, fillcolor='green', opacity=0.2, layer="below")
        fig_wbal_percent.add_hrect(y0=50, y1=70, line_width=0, fillcolor='yellow', opacity=0.2, layer="below")
        fig_wbal_percent.add_hrect(y0=30, y1=50, line_width=0, fillcolor='orange', opacity=0.2, layer="below")
        fig_wbal_percent.add_hrect(y0=10, y1=30, line_width=0, fillcolor='orange', opacity=0.3, layer="below")
        fig_wbal_percent.add_hrect(y0=0, y1=10, line_width=0, fillcolor='#8B0000', opacity=0.3, layer="below")

        fig_wbal_percent.add_annotation(
            x=df['time'].mean(), y=5, text="Danger Zone", showarrow=False,
            font=dict(color="white", size=12, family="Arial, sans-serif"),
            xanchor='center', yanchor='middle'
        )
        fig_wbal_percent.update_layout(
            title_text="W' Balance Percentage Over Time", template='plotly_white', font=dict(color="black"),
            showlegend=True, yaxis_range=[0,105]
        )
        fig_wbal_percent.update_xaxes(title_text="Time (s)", showline=True, linewidth=2, linecolor='black', mirror=False)
        fig_wbal_percent.update_yaxes(title_text="W'bal (%)", showline=True, linewidth=2, linecolor='black', mirror=False)
        st.plotly_chart(fig_wbal_percent, use_container_width=True)

        st.subheader("Time in W'bal Zones")
        wbal_zones_df = results["wbal_zones"]
        wbal_zones_df['Time (HMS)'] = wbal_zones_df['Time (s)'].apply(format_seconds_to_hms)
        wbal_zones_df['Chart Text'] = wbal_zones_df.apply(lambda row: f"{row['Time (HMS)']} ({row['Percentage']:.1f}%)", axis=1)

        zone_colors = {
            "Green (70-100%)": 'green',
            "Yellow (50-70%)": 'yellow',
            "Orange (30-50%)": 'orange',
            "Orange (10-30%)": 'darkorange',
            "Danger Zone (0-10%)": '#8B0000'
        }
        fig_wbal_zones = go.Figure(go.Bar(
            x=wbal_zones_df['Time (s)'], y=wbal_zones_df['Zone'], orientation='h',
            text=wbal_zones_df['Chart Text'],
            marker_color=[zone_colors.get(zone, 'grey') for zone in wbal_zones_df['Zone']]
        ))
        fig_wbal_zones.update_layout(title_text="Time Spent in W'bal Zones", template='plotly_white', font=dict(color="black"))
        fig_wbal_zones.update_xaxes(title_text="Time (s)", showline=True, linewidth=2, linecolor='black', mirror=False)
        fig_wbal_zones.update_yaxes(showline=True, linewidth=2, linecolor='black', mirror=False, categoryorder='array', categoryarray=wbal_zones_df['Zone'])
        st.plotly_chart(fig_wbal_zones, use_container_width=True)
        st.divider()
        
        st.dataframe(interval_analysis['above_summary'])
        st.dataframe(interval_analysis['below_summary'])
        st.divider()

        st.subheader("W' Depletion Analysis")
        col1, col2, col3 = st.columns(3)
        with col1:
            depletion_threshold = st.slider("Highlight efforts that deplete W' by at least:", 20, 90, 40, format="%d%%")
        with col2:
            max_duration = st.slider("Max duration of effort (seconds):", 1, 600, 300)
        with col3:
            recovery_tolerance = st.slider("Recovery Tolerance (s):", 1, 30, 5, help="Allowable recovery time within an effort before it's considered ended.")

        depletion_bouts = find_w_depletion_bouts(df, WP, depletion_threshold, max_duration, recovery_tolerance)
        
        st.markdown(f"Found **{len(depletion_bouts)}** efforts that met the criteria.")

        fig_depletion = make_subplots(specs=[[{"secondary_y": True}]])
        fig_depletion.add_trace(go.Scatter(x=df['time'], y=df['wbal_kj'], name='W\'bal (kJ)', line=dict(color='#9467bd', width=2)), secondary_y=False)
        fig_depletion.add_trace(go.Scatter(x=df['time'], y=df['power'], name='Power', line=dict(color='grey', width=1)), secondary_y=True)

        for bout in depletion_bouts:
            fig_depletion.add_vrect(x0=df['time'].iloc[bout['start']], x1=df['time'].iloc[bout['end']], fillcolor="rgba(255, 165, 0, 0.3)", layer="below", line_width=0)

        fig_depletion.update_layout(title_text=f"Efforts Depleting W' > {depletion_threshold}%", template='plotly_white', font=dict(color="black"), showlegend=True)
        fig_depletion.update_xaxes(showline=True, linewidth=2, linecolor='black', mirror=False)
        fig_depletion.update_yaxes(title_text="W'bal (kJ)", showline=True, linewidth=2, linecolor='black', mirror=False, secondary_y=False)
        fig_depletion.update_yaxes(title_text="Power (W)", showline=True, linewidth=2, linecolor='black', mirror=False, secondary_y=True)
        st.plotly_chart(fig_depletion, use_container_width=True)

    with tabs[2]: # Match Analysis
        st.header("Match Analysis")
        gap_tolerance = st.slider("Gap Tolerance (s)", min_value=0, max_value=10, value=3, help="Allowable time below threshold before ending a 'match'.")
        
        matches_df, matches_summary = calculate_matches(df, CP, WP, gap_tolerance)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Matches Burned", f"{matches_summary['Total Matches']}")
        col2.metric("Avg Match Duration", f"{matches_summary['Avg Duration (s)']:.1f} s")
        col3.metric("Avg Match Magnitude", f"{matches_summary['Avg Magnitude (%CP)']:.1f}%")

        fig_matches = go.Figure()
        fig_matches.add_trace(go.Scatter(
            x=matches_df['Duration (s)'], 
            y=matches_df['Magnitude (%CP)'], 
            mode='markers', 
            name='Matches',
            marker=dict(
                color=matches_df["Depletion (% W')"],
                colorscale='RdYlGn_r',
                showscale=True,
                colorbar=dict(title="W' Depletion %")
            )
        ))

        max_duration = max(71, matches_df['Duration (s)'].max() + 10) if not matches_df.empty else 71
        depletion_levels = range(10, 60, 10)
        colors = plotly.colors.sequential.YlOrRd[::2] 

        for i, depletion in enumerate(depletion_levels):
            durations = np.arange(1, max_duration)
            power_depletion = (WP * (depletion / 100) / durations) + CP
            magnitude = (power_depletion / CP) * 100
            fig_matches.add_trace(go.Scatter(
                x=durations, 
                y=magnitude, 
                mode='lines', 
                line=dict(dash='dot', color=colors[i]), 
                name=f'{depletion}% W\'',
                showlegend=False
            ))
            fig_matches.add_annotation(
                x=durations[-1], y=magnitude[-1],
                text=f" {depletion}%", showarrow=False,
                xanchor='left', font=dict(color=colors[i])
            )

        fig_matches.update_layout(
            title_text='Match Magnitude vs. Duration', 
            template='plotly_white', 
            font=dict(color="black"),
            legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
        )
        fig_matches.update_xaxes(title_text='Duration (s)', showline=True, linewidth=2, linecolor='black', mirror=False)
        fig_matches.update_yaxes(title_text='Magnitude (% of CP)', showline=True, linewidth=2, linecolor='black', mirror=False, range=[105, 250])
        st.plotly_chart(fig_matches, use_container_width=True)

        st.divider()
        st.subheader("Top W' Depleting Efforts")
        st.markdown("This table highlights the efforts that consumed the most `W'`, pinpointing the most anaerobically demanding moments of the ride.")

        num_efforts = st.slider("Number of top efforts to display:", min_value=2, max_value=20, value=5)

        if not matches_df.empty:
            top_efforts_df = matches_df.sort_values(by="Depletion (kJ)", ascending=False).head(num_efforts)

            display_df = top_efforts_df[[
                "Start Time (s)",
                "Start Distance (km)",
                "Duration (s)",
                "Magnitude (%CP)",
                "Depletion (kJ)"
            ]].copy()

            display_df["Start Time (s)"] = display_df["Start Time (s)"].apply(lambda s: format_seconds_to_hms(s))
            display_df["Start Distance (km)"] = display_df["Start Distance (km)"].map('{:.2f}'.format)
            display_df["Magnitude (%CP)"] = display_df["Magnitude (%CP)"].map('{:.1f}%'.format)
            display_df["Depletion (kJ)"] = display_df["Depletion (kJ)"].map('{:.2f}'.format)
            
            display_df.rename(columns={
                "Start Time (s)": "Time",
                "Start Distance (km)": "Distance (km)",
                "Duration (s)": "Duration (s)",
                "Magnitude (%CP)": "Magnitude",
                "Depletion (kJ)": "W' Depleted (kJ)"
            }, inplace=True)
            
            st.dataframe(display_df.reset_index(drop=True))
        else:
            st.info("No matches were found in this ride to analyze.")

    with tabs[3]: # Ride Profile
        st.header("Ride Profile Charts")
        fig_wbal = make_subplots(specs=[[{"secondary_y": True}]])
        fig_wbal.add_trace(go.Scatter(x=df['time'], y=df['wbal_kj'], name='W\'bal (kJ)', line=dict(color='#9467bd', width=2)), secondary_y=False)
        if 'altitude' in df.columns and df['altitude'].notna().any():
            fig_wbal.add_trace(go.Scatter(x=df['time'], y=df['altitude'], name='Elevation (m)', line=dict(color='#2ca02c', width=2), fill='tozeroy'), secondary_y=True)
        fig_wbal.update_layout(title_text='W\' Balance vs. Elevation', template='plotly_white', font=dict(color="black"))
        fig_wbal.update_xaxes(showline=True, linewidth=2, linecolor='black', mirror=False)
        fig_wbal.update_yaxes(showline=True, linewidth=2, linecolor='black', mirror=False, title_text="W'bal (kJ)", secondary_y=False); 
        fig_wbal.update_yaxes(showline=True, linewidth=2, linecolor='black', mirror=False, title_text="Elevation (m)", secondary_y=True)
        st.plotly_chart(fig_wbal, use_container_width=True)

        fig_power = go.Figure()
        fig_power.add_trace(go.Scatter(x=df['time'], y=df['power'], name='Power', line=dict(color='cyan', width=1)))
        fig_power.add_shape(type="line", x0=df['time'].min(), y0=CP, x1=df['time'].max(), y1=CP, line=dict(color="#ff7f0e", width=2, dash="dash"), name=f"CP ({CP}W)")
        fig_power.update_layout(title_text='Power over Time', template='plotly_white', font=dict(color="black"))
        fig_power.update_xaxes(showline=True, linewidth=2, linecolor='black', mirror=False)
        fig_power.update_yaxes(showline=True, linewidth=2, linecolor='black', mirror=False)
        st.plotly_chart(fig_power, use_container_width=True)

    with tabs[4]: # Power Profile
        st.header("Power Profile")
        zones_df = power_profile["zones"]
        zones_df['Time (HMS)'] = zones_df['Time (s)'].apply(format_seconds_to_hms)
        zones_df['Chart Text'] = zones_df.apply(lambda row: f"{row['Time (HMS)']} ({row['Percentage']:.1f}%)", axis=1)
        
        fig_zones = go.Figure(go.Bar(x=zones_df['Time (s)'], y=zones_df['Zone'], orientation='h', text=zones_df['Chart Text']))
        fig_zones.update_layout(title_text='Time in Power Zones', template='plotly_white', font=dict(color="black"))
        fig_zones.update_xaxes(showline=True, linewidth=2, linecolor='black', mirror=False)
        fig_zones.update_yaxes(showline=True, linewidth=2, linecolor='black', mirror=False)
        st.plotly_chart(fig_zones, use_container_width=True)
        
        mmp_df = power_profile["mmp"]
        st.subheader("Mean Maximal Power (Watts)")
        
        key_durations = {"5s": 5, "20s": 20, "1 min": 60, "3 min": 180, "5 min": 300, "8 min": 480, "12 min": 720, "20 min": 1200}
        mmp_data_w = mmp_df.set_index("Duration (s)")["Max Power (W)"]
        
        cols = st.columns(4)
        duration_keys = list(key_durations.keys())
        for i in range(0, len(duration_keys), 2):
            with cols[i//2]:
                label1 = duration_keys[i]
                duration1 = key_durations[label1]
                power_value1 = mmp_data_w.get(duration1)
                if power_value1 is not None:
                    st.metric(label=label1, value=f"{int(power_value1)} W")
                else:
                    st.metric(label=label1, value="N/A")
                
                if i + 1 < len(duration_keys):
                    label2 = duration_keys[i+1]
                    duration2 = key_durations[label2]
                    power_value2 = mmp_data_w.get(duration2)
                    if power_value2 is not None:
                        st.metric(label=label2, value=f"{int(power_value2)} W")
                    else:
                        st.metric(label=label2, value="N/A")

        fig_mmp = go.Figure(go.Scatter(x=mmp_df['Duration (s)'], y=mmp_df['Max Power (W)'], mode='lines+markers'))
        fig_mmp.update_layout(title_text='Mean Maximal Power (MMP) Curve', template='plotly_white', font=dict(color="black"),
                                xaxis_type="log",
                                xaxis = dict(
                                    tickmode = 'array',
                                    tickvals = [1, 5, 10, 30, 60, 120, 300, 600, 1200, 1800, 3600],
                                    ticktext = ['1s', '5s', '10s', '30s', '1m', '2m', '5m', '10m', '20m', '30m', '60m']
                                ))
        fig_mmp.update_xaxes(title_text='Duration (log scale)', showline=True, linewidth=2, linecolor='black', mirror=False)
        fig_mmp.update_yaxes(title_text='Max Power (W)', showline=True, linewidth=2, linecolor='black', mirror=False)
        st.plotly_chart(fig_mmp, use_container_width=True)

        if weight > 0:
            st.subheader("Mean Maximal Power (W/kg)")
            mmp_data_wkg = mmp_df.set_index("Duration (s)")["Max Power (W/kg)"]
            
            cols_wkg = st.columns(4)
            for i in range(0, len(duration_keys), 2):
                with cols_wkg[i//2]:
                    label1 = duration_keys[i]
                    duration1 = key_durations[label1]
                    power_value_wkg1 = mmp_data_wkg.get(duration1)
                    if power_value_wkg1 is not None:
                        st.metric(label=label1, value=f"{power_value_wkg1:.2f} W/kg")
                    else:
                        st.metric(label=label1, value="N/A")

                    if i + 1 < len(duration_keys):
                        label2 = duration_keys[i+1]
                        duration2 = key_durations[label2]
                        power_value_wkg2 = mmp_data_wkg.get(duration2)
                        if power_value_wkg2 is not None:
                            st.metric(label=label2, value=f"{power_value_wkg2:.2f} W/kg")
                        else:
                            st.metric(label=label2, value="N/A")

            fig_mmp_wkg = go.Figure(go.Scatter(x=mmp_df['Duration (s)'], y=mmp_df['Max Power (W/kg)'], mode='lines+markers', line=dict(color='orange')))
            fig_mmp_wkg.update_layout(title_text='Mean Maximal Power (MMP) Curve (W/kg)', template='plotly_white', font=dict(color="black"),
                                        xaxis_type="log",
                                        xaxis = dict(
                                            tickmode = 'array',
                                            tickvals = [1, 5, 10, 30, 60, 120, 300, 600, 1200, 1800, 3600],
                                            ticktext = ['1s', '5s', '10s', '30s', '1m', '2m', '5m', '10m', '20m', '30m', '60m']
                                        ))
            fig_mmp_wkg.update_xaxes(title_text='Duration (log scale)', showline=True, linewidth=2, linecolor='black', mirror=False)
            fig_mmp_wkg.update_yaxes(title_text='Max Power (W/kg)', showline=True, linewidth=2, linecolor='black', mirror=False)
            st.plotly_chart(fig_mmp_wkg, use_container_width=True)


    with tabs[5]: # Route Maps
        st.header("Route Maps")
        if 'position_lat' in df.columns and 'position_long' in df.columns and not df[['position_lat', 'position_long']].dropna().empty:
            gps_df = df[['position_lat', 'position_long', 'Wbal']].dropna().copy()
            
            st.subheader("Route Colored by W' Balance (%)")
            gps_df['Wbal_percent'] = (gps_df['Wbal'] / WP) * 100
            gps_df['Wbal_percent'] = gps_df['Wbal_percent'].clip(0, 100)
            
            wbal_colormap = cm.LinearColormap(colors=['red', 'yellow', 'green', 'blue'], vmin=0, vmax=100)
            
            m_wbal = folium.Map(location=[gps_df['position_lat'].mean(), gps_df['position_long'].mean()], zoom_start=13, tiles='CartoDB positron')
            
            coordinates = list(zip(gps_df['position_lat'], gps_df['position_long']))
            ColorLine(
                positions=coordinates,
                colors=gps_df['Wbal_percent'],
                colormap=wbal_colormap,
                weight=5
            ).add_to(m_wbal)

            wbal_colormap.caption = "W' Balance (%) (Red=Empty, Blue=Full)"
            m_wbal.add_child(wbal_colormap)
            st_folium(m_wbal, width=1400, height=500)
        else:
            st.warning("No GPS data found in the file to generate maps.")

    with tabs[6]: # Data Explorer
        st.header("Interactive Data Explorer")
        available_metrics = ['Power', 'Speed (km/h)']
        if 'cadence' in df.columns and df['cadence'].sum() > 0: available_metrics.append('Cadence')
        if 'heart_rate' in df.columns and df['heart_rate'].sum() > 0: available_metrics.append('Heart Rate')
        if 'altitude' in df.columns and df['altitude'].notna().any(): available_metrics.append('Altitude')

        selected_metrics = st.multiselect("Select data to display:", options=available_metrics, default=['Power', 'Speed (km/h)'])
        smoothing_window = st.slider("Smoothing (seconds)", min_value=1, max_value=30, value=5)

        if selected_metrics:
            fig_explorer = make_subplots(specs=[[{"secondary_y": True}]])
            axis_map = {'Power': 'left', 'Altitude': 'left', 'Speed (km/h)': 'right', 'Cadence': 'right', 'Heart Rate': 'right'}
            
            for metric in selected_metrics:
                col_name = metric.lower().replace(' (km/h)', '_kmh').replace(' ', '_')
                smoothed_data = df[col_name].rolling(window=smoothing_window, min_periods=1).mean()
                is_secondary = axis_map.get(metric) == 'right'
                fig_explorer.add_trace(go.Scatter(x=df['time'], y=smoothed_data, name=metric), secondary_y=is_secondary)
            
            fig_explorer.update_layout(title_text='Data Explorer', template='plotly_white', font=dict(color="black"))
            fig_explorer.update_xaxes(showline=True, linewidth=2, linecolor='black', mirror=False)
            fig_explorer.update_yaxes(showline=True, linewidth=2, linecolor='black', mirror=False, secondary_y=False)
            fig_explorer.update_yaxes(showline=True, linewidth=2, linecolor='black', mirror=False, secondary_y=True)
            st.plotly_chart(fig_explorer, use_container_width=True)
            
    with tabs[7]: # Raw Data Explorer
        st.header("Raw Data Explorer")
        
        cols_to_show = [col for col in ['power', 'cadence', 'heart_rate', 'altitude', 'speed_kmh', 'temperature'] if col in df.columns and df[col].notna().any()]
        
        num_cols = 3
        cols = st.columns(num_cols)
        for i, col_name in enumerate(cols_to_show):
            with cols[i % num_cols]:
                with st.container():
                    st.subheader(col_name.replace('_', ' ').title())
                    st.metric("Average", f"{df[col_name].mean():.1f}")
                    st.metric("Max", f"{df[col_name].max():.1f}")
                    st.metric("Min", f"{df[col_name].min():.1f}")

    with tabs[8]: # Beta Features
        st.header("🧪 Beta Features")
        st.warning("These features are experimental and may not be fully accurate. Use with caution.")
        
        st.subheader("Pacing Analysis (by Duration)")
        if not df.empty and df['time'].max() > 0:
            midpoint_time = df['time'].max() / 2
            first_half = df[df['time'] <= midpoint_time]
            second_half = df[df['time'] > midpoint_time]

            pacing_cols = st.columns(2)
            with pacing_cols[0]:
                st.markdown("#### First Half")
                if not first_half.empty:
                    st.metric("Avg Power", f"{round(first_half['power'].mean())} W")
                    st.metric("Avg Speed", f"{first_half['speed_kmh'].mean():.1f} km/h")
                    st.metric("Avg Cadence", f"{round(first_half[first_half['cadence'] > 0]['cadence'].mean()) if not first_half[first_half['cadence'] > 0].empty else 0} rpm")
                else:
                    st.write("No data in the first half.")
            with pacing_cols[1]:
                st.markdown("#### Second Half")
                if not second_half.empty:
                    st.metric("Avg Power", f"{round(second_half['power'].mean())} W")
                    st.metric("Avg Speed", f"{second_half['speed_kmh'].mean():.1f} km/h")
                    st.metric("Avg Cadence", f"{round(second_half[second_half['cadence'] > 0]['cadence'].mean()) if not second_half[second_half['cadence'] > 0].empty else 0} rpm")
                else:
                    st.write("No data in the second half.")
        else:
            st.info("Not enough data for pacing analysis.")


        st.divider()

        st.subheader("Ride Comparison")
        if 'df2' in results:
            df2 = results['df2']
            
            start_idx1 = (df['distance'] > 0).idxmax()
            start_idx2 = (df2['distance'] > 0).idxmax()
            
            df1_aligned = df.iloc[start_idx1:].copy()
            df2_aligned = df2.iloc[start_idx2:].copy()
            
            df1_aligned['time'] = df1_aligned['time'] - df1_aligned['time'].iloc[0]
            df2_aligned['time'] = df2_aligned['time'] - df2_aligned['time'].iloc[0]

            comp_cols = st.columns(2)
            with comp_cols[0]:
                st.markdown("#### Ride 1 (Primary)")
                st.metric("Avg Power", f"{round(df1_aligned['power'].mean())} W")
                st.metric("Avg Speed", f"{df1_aligned['speed_kmh'].mean():.1f} km/h")
                st.metric("Total Distance", f"{df1_aligned['distance'].max() / 1000:.2f} km")
            with comp_cols[1]:
                st.markdown("#### Ride 2 (Comparison)")
                st.metric("Avg Power", f"{round(df2_aligned['power'].mean())} W")
                st.metric("Avg Speed", f"{df2_aligned['speed_kmh'].mean():.1f} km/h")
                st.metric("Total Distance", f"{df2_aligned['distance'].max() / 1000:.2f} km")

            fig_comp = go.Figure()
            fig_comp.add_trace(go.Scatter(x=df1_aligned['time'], y=df1_aligned['power'], name='Ride 1 Power', line=dict(color='blue')))
            fig_comp.add_trace(go.Scatter(x=df2_aligned['time'], y=df2_aligned['power'], name='Ride 2 Power', line=dict(color='red')))
            fig_comp.update_layout(title_text='Power Comparison (Aligned by Start of Movement)', template='plotly_white')
            st.plotly_chart(fig_comp, use_container_width=True)

        else:
            st.info("Upload a second .fit file in the sidebar to use the ride comparison feature.")


elif not uploaded_file and analyze_button:
    st.warning("Please upload a .fit file first.")

else:
    if 'results' not in st.session_state:
        st.info("Welcome to my W'bal race analysis tool. Please input your values on the left and upload a .fit file. If there are any bugs/issues or requests for certain features, please email me at a.j.welburn@lboro.ac.uk. Please feel free to share this app as well.")
