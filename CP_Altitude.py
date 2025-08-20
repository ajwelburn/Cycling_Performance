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

    # Dynamically set the y-axis range to better showcase elevation changes.
    min_elevation = df['Elevation_m'].min()
    max_elevation = df['Elevation_m'].max()
    avg_elevation = df['Elevation_m'].mean()
    
    # Start the axis just below the ride's lowest point.
    elevation_axis_bottom = min_elevation * 0.95 
    
    # Set top of axis to double the average or just above the max, whichever is higher.
    elevation_axis_top = max(max_elevation * 1.05, avg_elevation * 2) 
    
    fig.update_layout(
        title_text='<b>Ride Profile: Elevation vs. Critical Power Decline</b>',
        template='plotly_dark',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_xaxes(title_text="Distance (km)")
    fig.update_yaxes(
        title_text="<b>Elevation (m)</b>", 
        color='#00bfff', 
        secondary_y=False, 
        range=[elevation_axis_bottom, elevation_axis_top] # Set new dynamic range
    )
    fig.update_yaxes(title_text="<b>CP Decline (%)</b>", color='#ff4500', secondary_y=True)
    return fig

def create_power_hr_chart(df: pd.DataFrame):
    """Creates a chart for Power and Heart Rate with a modern dark theme."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    if 'Power_W_Smoothed' in df.columns and not df['Power_W_Smoothed'].dropna().empty:
        fig.add_trace(go.Scatter(
            x=df['Distance_km'], y=df['Power_W_Smoothed'], name='Power (Smoothed)',
            line_color='#ee72f1',
            hovertemplate='<b>Smoothed Power</b>: %{y:.0f} W<br><b>Actual Power</b>: %{customdata:.0f} W<extra></extra>',
            customdata=df['Power_W']
        ), secondary_y=False)
    if 'Heart_Rate_bpm' in df.columns and not df['Heart_Rate_bpm'].dropna().empty:
        fig.add_trace(go.Scatter(
            x=df['Distance_km'], y=df['Heart_Rate_bpm'], name='Heart Rate (bpm)',
            line_color='#f5b342',
            hovertemplate='<b>Heart Rate</b>: %{y:.0f} bpm<extra></extra>'
        ), secondary_y=True)
    fig.update_layout(
        title_text='<b>Power and Heart Rate Profile</b>',
        template='plotly_dark',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_xaxes(title_text="Distance (km)")
    fig.update_yaxes(title_text="<b>Power (W)</b>", color='#ee72f1', secondary_y=False)
    fig.update_yaxes(title_text="<b>Heart Rate (bpm)</b>", color='#f5b342', secondary_y=True, showgrid=False)
    return fig

def create_sea_level_equivalent_power_chart(df: pd.DataFrame):
    """Creates a stacked chart comparing actual vs. sea-level equivalent power with unified hover."""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1)

    fig.add_trace(go.Scatter(
        x=df['Distance_km'], y=df['Power_W_Smoothed'], name='Actual Power (Smoothed)',
        line=dict(color='royalblue', width=2.5),
        hovertemplate='<b>Actual</b>: %{y:.0f} W<extra></extra>'
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df['Distance_km'], y=df['Sea_Level_Equivalent_Power_W_Smoothed'], name='Sea-Level Equivalent Power',
        line=dict(color='#00ff96', width=2.5),
        hovertemplate='<b>Equivalent</b>: %{y:.0f} W<extra></extra>'
    ), row=2, col=1)

    fig.update_layout(
        title_text='<b>Power vs. Sea-Level Equivalent Power</b>',
        template='plotly_dark',
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    fig.update_yaxes(title_text="Actual Power (W)", row=1, col=1)
    fig.update_yaxes(title_text="Sea-Level Equiv. (W)", row=2, col=1)
    fig.update_xaxes(title_text="Distance (km)", row=2, col=1)
    return fig

# --- Streamlit App UI ---

st.set_page_config(layout="wide", page_title="Altitude Power Analyzer")
st.title("🚴 Altitude Power Analyzer")

st.sidebar.header("⚙️ Settings")
sea_level_cp = st.sidebar.number_input(
    "Enter your Sea-Level Critical Power (W)",
    min_value=100, max_value=600, value=300, step=1
)

smoothing_window = st.sidebar.slider(
    "Power Smoothing (seconds)",
    min_value=1, max_value=60, value=30,
    help="Adjust the window for the rolling average to smooth the power data. 1 = raw data."
)

uploaded_file = st.sidebar.file_uploader(
    "Upload your .FIT file", type=["fit"]
)

if uploaded_file is not None:
    with st.spinner("Analyzing your ride... This might take a moment."):
        file_content = uploaded_file.getvalue()
        raw_df = parse_fit_file(file_content)

        if raw_df.empty:
            st.error("Could not find valid GPS or altitude data in the FIT file. Please try another file.")
        else:
            analyzed_df = perform_analysis(raw_df.copy(), sea_level_cp, smoothing_window)
            
            st.success("✅ Analysis Complete!")

            profile_fig = create_profile_chart(analyzed_df)
            st.plotly_chart(profile_fig, use_container_width=True)

            has_power = 'Power_W_Smoothed' in analyzed_df.columns and not analyzed_df['Power_W_Smoothed'].dropna().empty
            has_hr = 'Heart_Rate_bpm' in analyzed_df.columns and not analyzed_df['Heart_Rate_bpm'].dropna().empty

            if has_power or has_hr:
                st.divider()
                st.header("⚡️ Power & Heart Rate Analysis")
                power_hr_fig = create_power_hr_chart(analyzed_df)
                st.plotly_chart(power_hr_fig, use_container_width=True)
            
            if has_power:
                equivalent_power_fig = create_sea_level_equivalent_power_chart(analyzed_df)
                st.plotly_chart(equivalent_power_fig, use_container_width=True)

            st.divider()
            st.header("🗺️ Ride Map")
            folium_map = create_folium_map(analyzed_df)
            st_folium(folium_map, use_container_width=True, height=500)
else:
    st.info("👋 Welcome! Upload a .FIT file and set your CP in the sidebar to begin.")
