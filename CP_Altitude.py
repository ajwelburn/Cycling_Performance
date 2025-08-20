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
    # Use io.BytesIO to treat the byte string as a file
    with fitdecode.FitReader(io.BytesIO(file_content)) as fit:
        for frame in fit:
            if frame.frame_type == fitdecode.FIT_FRAME_DATA and frame.name == "record":
                # Base required fields
                if all(frame.has_field(f) for f in ["altitude", "distance", "position_lat", "position_long"]):
                    record_data = {
                        "Elevation_m": frame.get_value("altitude"),
                        "Distance_m": frame.get_value("distance"),
                        "Latitude": frame.get_value("position_lat"),
                        "Longitude": frame.get_value("position_long"),
                        # Add optional fields if they exist
                        "Power_W": frame.get_value("power") if frame.has_field("power") else None,
                        "Heart_Rate_bpm": frame.get_value("heart_rate") if frame.has_field("heart_rate") else None,
                    }
                    records.append(record_data)
    
    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    # Convert GPS coordinates from semicircles to degrees
    df["Latitude"] = df["Latitude"] * (180 / (2**31))
    df["Longitude"] = df["Longitude"] * (180 / (2**31))
    
    # Clean up non-power/hr data; other columns are cleaned later
    return df.dropna(subset=['Latitude', 'Longitude', 'Elevation_m', 'Distance_m']).reset_index(drop=True)

@st.cache_data
def perform_analysis(df: pd.DataFrame, sea_level_cp: float) -> pd.DataFrame:
    """Performs the analysis, including altitude-based CP decline and corrected power."""
    df["Distance_km"] = df["Distance_m"] / 1000
    df["Elevation_km"] = df["Elevation_m"] / 1000
    
    # Coefficients for the polynomial decline model
    coeffs = {"a": 0.0016, "b": -0.0156, "c": -0.0027, "d": 1.0025}
    h = df["Elevation_km"]
    df["Decline_Factor"] = (coeffs["a"] * (h ** 3) + coeffs["b"] * (h ** 2) + coeffs["c"] * h + coeffs["d"])
    df["CP_Adjusted"] = sea_level_cp * df["Decline_Factor"]
    df["Sea_Level_CP"] = sea_level_cp
    df["CP_Diff_W"] = df["CP_Adjusted"] - sea_level_cp
    df["CP_Decline_Percent"] = (df["CP_Diff_W"] / df["Sea_Level_CP"]) * 100
    
    # Calculate altitude-corrected power if power data exists
    if 'Power_W' in df.columns and not df['Power_W'].dropna().empty:
        # Calculate power as a percentage of sea-level CP
        df['Power_Percent_Sea_Level_CP'] = (df['Power_W'] / sea_level_cp) * 100
        # Apply that same percentage to the adjusted CP for each point in the ride
        df['Altitude_Corrected_Power_W'] = (df['Power_Percent_Sea_Level_CP'] / 100) * df['CP_Adjusted']

    return df

# --- Visualization Functions ---

def create_folium_map(df: pd.DataFrame):
    """Creates the Folium map showing the ride route colored by CP difference."""
    start_location = [df["Latitude"].iloc[0], df["Longitude"].iloc[0]]
    m = folium.Map(location=start_location, zoom_start=12, tiles="CartoDB positron")
    min_diff, max_diff = df["CP_Diff_W"].min(), df["CP_Diff_W"].max()
    colormap = cm.LinearColormap(
        colors=["#d73027", "#fdae61", "#ffffbf", "#a6d96a", "#1a9850"],
        vmin=min_diff, vmax=max_diff, caption="CP Difference (W)"
    )
    points = list(zip(df["Latitude"], df["Longitude"]))
    ColorLine(
        positions=points, colors=df["CP_Diff_W"], colormap=colormap, weight=7, opacity=0.9
    ).add_to(m)
    colormap.add_to(m)
    return m

def create_profile_chart(df: pd.DataFrame):
    """Creates an interactive Plotly chart with dual Y-axes for elevation and CP decline."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add Elevation trace
    fig.add_trace(go.Scatter(
        x=df['Distance_km'], y=df['Elevation_m'], name='Elevation (m)',
        fill='tozeroy', line_color='#1f77b4',
        hovertemplate='<b>Elevation</b>: %{y:.0f} m<extra></extra>'
    ), secondary_y=False)

    # Add CP Decline % trace
    fig.add_trace(go.Scatter(
        x=df['Distance_km'], y=df['CP_Decline_Percent'], name='CP Decline (%)',
        line_color='#d62728',
        hovertemplate='<b>CP Decline</b>: %{y:.0f}%%<br><b>Actual Change</b>: %{customdata:.1f} W<extra></extra>',
        customdata=df['CP_Diff_W']
    ), secondary_y=True)

    # Update layout
    fig.update_layout(
        title_text='<b>Ride Profile: Elevation vs. Critical Power Decline</b>',
        template='plotly_white',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_xaxes(title_text="Distance (km)")
    # --- Y-AXIS MODIFICATION: Ensure Elevation starts at 0 ---
    fig.update_yaxes(title_text="<b>Elevation (m)</b>", color='#1f77b4', secondary_y=False, rangemode='tozero')
    fig.update_yaxes(title_text="<b>CP Decline (%)</b>", color='#d62728', secondary_y=True)
    return fig

def create_power_hr_chart(df: pd.DataFrame):
    """Creates a chart for Power and Heart Rate if the data is available."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add Power trace if it exists
    if 'Power_W' in df.columns and not df['Power_W'].dropna().empty:
        fig.add_trace(go.Scatter(
            x=df['Distance_km'], y=df['Power_W'], name='Power (W)',
            line_color='#ff7f0e',
            hovertemplate='<b>Power</b>: %{y:.0f} W<extra></extra>'
        ), secondary_y=False)

    # Add Heart Rate trace if it exists
    if 'Heart_Rate_bpm' in df.columns and not df['Heart_Rate_bpm'].dropna().empty:
        fig.add_trace(go.Scatter(
            x=df['Distance_km'], y=df['Heart_Rate_bpm'], name='Heart Rate (bpm)',
            line_color='#9467bd',
            hovertemplate='<b>Heart Rate</b>: %{y:.0f} bpm<extra></extra>'
        ), secondary_y=True)

    fig.update_layout(
        title_text='<b>Power and Heart Rate Profile</b>',
        template='plotly_white',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_xaxes(title_text="Distance (km)")
    fig.update_yaxes(title_text="<b>Power (W)</b>", color='#ff7f0e', secondary_y=False)
    fig.update_yaxes(title_text="<b>Heart Rate (bpm)</b>", color='#9467bd', secondary_y=True, showgrid=False)
    return fig

def create_altitude_corrected_power_chart(df: pd.DataFrame):
    """Creates a chart comparing original power with altitude-corrected power."""
    fig = go.Figure()

    # Add original power trace
    fig.add_trace(go.Scatter(
        x=df['Distance_km'], y=df['Power_W'], name='Original Power (W)',
        line=dict(color='royalblue', width=2),
        hovertemplate='<b>Original Power</b>: %{y:.0f} W<extra></extra>'
    ))

    # Add altitude-corrected power trace
    fig.add_trace(go.Scatter(
        x=df['Distance_km'], y=df['Altitude_Corrected_Power_W'], name='Altitude-Corrected Power (W)',
        line=dict(color='firebrick', dash='dash'),
        hovertemplate='<b>Corrected Power</b>: %{y:.0f} W<extra></extra>'
    ))

    fig.update_layout(
        title_text='<b>Original vs. Altitude-Corrected Power</b>',
        xaxis_title='Distance (km)',
        yaxis_title='Power (W)',
        template='plotly_white',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig


# --- Streamlit App UI ---

st.set_page_config(layout="wide")
st.title("🚴 Critical Power Altitude Analysis")

st.sidebar.header("⚙️ Settings")
sea_level_cp = st.sidebar.number_input(
    "Enter your Sea-Level Critical Power (W)",
    min_value=100,
    max_value=600,
    value=300,
    step=1
)

uploaded_file = st.sidebar.file_uploader(
    "Upload your .FIT file",
    type=["fit"]
)

if uploaded_file is not None:
    with st.spinner("Analyzing your ride... This might take a moment."):
        # Get file content
        file_content = uploaded_file.getvalue()
        
        # 1. Parse the file (uses cache)
        raw_df = parse_fit_file(file_content)

        if raw_df.empty:
            st.error("Could not find valid GPS or altitude data in the FIT file. Please try another file.")
        else:
            # 2. Perform the analysis (uses cache)
            analyzed_df = perform_analysis(raw_df.copy(), sea_level_cp)

            # 3. Create visualizations
            profile_fig = create_profile_chart(analyzed_df)
            folium_map = create_folium_map(analyzed_df)
            
            st.success("✅ Analysis Complete!")

            # Display the main profile chart
            st.plotly_chart(profile_fig, use_container_width=True)

            # Conditionally display Power/HR and Corrected Power charts if data is available
            has_power = 'Power_W' in analyzed_df.columns and not analyzed_df['Power_W'].dropna().empty
            has_hr = 'Heart_Rate_bpm' in analyzed_df.columns and not analyzed_df['Heart_Rate_bpm'].dropna().empty

            if has_power or has_hr:
                st.divider()
                st.header("⚡️ Power & Heart Rate Analysis")
                power_hr_fig = create_power_hr_chart(analyzed_df)
                st.plotly_chart(power_hr_fig, use_container_width=True)
            
            if has_power:
                corrected_power_fig = create_altitude_corrected_power_chart(analyzed_df)
                st.plotly_chart(corrected_power_fig, use_container_width=True)

            st.divider()
            st.header("🗺️ Ride Map")
            # Display the Folium map
            st_folium(folium_map, use_container_width=True, height=500)

else:
    st.info("👋 Welcome! Please upload a .FIT file and set your CP in the sidebar to begin.")
