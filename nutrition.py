import streamlit as st
import datetime
import urllib.parse

# --- PAGE SETUP ---
st.set_page_config(page_title="Fuel Tracker", page_icon="⚡", layout="centered")

# --- MOBILE-FIRST CSS ---
st.markdown("""
    <style>
    /* Buttons with integrated counters */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 4.8em;
        background-color: #007BFF;
        color: white;
        border: none;
        font-weight: bold;
        line-height: 1.3;
        margin-bottom: -10px;
    }
    .count-badge {
        display: block;
        font-size: 1.4rem;
        background: rgba(255,255,255,0.25);
        border-radius: 6px;
        margin-top: 4px;
        padding: 2px;
    }
    .report-card {
        background-color: #ffffff;
        padding: 20px;
        border: 2px solid #007BFF;
        border-radius: 15px;
        color: #111;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.1);
    }
    .metric-row {
        display: flex;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1px solid #eee;
    }
    .total-row {
        display: flex;
        justify-content: space-between;
        padding: 10px 0;
        font-weight: bold;
        font-size: 1.2rem;
        color: #007BFF;
    }
    </style>
    """, unsafe_allow_html=True)

# --- STABLE DATA STRUCTURE ---
FUEL_DATA = {
    "item_1": {"EN": "Bar 30g", "FR": "Barre 30g", "carbs": 30, "fluid": 0, "type": "solid"},
    "item_2": {"EN": "Gel 40g", "FR": "Gel 40g", "carbs": 40, "fluid": 0, "type": "solid"},
    "item_3": {"EN": "Bottle 500mL 30g", "FR": "Bouteille 500mL 30g", "carbs": 30, "fluid": 500, "type": "fluid"},
    "item_4": {"EN": "Water 500mL", "FR": "Eau 500mL", "carbs": 0, "fluid": 500, "type": "fluid"},
    "item_5": {"EN": "Gel 30g", "FR": "Gel 30g", "carbs": 30, "fluid": 0, "type": "solid"},
    "item_6": {"EN": "Chew 35g", "FR": "Gomme 35g", "carbs": 35, "fluid": 0, "type": "solid"},
}

if 'counters' not in st.session_state:
    st.session_state.counters = {key: 0 for key in FUEL_DATA.keys()}

# --- LANGUAGE TOGGLE ---
lang = st.radio("Language / Langue", ["EN", "FR"], horizontal=True)

t = {
    "EN": {
        "title": "Performance Fuel Log",
        "name": "Athlete Name",
        "pre": "Weight Pre (kg)",
        "post": "Weight Post (kg)",
        "fuel": "Nutrition Intake",
        "review": "✅ Generate Final Report",
        "solid_cho": "Solid CHO Total",
        "fluid_cho": "Fluid CHO Total",
        "total_cho": "Combined CHO Total",
        "total_fluid": "Total Fluid Intake",
        "loss": "Weight Change",
        "whatsapp": "Share via WhatsApp",
        "edit_ask": "Do you need to edit/change anything?",
        "reset": "Reset All Data"
    },
    "FR": {
        "title": "Suivi de Nutrition",
        "name": "Nom de l'Athlète",
        "pre": "Poids Avant (kg)",
        "post": "Poids Après (kg)",
        "fuel": "Apport Nutritionnel",
        "review": "✅ Générer le Rapport Final",
        "solid_cho": "Total Glucides Solides",
        "fluid_cho": "Total Glucides Liquides",
        "total_cho": "Total Glucides (CHO)",
        "total_fluid": "Total Liquides Consommés",
        "loss": "Variation de Poids",
        "whatsapp": "Partager via WhatsApp",
        "edit_ask": "Souhaitez-vous modifier quelque chose ?",
        "reset": "Réinitialiser les données"
    }
}[lang]

# --- APP UI ---
st.title("⚡ " + t["title"])

with st.container(border=True):
    user_name = st.text_input(t["name"], placeholder="e.g. Alex Smith")
    c1, c2 = st.columns(2)
    w_pre = c1.number_input(t["pre"], step=0.1, format="%.1f")
    w_post = c2.number_input(t["post"], step=0.1, format="%.1f")

st.subheader(t["fuel"])
cols = st.columns(2)
for i, key in enumerate(FUEL_DATA.keys()):
    with cols[i % 2]:
        label = FUEL_DATA[key][lang]
        count = st.session_state.counters[key]
        
        # UI Button showing label and the number counter inside
        button_html = f"{label}<br><span class='count-badge'>{count}</span>"
        if st.button(button_html, key=key):
            st.session_state.counters[key] += 1
            st.rerun()

st.divider()

# --- CALCULATIONS ---
solid_cho = sum(st.session_state.counters[k] * FUEL_DATA[k]["carbs"] for k in FUEL_DATA if FUEL_DATA[k]["type"] == "solid")
fluid_cho = sum(st.session_state.counters[k] * FUEL_DATA[k]["carbs"] for k in FUEL_DATA if FUEL_DATA[k]["type"] == "fluid")
total_cho = solid_cho + fluid_cho
total_ml = sum(st.session_state.counters[k] * FUEL_DATA[k]["fluid"] for k in FUEL_DATA)
weight_loss = round(w_pre - w_post, 2)

st.write(f"### {t['edit_ask']}")
if st.checkbox(t["review"]):
    if not user_name:
        st.warning("⚠️ Please enter a name / Entrez un nom")
    else:
        # Final Report Card
        st.markdown(f"""
            <div class="report-card">
                <h3 style='text-align:center; color:#007BFF; margin-bottom:5px;'>{t['title']}</h3>
                <p style='text-align:center;'><b>{user_name}</b> | {datetime.date.today()}</p>
                
                <div class="metric-row"><span>{t['pre']}</span> <b>{w_pre} kg</b></div>
                <div class="metric-row"><span>{t['post']}</span> <b>{w_post} kg</b></div>
                <div class="metric-row" style="background:#f9f9f9;"><span><b>{t['loss']}</b></span> <b>{weight_loss} kg</b></div>
                
                <hr style="border:1px dashed #ddd">
                
                <div class="metric-row"><span>{t['solid_cho']}</span> <b>{solid_cho}g</b></div>
                <div class="metric-row"><span>{t['fluid_cho']}</span> <b>{fluid_cho}g</b></div>
                <div class="total-row"><span>{t['total_cho']}</span> <span>{total_cho}g</span></div>
                
                <hr style="border:1px dashed #ddd">
                
                <div class="metric-row"><span>{t['total_fluid']}</span> <b>{total_ml} mL</b></div>
            </div>
        """, unsafe_allow_html=True)

        # WhatsApp text summary (Bilingual)
        msg = (f"*{t['title']}*\n"
               f"{user_name} | {datetime.date.today()}\n"
               f"------------------------\n"
               f"{t['loss']}: {weight_loss}kg\n"
               f"{t['solid_cho']}: {solid_cho}g\n"
               f"{t['fluid_cho']}: {fluid_cho}g\n"
               f"{t['total_cho']}: {total_cho}g\n"
               f"{t['total_fluid']}: {total_ml}ml")
        
        wa_url = f"https://wa.me/?text={urllib.parse.quote(msg)}"
        st.markdown(f'<a href="{wa_url}" target="_blank"><button style="width:100%; border-radius:12px; height:3.5em; background-color:#25D366; color:white; border:none; font-weight:bold; margin-top:15px;">{t["whatsapp"]}</button></a>', unsafe_allow_html=True)

if st.button(t["reset"]):
    for key in FUEL_DATA:
        st.session_state.counters[key] = 0
    st.rerun()
