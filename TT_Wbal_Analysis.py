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
from datetime import datetime
import requests

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
    start_time = None
    try:
        with io.BytesIO(file_content) as fit_file:
            with fitdecode.FitReader(fit_file) as fit:
                for frame in fit:
                    # Prioritize the file_id message for the most accurate start time
                    if frame.frame_type == fitdecode.FIT_FRAME_DATA and frame.name == "file_id":
                        if frame.has_field("time_created"):
                            start_time = frame.get_value("time_created")
                    
                    # Second priority: session start time
                    if start_time is None and frame.frame_type == fitdecode.FIT_FRAME_DATA and frame.name == "session":
                        if frame.has_field("start_time"):
                            start_time = frame.get_value("start_time")
                    
                    if frame.frame_type == fitdecode.FIT_FRAME_DATA and frame.name == "record":
                        # Fallback: if no other time found, use the first record's timestamp
                        if start_time is None and frame.has_field("timestamp"):
                            start_time = frame.get_value("timestamp")

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

    if not records:
        st.warning("The selected .fit file contains no data records.")
        return pd.DataFrame(), 0, None

    df = pd.DataFrame(records)
    
    if 'position_lat' in df.columns:
        df['position_lat'] = df['position_lat'] * SEMICIRCLES_TO_DEGREES
    if 'position_long' in df.columns:
        df['position_long'] = df['position_long'] * SEMICIRCLES_TO_DEGREES

    if start_time and isinstance(start_time, datetime):
        df['time'] = (df['timestamp'] - start_time).dt.total_seconds()
    else: # Fallback if no timestamp is found
        df['time'] = range(len(df))
        
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
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
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
        "Z1 Active Recovery": (0, 0.55), "Z2 Endurance": (0.55, 0.75), "Z3 Tempo": (0.75, 0.90),
        "Z4 Threshold": (0.90, 1.05), "Z5 VO2 Max": (1.05, 1.20), "Z6 Anaerobic": (1.20, 1.50),
        "Z7 Neuromuscular": (1.50, np.inf),
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
def calculate_mmp_curve(power_data: pd.Series) -> pd.DataFrame:
    """Calculates the Mean Maximal Power (MMP) curve."""
    durations = [1, 5, 10, 30, 60, 120, 300, 600, 1200, 1800, 3600]
    mmp = {d: power_data.rolling(window=d).mean().max() for d in durations if len(power_data) >= d}
    return pd.DataFrame(list(mmp.items()), columns=["Duration (s)", "Max Power (W)"])

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
        w_prime_depleted = duration * (avg_power - cp)
        depletion_percent = (w_prime_depleted / w_prime) * 100 if w_prime > 0 else 0
        match_data.append({
            "Start Time (s)": df['time'].iloc[match['start_index']],
            "Duration (s)": duration, 
            "Magnitude (%CP)": magnitude,
            "Depletion (% W')": depletion_percent
        })

    summary = {
        "Total Matches": len(match_data),
        "Avg Duration (s)": np.mean([m["Duration (s)"] for m in match_data]) if match_data else 0,
        "Avg Magnitude (%CP)": np.mean([m["Magnitude (%CP)"] for m in match_data]) if match_data else 0
    }
    
    return pd.DataFrame(match_data), summary


def get_time_of_day(hour: int) -> str:
    """Categorizes the hour into Morning, Afternoon, or Evening."""
    if 5 <= hour < 12: return "Morning"
    elif 12 <= hour < 18: return "Afternoon"
    else: return "Evening"
    
def format_seconds_to_hms(seconds: float) -> str:
    """Converts seconds into a 'Xh Ym Zs' format."""
    seconds = round(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining_seconds = seconds % 60
    return f"{hours}h {minutes}m {remaining_seconds}s"

# --- Main App Interface ---
st.title("🚴 W' Balance and Time Trial Analysis Tool")
st.markdown("Upload a `.fit` file and set your parameters to generate a detailed performance analysis.")

# --- Sidebar for Inputs ---
with st.sidebar:
    st.header("1. Upload Activity File")
    uploaded_file = st.file_uploader("Choose a .fit file", type="fit")
    st.caption("Note: Your data is processed in memory and is deleted when you close the browser tab. No data is stored.")
    
    st.header("2. Input Parameters")
    if 'A' not in st.session_state: st.session_state.A = 6000.0
    if 'B' not in st.session_state: st.session_state.B = -0.68
    if 'CP' not in st.session_state: st.session_state.CP = 350
    if 'WP_kJ' not in st.session_state: st.session_state.WP_kJ = 20.0

    A = st.number_input('AW Simple Tau Constant (A)', value=st.session_state.A, format="%.2f")
    B = st.number_input('AW Simple Tau Constant (B)', value=st.session_state.B, format="%.2f")
    CP = st.number_input('Critical Power (CP) in Watts', value=st.session_state.CP, step=1)
    WP_kJ = st.number_input('W\' (W prime) in kJ', value=st.session_state.WP_kJ, step=1.0, format="%.1f")

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
        df, start_time, missing_power_count = parse_fit_file(file_content)

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

                # --- VECTORIZED POWER AND CADENCE ANALYSIS ---
                metrics = {}
                df['state'] = np.where(df['power'] > CP, 'above', 'below')
                
                # Work calculations (Joules -> kJ)
                metrics["total_work_kj"] = round(df['power'].sum() / 1000)
                work_above_cp = df['power'][df['power'] > CP] - CP
                metrics["total_work_above_cp_kj"] = round(work_above_cp.sum() / 1000)

                # Time and Power metrics
                grouped_state = df.groupby('state')
                metrics["total_time_above"] = len(df[df['state'] == 'above'])
                metrics["total_time_below"] = len(df[df['state'] == 'below'])
                metrics["avg_power_above"] = round(df.loc[df['state'] == 'above', 'power'].mean()) if metrics["total_time_above"] > 0 else 0
                metrics["avg_power_below"] = round(df.loc[df['state'] == 'below', 'power'].mean()) if metrics["total_time_below"] > 0 else 0

                # Bouts calculation
                bout_starts = df['state'].ne(df['state'].shift())
                metrics["bouts_above"] = bout_starts[df['state'] == 'above'].sum()
                metrics["bouts_below"] = bout_starts[df['state'] == 'below'].sum()

                # Cadence metrics
                pedaling_df = df[df['cadence'] > 0]
                metrics["avg_cadence"] = round(pedaling_df['cadence'].mean()) if not pedaling_df.empty else 0
                if not pedaling_df.empty:
                    grouped_cadence = pedaling_df.groupby('state')
                    metrics["avg_cadence_above"] = round(grouped_cadence.get_group('above')['cadence'].mean()) if 'above' in grouped_cadence.groups else 0
                    metrics["avg_cadence_below"] = round(grouped_cadence.get_group('below')['cadence'].mean()) if 'below' in grouped_cadence.groups else 0
                else:
                    metrics["avg_cadence_above"] = 0
                    metrics["avg_cadence_below"] = 0

                # Coasting metrics
                metrics["coasting_time"] = (df['cadence'] == 0).sum()
                metrics["coasting_percent"] = round((metrics["coasting_time"] / len(df)) * 100) if len(df) > 0 else 0
                
                # Overall ride metrics
                metrics["avg_power_overall"] = round(df['power'].mean())
                metrics["avg_speed_overall"] = round(df['speed_kmh'].mean(), 1) if 'speed_kmh' in df.columns else 0
                metrics["total_distance"] = round(df['distance'].max() / 1000, 2) if 'distance' in df.columns else 0
                
                # --- Further Analysis ---
                power_zones_df = calculate_power_zones(df['power'], CP)
                mmp_df = calculate_mmp_curve(df['power'])
                top_above_bouts, top_below_bouts = find_top_bouts(df, CP)
                above_bouts_summary = analyze_bouts(df, top_above_bouts, "Effort", CP)
                below_bouts_summary = analyze_bouts(df, top_below_bouts, "Recovery", CP)
                
                first_coord = df[['position_lat', 'position_long']].dropna().iloc[0] if not df[['position_lat', 'position_long']].dropna().empty else None
                weather_data = get_weather_data(first_coord['position_lat'], first_coord['position_long'], start_time) if first_coord is not None else None

                st.session_state.results = {
                    "df": df,
                    "metrics": metrics,
                    "power_profile": {"zones": power_zones_df, "mmp": mmp_df},
                    "interval_analysis": {"above_bouts": top_above_bouts, "below_bouts": top_below_bouts, "above_summary": above_bouts_summary, "below_summary": below_bouts_summary},
                    "params": {"CP": CP, "WP": WP},
                    "ride_info": {"start_time": start_time, "weather": weather_data}
                }
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
    CP, WP = params["CP"], params["WP"]
    df['wbal_kj'] = df['Wbal'] / 1000

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(["📊 Summary", "🏃 Interval Analysis", "🔥 Match Analysis", "📈 Ride Profile", "⚡ Power Profile", "🗺️ Route Maps", "⚙️ Data Explorer", "📋 Raw Data Explorer"])

    with tab1:
        st.header("Ride Summary")
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
                temp = weather['temperature']
                thermo_emoji = "🔥" if temp > 25 else "☀️" if temp > 18 else "⛅"
                st.metric(f"Temperature {thermo_emoji}", f"{temp}°C")
                st.metric("Wind", f"{weather['wind_speed']} km/h ({weather['wind_direction']}°)")
            else:
                st.info("No location data found to fetch weather.")

        st.divider()
        st.subheader("Overall Ride Metrics")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Distance", f"{metrics.get('total_distance', 'N/A')} km")
        c2.metric("Average Power", f"{metrics.get('avg_power_overall', 'N/A')} W")
        c3.metric("Average Speed", f"{metrics.get('avg_speed_overall', 'N/A')} km/h")

        c4, c5, c6 = st.columns(3)
        # --- [FIX] Use .get() to prevent KeyError ---
        total_work_val = metrics.get('total_work_kj', 'N/A')
        work_above_cp_val = metrics.get('total_work_above_cp_kj', 'N/A')
        
        c4.metric("Total Work", f"{total_work_val} kJ" if isinstance(total_work_val, (int, float)) else "N/A")
        c5.metric("Work Above CP", f"{work_above_cp_val} kJ" if isinstance(work_above_cp_val, (int, float)) else "N/A")
        c6.metric("Coasting", f"{metrics.get('coasting_percent', 'N/A')}%")
        
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

    with tab2:
        st.header("Interval Analysis")
        fig_intervals = make_subplots(specs=[[{"secondary_y": True}]])
        fig_intervals.add_trace(go.Scatter(x=df['time'], y=df['power'], name='Power', line=dict(color='grey', width=1)), secondary_y=False)
        fig_intervals.add_trace(go.Scatter(x=df['time'], y=df['wbal_kj'], name='W\'bal (kJ)', line=dict(color='#9467bd', width=2)), secondary_y=True)
        
        fig_intervals.add_trace(go.Scatter(x=[None], y=[None], mode='markers', marker=dict(color='rgba(214, 39, 40, 0.4)'), name='Top Effort'))
        fig_intervals.add_trace(go.Scatter(x=[None], y=[None], mode='markers', marker=dict(color='rgba(31, 119, 180, 0.4)'), name='Top Recovery'))

        for bout in interval_analysis['above_bouts']:
            fig_intervals.add_vrect(x0=df['time'].iloc[bout['start']], x1=df['time'].iloc[bout['end']], fillcolor="red", opacity=0.2, layer="below", line_width=0)
        for bout in interval_analysis['below_bouts']:
            fig_intervals.add_vrect(x0=df['time'].iloc[bout['start']], x1=df['time'].iloc[bout['end']], fillcolor="blue", opacity=0.2, layer="below", line_width=0)

        fig_intervals.update_layout(title_text='Top Bouts vs. Power and W\'bal', template='plotly_white', font=dict(color="black"), showlegend=True)
        fig_intervals.update_xaxes(showline=True, linewidth=2, linecolor='black', mirror=False)
        fig_intervals.update_yaxes(title_text="Power (W)", showline=True, linewidth=2, linecolor='black', mirror=False, secondary_y=False)
        fig_intervals.update_yaxes(title_text="W'bal (kJ)", showline=True, linewidth=2, linecolor='black', mirror=False, secondary_y=True)
        st.plotly_chart(fig_intervals, use_container_width=True)

        st.subheader("Top 3 Efforts (>CP)")
        st.dataframe(interval_analysis['above_summary'])
        st.subheader("Top 3 Recovery Bouts (<=CP)")
        st.dataframe(interval_analysis['below_summary'])

    with tab3:
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

        # Add W' depletion curves
        max_duration = max(71, matches_df['Duration (s)'].max() + 10) if not matches_df.empty else 71
        for depletion in range(10, 60, 10):
            durations = np.arange(1, max_duration)
            power_depletion = (WP * (depletion / 100) / durations) + CP
            magnitude = (power_depletion / CP) * 100
            fig_matches.add_trace(go.Scatter(x=durations, y=magnitude, mode='lines', line=dict(dash='dot', color='grey'), name=f'{depletion}% W\' depletion'))

        fig_matches.update_layout(
            title_text='Match Magnitude vs. Duration', 
            template='plotly_white', 
            font=dict(color="black"),
            legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
        )
        fig_matches.update_xaxes(title_text='Duration (s)', showline=True, linewidth=2, linecolor='black', mirror=False)
        fig_matches.update_yaxes(title_text='Magnitude (% of CP)', showline=True, linewidth=2, linecolor='black', mirror=False, range=[105, 250])
        st.plotly_chart(fig_matches, use_container_width=True)

    with tab4:
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

    with tab5:
        st.header("Power Profile")
        zones_df = power_profile["zones"]
        fig_zones = go.Figure(go.Bar(x=zones_df['Time (s)'], y=zones_df['Zone'], orientation='h', text=zones_df['Percentage'].apply(lambda x: f'{x:.1f}%')))
        fig_zones.update_layout(title_text='Time in Power Zones', template='plotly_white', font=dict(color="black"))
        fig_zones.update_xaxes(showline=True, linewidth=2, linecolor='black', mirror=False)
        fig_zones.update_yaxes(showline=True, linewidth=2, linecolor='black', mirror=False)
        st.plotly_chart(fig_zones, use_container_width=True)
        
        mmp_df = power_profile["mmp"]
        st.subheader("Mean Maximal Power")
        
        key_durations = {"5s": 5, "1 min": 60, "5 min": 300, "20 min": 1200}
        mmp_data = mmp_df.set_index("Duration (s)")["Max Power (W)"]
        
        cols = st.columns(len(key_durations))
        for i, (label, duration) in enumerate(key_durations.items()):
            power_value = mmp_data.get(duration)
            with cols[i]:
                if power_value is not None:
                    st.metric(label=label, value=f"{int(power_value)} W")
                else:
                    st.metric(label=label, value="N/A")

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

    with tab6:
        st.header("Route Maps")
        if 'position_lat' in df.columns and 'position_long' in df.columns and not df[['position_lat', 'position_long']].dropna().empty:
            gps_df = df[['position_lat', 'position_long', 'Wbal']].dropna().copy()
            
            st.subheader("Route Colored by W' Balance (%)")
            gps_df['Wbal_percent'] = (gps_df['Wbal'] / WP) * 100
            gps_df['Wbal_percent'] = gps_df['Wbal_percent'].clip(0, 100)
            
            wbal_colormap = cm.LinearColormap(colors=['red', 'yellow', 'green', 'blue'], vmin=0, vmax=100)
            
            m_wbal = folium.Map(location=[gps_df['position_lat'].mean(), gps_df['position_long'].mean()], zoom_start=13, tiles='CartoDB positron')
            for i in range(len(gps_df) - 1):
                p1, p2 = (gps_df[['position_lat', 'position_long']].iloc[i].values, 
                          gps_df[['position_lat', 'position_long']].iloc[i+1].values)
                avg_wbal_percent = (gps_df['Wbal_percent'].iloc[i] + gps_df['Wbal_percent'].iloc[i+1]) / 2
                folium.PolyLine([p1, p2], color=wbal_colormap(avg_wbal_percent), weight=5).add_to(m_wbal)
            wbal_colormap.caption = "W' Balance (%) (Red=Empty, Blue=Full)"
            m_wbal.add_child(wbal_colormap)
            st_folium(m_wbal, width=1400, height=500)
        else:
            st.warning("No GPS data found in the file to generate maps.")

    with tab7:
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
            
    with tab8:
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


elif not uploaded_file and analyze_button:
    st.warning("Please upload a .fit file first.")

else:
    if 'results' not in st.session_state:
        st.info("Upload a file and click 'Analyze Ride' to begin.")
