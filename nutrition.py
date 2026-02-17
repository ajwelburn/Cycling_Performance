import streamlit as st
import datetime
import urllib.parse

# --- PAGE SETUP ---
st.set_page_config(page_title="Fuel Tracker", page_icon="⚡", layout="centered")

# --- MODERN UI STYLING ---
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3.5em;
        background-color: #007BFF;
        color: white;
        border: none;
        font-weight: bold;
    }
    .report-card {
        background-color: #ffffff;
        padding: 20px;
        border: 2px solid #007BFF;
        border-radius: 15px;
        color: #111;
        font-family: sans-serif;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.1);
    }
    .blue-count {
        color: #007BFF;
        font-weight: bold;
        font-size: 1.1rem;
    }
    .weight-row {
        display: flex; 
        justify-content: space-between; 
        background: #f1f3f5; 
        padding: 10px; 
        border-radius: 8px;
        margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INTERNAL DATA STRUCTURE (STABLE KEYS) ---
# This prevents the app from breaking when switching languages
FUEL_DATA = {
    "item_1": {"EN": "Bar 30g", "FR": "Barre 30g", "carbs": 30},
    "item_2": {"EN": "Gel 40g", "FR": "Gel 40g", "carbs": 40},
    "item_3": {"EN": "ISO 30g", "FR": "ISO 30g", "carbs": 30},
    "item_4": {"EN": "Water 500ml", "FR": "Eau 500ml", "carbs": 0},
    "item_5": {"EN": "Gel 30g", "FR": "Gel 30g", "carbs": 30},
    "item_6": {"EN": "Chew 35g", "FR": "Gomme 35g", "carbs": 35},
}

if 'counters' not in st.session_state:
    st.session_state.counters = {key: 0 for key in FUEL_DATA.keys()}

# --- TRANSLATIONS ---
lang = st.radio("Language / Langue", ["EN", "FR"], horizontal=True)

t = {
    "EN": {
        "title": "Performance Fuel Log",
        "name_label": "Athlete Name",
        "pre_label": "Weight Pre (kg)",
        "post_label": "Weight Post (kg)",
        "fuel_header": "Fuel Intake (Tap to add)",
        "review": "✅ Generate Final Report",
        "total": "Total Carbohydrates",
        "loss": "Weight Change",
        "items_consumed": "Items Consumed:",
        "reset": "Reset Form",
        "whatsapp": "Share Summary via WhatsApp",
        "edit_ask": "Do you need to edit/change anything?"
    },
    "FR": {
        "title": "Suivi de Nutrition",
        "name_label": "Nom de l'Athlète",
        "pre_label": "Poids Avant (kg)",
        "post_label": "Poids Après (kg)",
        "fuel_header": "Apport Nutritionnel",
        "review": "✅ Générer le Rapport Final",
        "total": "Total Glucides",
        "loss": "Variation de Poids",
        "items_consumed": "Articles Consommés :",
        "reset": "Réinitialiser",
        "whatsapp": "Partager via WhatsApp",
        "edit_ask": "Souhaitez-vous modifier quelque chose ?"
    }
}[lang]

# --- APP LAYOUT ---
st.title("⚡ " + t["title"])

with st.container(border=True):
    user_name = st.text_input(t["name_label"], placeholder="John Doe")
    c1, c2 = st.columns(2)
    w_pre = c1.number_input(t["pre_label"], step=0.1, format="%.1f", key="w_pre")
    w_post = c2.number_input(t["post_label"], step=0.1, format="%.1f", key="w_post")

st.subheader(t["fuel_header"])
cols = st.columns(2)

# Loop through our stable keys
for i, key in enumerate(FUEL_DATA.keys()):
    with cols[i % 2]:
        label = FUEL_DATA[key][lang] # Get the label based on current lang
        if st.button(f"＋ {label}"):
            st.session_state.counters[key] += 1
            st.rerun()
        
        count = st.session_state.counters[key]
        if count > 0:
            st.markdown(f"**{label}:** <span class='blue-count'>{count}</span>", unsafe_allow_html=True)

st.divider()

# --- FINAL REPORT LOGIC ---
total_carbs = sum(st.session_state.counters[key] * FUEL_DATA[key]["carbs"] for key in FUEL_DATA.keys())
weight_loss = round(w_pre - w_post, 2)

st.write(f"### {t['edit_ask']}")
if st.checkbox(t["review"]):
    if not user_name:
        st.error("⚠️ Please enter a name / Veuillez entrer un nom.")
    else:
        # Visual Summary Card
        st.markdown(f"""
            <div class="report-card">
                <h2 style='text-align:center; color:#007BFF; margin-top:0;'>{t['title']}</h2>
                <p><b>{t['name_label']}:</b> {user_name}</p>
                <p><b>Date:</b> {datetime.date.today()}</p>
                <hr>
                <div class="weight-row">
                    <span><b>{t['pre_label']}:</b> {w_pre} kg</span>
                    <span><b>{t['post_label']}:</b> {w_post} kg</span>
                </div>
                <p style="font-size: 1.1rem; text-align:center;"><b>{t['loss']}: {weight_loss} kg</b></p>
                <hr>
                <p><b>{t['items_consumed']}</b></p>
                <ul style="list-style-type: none; padding-left: 0;">
                {"".join([f"<li>✅ {st.session_state.counters[k]}x {FUEL_DATA[k][lang]}</li>" for k in FUEL_DATA.keys() if st.session_state.counters[k] > 0])}
                </ul>
                <hr>
                <h3 style='text-align:center;'>{t['total']}: {total_carbs}g</h3>
            </div>
        """, unsafe_allow_html=True)

        # WhatsApp sharing
        msg = f"*{t['title']}*\n{t['name_label']}: {user_name}\n{t['pre_label']}: {w_pre}kg\n{t['post_label']}: {w_post}kg\n{t['loss']}: {weight_loss}kg\n{t['total']}: {total_carbs}g"
        wa_url = f"https://wa.me/?text={urllib.parse.quote(msg)}"
        st.markdown(f'<a href="{wa_url}" target="_blank"><button style="width:100%; border-radius:12px; height:3.5em; background-color:#25D366; color:white; border:none; font-weight:bold; margin-top:10px;">{t["whatsapp"]}</button></a>', unsafe_allow_html=True)

if st.button(t["reset"]):
    for key in FUEL_DATA.keys():
        st.session_state.counters[key] = 0
    st.rerun()
