import streamlit as st
import datetime
import urllib.parse

# --- PAGE SETUP ---
st.set_page_config(page_title="Fuel Tracker", page_icon="⚡", layout="centered")

# --- CUSTOM "DASHBOARD" CSS ---
st.markdown("""
    <style>
    /* Sleek Fuel Card - Dark Theme */
    .fuel-card {
        background-color: #1A1C23;
        border: 1px solid #30363D;
        border-radius: 12px;
        margin-bottom: 8px;
        overflow: hidden;
    }
    
    /* Neutral Slate Buttons */
    div.stButton > button {
        width: 100%;
        border-radius: 12px 12px 0px 0px !important;
        height: 3.2em;
        background-color: #2D333B; /* Slate Gray */
        color: #ADBAC7;
        font-weight: bold;
        border: none;
        font-size: 14px;
        transition: 0.2s;
    }
    div.stButton > button:active {
        background-color: #444C56;
    }

    /* Analyze Button - The only Red element */
    .stButton > button[kind="secondary"] {
        background-color: #E34C26 !important; 
        color: white !important;
        border-radius: 12px !important;
        height: 3.5em !important;
        font-size: 16px !important;
        font-weight: 800 !important;
        border: none !important;
        margin-top: 15px;
    }

    /* Counter Tray with Electric Blue Accent */
    .counter-tray {
        background-color: #0D1117;
        text-align: center;
        padding: 4px 0;
        border-top: 2px solid #58A6FF; /* Electric Blue */
    }
    .counter-num {
        font-weight: 900;
        color: #3FB950; /* Neon Green */
        font-size: 1.4rem;
        font-family: 'Courier New', monospace;
    }
    
    /* Summary Card */
    .report-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        color: #111;
        border-left: 8px solid #E34C26;
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
lang = st.radio("Language / Langue", ["EN", "FR"], horizontal=True, label_visibility="collapsed")

t = {
    "EN": {
        "title": "Performance Fuel Log", "name": "Athlete Name", "pre": "Pre (kg)", "post": "Post (kg)",
        "analyze": "📊 ANALYZE PERFORMANCE", "s_cho": "Solid CHO Total", "f_cho": "Fluid CHO Total",
        "t_cho": "Total CHO", "t_flu": "Total Fluid", "loss": "Weight Change", "whatsapp": "Share Report", "reset": "Reset"
    },
    "FR": {
        "title": "Suivi Performance", "name": "Nom de l'Athlète", "pre": "Avant (kg)", "post": "Après (kg)",
        "analyze": "📊 ANALYSER LA PERFORMANCE", "s_cho": "Total Solides", "f_cho": "Total Liquides",
        "t_cho": "Total Glucides (CHO)", "t_flu": "Total Fluides", "loss": "Variation Poids", "whatsapp": "Partager", "reset": "Réinitialiser"
    }
}[lang]

# --- UI ---
st.title("⚡ " + t["title"])

with st.container(border=True):
    user_name = st.text_input(t["name"], placeholder="Enter Athlete Name...")
    c1, c2 = st.columns(2)
    w_pre = c1.number_input(t["pre"], step=0.1, format="%.1f")
    w_post = c2.number_input(t["post"], step=0.1, format="%.1f")

# Condensed 2-Column Grid
cols = st.columns(2)
for i, key in enumerate(FUEL_DATA.keys()):
    with cols[i % 2]:
        st.markdown('<div class="fuel-card">', unsafe_allow_html=True)
        if st.button(FUEL_DATA[key][lang], key=key):
            st.session_state.counters[key] += 1
            st.rerun()
        
        count = st.session_state.counters[key]
        st.markdown(f'<div class="counter-tray"><span class="counter-num">{count}</span></div></div>', unsafe_allow_html=True)

# Main Analyze Button
if st.button(t["analyze"], type="secondary", use_container_width=True):
    st.session_state.show_report = True

# --- CALCULATIONS ---
solid_cho = sum(st.session_state.counters[k] * FUEL_DATA[k]["carbs"] for k in FUEL_DATA if FUEL_DATA[k]["type"] == "solid")
fluid_cho = sum(st.session_state.counters[k] * FUEL_DATA[k]["carbs"] for k in FUEL_DATA if FUEL_DATA[k]["type"] == "fluid")
total_cho = solid_cho + fluid_cho
total_ml = sum(st.session_state.counters[k] * FUEL_DATA[k]["fluid"] for k in FUEL_DATA)
weight_loss = round(w_pre - w_post, 2)

if st.session_state.show_report:
    st.write("---")
    st.markdown(f"""
        <div class="report-card">
            <h2 style='margin:0; color:#111;'>{user_name if user_name else "Athlete"}</h2>
            <p style='color:#666;'>{datetime.date.today()}</p>
            <div style="display:flex; justify-content:space-between; background:#F8F9FA; padding:10px; border-radius:8px; margin:10px 0;">
                <span>{t['pre']}: <b>{w_pre}kg</b></span>
                <span>{t['post']}: <b>{w_post}kg</b></span>
                <span><b>{weight_loss}kg loss</b></span>
            </div>
            <div style="display:flex; justify-content:space-between;">
                <span>{t['s_cho']}: <b>{solid_cho}g</b></span>
                <span>{t['f_cho']}: <b>{fluid_cho}g</b></span>
            </div>
            <h1 style='color:#E34C26; margin:10px 0;'>{total_cho}g CHO</h1>
            <p>{t['t_flu']}: <b>{total_ml}mL</b></p>
        </div>
    """, unsafe_allow_html=True)
    
    msg = f"Report: {user_name}\nLoss: {weight_loss}kg\nTotal CHO: {total_cho}g\nFluid: {total_ml}ml"
    wa_url = f"https://wa.me/?text={urllib.parse.quote(msg)}"
    st.markdown(f'<a href="{wa_url}" target="_blank"><button style="width:100%; border-radius:12px; height:3.5em; background-color:#238636; color:white; border:none; font-weight:bold; margin-top:15px;">{t["whatsapp"]}</button></a>', unsafe_allow_html=True)

# Reset Link
st.markdown("<br>", unsafe_allow_html=True)
if st.button(t["reset"]):
    for k in st.session_state.counters: st.session_state.counters[k] = 0
    st.session_state.show_report = False
    st.rerun()
