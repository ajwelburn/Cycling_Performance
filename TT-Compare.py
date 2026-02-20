import streamlit as st
import pandas as pd
import numpy as np
import fitparse
import folium
from streamlit_folium import st_folium
from io import BytesIO

# --- HELPER FUNCTIONS ---
def parse_fit(file):
    """Extracts records from FIT file into a DataFrame."""
    fitfile = fitparse.FitFile(file)
    data = []
    for record in fitfile.get_messages('record'):
        r = {m.name: m.value for m in record}
        # Only keep records with lat/lon
        if 'position_lat' in r and 'position_long' in r:
            # Convert semicircles to degrees
            r['lat'] = r['position_lat'] * (180 / 2**31)
            r['lon'] = r['position_long'] * (180 / 2**31)
            data.append(r)
    df = pd.DataFrame(data)
    # Basic data cleaning
    if 'enhanced_speed' in df.columns:
        df['speed_kmh'] = df['enhanced_speed'] * 3.6
    return df

def calculate_distance(df):
    """Calculates cumulative distance in meters."""
    # Simplified haversine or use cumulative distance if available in FIT
    if 'distance' in df.columns:
        df['cum_dist'] = df['distance'] - df['distance'].iloc[0]
    return df

# --- APP UI ---
st.set_page_config(layout="wide", page_title="Cycling Segment Pacing")
st.title("🚴‍♂️ Pro Pacing Comparator")

# 1. File Uploads
col1, col2 = st.columns(2)
with col1:
    master_file = st.file_uploader("Upload Master Rider (The Benchmark)", type=["fit"])
with col2:
    comp_files = st.file_uploader("Upload Competitor(s)", type=["fit"], accept_multiple_files=True)

if master_file:
    df_master = parse_fit(master_file)
    df_master = calculate_distance(df_master)

    # 2. Segment Selection
    st.subheader("Select Your Segment")
    indices = st.slider("Select Start and End Points", 0, len(df_master)-1, (0, len(df_master)-1))
    
    seg_start, seg_end = indices
    df_seg_master = df_master.iloc[seg_start:seg_end].copy()
    # Reset distance for the segment so it starts at 0
    df_seg_master['seg_dist'] = df_seg_master['cum_dist'] - df_seg_master['cum_dist'].iloc[0]
    df_seg_master['elapsed_time'] = (df_seg_master['timestamp'] - df_seg_master['timestamp'].iloc[0]).dt.total_seconds()

    # Preview Map
    m = folium.Map(location=[df_seg_master['lat'].mean(), df_seg_master['lon'].mean()], zoom_start=14)
    folium.PolyLine(df_seg_master[['lat', 'lon']].values, color="blue", weight=5).add_to(m)
    st_folium(m, width=700, height=300)

    # 3. Comparison Logic
    if comp_files:
        st.subheader("Comparison Results")
        
        # We define a common distance grid (every 10 meters)
        common_dist = np.linspace(0, df_seg_master['seg_dist'].max(), 200)
        
        # Interpolate Master Data
        master_interp_time = np.interp(common_dist, df_seg_master['seg_dist'], df_seg_master['elapsed_time'])
        
        all_results = []
        
        for f in comp_files:
            df_c = parse_fit(f)
            df_c = calculate_distance(df_c)
            
            # This is a simplified 'nearest neighbor' find for the segment
            # In a pro app, you'd use spatial coordinates, but here we use the distance offset
            # (Assuming they rode the same course)
            c_interp_time = np.interp(common_dist, df_c['cum_dist'], (df_c['timestamp'] - df_c['timestamp'].iloc[0]).dt.total_seconds())
            c_interp_speed = np.interp(common_dist, df_c['cum_dist'], df_c.get('speed_kmh', np.zeros(len(df_c))))
            
            # Calculate Gap (Master Time - Competitor Time)
            # Positive means Competitor is FASTER (took less time)
            time_gap = master_interp_time - c_interp_time
            
            res_df = pd.DataFrame({
                'Distance': common_dist,
                'Time Gap (s)': time_gap,
                'Speed': c_interp_speed,
                'Rider': f.name
            })
            all_results.append(res_df)

        comparison_df = pd.concat(all_results)

        # 4. Visualizations
        st.line_chart(comparison_df, x='Distance', y='Time Gap (s)', color='Rider')
        st.caption("Time Gap: Above 0 means the rider is currently AHEAD of the Master.")
        
        st.line_chart(comparison_df, x='Distance', y='Speed', color='Rider')

else:
    st.info("Please upload a 'Master' .fit file to begin.")
