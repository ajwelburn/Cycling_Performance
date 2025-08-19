import streamlit as st
import pandas as pd
from fitparse import FitFile
import matplotlib.pyplot as plt

# --- App Title and Description ---
st.set_page_config(page_title="Cycling FIT File Analyzer", layout="wide")
st.title("🚴 Cycling FIT File Analyzer")
st.markdown("Upload your `.fit` file to see basic stats and graphs from your ride.")

# --- File Uploader ---
uploaded_file = st.file_uploader("Choose a FIT file", type="fit")

if uploaded_file is not None:
    st.success("File uploaded successfully!")

    # --- Data Processing ---
    try:
        # Parse the FIT file
        fitfile = FitFile(uploaded_file)
        
        # Extract record messages (contain the main ride data)
        records = []
        for record in fitfile.get_messages("record"):
            # Get all data fields that are not None
            r = {}
            for record_data in record:
                if record_data.value is not None:
                    r[record_data.name] = record_data.value
            if r: # Only append if the record is not empty
                records.append(r)
        
        if not records:
            st.warning("No record data found in the FIT file.")
        else:
            # Convert to a pandas DataFrame
            df = pd.DataFrame(records)

            st.header("Ride Data Overview")
            st.dataframe(df.head())

            # --- Basic Stats ---
            st.header("Key Ride Metrics")
            
            col1, col2, col3, col4 = st.columns(4)
            
            if 'distance' in df.columns:
                total_distance_km = df['distance'].max() / 1000
                col1.metric("Total Distance", f"{total_distance_km:.2f} km")

            if 'enhanced_speed' in df.columns:
                avg_speed_kmh = df['enhanced_speed'].mean() * 3.6
                col2.metric("Average Speed", f"{avg_speed_kmh:.2f} km/h")
            
            if 'heart_rate' in df.columns:
                avg_hr = df['heart_rate'].mean()
                col3.metric("Average Heart Rate", f"{avg_hr:.0f} bpm")

            if 'cadence' in df.columns:
                avg_cadence = df['cadence'].mean()
                col4.metric("Average Cadence", f"{avg_cadence:.0f} rpm")


            # --- Data Visualization ---
            st.header("Data Plots")
            
            # Select columns to plot
            plot_options = [col for col in ['heart_rate', 'enhanced_speed', 'cadence', 'power'] if col in df.columns]
            
            if plot_options:
                selected_metric = st.selectbox("Select a metric to plot over time:", plot_options)

                fig, ax = plt.subplots(figsize=(10, 4))
                ax.plot(df['timestamp'], df[selected_metric])
                ax.set_title(f"{selected_metric.replace('_', ' ').title()} Over Time")
                ax.set_xlabel("Time")
                ax.set_ylabel(selected_metric.replace('_', ' ').title())
                st.pyplot(fig)
            else:
                st.info("No plottable data (like heart rate, speed, cadence, or power) was found.")

    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")
        st.error("This could be due to a corrupted file or an unsupported format.")

else:
    st.info("Awaiting file upload...")
