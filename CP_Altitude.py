import streamlit as st
import pandas as pd
import fitdecode
import folium
import branca.colormap as cm
from folium.features import ColorLine
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
from streamlit_folium import st_folium

# --- Caching Functions to Prevent Re-running ---

@st.cache_data
def parse_fit_file(file_content: bytes) -> pd.DataFrame:
    """Parses the in-memory .fit file content into a pandas DataFrame."""
    records = []
    with io.BytesIO(file_content) as fit_file:
        with fitdecode.FitReader(fit_file) as fit:
            for frame in fit:
                if frame.frame_type == fitdecode.FIT_FRAME_DATA and frame.name == "record":
                    if all(frame.has_field(f) for f in ["altitude", "distance", "position_lat", "position_long"]):
                        record_data = {
                            "Elevation_m": frame.get_value("altitude"),
                            "Distance_m": frame.get_value("distance"),
                            "Latitude": frame.get_value("position_lat"),
                            "Longitude": frame.get_value("position_long"),
                            "Power_W": frame.get_value("power") if frame.has_field("power") else None,
                            "Heart_Rate_bpm": frame.get_value("heart_rate") if frame.has_field("heart_rate") else None,
                        }
                        records.append(record_data)
    
    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    df["Latitude"] = df["Latitude"] * (180 / (2**31))
    df["Longitude"] = df["Longitude"] * (180 / (2**31))
    return df.dropna(subset=['Latitude', 'Longitude', 'Elevation_m', 'Distance_m']).reset_index(drop=True)

@st.cache_data
def perform_analysis(df: pd.DataFrame, sea_level_cp: float, smoothing_window: int) -> pd.DataFrame:
    """Performs analysis, including altitude-based CP decline and sea-level equivalent power."""
    df["Distance_km"] = df["Distance_m"] / 1000
    df["Elevation_km"] = df["Elevation_m"] / 1000
    
    # Altitude decline model
    coeffs = {"a": 0.0016, "b": -0.0156, "c": -0.0027, "d": 1.0025}
    h = df["Elevation_km"]
    df["Decline_Factor"] = (coeffs["a"] * (h ** 3) + coeffs["b"] * (h ** 2) + coeffs["c"] * h + coeffs["d"])
    df["CP_Adjusted"] = sea_level_cp * df["Decline_Factor"]
    df["Sea_Level_CP"] = sea_level_cp
    df["CP_Diff_W"] = df["CP_Adjusted"] - sea_level_cp
    df["CP_Decline_Percent"] = (df["CP_Diff_W"] / df["Sea_Level_CP"]) * 100
    
    # Calculate sea-level equivalent power if power data exists
    if 'Power_W' in df.columns and not df['Power_W'].dropna().empty:
        df['Sea_Level_Equivalent_Power_W'] = (df['Power_W'] / df['Decline_Factor'])
        
        # Apply smoothing
        df['Power_W_Smoothed'] = df['Power_W'].rolling(window=smoothing_window, min_periods=1, center=True).mean()
        df['Sea_Level_Equivalent_Power_W_Smoothed'] = df['Sea_Level_Equivalent_Power_W'].rolling(window=smoothing_window, min_periods=1, center=True).mean()
        
        # Calculate the difference for the hover tooltip
        df['Power_Gain_W_Smoothed'] = df['Sea_Level_Equivalent_Power_W_Smoothed'] - df['Power_W_Smoothed']
        
    return df

# --- Visualization Functions ---

def create_folium_map(df: pd.DataFrame):
    """Creates the Folium map showing the ride route colored by CP difference."""
    start_location = [df["Latitude"].iloc[0], df["Longitude"].iloc[0]]
    m = folium.Map(location=start_location, zoom_start=12, tiles="OpenStreetMap")
    min_diff, max_diff = df["CP_Diff_W"].min(), df["CP_Diff_W"].max()
    colormap = cm.LinearColormap(
        colors=["#d73027", "#fdae61", "#ffffbf", "#abdda4", "#2b83ba"],
        vmin=min_diff, vmax=max_diff, caption="CP Difference (W) vs Sea Level"
    )
    points = list(zip(df["Latitude"], df["Longitude"]))
    ColorLine(
        positions=points, colors=df["CP_Diff_W"], colormap=colormap, weight=7, opacity=0.9
    ).add_to(m)
    colormap.add_to(m)
    return m

def create_profile_chart(df: pd.DataFrame):
    """Creates an interactive Plotly chart for elevation and CP decline."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(go.Scatter(
        x=df['Distance_km'], y=df['Elevation_m'], name='Elevation (m)',
        fill='tozeroy', line_color='#00bfff',
        hovertemplate='<b>Elevation</b>: %{y:.0f} m<extra></extra>'
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=df['Distance_km'], y=df['CP_Decline_Percent'], name='CP Decline (%)',
        line_color='#ff4500',
        hovertemplate='<b>CP Decline</b>: %{y:.1f}%%<br><b>Adjusted CP</b>: %{customdata:.0f} W<extra></extra>',
        customdata=df['CP_Adjusted']
    ), secondary_y=True)

    min_elevation = df['Elevation_m'].min()
    max_elevation = df['Elevation_m'].max()
    elevation_range = max_elevation - min_elevation
