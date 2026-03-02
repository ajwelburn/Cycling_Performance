import streamlit as st
import urllib.parse

# 1. Configuration & Data
st.set_page_config(page_title="Carb Tracker", page_icon="🍞")

CARB_DATA = {
    "Bar (30g)": 30,
    "Bottle (60g)": 60,
    "Bottle (30g)": 30,
    "Mysteryer Bar!": 25  # You can adjust this value
}

st.title("🍞 Carb Tracker")
st.write("Select your items below to calculate your total intake.")

# 2. User Input Section
totals = []

col1, col2 = st.columns(2)

with col1:
    st.subheader("Items")
    for item in CARB_DATA.keys():
        count = st.number_input(f"{item}", min_value=0, step=1, key=item)
        if count > 0:
            totals.append((item, count, count * CARB_DATA[item]))

# 3. Calculation & Display
total_carbs = sum(item[2] for item in totals)

with col2:
    st.subheader("Summary")
    if total_carbs > 0:
        for name, qty, carbs in totals:
            st.write(f"**{qty}x** {name}: {carbs}g")
        
        st.divider()
        st.metric("Total Carbohydrates", f"{total_carbs}g")
    else:
        st.info("No items selected yet.")

# 4. WhatsApp Integration
if total_carbs > 0:
    # Format the message
    msg_body = f"Daily Carb Report:\n"
    for name, qty, carbs in totals:
        msg_body += f"- {qty}x {name} ({carbs}g)\n"
    msg_body += f"\n*Total: {total_carbs}g*"
    
    # Encode for URL
    encoded_msg = urllib.parse.quote(msg_body)
    whatsapp_url = f"https://wa.me/?text={encoded_msg}"
    
    st.link_button("Share via WhatsApp", whatsapp_url)
