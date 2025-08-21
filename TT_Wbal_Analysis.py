import streamlit as st
import pandas as pd
import math as m
import matplotlib.pyplot as plt
import numpy as np
import fitdecode
import io
import folium
import branca.colormap as cm
from folium.features import ColorLine
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
st.title("� W' Balance and Time Trial Analysis Tool")
st.markdown("Upload a `.fit` file and set your parameters to generate a detailed performance analysis.")

# --- Sidebar for Inputs ---
with st.sidebar:
    st.header("1. Upload Activity File")
    uploaded_file = st.file_uploader("Choose a .fit file", type="fit")
    
    st.header("2. Input Parameters")
    # Using session state to remember values and new defaults
    if 'A' not in st.session_state: st.session_state.A = 6000.0
    if 'B' not in st.session_state: st.session_state.B = -0.68
    if 'CP' not in st.session_state: st.session_state.CP = 350
    if 'WP' not in st.session_state: st.session_state.WP = 20000

    A = st.number_input('AW Simple Tau Constant (A)', value=st.session_state.A, format="%.2f")
    B = st.number_input('AW Simple Tau Constant (B)', value=st.session_state.B, format="%.2f")
    CP = st.number_input('Critical Power (CP) in Watts', value=st.session_state.CP, step=1)
    WP = st.number_input('W\' (W prime) in Joules', value=st.session_state.WP, step=100)

    analyze_button = st.button("Analyze Ride", type="primary")

# --- Main Panel for Outputs ---
if uploaded_file and analyze_button:
    # --- 2. DATA PROCESSING ---
    file_content = uploaded_file.getvalue()
    df, missing_power_count, missing_power_times = parse_fit_file(file_content)

    if df.empty:
        st.error("Could not parse the .fit file. It might be empty or corrupted.")
    else:
        st.success(f"Successfully loaded and parsed the .fit file. Found {len(df)} data records.")
        if missing_power_count > 0:
            st.warning(f"Found and replaced {missing_power_count} missing power data point(s) with 0.")

        # --- 3. W'bal CALCULATION ---
        with st.spinner("Calculating W' balance..."):
            Wbal = float(WP)
            Wbal_old = float(WP)
            Wexp = 0.0
            
            wbal_list, tau_list, wexp_list, rec_list = [0.0]*len(df), [0.0]*len(df), [0.0]*len(df), [0.0]*len(df)
            wbal_list[0] = float(WP)

            power_np = df['power'].to_numpy()

            for i in range(1, len(df)):
                P = power_np[i]
                if P > CP:
                    Wbal -= (P - CP)
                    Tau = 0.0
                else:
                    DCP2 = CP - P
                    Tau = A * (DCP2 ** B) if DCP2 > 0 else 0
                    Wbal = WP - (Wexp * m.exp(-1 / Tau)) if Tau > 0 else Wbal
                
                Wbal = min(WP, Wbal)
                Wexp = WP - Wbal
                Rec = Wbal - Wbal_old

                wbal_list[i] = Wbal
                tau_list[i] = Tau
                wexp_list[i] = Wexp
                rec_list[i] = Rec
                Wbal_old = Wbal
            
            df['Wbal'], df['Tau'], df['Wexp'], df['Rec'] = wbal_list, tau_list, wexp_list, rec_list

        # --- 4. POWER AND CADENCE ANALYSIS ---
        with st.spinner("Analyzing power and cadence data..."):
            time_values = df['time'].tolist()
            power_values = df['power'].tolist()
            cadence_values = df['cadence'].tolist()
            durations = [0] + [(time_values[i] - time_values[i-1]) for i in range(1, len(time_values))]
            if sum(durations) == 0 or len(durations) != len(time_values):
                durations = [1] * len(time_values)
            
            total_time_above, total_work_above, total_time_below, total_work_below = 0, 0, 0, 0
            bouts_above, bouts_below = 0, 0
            previous_state = 'below' if power_values[0] <= CP else 'above'
            cadence_sum, cadence_count, cadence_above_sum, cadence_above_count = 0, 0, 0, 0
            cadence_below_sum, cadence_below_count, coasting_time = 0, 0, 0
            
            for i in range(len(power_values)):
                dur, powr, cad = durations[i], power_values[i], cadence_values[i]
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
            coasting_percent = round((coasting_time / total_time) * 100) if total_time > 0 else 0

        # --- 5. DISPLAY OUTPUTS IN TABS ---
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Summary Metrics", "📈 Charts", "🗺️ Route Maps", "📋 Raw Data"])

        with tab1:
            st.header(f"Summary Metrics (Threshold = {int(CP)} W)")
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Above CP")
                c1, c2 = st.columns(2)
                c1.metric("Total Time", f"{round(total_time_above)} s")
                c2.metric("Avg Power", f"{avg_power_above} W")
                c1.metric("Number of Bouts", f"{bouts_above}")
                c2.metric("Avg Time/Bout", f"{avg_time_per_bout_above} s")
            with col2:
                st.subheader("Below CP")
                c1, c2 = st.columns(2)
                c1.metric("Total Time", f"{round(total_time_below)} s")
                c2.metric("Avg Power", f"{avg_power_below} W")
                c1.metric("Number of Bouts", f"{bouts_below}")
                c2.metric("Avg Time/Bout", f"{avg_time_per_bout_below} s")
            
            st.divider()
            st.subheader("Cadence Statistics (excluding coasting)")
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
            ax1.grid(False)
            ax1.legend()
            st.pyplot(fig1)

            # NEW PLOT: W'bal and Elevation
            if 'altitude' in df.columns and df['altitude'].notna().any():
                fig_elev, ax_elev1 = plt.subplots(figsize=(12, 6))
                
                # W'bal axis (left)
                ax_elev1.set_xlabel('Time (s)')
                ax_elev1.set_ylabel('W\'bal (Joules)', color='purple')
                ax_elev1.plot(df['time'], df['Wbal'], color='purple', linewidth=2, label='W\'bal')
                ax_elev1.tick_params(axis='y', labelcolor='purple')
                ax_elev1.axhline(y=0, color='grey', linestyle='--', linewidth=1)
                
                # Elevation axis (right)
                ax_elev2 = ax_elev1.twinx()
                ax_elev2.set_ylabel('Elevation (m)', color='green')
                ax_elev2.plot(df['time'], df['altitude'], color='green', linewidth=2, label='Elevation')
                ax_elev2.tick_params(axis='y', labelcolor='green')

                fig_elev.suptitle('W\' Balance vs. Elevation')
                fig_elev.tight_layout()
                st.pyplot(fig_elev)

            # PLOT 2: Summary Bar Plots
            labels, time_data = ['Above CP', 'Below CP'], [round(total_time_above), round(total_time_below)]
            avg_power_data, bouts_data = [avg_power_above, avg_power_below], [bouts_above, bouts_below]
            avg_bout_time = [avg_time_per_bout_above, avg_time_per_bout_below]
            fig2, axs = plt.subplots(1, 4, figsize=(15, 4))
            fig2.suptitle(f"Power Data Summary (Threshold = {int(CP)} W)", fontsize=14)
            for ax in axs: ax.grid(False) # Remove gridlines
            axs[0].bar(labels, time_data, color=['#d62728', '#1f77b4']), axs[0].set_title("Total Time (s)")
            axs[1].bar(labels, avg_power_data, color=['#d62728', '#1f77b4']), axs[1].set_title("Average Power (W)")
            axs[2].bar(labels, bouts_data, color=['#d62728', '#1f77b4']), axs[2].set_title("Number of Bouts")
            axs[3].bar(labels, avg_bout_time, color=['#d62728', '#1f77b4']), axs[3].set_title("Avg Time per Bout (s)")
            plt.tight_layout(rect=[0, 0.03, 1, 0.95])
            st.pyplot(fig2)

            # PLOT 3: Power Over Time
            fig3, ax3 = plt.subplots(figsize=(12, 6))
            ax3.set_title("Power over Time with Threshold Coloring", fontsize=14)
            ax3.set_xlabel("Time (s)"), ax3.set_ylabel("Power (W)")
            ax3.fill_between(df['time'], df['power'], CP, where=df['power'] <= CP, color='#1f77b4', alpha=0.5, interpolate=True)
            ax3.fill_between(df['time'], df['power'], CP, where=df['power'] > CP, color='#d62728', alpha=0.5, interpolate=True)
            ax3.plot(df['time'], df['power'], color='black', linewidth=0.5, label='Power')
            ax3.axhline(y=CP, color='orange', linestyle='--', label=f"CP = {int(CP)} W")
            ax3.legend()
            ax3.grid(False)
            st.pyplot(fig3)

            # PLOT 4: Power vs. Cadence Heatmap (smaller)
            pedaling_df = df[df['cadence'] > 0]
            if not pedaling_df.empty:
                fig4, ax4 = plt.subplots(figsize=(8, 5))
                hb = ax4.hexbin(pedaling_df['cadence'], pedaling_df['power'], gridsize=40, cmap='viridis', mincnt=1)
                fig4.colorbar(hb, ax=ax4, label='Frequency of Occurrence')
                ax4.set_xlabel("Cadence (rpm)"), ax4.set_ylabel("Power (W)"), ax4.set_title("Power vs. Cadence Density")
                ax4.grid(False)
                st.pyplot(fig4)

        with tab3:
            st.header("Route Maps")
            if 'position_lat' in df.columns and 'position_long' in df.columns and df[['position_lat', 'position_long']].notnull().all(axis=1).any():
                gps_df = df[['position_lat', 'position_long', 'Wbal', 'power']].dropna().copy()
                
                st.subheader("Route Colored by W' Balance (%)")
                gps_df['Wbal_percent'] = (gps_df['Wbal'] / WP) * 100
                gps_df['Wbal_percent'] = gps_df['Wbal_percent'].clip(0, 100)
                points = list(zip(gps_df['position_lat'], gps_df['position_long']))
                wbal_colormap = cm.linear.RdYlGn_09.scale(0, 100)
                wbal_colors = [wbal_colormap(float(p)) for p in gps_df['Wbal_percent']]
                m_wbal = folium.Map(location=[gps_df['position_lat'].mean(), gps_df['position_long'].mean()], zoom_start=13)
                ColorLine(points, colors=wbal_colors, colormap=wbal_colormap, weight=5).add_to(m_wbal)
                wbal_colormap.caption = "W' Balance (%)"
                m_wbal.add_child(wbal_colormap)
                st_folium(m_wbal, width=1400, height=500)

                st.subheader("Route Colored by Power vs. CP")
                power_diff = gps_df['power'] - CP
                norm_power = np.clip(power_diff, -150, 150)
                power_colormap = cm.linear.RdBu_11.scale(-150, 150)
                power_colors = [power_colormap(float(p)) for p in norm_power]
                m_power = folium.Map(location=[gps_df['position_lat'].mean(), gps_df['position_long'].mean()], zoom_start=13)
                ColorLine(points, colors=power_colors, colormap=power_colormap, weight=5).add_to(m_power)
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
