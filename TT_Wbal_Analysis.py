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
from typing import Tuple, List

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
    missing_times = df.loc[missing_power_mask, 'time'].round().astype(int).tolist()

    df['power'].fillna(0, inplace=True)
    df['power'] = pd.to_numeric(df['power'], errors='coerce')

    if 'cadence' not in df.columns:
        df['cadence'] = 0
    df['cadence'].fillna(0, inplace=True)
    df['cadence'] = pd.to_numeric(df['cadence'], errors='coerce')

    if 'altitude' in df.columns:
        df['altitude'].fillna(method='ffill', inplace=True) # Forward fill any gaps in altitude

    return df, missing_count, missing_times

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
    if 'WP_kJ' not in st.session_state: st.session_state.WP_kJ = 20.0 # Default in kJ

    A = st.number_input('AW Simple Tau Constant (A)', value=st.session_state.A, format="%.2f")
    B = st.number_input('AW Simple Tau Constant (B)', value=st.session_state.B, format="%.2f")
    CP = st.number_input('Critical Power (CP) in Watts', value=st.session_state.CP, step=1)
    WP_kJ = st.number_input('W\' (W prime) in kJ', value=st.session_state.WP_kJ, step=1.0, format="%.1f")

    analyze_button = st.button("Analyze Ride", type="primary")

# --- Main Panel for Outputs ---
if uploaded_file and analyze_button:
    WP = WP_kJ * 1000 # Convert kJ input to Joules for calculation
    file_content = uploaded_file.getvalue()
    df, missing_power_count, missing_power_times = parse_fit_file(file_content)

    if df.empty:
        st.error("Could not parse the .fit file. It might be empty or corrupted.")
    else:
        st.success(f"Successfully loaded and parsed the .fit file. Found {len(df)} data records.")
        if missing_power_count > 0:
            st.warning(f"Found and replaced {missing_power_count} missing power data point(s) with 0.")

        # --- W'bal CALCULATION ---
        with st.spinner("Calculating W' balance..."):
            Wbal, Wbal_old, Wexp = float(WP), float(WP), 0.0
            wbal_list, tau_list = [0.0]*len(df), [0.0]*len(df)
            wbal_list[0] = float(WP)
            power_np = df['power'].to_numpy()
            for i in range(1, len(df)):
                P = power_np[i]
                if P > CP:
                    Wbal -= (P - CP)
                else:
                    DCP2 = CP - P
                    Tau = A * (DCP2 ** B) if DCP2 > 0 else 0
                    Wbal = WP - ((WP - Wbal_old) * m.exp(-1 / Tau)) if Tau > 0 else Wbal
                Wbal = min(WP, Wbal)
                Wbal_old = Wbal
                wbal_list[i], tau_list[i] = Wbal, Tau
            df['Wbal'], df['Tau'] = wbal_list, tau_list

        # --- POWER AND CADENCE ANALYSIS ---
        with st.spinner("Analyzing power and cadence data..."):
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

            avg_power_above = round(total_work_above / total_time_above) if total_time_above > 0 else 0
            avg_power_below = round(total_work_below / total_time_below) if total_time_below > 0 else 0
            avg_time_per_bout_above = round(total_time_above / bouts_above) if bouts_above > 0 else 0
            avg_time_per_bout_below = round(total_time_below / bouts_below) if bouts_below > 0 else 0
            avg_cadence = round(cadence_sum / cadence_count) if cadence_count > 0 else 0
            avg_cadence_above = round(cadence_above_sum / cadence_above_count) if cadence_above_count > 0 else 0
            avg_cadence_below = round(cadence_below_sum / cadence_below_count) if cadence_below_count > 0 else 0
            total_time = sum(durations)
            avg_power_overall = round(df['power'].mean())
            coasting_percent = round((coasting_time / total_time) * 100) if total_time > 0 else 0

        # --- DISPLAY OUTPUTS IN TABS ---
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Summary Metrics", "📈 Charts", "🗺️ Route Maps", "📋 Raw Data"])

        with tab1:
            st.header(f"Summary Metrics (Threshold = {int(CP)} W)")
            st.subheader("Power Analysis")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("##### Above CP")
                st.metric("Total Time", f"{round(total_time_above)} s")
                st.metric("Avg Power", f"{avg_power_above} W")
                st.metric("Number of Bouts", f"{bouts_above}")
                st.metric("Avg Time/Bout", f"{avg_time_per_bout_above} s")
            with col2:
                st.markdown("##### Below or At CP")
                st.metric("Total Time", f"{round(total_time_below)} s")
                st.metric("Avg Power", f"{avg_power_below} W")
                st.metric("Number of Bouts", f"{bouts_below}")
                st.metric("Avg Time/Bout", f"{avg_time_per_bout_below} s")
            
            st.divider()
            st.subheader("Cadence Analysis")
            c1, c2, c3 = st.columns(3)
            c1.metric("Avg Cadence Overall", f"{avg_cadence} rpm")
            c2.metric("Avg Cadence >CP", f"{avg_cadence_above} rpm")
            c3.metric("Avg Cadence <=CP", f"{avg_cadence_below} rpm")
            st.metric("Total Coasting Time (Cadence=0)", f"{round(coasting_time)}s ({coasting_percent}%)")

        with tab2:
            st.header("Charts")

            # PLOT 1: W' Balance Over Time
            fig1, ax1 = plt.subplots(figsize=(12, 6))
            ax1.plot(df['time'], df['Wbal'], label='W\'bal', color='purple', linewidth=2)
            ax1.axhline(y=0, color='grey', linestyle='--', linewidth=1)
            ax1.set_xlabel('Time (s)'), ax1.set_ylabel('W\'bal (Joules)'), ax1.set_title('W\' Balance Over Time')
            ax1.grid(False), ax1.legend()
            st.pyplot(fig1)

            # PLOT 2: W'bal and Elevation
            if 'altitude' in df.columns and df['altitude'].notna().any():
                fig_elev, ax_elev1 = plt.subplots(figsize=(12, 6))
                ax_elev1.set_xlabel('Time (s)'), ax_elev1.set_ylabel('W\'bal (Joules)', color='purple')
                ax_elev1.plot(df['time'], df['Wbal'], color='purple', linewidth=2, label='W\'bal')
                ax_elev1.tick_params(axis='y', labelcolor='purple')
                ax_elev1.axhline(y=0, color='grey', linestyle='--', linewidth=1)
                ax_elev2 = ax_elev1.twinx()
                ax_elev2.set_ylabel('Elevation (m)', color='green')
                ax_elev2.plot(df['time'], df['altitude'], color='green', linewidth=2, label='Elevation')
                ax_elev2.tick_params(axis='y', labelcolor='green')
                fig_elev.suptitle('W\' Balance vs. Elevation'), fig_elev.tight_layout()
                st.pyplot(fig_elev)

            # PLOT 3: Power Over Time with Averages
            fig3, ax3 = plt.subplots(figsize=(12, 6))
            ax3.set_title("Power over Time with Threshold Coloring", fontsize=14)
            ax3.set_xlabel("Time (s)"), ax3.set_ylabel("Power (W)")
            ax3.fill_between(df['time'], df['power'], CP, where=df['power'] <= CP, color='#1f77b4', alpha=0.5, interpolate=True)
            ax3.fill_between(df['time'], df['power'], CP, where=df['power'] > CP, color='#d62728', alpha=0.5, interpolate=True)
            ax3.plot(df['time'], df['power'], color='black', linewidth=0.5, label='Power')
            ax3.axhline(y=CP, color='orange', linestyle='--', label=f"CP = {int(CP)} W")
            
            stats_text = (
                f"Avg Power (Overall): {avg_power_overall} W\n"
                f"Avg Power (>CP): {avg_power_above} W\n"
                f"Avg Power (<=CP): {avg_power_below} W"
            )
            ax3.text(0.02, 0.95, stats_text, transform=ax3.transAxes, fontsize=10,
                     verticalalignment='top', bbox=dict(boxstyle='round,pad=0.5', facecolor='wheat', alpha=0.5))

            ax3.legend(), ax3.grid(False)
            st.pyplot(fig3)

        with tab3:
            st.header("Route Maps")
            if 'position_lat' in df.columns and 'position_long' in df.columns and df[['position_lat', 'position_long']].notnull().all(axis=1).any():
                gps_df = df[['position_lat', 'position_long', 'Wbal', 'power']].dropna().copy()
                
                st.subheader("Route Colored by W' Balance (%)")
                gps_df['Wbal_percent'] = (gps_df['Wbal'] / WP) * 100
                gps_df['Wbal_percent'] = gps_df['Wbal_percent'].clip(0, 100)
                wbal_colormap = cm.linear.RdYlGn_09.scale(0, 100)
                m_wbal = folium.Map(location=[gps_df['position_lat'].mean(), gps_df['position_long'].mean()], zoom_start=13)
                
                for i in range(len(gps_df) - 1):
                    p1 = (gps_df['position_lat'].iloc[i], gps_df['position_long'].iloc[i])
                    p2 = (gps_df['position_lat'].iloc[i+1], gps_df['position_long'].iloc[i+1])
                    avg_wbal_percent = (gps_df['Wbal_percent'].iloc[i] + gps_df['Wbal_percent'].iloc[i+1]) / 2
                    color = wbal_colormap(avg_wbal_percent)
                    folium.PolyLine([p1, p2], color=color, weight=5).add_to(m_wbal)

                wbal_colormap.caption = "W' Balance (%)"
                m_wbal.add_child(wbal_colormap)
                st_folium(m_wbal, width=1400, height=500)

                st.subheader("Route Colored by Power vs. CP")
                power_diff = gps_df['power'] - CP
                norm_power = np.clip(power_diff, -150, 150)
                power_colormap = cm.linear.RdBu_11.scale(-150, 150)
                m_power = folium.Map(location=[gps_df['position_lat'].mean(), gps_df['position_long'].mean()], zoom_start=13)

                for i in range(len(gps_df) - 1):
                    p1 = (gps_df['position_lat'].iloc[i], gps_df['position_long'].iloc[i])
                    p2 = (gps_df['position_lat'].iloc[i+1], gps_df['position_long'].iloc[i+1])
                    avg_norm_power = (norm_power.iloc[i] + norm_power.iloc[i+1]) / 2
                    color = power_colormap(avg_norm_power)
                    folium.PolyLine([p1, p2], color=color, weight=5).add_to(m_power)

                power_colormap.caption = "Power relative to CP (Watts)"
                m_power.add_child(power_colormap)
                st_folium(m_power, width=1400, height=500)
            else:
                st.warning("No GPS data found in the file to generate maps.")

        with tab4:
            st.header("Full Data Table")
            st.dataframe(df.round(2))
            
            @st.cache_data
            def convert_df_to_csv(df_to_convert):
                return df_to_convert.to_csv(index=False).encode('utf-8')

            csv = convert_df_to_csv(df)
            st.download_button(
                label="Download data as CSV",
                data=csv,
                file_name=f"{uploaded_file.name.split('.')[0]}_analysis.csv",
                mime='text/csv',
            )

elif not uploaded_file and analyze_button:
    st.warning("Please upload a .fit file first.")

else:
    st.info("Upload a file and click 'Analyze Ride' to begin.")
