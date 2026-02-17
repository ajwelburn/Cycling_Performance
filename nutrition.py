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

# --- BILINGUAL DICTIONARY ---
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
        "edit_ask": "Do you need to edit/change anything?",
        "items": ["Bar 30g", "Gel 40g", "ISO 30g", "Water 500ml", "Gel 30g", "Chew 35g"]
    },
    "FR": {
        "title": "Suivi de Nutrition",
        "name_label": "Nom de l'Athlète",
        "pre_label": "Poids Avant (kg)",
        "post_label": "Poids Après (kg)",
        "fuel_header": "Apport Nutritionnel (Appuyez pour ajouter)",
        "review": "✅ Générer le Rapport Final",
        "total": "Total Glucides",
        "loss": "Variation de Poids",
        "items_consumed": "Articles Consommés :",
        "reset": "Réinitialiser",
        "whatsapp": "Partager via WhatsApp",
        "edit_ask": "Souhaitez-vous modifier quelque chose ?",
        "items": ["Barre 30g", "Gel 40g", "ISO 30g", "Eau 500ml", "Gel 30g", "Gomme 35g"]
    }
}[lang]

# Carb values mapping
carb_map = {t["items"][0]: 30, t["items"][1]: 40, t["items"][2]: 30, t["items"][3]: 0, t["items"][4]: 30, t["items"][5]: 35}

if 'counters' not in st.session_state:
    st.session_state.counters = {item: 0 for item in t["items"]}

# --- APP LAYOUT ---
st.title("⚡ " + t["title"])

with st.container(border=True):
    user_name = st.text_input(t["name_label"], placeholder="John Doe")
    c1, c2 = st.columns(2)
    w_pre = c1.number_input(t["pre_label"], step=0.1, format="%.1f")
    w_post = c2.number_input(t["post_label"], step=0.1, format="%.1f")

st.subheader(t["fuel_header"])
cols = st.columns(2)
for i, item in enumerate(t["items"]):
    with cols[i % 2]:
        if st.button(f"＋ {item}"):
            st.session_state.counters[item] += 1
            st.rerun()
        
        count = st.session_state.counters[item]
        if count > 0:
            st.markdown(f"**{item}:** <span class='blue-count'>{count}</span>", unsafe_allow_html=True)

st.divider()

# --- FINAL REPORT LOGIC ---
total_carbs = sum(st.session_state.counters[item] * carb_map[item] for item in t["items"])
weight_loss = round(w_pre - w_post, 2)

st.write(f"### {t['edit_ask']}")
if st.checkbox(t["review"]):
    if not user_name:
        st.error("⚠️ Please enter a name / Veuillez entrer un nom.")
    else:
        # Visual Summary Card (Screenshot Ready)
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
                {"".join([f"<li>✅ {count}x {item}</li>" for item, count in st.session_state.counters.items() if count > 0])}
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
    for item in t["items"]:
        st.session_state.counters[item] = 0
    st.rerun()
