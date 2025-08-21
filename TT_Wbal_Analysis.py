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

# --- Page Configuration ---
st.set_page_config(
    page_title="W'bal Analysis Tool",
    page_icon="🚴",
    layout="wide"
)

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
                    
                    if frame.frame_type == fitdecode.FIT_FRAME_DATA and frame.name == "record":
                        # Fallback: if no file_id message, use the first record's timestamp
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
        df['position_lat'] = df['position_lat'] * (180 / 2**31) if df['position_lat'].notnull().any() else np.nan
    if 'position_long' in df.columns:
        df['position_long'] = df['position_long'] * (180 / 2**31) if df['position_long'].notnull().any() else np.nan

    if start_time:
        df['time'] = (df['timestamp'] - start_time).dt.total_seconds()
    else: # Fallback if no timestamp is found
        df['time'] = range(len(df))
        
    df.drop(columns=['timestamp'], inplace=True, errors='ignore')

    missing_power_count = df['power'].isnull().sum()
    if missing_power_count > 0:
        st.warning(f"Note: Found and replaced {missing_power_count} missing power data point(s) with 0.")
    df['power'].fillna(0, inplace=True)
    
    for col in ['power', 'cadence', 'heart_rate', 'speed', 'distance', 'temperature']:
        if col not in df.columns: df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)


    if 'altitude' in df.columns: df['altitude'].fillna(method='ffill', inplace=True)
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
        if response.status_code == 200:
            data = response.json()
            hour = start_time.hour
            return {
                "temperature": data['hourly']['temperature_2m'][hour],
                "humidity": data['hourly']['relativehumidity_2m'][hour],
                "wind_speed": data['hourly']['windspeed_10m'][hour],
                "wind_direction": data['hourly']['winddirection_10m'][hour],
            }
    except Exception:
        pass
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
        
        bout_summary = {
            "Bout": f"{bout_type} Bout {i+1}",
            "Duration (s)": bout['duration'],
            "Avg Power (W)": round(bout_df['power'].mean()),
            "Avg Speed (km/h)": round(bout_df['speed_kmh'].mean(), 1),
            "Avg Cadence (rpm)": round(bout_df['cadence'][bout_df['cadence'] > 0].mean()),
            "W' Change (kJ)": round(wbal_change / 1000, 2)
        }
        
        if bout_type == "Effort":
            bout_summary["Avg Power > CP (W)"] = round(bout_df['power'].mean() - cp)
        else: # Recovery
            bout_summary["Avg Power < CP (W)"] = round(cp - bout_df['power'].mean())

        summary.append(bout_summary)
        
    return pd.DataFrame(summary)


def get_time_of_day(hour: int) -> str:
    """Categorizes the hour into Morning, Afternoon, or Evening."""
    if 5 <= hour < 12: return "Morning"
    elif 12 <= hour < 18: return "Afternoon"
    else: return "Evening"

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

                # --- POWER AND CADENCE ANALYSIS ---
                durations = df['time'].diff().fillna(1).tolist()
                total_time_above, total_work_above, total_time_below, total_work_below = 0, 0, 0, 0
                bouts_above, bouts_below = 0, 0
                previous_state = 'below' if df['power'].iloc[0] <= CP else 'above'
                cadence_sum, cadence_count, cadence_above_sum, cadence_above_count = 0, 0, 0, 0
                cadence_below_sum, cadence_below_count, coasting_time = 0, 0, 0
                
                for i in range(len(df)):
                    dur, powr, cad = durations[i], df['power'].iloc[i], df['cadence'].iloc[i]
                    current_state = 'above' if powr > CP else 'below'
                    if cad == 0: coasting_time += dur
                    else:
                        cadence_sum += cad * dur
                        cadence_count += dur
                        if current_state == 'above':
                            cadence_above_sum += cad * dur
                            cadence_above_count += dur
                        else:
                            cadence_below_sum += cad * dur
                            cadence_below_count += dur
                    if current_state != previous_state:
                        if current_state == 'above': bouts_above += 1
                        else: bouts_below += 1
                        previous_state = current_state
                    if current_state == 'above':
                        total_time_above += dur
                        total_work_above += powr * dur
                    else:
                        total_time_below += dur
                        total_work_below += powr * dur
                
                power_zones_df = calculate_power_zones(df['power'], CP)
                mmp_df = calculate_mmp_curve(df['power'])
                top_above_bouts, top_below_bouts = find_top_bouts(df, CP)
                above_bouts_summary = analyze_bouts(df, top_above_bouts, "Effort", CP)
                below_bouts_summary = analyze_bouts(df, top_below_bouts, "Recovery", CP)
                
                first_coord = df[['position_lat', 'position_long']].dropna().iloc[0] if not df[['position_lat', 'position_long']].dropna().empty else None
                weather_data = get_weather_data(first_coord['position_lat'], first_coord['position_long'], start_time) if first_coord is not None else None

                st.session_state.results = {
                    "df": df,
                    "metrics": {
                        "avg_power_above": round(total_work_above / total_time_above) if total_time_above > 0 else 0,
                        "avg_power_below": round(total_work_below / total_time_below) if total_time_below > 0 else 0,
                        "avg_power_overall": round(df['power'].mean()),
                        "avg_speed_overall": round(df['speed_kmh'].mean(), 1) if 'speed_kmh' in df.columns else 0,
                        "total_distance": round(df['distance'].max() / 1000, 2) if 'distance' in df.columns else 0,
                        "total_time_above": total_time_above, "total_time_below": total_time_below,
                        "bouts_above": bouts_above, "bouts_below": bouts_below,
                        "avg_cadence": round(cadence_sum / cadence_count) if cadence_count > 0 else 0,
                        "avg_cadence_above": round(cadence_above_sum / cadence_above_count) if cadence_above_count > 0 else 0,
                        "avg_cadence_below": round(cadence_below_sum / cadence_below_count) if cadence_below_count > 0 else 0,
                        "coasting_time": coasting_time,
                        "coasting_percent": round((coasting_time / sum(durations)) * 100) if sum(durations) > 0 else 0,
                    },
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

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["📊 Summary", "🏃 Interval Analysis", "📈 Ride Profile", "⚡ Power Profile", "🗺️ Route Maps", "⚙️ Data Explorer", "📋 Raw Data Explorer"])

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
        c1.metric("Total Distance", f"{metrics['total_distance']} km")
        c2.metric("Average Power", f"{metrics['avg_power_overall']} W")
        c3.metric("Average Speed", f"{metrics['avg_speed_overall']} km/h")
        
        st.divider()
        st.header(f"Power Analysis (Threshold = {int(CP)} W)")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### Above CP")
            st.metric("Total Time", f"{round(metrics['total_time_above'])} s")
            st.metric("Avg Power", f"{metrics['avg_power_above']} W")
            st.metric("Number of Bouts", f"{metrics['bouts_above']}")
        with col2:
            st.markdown("##### Below or At CP")
            st.metric("Total Time", f"{round(metrics['total_time_below'])} s")
            st.metric("Avg Power", f"{metrics['avg_power_below']} W")
            st.metric("Number of Bouts", f"{metrics['bouts_below']}")

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

    with tab4:
        st.header("Power Profile")
        zones_df = power_profile["zones"]
        fig_zones = go.Figure(go.Bar(x=zones_df['Time (s)'], y=zones_df['Zone'], orientation='h', text=zones_df['Percentage'].apply(lambda x: f'{x:.1f}%')))
        fig_zones.update_layout(title_text='Time in Power Zones', template='plotly_white', font=dict(color="black"))
        fig_zones.update_xaxes(showline=True, linewidth=2, linecolor='black', mirror=False)
        fig_zones.update_yaxes(showline=True, linewidth=2, linecolor='black', mirror=False)
        st.plotly_chart(fig_zones, use_container_width=True)
        
        mmp_df = power_profile["mmp"]
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

    with tab5:
        st.header("Route Maps")
        if 'position_lat' in df.columns and 'position_long' in df.columns and not df[['position_lat', 'position_long']].dropna().empty:
            gps_df = df[['position_lat', 'position_long', 'Wbal', 'power', 'speed_kmh']].dropna().copy()
            
            st.subheader("Route Colored by W' Balance (%)")
            gps_df['Wbal_percent'] = (gps_df['Wbal'] / WP) * 100
            gps_df['Wbal_percent'] = gps_df['Wbal_percent'].clip(0, 100)
            wbal_colormap = cm.LinearColormap(colors=['blue', 'cyan', 'yellow', 'red'], vmin=0, vmax=100)
            m_wbal = folium.Map(location=[gps_df['position_lat'].mean(), gps_df['position_long'].mean()], zoom_start=13, tiles='CartoDB positron')
            for i in range(len(gps_df) - 1):
                p1, p2 = (gps_df[['position_lat', 'position_long']].iloc[i].values, 
                          gps_df[['position_lat', 'position_long']].iloc[i+1].values)
                avg_wbal_percent = (gps_df['Wbal_percent'].iloc[i] + gps_df['Wbal_percent'].iloc[i+1]) / 2
                folium.PolyLine([p1, p2], color=wbal_colormap(avg_wbal_percent), weight=5).add_to(m_wbal)
            wbal_colormap.caption = "W' Balance (%)"
            m_wbal.add_child(wbal_colormap)
            st_folium(m_wbal, width=1400, height=500)
        else:
            st.warning("No GPS data found in the file to generate maps.")

    with tab6:
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
                col_name = metric.lower().replace(' (km/h)', '_kmh')
                smoothed_data = df[col_name].rolling(window=smoothing_window, min_periods=1).mean()
                is_secondary = axis_map.get(metric) == 'right'
                fig_explorer.add_trace(go.Scatter(x=df['time'], y=smoothed_data, name=metric), secondary_y=is_secondary)
            
            fig_explorer.update_layout(title_text='Data Explorer', template='plotly_white', font=dict(color="black"))
            fig_explorer.update_xaxes(showline=True, linewidth=2, linecolor='black', mirror=False)
            fig_explorer.update_yaxes(showline=True, linewidth=2, linecolor='black', mirror=False, secondary_y=False)
            fig_explorer.update_yaxes(showline=True, linewidth=2, linecolor='black', mirror=False, secondary_y=True)
            st.plotly_chart(fig_explorer, use_container_width=True)
            
    with tab7:
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
