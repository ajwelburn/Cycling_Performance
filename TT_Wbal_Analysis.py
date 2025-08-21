import streamlit as st
import pandas as pd
import math as m
import matplotlib.pyplot as plt
import numpy as np
import fitdecode
import io
import folium
import branca.colormap as cm
from streamlit_folium import st_folium
from typing import Tuple, List, Dict

# --- Page Configuration ---
st.set_page_config(
    page_title="W'bal Analysis Tool",
    page_icon="🚴",
    layout="wide"
)

# --- 1. FIT FILE PARSING FUNCTION (Cached for performance) ---
@st.cache_data
def parse_fit_file(file_content: bytes) -> Tuple[pd.DataFrame, int, List[int]]:
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
        return pd.DataFrame(), 0, []

    if not records:
        return pd.DataFrame(), 0, []

    df = pd.DataFrame(records)
    
    if 'position_lat' in df.columns:
        df['position_lat'] = df['position_lat'] * (180 / 2**31) if df['position_lat'].notnull().any() else np.nan
    if 'position_long' in df.columns:
        df['position_long'] = df['position_long'] * (180 / 2**31) if df['position_long'].notnull().any() else np.nan

    start_time = df['timestamp'].iloc[0]
    df['time'] = (df['timestamp'] - start_time).dt.total_seconds()
    df.drop(columns=['timestamp'], inplace=True)

    missing_power_mask = df['power'].isnull()
    missing_count = missing_power_mask.sum()
    
    df['power'].fillna(0, inplace=True)
    df['power'] = pd.to_numeric(df['power'], errors='coerce')

    for col in ['cadence', 'heart_rate', 'speed']:
        if col not in df.columns:
            df[col] = 0
        df[col].fillna(0, inplace=True)
        df[col] = pd.to_numeric(df[col], errors='coerce')

    if 'altitude' in df.columns:
        df['altitude'].fillna(method='ffill', inplace=True)
        
    # Convert speed from m/s to km/h
    if 'speed' in df.columns:
        df['speed_kmh'] = df['speed'] * 3.6

    return df, missing_count, []

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
        df, missing_power_count, missing_power_times = parse_fit_file(file_content)

        if df.empty:
            st.error("Could not parse the .fit file. It might be empty or corrupted.")
            if 'results' in st.session_state:
                del st.session_state['results']
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
                
                # Store results in session state
                st.session_state.results = {
                    "df": df,
                    "metrics": {
                        "avg_power_above": round(total_work_above / total_time_above) if total_time_above > 0 else 0,
                        "avg_power_below": round(total_work_below / total_time_below) if total_time_below > 0 else 0,
                        "avg_time_per_bout_above": round(total_time_above / bouts_above) if bouts_above > 0 else 0,
                        "avg_time_per_bout_below": round(total_time_below / bouts_below) if bouts_below > 0 else 0,
                        "avg_cadence": round(cadence_sum / cadence_count) if cadence_count > 0 else 0,
                        "avg_cadence_above": round(cadence_above_sum / cadence_above_count) if cadence_above_count > 0 else 0,
                        "avg_cadence_below": round(cadence_below_sum / cadence_below_count) if cadence_below_count > 0 else 0,
                        "avg_power_overall": round(df['power'].mean()),
                        "coasting_percent": round((coasting_time / sum(durations)) * 100) if sum(durations) > 0 else 0,
                        "total_time_above": total_time_above, "total_time_below": total_time_below,
                        "bouts_above": bouts_above, "bouts_below": bouts_below,
                        "coasting_time": coasting_time
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
    CP = params["CP"]
    WP = params["WP"]
    df['wbal_kj'] = df['Wbal'] / 1000

    # Set modern plot style
    plt.style.use("dark_background")
    plt.rcParams.update({
        'axes.edgecolor': 'white', 'axes.labelcolor': 'white',
        'xtick.color': 'white', 'ytick.color': 'white',
        'figure.facecolor': 'black', 'axes.facecolor': 'black',
        'text.color': 'white', 'legend.facecolor': 'none'
    })

    tab1, tab2, tab3, tab4 = st.tabs(["📊 Summary Metrics", "📈 Charts", "🗺️ Route Maps", "⚙️ Interactive Data"])

    with tab1:
        st.header(f"Summary Metrics (Threshold = {int(CP)} W)")
        st.subheader("Power Analysis")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### Above CP")
            st.metric("Total Time", f"{round(metrics['total_time_above'])} s")
            st.metric("Avg Power", f"{metrics['avg_power_above']} W")
            st.metric("Number of Bouts", f"{metrics['bouts_above']}")
            st.metric("Avg Time/Bout", f"{metrics['avg_time_per_bout_above']} s")
        with col2:
            st.markdown("##### Below or At CP")
            st.metric("Total Time", f"{round(metrics['total_time_below'])} s")
            st.metric("Avg Power", f"{metrics['avg_power_below']} W")
            st.metric("Number of Bouts", f"{metrics['bouts_below']}")
            st.metric("Avg Time/Bout", f"{metrics['avg_time_per_bout_below']} s")
        
        st.divider()
        st.subheader("Cadence Analysis")
        c1, c2, c3 = st.columns(3)
        c1.metric("Avg Cadence Overall", f"{metrics['avg_cadence']} rpm")
        c2.metric("Avg Cadence >CP", f"{metrics['avg_cadence_above']} rpm")
        c3.metric("Avg Cadence <=CP", f"{metrics['avg_cadence_below']} rpm")
        st.metric("Total Coasting Time (Cadence=0)", f"{round(metrics['coasting_time'])}s ({metrics['coasting_percent']}%)")

    with tab2:
        st.header("Charts")
        if 'altitude' in df.columns and df['altitude'].notna().any():
            fig_elev, ax_elev1 = plt.subplots(figsize=(12, 6))
            ax_elev1.set_xlabel('Time (s)'); ax_elev1.set_ylabel('W\'bal (kJ)', color='#9467bd')
            ax_elev1.plot(df['time'], df['wbal_kj'], color='#9467bd', linewidth=2, label='W\'bal')
            ax_elev1.tick_params(axis='y', labelcolor='#9467bd')
            ax_elev1.axhline(y=0, color='grey', linestyle='--', linewidth=1)
            ax_elev2 = ax_elev1.twinx()
            ax_elev2.set_ylabel('Elevation (m)', color='#2ca02c')
            ax_elev2.fill_between(df['time'], df['altitude'], color='#2ca02c', alpha=0.3, label='Elevation')
            ax_elev2.tick_params(axis='y', labelcolor='#2ca02c')
            fig_elev.suptitle('W\' Balance vs. Elevation'); fig_elev.tight_layout()
            st.pyplot(fig_elev)
        
        fig3, ax3 = plt.subplots(figsize=(12, 6))
        ax3.set_title("Power over Time with Threshold Coloring", fontsize=14)
        ax3.set_xlabel("Time (s)"); ax3.set_ylabel("Power (W)")
        ax3.fill_between(df['time'], df['power'], CP, where=df['power'] <= CP, color='#1f77b4', alpha=0.7, interpolate=True)
        ax3.fill_between(df['time'], df['power'], CP, where=df['power'] > CP, color='#d62728', alpha=0.7, interpolate=True)
        ax3.plot(df['time'], df['power'], color='lightgrey', linewidth=0.5, label='Power')
        ax3.axhline(y=CP, color='#ff7f0e', linestyle='--', label=f"CP = {int(CP)} W")
        stats_text = (f"Avg Power (Overall): {metrics['avg_power_overall']} W\n"
                      f"Avg Power (>CP): {metrics['avg_power_above']} W\n"
                      f"Avg Power (<=CP): {metrics['avg_power_below']} W")
        ax3.text(0.02, 0.95, stats_text, transform=ax3.transAxes, fontsize=10,
                 verticalalignment='top', bbox=dict(boxstyle='round,pad=0.5', facecolor='black', alpha=0.7))
        ax3.legend(); ax3.grid(False)
        st.pyplot(fig3)
        plt.close('all')

    with tab3:
        st.header("Route Maps")
        if 'position_lat' in df.columns and 'position_long' in df.columns and not df[['position_lat', 'position_long']].dropna().empty:
            gps_df = df[['position_lat', 'position_long', 'Wbal', 'power', 'speed_kmh']].dropna().copy()
            
            st.subheader("Route Colored by W' Balance (%)")
            gps_df['Wbal_percent'] = (gps_df['Wbal'] / WP) * 100
            gps_df['Wbal_percent'] = gps_df['Wbal_percent'].clip(0, 100)
            wbal_colormap = cm.linear.Plasma_06.scale(0, 100)
            m_wbal = folium.Map(location=[gps_df['position_lat'].mean(), gps_df['position_long'].mean()], zoom_start=13, tiles='CartoDB dark_matter')
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
            m_power = folium.Map(location=[gps_df['position_lat'].mean(), gps_df['position_long'].mean()], zoom_start=13, tiles='CartoDB dark_matter')
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
            speed_colormap = cm.linear.Inferno_06.scale(min_speed, max_speed)
            m_speed = folium.Map(location=[gps_df['position_lat'].mean(), gps_df['position_long'].mean()], zoom_start=13, tiles='CartoDB dark_matter')
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

    with tab4:
        st.header("Interactive Data Explorer")
        
        available_metrics = ['Power', 'Speed (km/h)']
        selected_metrics = st.multiselect(
            "Select data to display:",
            options=available_metrics,
            default=['Power', 'Speed (km/h)']
        )

        smoothing_window = st.slider("Smoothing (seconds)", min_value=1, max_value=30, value=5,
                                     help="Applies a rolling average to the data. 1 = raw data.")

        if selected_metrics:
            fig_interactive, ax_interactive = plt.subplots(figsize=(12, 6))
            ax_interactive.set_xlabel('Time (s)')
            
            ax2 = ax_interactive.twinx()
            ax_map = {'Power': ax_interactive, 'Speed (km/h)': ax2}
            color_map = {'Power': '#1f77b4', 'Speed (km/h)': '#ff7f0e'}
            label_map = {'Power': 'Power (W)', 'Speed (km/h)': 'Speed (km/h)'}
            
            ax1_used, ax2_used = False, False

            for metric in selected_metrics:
                axis = ax_map[metric]
                col_name = metric.lower().replace(' (km/h)', '_kmh')
                
                smoothed_data = df[col_name].rolling(window=smoothing_window, min_periods=1).mean()
                
                axis.plot(df['time'], smoothed_data, label=metric, color=color_map[metric])
                axis.set_ylabel(label_map[metric], color=color_map[metric])
                axis.tick_params(axis='y', labelcolor=color_map[metric])
                if axis == ax_interactive: ax1_used = True
                if axis == ax2: ax2_used = True
            
            if not ax1_used: ax_interactive.get_yaxis().set_visible(False)
            if not ax2_used: ax2.get_yaxis().set_visible(False)
            
            fig_interactive.legend(loc="upper right", bbox_to_anchor=(1,1), bbox_transform=ax_interactive.transAxes)
            fig_interactive.tight_layout()
            st.pyplot(fig_interactive)
            plt.close(fig_interactive)

elif not uploaded_file and analyze_button:
    st.warning("Please upload a .fit file first.")

else:
    if 'results' not in st.session_state:
        st.info("Upload a file and click 'Analyze Ride' to begin.")
