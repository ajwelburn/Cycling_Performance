import streamlit as st
import datetime
import urllib.parse

# --- PAGE SETUP ---
st.set_page_config(page_title="Fuel Tracker", page_icon="⚡", layout="centered")

# --- MOBILE CSS ---
st.markdown("""
    <style>
    /* Main Action Buttons */
    div.stButton > button {
        width: 100%;
        border-radius: 12px;
        height: 3.8em;
        background-color: #007BFF;
        color: white;
        font-weight: bold;
        border: none;
        font-size: 16px;
        box-shadow: 0px 2px 4px rgba(0,0,0,0.1);
    }
    /* Neat Green Number Badge */
    .counter-badge {
        text-align: center;
        font-weight: 900;
        color: #28a745; /* Clean Green */
        font-size: 1.6rem;
        margin-top: -8px;
        margin-bottom: 12px;
        font-family: 'Courier New', monospace;
    }
    .report-card {
        background-color: #ffffff;
        padding: 20px;
        border: 2px solid #007BFF;
        border-radius: 15px;
        color: #111;
    }
    .metric-row {
        display: flex;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1px solid #eee;
    }
    </style>
    """, unsafe_allow_html=True)

# --- STABLE DATA KEYS ---
FUEL_DATA = {
    "item_1": {"EN": "Bar 30g", "FR": "Barre 30g", "carbs": 30, "fluid": 0, "type": "solid"},
    "item_2": {"EN": "Gel 40g", "FR": "Gel 40g", "carbs": 40, "fluid": 0, "type": "solid"},
    "item_3": {"EN": "Bottle 500mL 30g", "FR": "Bout. 500mL 30g", "carbs": 30, "fluid": 500, "type": "fluid"},
    "item_4": {"EN": "Water 500mL", "FR": "Eau 500mL", "carbs": 0, "fluid": 500, "type": "fluid"},
    "item_5": {"EN": "Gel 30g", "FR": "Gel 30g", "carbs": 30, "fluid": 0, "type": "solid"},
    "item_6": {"EN": "Chew 35g", "FR": "Gomme 35g", "carbs": 35, "fluid": 0, "type": "solid"},
}

if 'counters' not in st.session_state:
    st.session_state.counters = {key: 0 for key in FUEL_DATA.keys()}

# --- TRANSLATIONS ---
lang = st.radio("Language / Langue", ["EN", "FR"], horizontal=True)

t = {
    "EN": {
        "title": "Fuel Log",
        "name": "Athlete Name",
        "pre": "Weight Pre (kg)",
        "post": "Weight Post (kg)",
        "fuel": "Nutrition Intake",
        "review": "✅ Generate Report",
        "s_cho": "Solid CHO Total",
        "f_cho": "Fluid CHO Total",
        "t_cho": "Total CHO",
        "t_flu": "Total Fluid Intake",
        "loss": "Weight Change",
        "whatsapp": "Share via WhatsApp",
        "edit": "Do you need to edit anything?",
        "reset": "Reset Form"
    },
    "FR": {
        "title": "Suivi Nutrition",
        "name": "Nom de l'Athlète",
        "pre": "Poids Avant (kg)",
        "post": "Poids Après (kg)",
        "fuel": "Apport Nutritionnel",
        "review": "✅ Générer le Rapport",
        "s_cho": "Total Glucides Solides",
        "f_cho": "Total Glucides Liquides",
        "t_cho": "Total Glucides",
        "t_flu": "Total Liquides",
        "loss": "Variation de Poids",
        "whatsapp": "Partager via WhatsApp",
        "edit": "Souhaitez-vous modifier ?",
        "reset": "Réinitialiser"
    }
}[lang]

# --- APP UI ---
st.title("⚡ " + t["title"])

with st.container(border=True):
    user_name = st.text_input(t["name"])
    c1, c2 = st.columns(2)
    w_pre = c1.number_input(t["pre"], step=0.1, format="%.1f")
    w_post = c2.number_input(t["post"], step=0.1, format="%.1f")

st.subheader(t["fuel"])
cols = st.columns(2)
for i, key in enumerate(FUEL_DATA.keys()):
    with cols[i % 2]:
        if st.button(FUEL_DATA[key][lang], key=key):
            st.session_state.counters[key] += 1
            st.rerun()
        
        count = st.session_state.counters[key]
        # Only show the green number
        display_val = count if count > 0 else "0"
        st.markdown(f"<div class='counter-badge'>{display_val}</div>", unsafe_allow_html=True)

st.divider()

# --- FINAL TOTALS ---
solid_cho = sum(st.session_state.counters[k] * FUEL_DATA[k]["carbs"] for k in FUEL_DATA if FUEL_DATA[k]["type"] == "solid")
fluid_cho = sum(st.session_state.counters[k] * FUEL_DATA[k]["carbs"] for k in FUEL_DATA if FUEL_DATA[k]["type"] == "fluid")
total_cho = solid_cho + fluid_cho
total_ml = sum(st.session_state.counters[k] * FUEL_DATA[k]["fluid"] for k in FUEL_DATA)
weight_loss = round(w_pre - w_post, 2)

st.write(f"### {t['edit']}")
if st.checkbox(t["review"]):
    if user_name:
        st.markdown(f"""
            <div class="report-card">
                <h3 style='text-align:center;'>{t['title']}</h3>
                <p><b>{user_name}</b> | {datetime.date.today()}</p>
                <div class="metric-row"><span>{t['pre']}</span> <b>{w_pre} kg</b></div>
                <div class="metric-row"><span>{t['post']}</span> <b>{w_post} kg</b></div>
                <div class="metric-row" style="background:#f8f9fa;"><span><b>{t['loss']}</b></span> <b>{weight_loss} kg</b></div>
                <hr>
                <div class="metric-row"><span>{t['s_cho']}</span> <b>{solid_cho}g</b></div>
                <div class="metric-row"><span>{t['f_cho']}</span> <b>{fluid_cho}g</b></div>
                <div class="metric-row" style="color:#007BFF; font-size:1.1rem;"><span><b>{t['t_cho']}</b></span> <b>{total_cho}g</b></div>
                <div class="metric-row"><span>{t['t_flu']}</span> <b>{total_ml} mL</b></div>
            </div>
        """, unsafe_allow_html=True)

        msg = f"*{t['title']}*\n{user_name}\nLoss: {weight_loss}kg\nCHO: {total_cho}g ({solid_cho}s/{fluid_cho}f)\nFluid: {total_ml}ml"
        wa_url = f"https://wa.me/?text={urllib.parse.quote(msg)}"
        st.markdown(f'<a href="{wa_url}" target="_blank"><button style="width:100%; border-radius:12px; height:3.5em; background-color:#25D366; color:white; border:none; font-weight:bold; margin-top:10px;">{t["whatsapp"]}</button></a>', unsafe_allow_html=True)
    else:
        st.error("Please enter a name / Entrez un nom")

if st.button(t["reset"]):
    for k in st.session_state.counters: st.session_state.counters[k] = 0
    st.rerun()
