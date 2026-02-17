import streamlit as st
from fpdf import FPDF
import datetime
import urllib.parse

# --- PAGE SETUP & COMPACT MOBILE CSS ---
st.set_page_config(page_title="Fuel Tracker", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    /* Main Action Buttons */
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        background-color: #007BFF;
        color: white;
        border: none;
        font-weight: 600;
    }
    /* Compact Counter Badge */
    .counter-badge {
        background-color: #007BFF;
        color: white;
        padding: 2px 10px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.9rem;
        float: right;
    }
    /* Item Row Styling */
    .fuel-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 5px 10px;
        background: #f8f9fa;
        border-radius: 8px;
        margin-bottom: 5px;
        border: 1px solid #eee;
    }
    </style>
    """, unsafe_allow_html=True)

# --- TRANSLATIONS ---
lang = st.radio("Language / Langue", ["EN", "FR"], horizontal=True)

t = {
    "EN": {
        "title": "Training Fuel Report",
        "name": "Full Name",
        "pre": "Pre (kg)",
        "post": "Post (kg)",
        "fuel": "Nutrition Intake",
        "review": "Review & Complete",
        "total": "Total Carbs",
        "reset": "Reset",
        "download": "Download PDF",
        "items": ["Bar 30g", "Gel 40g", "ISO 30g", "Water 500ml", "Gel 30g", "Chew 35g"]
    },
    "FR": {
        "title": "Rapport Nutrition",
        "name": "Nom Complet",
        "pre": "Avant (kg)",
        "post": "Apres (kg)",
        "fuel": "Apport Nutritionnel",
        "review": "Verifier et Terminer",
        "total": "Total Glucides",
        "reset": "Reinitialiser",
        "download": "Telecharger PDF",
        "items": ["Barre 30g", "Gel 40g", "ISO 30g", "Eau 500ml", "Gel 30g", "Gomme 35g"]
    }
}[lang]

carb_map = {t["items"][0]: 30, t["items"][1]: 40, t["items"][2]: 30, t["items"][3]: 0, t["items"][4]: 30, t["items"][5]: 35}

if 'counters' not in st.session_state:
    st.session_state.counters = {item: 0 for item in t["items"]}

# --- APP UI ---
st.title("⚡ " + t["title"])

# Compact Weight Inputs
with st.container(border=True):
    user_name = st.text_input(t["name"], placeholder="Enter name...")
    c1, c2 = st.columns(2)
    w_pre = c1.number_input(t["pre"], format="%.1f")
    w_post = c2.number_input(t["post"], format="%.1f")

st.subheader(t["fuel"])

# Grid Layout for Buttons
cols = st.columns(2)
for i, item in enumerate(t["items"]):
    with cols[i % 2]:
        # Compact Button with Badge
        count = st.session_state.counters[item]
        badge_html = f'<span class="counter-badge">{count}</span>' if count > 0 else ''
        
        if st.button(f"➕ {item}"):
            st.session_state.counters[item] += 1
            st.rerun()
            
        if count > 0:
            st.markdown(f"Count: **{count}**", unsafe_allow_html=True)

# --- REPORT GENERATION ---
st.divider()
total_carbs = sum(st.session_state.counters[item] * carb_map[item] for item in t["items"])

if st.checkbox(t["review"]):
    if not user_name:
        st.warning("Please enter a name")
    else:
        # Mini Report Card
        st.info(f"**{user_name}** | {total_carbs}g Carbs | {round(w_pre - w_post, 2)}kg Loss")
        
        # PDF Generation (Fpdf2 compatible)
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", 'B', 16)
        pdf.cell(0, 10, txt=t["title"], ln=True, align='C')
        pdf.ln(5)
        pdf.set_font("helvetica", size=12)
        pdf.cell(0, 8, txt=f"Name: {user_name}", ln=True)
        pdf.cell(0, 8, txt=f"Date: {datetime.date.today()}", ln=True)
        pdf.cell(0, 8, txt=f"Weight: {w_pre}kg -> {w_post}kg", ln=True)
        pdf.ln(5)
        
        for item, count in st.session_state.counters.items():
            if count > 0:
                pdf.cell(0, 8, txt=f"- {item}: {count}", ln=True)
        
        pdf.ln(5)
        pdf.set_font("helvetica", 'B', 14)
        pdf.cell(0, 10, txt=f"TOTAL: {total_carbs}g Carbs", ln=True)
        
        pdf_bytes = pdf.output()

        # Action Buttons
        st.download_button(t["download"], data=pdf_bytes, file_name=f"{user_name}_Fuel.pdf", mime="application/pdf")
        
        msg = f"Report: {user_name}\nCarbs: {total_carbs}g\nWeight: {w_pre}kg to {w_post}kg"
        wa_url = f"https://wa.me/?text={urllib.parse.quote(msg)}"
        st.markdown(f'<a href="{wa_url}" target="_blank"><button style="width:100%; border-radius:10px; height:3em; background-color:#25D366; color:white; border:none; font-weight:bold; margin-top:10px;">Send to Coach (WhatsApp)</button></a>', unsafe_allow_html=True)

if st.button(t["reset"]):
    st.session_state.counters = {item: 0 for item in t["items"]}
    st.rerun()
