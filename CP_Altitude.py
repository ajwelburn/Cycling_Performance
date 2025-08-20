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

# --- Core Functions (Copied directly from your Colab notebook) ---
# These functions don't need any changes as they handle the data processing.

def parse_fit_file(file_content: bytes) -> pd.DataFrame:
    """Parses the in-memory .fit file content into a pandas DataFrame."""
    records = []
    # Use io.BytesIO to treat the byte string as a file
    with fitdecode.FitReader(io.BytesIO(file_content)) as fit:
        for frame in fit:
            if frame.frame_type == fitdecode.FIT_FRAME_DATA and frame.name == "record":
                if all(frame.has_field(f) for f in ["altitude", "distance", "position_lat", "position_long"]):
                    records.append({
                        "Elevation_m": frame.get_value("altitude"),
                        "Distance_m": frame.get_value("distance"),
                        "Latitude": frame.get_value("position_lat"),
                        "Longitude": frame.get_value("position_long"),
                    })
    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    # Convert GPS coordinates from semicircles to degrees
    df["Latitude"] = df["Latitude"] * (180 / (2**31))
    df["Longitude"] = df["Longitude"] * (180 / (2**31))
    return df.dropna().reset_index(drop=True)

def perform_analysis(df: pd.DataFrame, sea_level_cp: float) -> pd.DataFrame:
    """Performs the analysis, including altitude-based CP decline."""
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
    return df

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
    """Creates an interactive Plotly chart with dual Y-axes."""
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
    fig.update_yaxes(title_text="<b>Elevation (m)</b>", color='#1f77b4', secondary_y=False)
    fig.update_yaxes(title_text="<b>CP Decline (%)</b>", color='#d62728', secondary_y=True)
    return fig

# --- Streamlit App UI ---

st.set_page_config(layout="wide")
st.title("🚴 Critical Power Altitude Analysis")

# --- Sidebar for User Inputs ---
st.sidebar.header("⚙️ Settings")
sea_level_cp = st.sidebar.number_input(
    "Enter your Sea-Level Critical Power (W)",
    min_value=100,
    max_value=600,
    value=300, # A sensible default
    step=1
)

uploaded_file = st.sidebar.file_uploader(
    "Upload your .FIT file",
    type=["fit"]
)

# --- Main App Logic ---
if uploaded_file is not None:
    with st.spinner("Analyzing your ride... This might take a moment."):
        # Get file content
        file_content = uploaded_file.getvalue()
        
        # 1. Parse the file
        raw_df = parse_fit_file(file_content)

        if raw_df.empty:
            st.error("Could not find valid GPS or altitude data in the FIT file. Please try another file.")
        else:
            # 2. Perform the analysis
            analyzed_df = perform_analysis(raw_df, sea_level_cp)

            # 3. Create visualizations
            profile_fig = create_profile_chart(analyzed_df)
            folium_map = create_folium_map(analyzed_df)
            
            st.success("✅ Analysis Complete!")

            # Display the Plotly chart
            st.plotly_chart(profile_fig, use_container_width=True)
            
            # Display the Folium map
            st_folium(folium_map, use_container_width=True, height=500)

else:
    # Initial state when no file is uploaded
    st.info("👋 Welcome! Please upload a .FIT file and set your CP in the sidebar to begin.")
