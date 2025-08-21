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

# --- Page Configuration ---
st.set_page_config(
    page_title="W'bal Analysis Tool",
    page_icon="🚴",
    layout="wide"
)

# --- 1. ANALYSIS FUNCTIONS (Cached for performance) ---

@st.cache_data
def parse_fit_file(file_content: bytes) -> Tuple[pd.DataFrame, int]:
    """
    Parses the in-memory .fit file content into a pandas DataFrame.
    """
    records = []
    try:
        with io.BytesIO(file_content) as fit_file:
            with fitdecode.FitReader(fit_file) as fit:
                for frame in fit:
                    if frame.frame_type == fitdecode.FIT_FRAME_DATA and frame.name == "record":
                        record_data = {
                            "timestamp": frame.get_value("timestamp", fallback=None),
                            "power": frame.get_value("power", fallback=None),
                            "cadence": frame.get_value("cadence", fallback=None),
                            "altitude": frame.get_value("altitude", fallback=None),
                            "heart_rate": frame.get_value("heart_rate", fallback=None),
                            "speed": frame.get_value("speed", fallback=None),
                            "position_lat": frame.get_value("position_lat", fallback=None),
                            "position_long": frame.get_value("position_long", fallback=None),
                        }
                        if record_data["timestamp"] is not None:
                            records.append(record_data)
    except fitdecode.FitDecodeError as e:
        st.error(f"Error decoding .fit file: {e}")
        return pd.DataFrame(), 0

    if not records:
        return pd.DataFrame(), 0

    df = pd.DataFrame(records)
    
    if 'position_lat' in df.columns:
        df['position_lat'] = df['position_lat'] * (180 / 2**31) if df['position_lat'].notnull().any() else np.nan
    if 'position_long' in df.columns:
        df['position_long'] = df['position_long'] * (180 / 2**31) if df['position_long'].notnull().any() else np.nan

    start_time = df['timestamp'].iloc[0]
    df['time'] = (df['timestamp'] - start_time).dt.total_seconds()
    df.drop(columns=['timestamp'], inplace=True)

    missing_power_count = df['power'].isnull().sum()
    df['power'].fillna(0, inplace=True)
    
    for col in ['power', 'cadence', 'heart_rate', 'speed']:
        if col not in df.columns: df[col] = 0
        df[col].fillna(0, inplace=True)
        df[col] = pd.to_numeric(df[col], errors='coerce')

    if 'altitude' in df.columns: df['altitude'].fillna(method='ffill', inplace=True)
    if 'speed' in df.columns: df['speed_kmh'] = df['speed'] * 3.6

    return df, missing_power_count

@st.cache_data
def calculate_power_zones(power_data: pd.Series, cp: int) -> pd.DataFrame:
    """Calculates time spent in 7 power zones based on CP."""
    zones = {
        "Z1 Active Recovery": (0, 0.55),
        "Z2 Endurance": (0.55, 0.75),
        "Z3 Tempo": (0.75, 0.90),
        "Z4 Threshold": (0.90, 1.05),
        "Z5 VO2 Max": (1.05, 1.20),
        "Z6 Anaerobic": (1.20, 1.50),
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
    zone_data = []
    for name, seconds in zone_counts.items():
        percentage = (seconds / total_seconds) * 100 if total_seconds > 0 else 0
        zone_data.append({"Zone": name, "Time (s)": seconds, "Percentage": percentage})
        
    return pd.DataFrame(zone_data)

@st.cache_data
def calculate_mmp_curve(power_data: pd.Series) -> pd.DataFrame:
    """Calculates the Mean Maximal Power (MMP) curve."""
    durations = [1, 5, 10, 30, 60, 120, 300, 600, 1200, 1800, 3600]
    mmp = {}
    for d in durations:
        if len(power_data) >= d:
            mmp[d] = power_data.rolling(window=d).mean().max()
    
    return pd.DataFrame(list(mmp.items()), columns=["Duration (s)", "Max Power (W)"])


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
        df, missing_power_count = parse_fit_file(file_content)

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

                st.session_state.results = {
                    "df": df,
                    "metrics": {
                        "avg_power_above": round(total_work_above / total_time_above) if total_time_above > 0 else 0,
                        "avg_power_below": round(total_work_below / total_time_below) if total_time_below > 0 else 0,
                        "avg_power_overall": round(df['power'].mean()),
                        "total_time_above": total_time_above, "total_time_below": total_time_below,
                        "bouts_above": bouts_above, "bouts_below": bouts_below,
                        "avg_cadence": round(cadence_sum / cadence_count) if cadence_count > 0 else 0,
                        "avg_cadence_above": round(cadence_above_sum / cadence_above_count) if cadence_above_count > 0 else 0,
                        "avg_cadence_below": round(cadence_below_sum / cadence_below_count) if cadence_below_count > 0 else 0,
                        "coasting_time": coasting_time,
                        "coasting_percent": round((coasting_time / sum(durations)) * 100) if sum(durations) > 0 else 0,
                    },
                    "power_profile": {
                        "zones": power_zones_df,
                        "mmp": mmp_df
                    },
                    "params": {"CP": CP, "WP": WP}
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
    CP, WP = params["CP"], params["WP"]
    df['wbal_kj'] = df['Wbal'] / 1000

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Summary", "📈 Ride Profile", "⚡ Power Profile", "🗺️ Route Maps", "⚙️ Data Explorer"])

    with tab1:
        st.header(f"Summary Metrics (Threshold = {int(CP)} W)")
        st.subheader("Power Analysis")
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
        
        st.divider()
        st.subheader("Cadence Analysis")
        c1, c2, c3 = st.columns(3)
        c1.metric("Avg Cadence Overall", f"{metrics['avg_cadence']} rpm")
        c2.metric("Avg Cadence >CP", f"{metrics['avg_cadence_above']} rpm")
        c3.metric("Avg Cadence <=CP", f"{metrics['avg_cadence_below']} rpm")
        st.metric("Total Coasting Time (Cadence=0)", f"{round(metrics['coasting_time'])}s ({metrics['coasting_percent']}%)")

    with tab2:
        st.header("Ride Profile Charts")
        fig_wbal = make_subplots(specs=[[{"secondary_y": True}]])
        fig_wbal.add_trace(go.Scatter(x=df['time'], y=df['wbal_kj'], name='W\'bal (kJ)', line=dict(color='#9467bd', width=2)), secondary_y=False)
        if 'altitude' in df.columns and df['altitude'].notna().any():
            fig_wbal.add_trace(go.Scatter(x=df['time'], y=df['altitude'], name='Elevation (m)', line=dict(color='#2ca02c', width=2), fill='tozeroy'), secondary_y=True)
        fig_wbal.update_layout(title_text='W\' Balance vs. Elevation', template='plotly_dark')
        fig_wbal.update_yaxes(title_text="W'bal (kJ)", secondary_y=False); fig_wbal.update_yaxes(title_text="Elevation (m)", secondary_y=True)
        st.plotly_chart(fig_wbal, use_container_width=True)

        fig_power = go.Figure()
        fig_power.add_trace(go.Scatter(x=df['time'], y=df['power'], name='Power', line=dict(color='cyan', width=1)))
        fig_power.add_shape(type="line", x0=df['time'].min(), y0=CP, x1=df['time'].max(), y1=CP, line=dict(color="#ff7f0e", width=2, dash="dash"), name=f"CP ({CP}W)")
        fig_power.update_layout(title_text='Power over Time', template='plotly_dark')
        st.plotly_chart(fig_power, use_container_width=True)

    with tab3:
        st.header("Power Profile")
        zones_df = power_profile["zones"]
        fig_zones = go.Figure(go.Bar(x=zones_df['Time (s)'], y=zones_df['Zone'], orientation='h', text=zones_df['Percentage'].apply(lambda x: f'{x:.1f}%')))
        fig_zones.update_layout(title_text='Time in Power Zones', template='plotly_dark')
        st.plotly_chart(fig_zones, use_container_width=True)
        
        mmp_df = power_profile["mmp"]
        fig_mmp = go.Figure(go.Scatter(x=mmp_df['Duration (s)'], y=mmp_df['Max Power (W)'], mode='lines+markers'))
        fig_mmp.update_layout(title_text='Mean Maximal Power (MMP) Curve', template='plotly_dark', 
                              xaxis_type="log",
                              xaxis = dict(
                                tickmode = 'array',
                                tickvals = [1, 5, 10, 30, 60, 120, 300, 600, 1200, 1800, 3600],
                                ticktext = ['1s', '5s', '10s', '30s', '1m', '2m', '5m', '10m', '20m', '30m', '60m']
                            ))
        fig_mmp.update_xaxes(title_text='Duration (log scale)'); fig_mmp.update_yaxes(title_text='Max Power (W)')
        st.plotly_chart(fig_mmp, use_container_width=True)

    with tab4:
        st.header("Route Maps")
        if 'position_lat' in df.columns and 'position_long' in df.columns and not df[['position_lat', 'position_long']].dropna().empty:
            gps_df = df[['position_lat', 'position_long', 'Wbal', 'power', 'speed_kmh']].dropna().copy()
            
            st.subheader("Route Colored by W' Balance (%)")
            gps_df['Wbal_percent'] = (gps_df['Wbal'] / WP) * 100
            gps_df['Wbal_percent'] = gps_df['Wbal_percent'].clip(0, 100)
            # FIX: Using a valid, high-contrast colormap name in lowercase
            wbal_colormap = cm.linear.viridis.scale(0, 100)
            m_wbal = folium.Map(location=[gps_df['position_lat'].mean(), gps_df['position_long'].mean()], zoom_start=13, tiles='CartoDB positron')
            for i in range(len(gps_df) - 1):
                p1, p2 = (gps_df[['position_lat', 'position_long']].iloc[i].values, 
                          gps_df[['position_lat', 'position_long']].iloc[i+1].values)
                avg_wbal_percent = (gps_df['Wbal_percent'].iloc[i] + gps_df['Wbal_percent'].iloc[i+1]) / 2
                folium.PolyLine([p1, p2], color=wbal_colormap(avg_wbal_percent), weight=5).add_to(m_wbal)
            wbal_colormap.caption = "W' Balance (%)"
            m_wbal.add_child(wbal_colormap)
            st_folium(m_wbal, width=1400, height=500)

            st.subheader("Route Colored by Power vs. CP")
            power_diff = gps_df['power'] - CP
            norm_power = np.clip(power_diff, -150, 150)
            power_colormap = cm.linear.coolwarm.scale(-150, 150)
            m_power = folium.Map(location=[gps_df['position_lat'].mean(), gps_df['position_long'].mean()], zoom_start=13, tiles='CartoDB positron')
            for i in range(len(gps_df) - 1):
                p1, p2 = (gps_df[['position_lat', 'position_long']].iloc[i].values, 
                          gps_df[['position_lat', 'position_long']].iloc[i+1].values)
                avg_norm_power = (norm_power.iloc[i] + norm_power.iloc[i+1]) / 2
                folium.PolyLine([p1, p2], color=power_colormap(avg_norm_power), weight=5).add_to(m_power)
            power_colormap.caption = "Power relative to CP (Watts)"
            m_power.add_child(power_colormap)
            st_folium(m_power, width=1400, height=500)
            
            st.subheader("Route Colored by Speed (km/h)")
            min_speed, max_speed = gps_df['speed_kmh'].min(), gps_df['speed_kmh'].max()
            speed_colormap = cm.linear.inferno.scale(min_speed, max_speed)
            m_speed = folium.Map(location=[gps_df['position_lat'].mean(), gps_df['position_long'].mean()], zoom_start=13, tiles='CartoDB positron')
            for i in range(len(gps_df) - 1):
                p1, p2 = (gps_df[['position_lat', 'position_long']].iloc[i].values, 
                          gps_df[['position_lat', 'position_long']].iloc[i+1].values)
                avg_speed = (gps_df['speed_kmh'].iloc[i] + gps_df['speed_kmh'].iloc[i+1]) / 2
                folium.PolyLine([p1, p2], color=speed_colormap(avg_speed), weight=5).add_to(m_speed)
            speed_colormap.caption = "Speed (km/h)"
            m_speed.add_child(speed_colormap)
            st_folium(m_speed, width=1400, height=500)
        else:
            st.warning("No GPS data found in the file to generate maps.")

    with tab5:
        st.header("Interactive Data Explorer")
        available_metrics = ['Power', 'Speed (km/h)']
        selected_metrics = st.multiselect("Select data to display:", options=available_metrics, default=['Power', 'Speed (km/h)'])
        smoothing_window = st.slider("Smoothing (seconds)", min_value=1, max_value=30, value=5)

        if selected_metrics:
            fig_explorer = make_subplots(specs=[[{"secondary_y": True}]])
            for metric in selected_metrics:
                col_name = metric.lower().replace(' (km/h)', '_kmh')
                smoothed_data = df[col_name].rolling(window=smoothing_window, min_periods=1).mean()
                is_secondary = metric == 'Speed (km/h)'
                fig_explorer.add_trace(go.Scatter(x=df['time'], y=smoothed_data, name=metric), secondary_y=is_secondary)
            
            fig_explorer.update_layout(title_text='Data Explorer', template='plotly_dark')
            st.plotly_chart(fig_explorer, use_container_width=True)

elif not uploaded_file and analyze_button:
    st.warning("Please upload a .fit file first.")

else:
    if 'results' not in st.session_state:
        st.info("Upload a file and click 'Analyze Ride' to begin.")
