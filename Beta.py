# ==============================================================================
# --- IMPORTS & INITIAL CONFIGURATION ---
# ==============================================================================
import streamlit as st
import pandas as pd
import math
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
from folium.features import ColorLine
import plotly.colors

st.set_page_config(page_title="W'bal Analysis Tool", page_icon="🚴", layout="wide")

# ==============================================================================
# --- CONSTANTS ---
# ==============================================================================
SEMICIRCLES_TO_DEGREES = 180 / (2**31)

# ==============================================================================
# --- HELPER & ANALYSIS FUNCTIONS ---
# ==============================================================================
@st.cache_data
def parse_fit_file(fit_file_bytes: bytes) -> Tuple[pd.DataFrame, datetime]:
    """Parses a .fit file into a clean pandas DataFrame."""
    records, session_start_time, first_record_time = [], None, None
    try:
        with fitdecode.FitReader(io.BytesIO(fit_file_bytes)) as fit:
            for frame in fit:
                if frame.frame_type == fitdecode.FIT_FRAME_DATA:
                    if frame.name == "session": session_start_time = frame.get_value("start_time", fallback=None)
                    elif frame.name == "record":
                        if first_record_time is None: first_record_time = frame.get_value("timestamp", fallback=None)
                        records.append({field.name: field.value for field in frame.fields if field.value is not None})
    except fitdecode.FitDecodeError as e:
        st.error(f"Error decoding .fit file: {e}"); return pd.DataFrame(), None

    if not records: st.warning("No data records found in file."); return pd.DataFrame(), None

    ride_df = pd.DataFrame(records).dropna(subset=['timestamp'])
    start_time = session_start_time or first_record_time
    ride_df['time'] = (ride_df['timestamp'] - (start_time or ride_df['timestamp'].iloc[0])).dt.total_seconds()
    ride_df['time_hms'] = pd.to_datetime(ride_df['time'], unit='s')
    
    for coord_col in ['position_lat', 'position_long']:
        if coord_col in ride_df: ride_df[coord_col] *= SEMICIRCLES_TO_DEGREES
    
    data_cols = ['power', 'cadence', 'heart_rate', 'speed', 'distance', 'temperature', 'altitude']
    for col in data_cols:
        if col not in ride_df: ride_df[col] = 0
        ride_df[col] = pd.to_numeric(ride_df[col], errors='coerce').fillna(0)
    
    if 'speed' in ride_df: ride_df['speed_kmh'] = (ride_df['speed'] * 3.6).rolling(3, min_periods=1).mean()
    
    return ride_df, start_time

@st.cache_data
def calculate_wbal(ride_df, critical_power, w_prime_joules, tau_a, tau_b):
    """Calculates the W' balance for the entire ride."""
    wbal_list = [float(w_prime_joules)]
    Wbal_old = float(w_prime_joules)
    power_np = ride_df['power'].to_numpy()
    
    for i in range(1, len(ride_df)):
        power = power_np[i]
        if power > critical_power:
            Wbal = wbal_list[-1] - (power - critical_power)
        else:
            power_diff = critical_power - power
            tau = tau_a * (power_diff ** tau_b) if power_diff > 0 else 1e9
            Wbal = w_prime_joules - ((w_prime_joules - Wbal_old) * math.exp(-1 / tau))
        
        wbal_list.append(min(w_prime_joules, Wbal))
        Wbal_old = wbal_list[-1]
        
    ride_df['Wbal'] = wbal_list
    ride_df['wbal_percent'] = (ride_df['Wbal'] / w_prime_joules) * 100
    return ride_df

@st.cache_data
def get_ride_summary_metrics(ride_df, critical_power, rider_weight_kg):
    """Calculates a dictionary of summary metrics from the ride data."""
    metrics = {}
    ride_df['state'] = np.where(ride_df['power'] > critical_power, 'above', 'below')
    
    metrics['avg_power_overall'] = ride_df['power'].mean()
    metrics['total_work_kj'] = ride_df['power'].sum() / 1000
    metrics['total_work_above_cp_kj'] = (ride_df['power'] - critical_power).clip(lower=0).sum() / 1000
    
    if rider_weight_kg > 0:
        metrics['avg_power_w_kg'] = metrics['avg_power_overall'] / rider_weight_kg
        metrics['total_work_kj_per_kg'] = metrics['total_work_kj'] / rider_weight_kg
        metrics['total_work_above_cp_kj_per_kg'] = metrics['total_work_above_cp_kj'] / rider_weight_kg

    time_split = ride_df['state'].value_counts()
    power_split = ride_df.groupby('state')['power'].mean()
    metrics['total_time_above'] = time_split.get('above', 0)
    metrics['total_time_below'] = time_split.get('below', 0)
    metrics['avg_power_above'] = power_split.get('above', 0)
    metrics['avg_power_below'] = power_split.get('below', 0)
    
    metrics['coasting_percent'] = (ride_df['cadence'] == 0).sum() / len(ride_df) * 100
    metrics['avg_speed_overall'] = ride_df['speed_kmh'].mean() if 'speed_kmh' in ride_df else 0
    metrics['total_distance'] = ride_df['distance'].max() / 1000 if 'distance' in ride_df else 0
    return metrics

@st.cache_data
def calculate_mmp_curve(power_series: pd.Series) -> pd.DataFrame:
    """Correctly calculates the Mean Maximal Power (MMP) curve."""
    mmp_data = []
    # Use a limited set of durations for performance
    durations = sorted(list(set(np.logspace(0, np.log10(len(power_series)), 100).astype(int))))
    
    for d in durations:
        if d > 0:
            max_power = power_series.rolling(window=d).mean().max()
            mmp_data.append({'duration': d, 'mmp': max_power})
    
    return pd.DataFrame(mmp_data)

def format_seconds(seconds: float, mode='hms') -> str:
    """Formats seconds into H:M:S or M:S strings."""
    seconds = round(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h}h {m:02d}m {s:02d}s" if mode == 'hms' else f"{int(h*60 + m)}m {s:02d}s"

# ==============================================================================
# --- UI HELPER FUNCTIONS ---
# ==============================================================================

def display_summary_metrics(metrics_dict: Dict, num_columns: int = 3):
    """Dynamically displays a dictionary of metrics in styled columns."""
    cols = st.columns(num_columns)
    for i, (label, (value, sub_value)) in enumerate(metrics_dict.items()):
        with cols[i % num_columns]:
            st.metric(label, value)
            if sub_value:
                st.markdown(f"<p style='color:green; font-size: 0.9em; margin-top: -10px;'>{sub_value}</p>", unsafe_allow_html=True)

def create_main_figure(title, y1_title, y2_title=None):
    """Creates a configured Plotly figure object to reduce boilerplate."""
    fig = make_subplots(specs=[[{"secondary_y": bool(y2_title)}]])
    fig.update_layout(template='plotly_white', title_text=title, legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5))
    fig.update_xaxes(title_text="Time (HH:MM:SS)", tickformat='%H:%M:%S')
    fig.update_yaxes(title_text=f"<b>{y1_title}</b>", secondary_y=False)
    if y2_title:
        fig.update_yaxes(title_text=f"<b>{y2_title}</b>", secondary_y=True)
    return fig

# ==============================================================================
# --- SIDEBAR / USER INPUTS ---
# ==============================================================================
with st.sidebar:
    st.header("1. Upload Activity")
    uploaded_fit_file = st.file_uploader("Choose a .fit file", type="fit")

    st.header("2. Set Parameters")
    rider_weight_kg = st.number_input(
        'Weight (kg)', 
        min_value=30.0, 
        max_value=200.0, 
        value=75.0, 
        step=0.5, 
        format="%.1f"
    )
    critical_power = st.number_input('Critical Power (CP) in Watts', value=350, step=1)
    w_prime_kilojoules = st.number_input("W' (kJ)", value=20.0, min_value=1.0, max_value=100.0, step=1.0, format="%.1f")
    
    with st.expander("Advanced Model Parameters (Tau)"):
        tau_a = st.number_input('Parameter A', value=5187, step=1)
        tau_b = st.number_input('Parameter B', value=-0.70, format="%.2f")
        
    analyze_button = st.button("Analyze Ride", type="primary")

# ==============================================================================
# --- MAIN ANALYSIS & UI DISPLAY ---
# ==============================================================================
if 'current_file' not in st.session_state: st.session_state.current_file = None
if uploaded_fit_file and uploaded_fit_file.name != st.session_state.current_file:
    st.session_state.current_file = uploaded_fit_file.name
    if 'analysis_results' in st.session_state: del st.session_state['analysis_results']

if analyze_button and uploaded_fit_file:
    with st.spinner("Analyzing... This may take a moment. ⚙️"):
        ride_data, start_time = parse_fit_file(uploaded_fit_file.getvalue())
        if not ride_data.empty:
            w_prime_joules = w_prime_kilojoules * 1000
            ride_data = calculate_wbal(ride_data, critical_power, w_prime_joules, tau_a, tau_b)
            ride_metrics = get_ride_summary_metrics(ride_data, critical_power, rider_weight_kg)
            
            st.session_state.analysis_results = {
                "ride_data": ride_data,
                "ride_metrics": ride_metrics,
                "user_params": {"CP": critical_power, "WP_J": w_prime_joules, "Weight": rider_weight_kg},
                "ride_info": {"start_time": start_time}
            }
elif analyze_button:
    st.warning("Please upload a .fit file first.")

if 'analysis_results' in st.session_state:
    # --- Unpack results from session state ---
    results = st.session_state.analysis_results
    ride_data = results["ride_data"]
    ride_metrics = results["ride_metrics"]
    user_params = results["user_params"]
    
    ride_data['wbal_kj'] = ride_data['Wbal'] / 1000 # Derived column for plotting
    min_wbal_kj, max_wbal_kj = ride_data['wbal_kj'].min(), ride_data['wbal_kj'].max()
    yaxis_range = [min(0, min_wbal_kj), user_params['WP_J'] / 1000 * 1.05]

    st.title("🚴 W' Bal: Ride Analysis")
    
    # --- DEFINE TABS ---
    summary_tab, profile_tab, power_tab, map_tab = st.tabs(["📊 Summary", "📈 Ride Profile", "⚡ Power Profile", "🗺️ Route Map"])

    # --- TAB 1: SUMMARY ---
    with summary_tab:
        st.header("Overall Ride Metrics")
        summary_metrics = {
            "Total Distance": (f"{ride_metrics['total_distance']:.2f} km", None),
            "Average Power": (f"{ride_metrics['avg_power_overall']:.0f} W", f"{ride_metrics.get('avg_power_w_kg', 0):.2f} W/kg"),
            "Average Speed": (f"{ride_metrics['avg_speed_overall']:.1f} km/h", None),
            "Total Work": (f"{ride_metrics['total_work_kj']:.0f} kJ", f"{ride_metrics.get('total_work_kj_per_kg', 0):.1f} kJ/kg"),
            "Work > CP": (f"{ride_metrics['total_work_above_cp_kj']:.0f} kJ", f"{ride_metrics.get('total_work_above_cp_kj_per_kg', 0):.1f} kJ/kg"),
            "Coasting": (f"{ride_metrics['coasting_percent']:.1f}%", None),
        }
        display_summary_metrics(summary_metrics)
        
        st.divider()
        st.header(f"Analysis vs. CP ({user_params['CP']} W)")
        above_cp_col, below_cp_col = st.columns(2)
        with above_cp_col:
            st.markdown("##### 📈 Above CP")
            display_summary_metrics({
                "Total Time": (format_seconds(ride_metrics['total_time_above']), None),
                "Avg Power": (f"{ride_metrics['avg_power_above']:.0f} W", None),
            }, num_columns=2)
        with below_cp_col:
            st.markdown("##### 📉 Below or At CP")
            display_summary_metrics({
                "Total Time": (format_seconds(ride_metrics['total_time_below']), None),
                "Avg Power": (f"{ride_metrics['avg_power_below']:.0f} W", None),
            }, num_columns=2)

    # --- TAB 2: RIDE PROFILE ---
    with profile_tab:
        st.header("W' Balance & Power Profile")
        profile_fig = create_main_figure("W' Balance vs. Power", "W'bal (kJ)", "Power (W)")
        profile_fig.add_trace(go.Scatter(x=ride_data['time_hms'], y=ride_data['power'], name='Power', line=dict(color='grey', width=1.5)), secondary_y=True)
        profile_fig.add_trace(go.Scatter(x=ride_data['time_hms'], y=ride_data['wbal_kj'], name="W'bal", line=dict(color='#9467bd', width=2.5)), secondary_y=False)
        profile_fig.update_yaxes(range=yaxis_range, secondary_y=False)
        st.plotly_chart(profile_fig, use_container_width=True)

        if 'altitude' in ride_data.columns and ride_data['altitude'].notna().any():
            st.header("W' Balance & Elevation Profile")
            elevation_fig = create_main_figure("W' Balance vs. Elevation", "W'bal (kJ)", "Elevation (m)")
            elevation_fig.add_trace(go.Scatter(x=ride_data['time_hms'], y=ride_data['altitude'], name='Elevation', line=dict(color='#2ca02c', width=2), fill='tozeroy'), secondary_y=True)
            elevation_fig.add_trace(go.Scatter(x=ride_data['time_hms'], y=ride_data['wbal_kj'], name="W'bal", line=dict(color='#9467bd', width=2.5)), secondary_y=False)
            elevation_fig.update_yaxes(range=yaxis_range, secondary_y=False)
            st.plotly_chart(elevation_fig, use_container_width=True)

    # --- TAB 3: POWER PROFILE ---
    with power_tab:
        st.header("Mean Maximal Power (MMP)")
        mmp_df = calculate_mmp_curve(ride_data['power'])
        
        mmp_fig = go.Figure(go.Scatter(x=mmp_df['duration'], y=mmp_df['mmp'], mode='lines'))
        mmp_fig.update_layout(title_text='Mean Maximal Power (MMP) Curve', template='plotly_white', xaxis_type="log",
                              xaxis=dict(tickmode='array', tickvals=[1, 5, 10, 30, 60, 300, 600, 1200, 3600],
                                         ticktext=['1s', '5s', '10s', '30s', '1m', '5m', '10m', '20m', '60m']))
        mmp_fig.update_xaxes(title_text='Duration (log scale)')
        mmp_fig.update_yaxes(title_text='Max Power (W)')
        st.plotly_chart(mmp_fig, use_container_width=True)

    # --- TAB 4: ROUTE MAP ---
    with map_tab:
        st.header("Route Map")
        if 'position_lat' in ride_data.columns and ride_data['position_lat'].notna().any():
            gps_df = ride_data[['position_lat', 'position_long', 'wbal_percent']].dropna()
            wbal_colormap = cm.LinearColormap(colors=['red', 'yellow', 'green'], vmin=0, vmax=100, caption="W' Balance (%)")
            route_map = folium.Map(location=[gps_df['position_lat'].mean(), gps_df['position_long'].mean()], zoom_start=13, tiles='CartoDB positron')
            ColorLine(positions=list(zip(gps_df['position_lat'], gps_df['position_long'])),
                      colors=gps_df['wbal_percent'], colormap=wbal_colormap, weight=5).add_to(route_map)
            route_map.add_child(wbal_colormap)
            st_folium(route_map, width=1400, height=500)
        else:
            st.warning("No GPS data found in the file to generate a map.")
            
else:
     if 'analysis_results' not in st.session_state:
        st.info("Welcome! Please upload a .fit file and click 'Analyze Ride' in the sidebar to begin.")
