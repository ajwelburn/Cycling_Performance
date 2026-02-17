import streamlit as st
import datetime
import urllib.parse

# --- PAGE SETUP ---
st.set_page_config(page_title="Fuel Tracker", page_icon="⚡", layout="centered")

# --- SLEEK DARK UI STYLING ---
st.markdown("""
    <style>
    /* Overall Background Tweak */
    .main { background-color: #0E1117; }
    
    /* Sleek Fuel Card */
    .fuel-card {
        background-color: #161B22;
        border: 1px solid #30363D;
        border-radius: 10px;
        margin-bottom: 10px;
        transition: 0.2s;
    }
    .fuel-card:active { transform: scale(0.97); }
    
    /* Button inside the card */
    div.stButton > button {
        width: 100%;
        border-radius: 10px 10px 0px 0px !important;
        height: 3.2em;
        background-color: #21262D; /* Darker Slate */
        color: #C9D1D9;
        font-weight: 600;
        border: 1px solid #30363D;
        font-size: 14px;
    }

    /* Analyze Button (The "Hero" Action) */
    .stButton > button[kind="secondary"] {
        background-color: #D73A49 !important; /* Performance Red */
        color: white !important;
        border-radius: 12px !important;
        height: 3.5em !important;
        font-size: 16px !important;
        font-weight: 800 !important;
        letter-spacing: 1px;
        border: none !important;
        margin-top: 10px;
    }

    /* Subtle Counter Tray */
    .counter-tray {
        background-color: #0D1117;
        text-align: center;
        padding: 5px 0;
        border-top: 2px solid #58A6FF; /* Electric Blue Accent */
        border-radius: 0px 0px 10px 10px;
    }
    .counter-num {
        font-weight: 800;
        color: #3FB950; /* Success Green */
        font-size: 1.3rem;
    }
    
    /* Modern Report Card */
    .report-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        color: #111;
        border-top: 8px solid #D73A49;
        box-shadow: 0px 10px 20px rgba(0,0,0,0.2);
    }
    </style>
    """, unsafe_allow_html=True)

# --- APP LOGIC ---
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
        "title": "Fuel Log", "name": "Athlete Name", "pre": "Pre (kg)", "post": "Post (kg)",
        "analyze": "📊 ANALYZE PERFORMANCE", "s_cho": "Solid CHO", "f_cho": "Fluid CHO",
        "t_cho": "Total CHO", "t_flu": "Total Fluid", "whatsapp": "Share Report", "reset": "Reset"
    },
    "FR": {
        "title": "Suivi Nutrition", "name": "Nom de l'Athlète", "pre": "Avant (kg)", "post": "Après (kg)",
        "analyze": "📊 ANALYSER", "s_cho": "CHO Solides", "f_cho": "CHO Liquides",
        "t_cho": "Total CHO", "t_flu": "Total Liquides", "whatsapp": "Partager", "reset": "Réinitialiser"
    }
}[lang]

# --- UI ---
st.title("⚡ " + t["title"])

with st.container(border=True):
    user_name = st.text_input(t["name"], label_visibility="collapsed", placeholder=t["name"])
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

# --- REPORT CALCULATIONS ---
solid_cho = sum(st.session_state.counters[k] * FUEL_DATA[k]["carbs"] for k in FUEL_DATA if FUEL_DATA[k]["type"] == "solid")
fluid_cho = sum(st.session_state.counters[k] * FUEL_DATA[k]["carbs"] for k in FUEL_DATA if FUEL_DATA[k]["type"] == "fluid")
total_cho = solid_cho + fluid_cho
total_ml = sum(st.session_state.counters[k] * FUEL_DATA[k]["fluid"] for k in FUEL_DATA)
weight_loss = round(w_pre - w_post, 2)

if st.session_state.show_report:
    st.write("---")
    st.markdown(f"""
        <div class="report-card">
            <h2 style='margin-top:0; color:#111;'>{user_name if user_name else "Athlete"}</h2>
            <p>Weight: {w_pre}kg → {w_post}kg (<b>{weight_loss}kg loss</b>)</p>
            <hr>
            <div style="display:flex; justify-content:space-between;">
                <span>{t['s_cho']}: <b>{solid_cho}g</b></span>
                <span>{t['f_cho']}: <b>{fluid_cho}g</b></span>
            </div>
            <h1 style='color:#D73A49; margin:10px 0;'>{total_cho}g CHO</h1>
            <p>{t['t_flu']}: <b>{total_ml}mL</b></p>
        </div>
    """, unsafe_allow_html=True)
    
    msg = f"Report: {user_name}\nLoss: {weight_loss}kg\nTotal CHO: {total_cho}g\nFluid: {total_ml}ml"
    wa_url = f"https://wa.me/?text={urllib.parse.quote(msg)}"
    st.markdown(f'<a href="{wa_url}" target="_blank"><button style="width:100%; border-radius:12px; height:3.5em; background-color:#238636; color:white; border:none; font-weight:bold; margin-top:15px;">{t["whatsapp"]}</button></a>', unsafe_allow_html=True)

# Minimal Reset Link
st.markdown("<br>", unsafe_allow_html=True)
if st.button(t["reset"], key="reset_btn", help="Clear all"):
    for k in st.session_state.counters: st.session_state.counters[k] = 0
    st.session_state.show_report = False
    st.rerun()
