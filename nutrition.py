import streamlit as st
from fpdf import FPDF
import datetime

# --- PAGE SETUP & MODERN CSS ---
st.set_page_config(page_title="Fuel Tracker", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        border-radius: 15px;
        height: 3.5em;
        background-color: #007BFF;
        color: white;
        border: none;
        font-weight: bold;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
    }
    .count-box {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 10px;
        text-align: center;
        font-size: 1.5rem;
        font-weight: bold;
        color: #007BFF;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- TRANSLATIONS ---
lang = st.radio("Language / Langue", ["EN", "FR"], horizontal=True)

t = {
    "EN": {
        "title": "⚡ Training Fuel Report",
        "name": "Full Name",
        "pre": "Weight Pre-Training (kg)",
        "post": "Weight Post-Training (kg)",
        "fuel": "Fuel Consumed",
        "review": "Review & Generate Report",
        "total": "Total Carbohydrates",
        "reset": "Reset Form",
        "download": "Download PDF Report",
        "items": ["Bar 30g", "Gel 40g", "Bottle ISO 30g", "500ml Water", "Gel 30g", "Chew 35g"]
    },
    "FR": {
        "title": "⚡ Rapport de Nutrition",
        "name": "Nom Complet",
        "pre": "Poids Avant (kg)",
        "post": "Poids Après (kg)",
        "fuel": "Nutrition Consommée",
        "review": "Vérifier et Générer le Rapport",
        "total": "Total Glucides",
        "reset": "Réinitialiser",
        "download": "Télécharger le PDF",
        "items": ["Barre 30g", "Gel 40g", "Bouteille ISO 30g", "500ml Eau", "Gel 30g", "Gomme 35g"]
    }
}[lang]

# Carb values mapping
carb_map = {t["items"][0]: 30, t["items"][1]: 40, t["items"][2]: 30, t["items"][3]: 0, t["items"][4]: 30, t["items"][5]: 35}

if 'counters' not in st.session_state:
    st.session_state.counters = {item: 0 for item in t["items"]}

# --- UI COMPONENTS ---
st.title(t["title"])

with st.container(border=True):
    user_name = st.text_input(t["name"], placeholder="John Doe")
    c1, c2 = st.columns(2)
    w_pre = c1.number_input(t["pre"], format="%.1f", value=0.0)
    w_post = c2.number_input(t["post"], format="%.1f", value=0.0)

st.subheader(t["fuel"])
cols = st.columns(2)
for i, item in enumerate(t["items"]):
    with cols[i % 2]:
        if st.button(f"＋ {item}"):
            st.session_state.counters[item] += 1
        count = st.session_state.counters[item]
        st.markdown(f"<div class='count-box'>{count}</div>", unsafe_allow_html=True)

# --- REPORT GENERATION ---
st.divider()
total_carbs = sum(st.session_state.counters[item] * carb_map[item] for item in t["items"])

if st.checkbox(t["review"]):
    if not user_name:
        st.warning("Please enter a name / Veuillez entrer un nom")
    else:
        # Visual Summary Card
        with st.container(border=True):
            st.markdown(f"### Summary for {user_name}")
            st.write(f"**Weight Loss:** {round(w_pre - w_post, 2)} kg")
            st.write(f"**Total Carbs:** {total_carbs}g")
            
            # PDF Creation Logic
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, txt=t["title"], ln=True, align='C')
            pdf.ln(10)
            
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt=f"{t['name']}: {user_name}", ln=True)
            pdf.cell(200, 10, txt=f"Date: {datetime.date.today()}", ln=True)
            pdf.cell(200, 10, txt=f"{t['pre']}: {w_pre} kg", ln=True)
            pdf.cell(200, 10, txt=f"{t['post']}: {w_post} kg", ln=True)
            pdf.ln(5)
            pdf.cell(200, 10, txt="--- Consumption Detail ---", ln=True)
            
            for item, count in st.session_state.counters.items():
                if count > 0:
                    pdf.cell(200, 10, txt=f"- {item}: {count}", ln=True)
            
            pdf.ln(5)
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(200, 10, txt=f"{t['total']}: {total_carbs}g", ln=True)
            
            pdf_output = pdf.output(dest='S').encode('latin-1')

            st.download_button(
                label=t["download"],
                data=pdf_output,
                file_name=f"Report_{user_name}.pdf",
                mime="application/pdf"
            )

if st.button(t["reset"]):
    st.session_state.counters = {item: 0 for item in t["items"]}
    st.rerun()
