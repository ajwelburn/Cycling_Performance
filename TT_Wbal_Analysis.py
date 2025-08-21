import pandas as pd
import math as m
import matplotlib.pyplot as plt
import numpy as np
import fitdecode
import io
import folium
import branca.colormap as cm
from folium.features import ColorLine
from typing import Tuple, List
#pray it uploads the fit file 
def parse_fit_file(file_path: str) -> Tuple[pd.DataFrame, int, List[int]]:
    """
    Parses a .fit file into a pandas DataFrame, handling missing data.

    Returns:
        A tuple containing:
        - The parsed DataFrame.
        - The count of missing power data points.
        - A list of time points (in seconds) where power was missing.
    """
    records = []
    try:
        with fitdecode.FitReader(file_path) as fit:
            for frame in fit:
                if frame.frame_type == fitdecode.FIT_FRAME_DATA and frame.name == "record":
                    record_data = {
                        "timestamp": frame.get_value("timestamp", fallback=None),
                        "power": frame.get_value("power", fallback=None),
                        "cadence": frame.get_value("cadence", fallback=None),
                        "position_lat": frame.get_value("position_lat", fallback=None),
                        "position_long": frame.get_value("position_long", fallback=None),
                    }
                    if record_data["timestamp"] is not None:
                        records.append(record_data)
    except fitdecode.FitDecodeError as e:
        print(f"Error decoding .fit file: {e}")
        return pd.DataFrame(), 0, []

    if not records:
        return pd.DataFrame(), 0, []

    df = pd.DataFrame(records)
    
    # Convert Garmin's semicircles to degrees for GPS coordinates
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

    return df, missing_count, missing_times


# --- 2. LOAD DATA & GET USER INPUTS ---
try:
    # TODO: Replace this with a file uploader in your Streamlit app
    file_path = 'your_activity.fit' # <--- CHANGE THIS TO YOUR .FIT FILE
    df, missing_power_count, missing_power_times = parse_fit_file(file_path)

    if df.empty:
        raise ValueError("Failed to parse .fit file or the file contains no valid records.")

    print("Data loaded successfully from .fit file. Columns found:", df.columns.tolist())

    if missing_power_count > 0:
        print(f"\nNOTE: Found and replaced {missing_power_count} missing power data point(s) with 0.")
        if len(missing_power_times) > 10:
            print(f"      Occurred at times (seconds): {missing_power_times[:10]}... and more.")
        else:
            print(f"      Occurred at times (seconds): {missing_power_times}")

    # TODO: Replace these with Streamlit input widgets
    A = float(input('\nEnter Tau calculation constant A (e.g., 339.3): '))
    B = float(input('Enter Tau calculation constant B (e.g., -0.789): '))
    CP = int(input('Enter Critical Power (CP) in Watts (e.g., 350): '))
    WP = int(input('Enter W\' (W prime) in Joules (e.g., 20000): '))

except FileNotFoundError:
    print(f"Error: The file was not found at '{file_path}'. Please update the 'file_path' variable.")
    exit()
except ValueError as e:
    print(f"Error: {e}")
    exit()
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    exit()


# --- 3. W'bal CALCULATION ---
print("\nCalculating W' balance...")
Wbal = WP
Wbal_old = WP
Wexp = 0
df['DCP'] = CP - df['power']
df['Wbal'] = float(WP)
df['Tau'] = 0.0
df['Wexp'] = 0.0
df['Rec'] = 0.0

for i in range(1, len(df)):
    P = df.at[i, 'power']
    if P > CP:
        Wbal = Wbal - (P - CP)
        Tau = 0.0
    else:
        DCP2 = CP - P
        Tau = A * (DCP2 ** B) if DCP2 > 0 else 0
        Wbal = WP - (Wexp * m.exp(-1 / Tau)) if Tau > 0 else Wbal
    Wbal = max(0, min(WP, Wbal))
    Wexp = WP - Wbal
    Rec = Wbal - Wbal_old
    df.at[i, 'Wbal'] = Wbal
    df.at[i, 'Tau'] = Tau
    df.at[i, 'Wexp'] = Wexp
    df.at[i, 'Rec'] = Rec
    Wbal_old = Wbal

output_file_path = 'activity-results.xlsx'
df.to_excel(output_file_path, index=False)
print(f"W'bal calculation complete. Results saved to {output_file_path}")


# --- 4. POWER AND CADENCE ANALYSIS ---
print("\nPerforming Power and Cadence Analysis...")
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


# --- 5. CONSOLE OUTPUT ---
print(f"\n--- RESULTS (Threshold = {int(CP)} W) ---")
print(f"Time Above: {round(total_time_above)}s | Avg Power: {avg_power_above}W | Bouts: {bouts_above} | Avg Time/Bout: {avg_time_per_bout_above}s")
print(f"Time Below: {round(total_time_below)}s | Avg Power: {avg_power_below}W | Bouts: {bouts_below} | Avg Time/Bout: {avg_time_per_bout_below}s")
print("\n--- CADENCE STATISTICS (excluding coasting) ---")
print(f"Avg Cadence Overall: {avg_cadence} rpm")
print(f"Avg Cadence >CP: {avg_cadence_above} rpm")
print(f"Avg Cadence <=CP: {avg_cadence_below} rpm")
print(f"Total Coasting Time (Cadence=0): {round(coasting_time)}s ({coasting_percent}%)")


# --- 6. VISUALIZATIONS ---
print("\nGenerating plots...")
# PLOT 1: W' Balance Over Time
plt.figure(figsize=(15, 7))
plt.plot(df['time'], df['Wbal'], label='W\'bal', color='purple', linewidth=2)
plt.xlabel('Time (s)'), plt.ylabel('W\'bal (Joules)'), plt.title('W\' Balance Over Time')
plt.grid(True, linestyle='--', alpha=0.6), plt.legend(), plt.tight_layout(), plt.show()

# PLOT 2: Summary Bar Plots
labels, time_data = ['Above CP', 'Below CP'], [round(total_time_above), round(total_time_below)]
avg_power_data, bouts_data = [avg_power_above, avg_power_below], [bouts_above, bouts_below]
avg_bout_time = [avg_time_per_bout_above, avg_time_per_bout_below]
fig, axs = plt.subplots(1, 4, figsize=(18, 5))
fig.suptitle(f"Power Data Summary (Threshold = {int(CP)} W)", fontsize=16)
axs[0].bar(labels, time_data, color=['#d62728', '#1f77b4']), axs[0].set_title("Total Time (s)"), axs[0].set_ylabel("Seconds")
axs[1].bar(labels, avg_power_data, color=['#d62728', '#1f77b4']), axs[1].set_title("Average Power (W)"), axs[1].set_ylabel("Watts")
axs[2].bar(labels, bouts_data, color=['#d62728', '#1f77b4']), axs[2].set_title("Number of Bouts"), axs[2].set_ylabel("Count")
axs[3].bar(labels, avg_bout_time, color=['#d62728', '#1f77b4']), axs[3].set_title("Avg Time per Bout (s)"), axs[3].set_ylabel("Seconds")
plt.tight_layout(rect=[0, 0.03, 1, 0.95]), plt.show()

# PLOT 3: Power Over Time
plt.figure(figsize=(15, 7)), plt.title("Power over Time with Threshold Coloring", fontsize=16)
plt.xlabel("Time (s)"), plt.ylabel("Power (W)")
plt.fill_between(df['time'], df['power'], CP, where=df['power'] <= CP, color='#1f77b4', alpha=0.5, interpolate=True)
plt.fill_between(df['time'], df['power'], CP, where=df['power'] > CP, color='#d62728', alpha=0.5, interpolate=True)
plt.plot(df['time'], df['power'], color='black', linewidth=0.5, label='Power')
plt.axhline(y=CP, color='orange', linestyle='--', label=f"CP = {int(CP)} W")
plt.legend(), plt.grid(True, linestyle='--', alpha=0.6), plt.tight_layout(), plt.show()

# PLOT 4: Power vs. Cadence Heatmap
pedaling_df = df[df['cadence'] > 0]
if not pedaling_df.empty:
    plt.figure(figsize=(10, 6))
    hb = plt.hexbin(pedaling_df['cadence'], pedaling_df['power'], gridsize=50, cmap='viridis', mincnt=1)
    plt.colorbar(hb, label='Frequency of Occurrence')
    plt.xlabel("Cadence (rpm)"), plt.ylabel("Power (W)"), plt.title("Power vs. Cadence Density")
    plt.grid(True, linestyle='--', alpha=0.6), plt.tight_layout(), plt.show()
else:
    print("Skipping Power vs. Cadence plot: No pedaling data found.")


# --- 7. MAP VISUALIZATIONS ---
# This section generates interactive maps of the route colored by performance metrics.
# TODO: In Streamlit, these functions can be called within tabs or based on a selectbox.
print("\nGenerating map visualizations...")

# Check if GPS data is available
if 'position_lat' in df.columns and 'position_long' in df.columns and df[['position_lat', 'position_long']].notnull().all(axis=1).any():
    gps_df = df[['position_lat', 'position_long', 'Wbal', 'power']].dropna().copy()
    
    # --- Map 1: W'bal Percentage Route ---
    gps_df['Wbal_percent'] = (gps_df['Wbal'] / WP) * 100
    points = list(zip(gps_df['position_lat'], gps_df['position_long']))
    
    # Create a colormap from Red (0%) to Yellow (50%) to Green (100%)
    wbal_colormap = cm.linear.RdYlGn_09.scale(0, 100)
    wbal_colors = [wbal_colormap(p) for p in gps_df['Wbal_percent']]

    m_wbal = folium.Map(location=[gps_df['position_lat'].mean(), gps_df['position_long'].mean()], zoom_start=14)
    ColorLine(points, colors=wbal_colors, colormap=wbal_colormap, weight=5).add_to(m_wbal)
    wbal_colormap.caption = "W' Balance (%)"
    m_wbal.add_child(wbal_colormap)
    
    map_wbal_path = 'wbal_route.html'
    m_wbal.save(map_wbal_path)
    print(f"W'bal route map saved to: {map_wbal_path}")

    # --- Map 2: Power vs. CP Route ---
    # Normalize power relative to CP. We'll set a range, e.g., 50% below CP to 50% above CP
    power_diff = gps_df['power'] - CP
    # Cap the range for better color contrast, e.g., from -150W to +150W from CP
    norm_power = np.clip(power_diff, -150, 150)
    
    # Create a diverging colormap from Blue (below) to White (at CP) to Red (above)
    power_colormap = cm.linear.RdBu_11.scale(-150, 150)
    power_colors = [power_colormap(p) for p in norm_power]

    m_power = folium.Map(location=[gps_df['position_lat'].mean(), gps_df['position_long'].mean()], zoom_start=14)
    ColorLine(points, colors=power_colors, colormap=power_colormap, weight=5).add_to(m_power)
    power_colormap.caption = "Power relative to CP (Watts)"
    m_power.add_child(power_colormap)

    map_power_path = 'power_vs_cp_route.html'
    m_power.save(map_power_path)
    print(f"Power vs. CP route map saved to: {map_power_path}")

else:
    print("Skipping map generation: No valid GPS data found in the file.")

print("\nAnalysis complete.")
