import streamlit as st
import datetime
import urllib.parse

# --- PAGE SETUP ---
st.set_page_config(page_title="Fuel Tracker", page_icon="⚡", layout="centered")

# --- ADVANCED MOBILE UI STYLING ---
st.markdown("""
    <style>
    /* Fuel Card Container */
    .fuel-card {
        background-color: #1E1E1E;
        border: 1px solid #333;
        border-radius: 12px;
        margin-bottom: 15px;
        overflow: hidden;
    }
    
    /* Integrated Button Styling */
    div.stButton > button {
        width: 100%;
        border-radius: 12px 12px 0px 0px !important;
        height: 3.8em;
        background-color: #007BFF;
        color: white;
        font-weight: bold;
        border: none;
        font-size: 15px;
    }

    /* Red Analysis Button Styling */
    .stButton > button[kind="secondary"] {
        background-color: #FF4B4B !important;
        color: white !important;
        border-radius: 12px !important;
        height: 4em !important;
        font-size: 18px !important;
        margin-top: 20px;
    }

    /* Neon Green Counter Tray */
    .counter-tray {
        background-color: #111;
        text-align: center;
        padding: 8px 0;
        border-top: 1px solid #007BFF;
    }
    .counter-num {
        font-weight: 900;
        color: #28a745;
        font-size: 1.6rem;
        font-family: 'Courier New', monospace;
    }
    
    /* Report Styling */
    .report-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 15px;
        color: #111;
        border-left: 10px solid #FF4B4B;
    }
    </style>
    """, unsafe_allow_html=True)

# --- DATA ---
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
if 'show_report' not in st.session_state:
    st.session_state.show_report = False

# --- LANG ---
lang = st.radio("Language / Langue", ["EN", "FR"], horizontal=True)

t = {
    "EN": {
        "title": "Fuel Log", "name": "Athlete Name", "pre": "Weight Pre (kg)", "post": "Weight Post (kg)",
        "fuel": "Nutrition Intake", "analyze": "📊 ANALYZE PERFORMANCE", "s_cho": "Solid CHO", "f_cho": "Fluid CHO",
        "t_cho": "Total CHO", "t_flu": "Total Fluid", "loss": "Weight Change", "whatsapp": "Share Summary", "reset": "Reset"
    },
    "FR": {
        "title": "Suivi Nutrition", "name": "Nom de l'Athlète", "pre": "Poids Avant (kg)", "post": "Poids Après (kg)",
        "fuel": "Apport Nutritionnel", "analyze": "📊 ANALYSER LA PERFORMANCE", "s_cho": "Glucides Solides", "f_cho": "Glucides Liquides",
        "t_cho": "Total Glucides", "t_flu": "Total Liquides", "loss": "Variation Poids", "whatsapp": "Partager", "reset": "Réinitialiser"
    }
}[lang]

# --- UI ---
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
        # Using a div to force the button and number to stay together
        st.markdown('<div class="fuel-card">', unsafe_allow_html=True)
        if st.button(FUEL_DATA[key][lang], key=key):
            st.session_state.counters[key] += 1
            st.rerun()
        
        count = st.session_state.counters[key]
        st.markdown(f'<div class="counter-tray"><span class="counter-num">{count}</span></div></div>', unsafe_allow_html=True)

# --- ANALYSIS TRIGGER ---
if st.button(t["analyze"], type="secondary", use_container_width=True):
    st.session_state.show_report = True

# --- CALCULATIONS ---
solid_cho = sum(st.session_state.counters[k] * FUEL_DATA[k]["carbs"] for k in FUEL_DATA if FUEL_DATA[k]["type"] == "solid")
fluid_cho = sum(st.session_state.counters[k] * FUEL_DATA[k]["carbs"] for k in FUEL_DATA if FUEL_DATA[k]["type"] == "fluid")
total_cho = solid_cho + fluid_cho
total_ml = sum(st.session_state.counters[k] * FUEL_DATA[k]["fluid"] for k in FUEL_DATA)
weight_loss = round(w_pre - w_post, 2)

if st.session_state.show_report:
    if not user_name:
        st.error("⚠️ Please enter a name first.")
    else:
        st.markdown(f"""
            <div class="report-card">
                <h3 style='margin-top:0;'>{t['title']} - {user_name}</h3>
                <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                    <span>{t['pre']}: <b>{w_pre}kg</b></span>
                    <span>{t['post']}: <b>{w_post}kg</b></span>
                </div>
                <p><b>{t['loss']}: {weight_loss}kg</b></p>
                <hr>
                <p>{t['s_cho']}: <b>{solid_cho}g</b></p>
                <p>{t['f_cho']}: <b>{fluid_cho}g</b></p>
                <h2 style='color:#FF4B4B; margin:0;'>{t['t_cho']}: {total_cho}g</h2>
                <p>{t['t_flu']}: <b>{total_ml}mL</b></p>
            </div>
        """, unsafe_allow_html=True)
        
        msg = f"*{t['title']}*\nAthlete: {user_name}\nLoss: {weight_loss}kg\nTotal CHO: {total_cho}g\nFluid: {total_ml}ml"
        wa_url = f"https://wa.me/?text={urllib.parse.quote(msg)}"
        st.markdown(f'<a href="{wa_url}" target="_blank"><button style="width:100%; border-radius:12px; height:3.5em; background-color:#25D366; color:white; border:none; font-weight:bold; margin-top:15px;">{t["whatsapp"]}</button></a>', unsafe_allow_html=True)

st.write("---")
if st.button(t["reset"]):
    for k in st.session_state.counters: st.session_state.counters[k] = 0
    st.session_state.show_report = False
    st.rerun()
    
