import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
from io import BytesIO
import datetime

# ----------------------------------------------------
# 1. Configuration & Constants
# ----------------------------------------------------
st.set_page_config(page_title="Rider Performance Profiler", layout="wide")

PROFILE_WEIGHTS = {
    "Sprinter": {"Pmax_CP": 0.45, "W_CP": 0.35, "CP_per_kg": 0.10, "Weight": -0.10},
    "Climber": {"CP_per_kg": 0.55, "CP": 0.20, "Pmax_CP": 0.05, "Weight": -0.20},
    "Time-Trialist": {"CP": 0.45, "CP_per_kg": 0.20, "W_CP": 0.20, "Pmax_CP": 0.10},
    "Rouleur": {"CP": 0.35, "W_CP": 0.30, "Pmax_CP": 0.20, "CP_per_kg": 0.15},
    "Classics/Puncheur": {"W_CP": 0.40, "Pmax_CP": 0.30, "CP": 0.20, "CP_per_kg": 0.10},
    "Breakaway Specialist": {"CP": 0.30, "W_CP": 0.30, "CP_per_kg": 0.20, "Pmax_CP": 0.20}
}

# ----------------------------------------------------
# 2. Calculation Logic (Your Code)
# ----------------------------------------------------

def compute_ratios(CP, W_prime, Pmax, weight):
    ratios = {
        "CP": CP,
        "W_prime": W_prime,
        "Pmax": Pmax,
        "weight": weight,
        "CP_per_kg": CP / weight,
        "Pmax_CP": Pmax / CP,
        "W_CP": W_prime / CP
    }
    return ratios

def calculate_profile_scores(ratios, profile_weights):
    scores = {}
    for profile, weights in profile_weights.items():
        score = 0
        for metric, weight in weights.items():
            score += ratios.get(metric, 0) * weight
        scores[profile] = score
    return scores

def normalise_scores(scores):
    min_s = min(scores.values())
    max_s = max(scores.values())
    # Avoid division by zero
    denom = max_s - min_s
    if denom == 0: denom = 1
    return {p: (s - min_s) / denom * 100 for p, s in scores.items()}

def classify_rider(CP, W_prime, Pmax, weight):
    ratios = compute_ratios(CP, W_prime, Pmax, weight)
    raw_scores = calculate_profile_scores(ratios, PROFILE_WEIGHTS)
    normalised = normalise_scores(raw_scores)
    best_profile = max(normalised, key=normalised.get)
    return best_profile, normalised, ratios

def plot_radar_chart(scores, title="Cycling Profile"):
    labels = list(scores.keys())
    values = list(scores.values())
    
    # Close the circle
    values += values[:1]
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
    ax.fill(angles, values, color="#FF4B4B", alpha=0.25)
    ax.plot(angles, values, color="#FF4B4B", linewidth=2)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=7, color="grey")
    
    ax.set_title(title, fontsize=12, fontweight="bold", y=1.1)
    return fig

# ----------------------------------------------------
# 3. Main Streamlit App
# ----------------------------------------------------

def main():
    st.title("🚴 Rider Performance Platform")

    # --- Sidebar: Inputs ---
    st.sidebar.header("Rider Inputs")
    cp_input = st.sidebar.number_input("Critical Power (CP)", value=360, step=5)
    w_prime_input = st.sidebar.number_input("W' (Anaerobic Capacity)", value=22000, step=100)
    pmax_input = st.sidebar.number_input("Pmax (Max Sprint Power)", value=1300, step=10)
    weight_input = st.sidebar.number_input("Weight (kg)", value=71.0, step=0.5)

    # Perform Calculations
    best_profile, scores, ratios = classify_rider(cp_input, w_prime_input, pmax_input, weight_input)

    # --- TABS ---
    tab1, tab2, tab3 = st.tabs(["📊 Profile Analysis", "📅 Season Planner (Gantt)", "📥 Export Report"])

    # ------------------------------------------------
    # TAB 1: Profile Analysis
    # ------------------------------------------------
    with tab1:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader(f"Identified Profile: **{best_profile}**")
            st.write("Based on the input metrics, here is the breakdown of the rider's strengths:")
            
            # Display metrics nicely
            st.metric("Watts/Kg (CP)", f"{ratios['CP_per_kg']:.2f} W/kg")
            
            # Dataframe for scores
            df_scores = pd.DataFrame(list(scores.items()), columns=['Profile Type', 'Score'])
            st.dataframe(df_scores.style.highlight_max(axis=0, color='lightgreen'), use_container_width=True)

        with col2:
            st.pyplot(plot_radar_chart(scores, title=f"Profile: {best_profile}"))

    # ------------------------------------------------
    # TAB 2: Season Planner (Gantt & SWOT)
    # ------------------------------------------------
    with tab2:
        st.header("Strategic Performance Planning")
        
        # Initialize Session State for the Plan
        if 'plan_data' not in st.session_state:
            st.session_state['plan_data'] = []

        # --- Input Form for New Phase ---
        with st.expander("➕ Add New Training Phase / Decision", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                phase_name = st.text_input("Phase Name", "Base Build 1")
                focus_var = st.selectbox("Focus Variable", ["Aerobic Endurance (CP)", "Anaerobic Capacity (W')", "Sprint Power (Pmax)", "Weight Management", "Recovery", "Race Specific"])
            with c2:
                start_date = st.date_input("Start Date", datetime.date.today())
                end_date = st.date_input("End Date", datetime.date.today() + datetime.timedelta(days=14))
            with c3:
                swot_input = st.text_area("SWOT / Notes", "Strengths: ...\nWeaknesses: ...")
            
            if st.button("Add Phase to Plan"):
                st.session_state['plan_data'].append({
                    "Task": phase_name,
                    "Start": pd.to_datetime(start_date),
                    "Finish": pd.to_datetime(end_date),
                    "Focus": focus_var,
                    "SWOT": swot_input
                })
                st.success(f"Added '{phase_name}' to plan.")

        # --- Display Gantt Chart ---
        if len(st.session_state['plan_data']) > 0:
            df_plan = pd.DataFrame(st.session_state['plan_data'])
            
            st.divider()
            st.subheader("Season Timeline")
            
            # Plotly Gantt
            fig_gantt = px.timeline(
                df_plan, 
                x_start="Start", 
                x_end="Finish", 
                y="Task", 
                color="Focus", 
                hover_data=["SWOT"],
                title="Rider Season Plan"
            )
            fig_gantt.update_yaxes(autorange="reversed") # Standard Gantt order
            st.plotly_chart(fig_gantt, use_container_width=True)
            
            # Show Data Table
            st.subheader("Phase Details (SWOT)")
            st.table(df_plan[["Task", "Start", "Finish", "Focus", "SWOT"]])
            
            # Clear button
            if st.button("Clear Plan"):
                st.session_state['plan_data'] = []
                st.rerun()
        else:
            st.info("Add a phase above to generate the Gantt chart.")

    # ------------------------------------------------
    # TAB 3: Export
    # ------------------------------------------------
    with tab3:
        st.header("Download Report")
        
        # Prepare Text Report
        report_text = f"""
RIDER PERFORMANCE REPORT
========================
Generated on: {datetime.date.today()}

1. RIDER PROFILE
----------------
Inputs:
- CP: {cp_input} W
- W': {w_prime_input} J
- Pmax: {pmax_input} W
- Weight: {weight_input} kg

Classification: {best_profile}
Watts/kg: {ratios['CP_per_kg']:.2f}

Profile Scores:
"""
        for k, v in scores.items():
            report_text += f"- {k}: {v:.1f}\n"

        report_text += "\n\n2. SEASON PLAN\n----------------\n"
        
        if st.session_state['plan_data']:
            for item in st.session_state['plan_data']:
                report_text += f"\n[{item['Start'].date()} to {item['Finish'].date()}] : {item['Task']}\n"
                report_text += f"Focus: {item['Focus']}\n"
                report_text += f"Notes/SWOT: {item['SWOT']}\n"
        else:
            report_text += "No plan data entered."

        # Download Buttons
        col_dl1, col_dl2 = st.columns(2)
        
        with col_dl1:
            st.download_button(
                label="📄 Download Report (Text)",
                data=report_text,
                file_name=f"Rider_Profile_{best_profile}.txt",
                mime="text/plain"
            )

        with col_dl2:
            if len(st.session_state['plan_data']) > 0:
                # Convert plan to CSV
                csv = df_plan.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📊 Download Plan Data (CSV)",
                    data=csv,
                    file_name="season_plan.csv",
                    mime="text/csv",
                )
            else:
                st.write("Add plan data to enable CSV download.")

if __name__ == "__main__":
    main()
