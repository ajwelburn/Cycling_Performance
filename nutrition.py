import streamlit as st

# Page config for a mobile-friendly feel
st.set_page_config(page_title="Training Fuel Tracker", layout="centered")

# Initialize session state for the counters
items = {
    "Bar (30g)": 30,
    "Gel (40g)": 40,
    "Bottle ISO (30g)": 30,
    "500ml Water": 0,
    "Gel (30g)": 30,
    "Chew (35g)": 35
}

if 'counters' not in st.session_state:
    st.session_state.counters = {item: 0 for item in items}

st.title("🏃 Training Fuel Log")

# --- Section 1: User Info ---
with st.expander("Session Details", expanded=True):
    name = st.text_input("Name")
    col_w1, col_w2 = st.columns(2)
    weight_pre = col_w1.number_input("Weight Pre (kg)", step=0.1)
    weight_post = col_w2.number_input("Weight Post (kg)", step=0.1)

# --- Section 2: Toggles (The "Clicker" Section) ---
st.subheader("Fuel Intake")
# Create a grid for buttons
cols = st.columns(2)

for i, (item, carbs) in enumerate(items.items()):
    with cols[i % 2]:
        # Using a button as a toggle/counter
        if st.button(f"➕ {item}"):
            st.session_state.counters[item] += 1
        
        # Display the count clearly
        count = st.session_state.counters[item]
        if count > 0:
            st.markdown(f"**Count: {count}**")
        else:
            st.write("---")

# --- Section 3: Summary & Total ---
st.divider()
total_carbs = sum(st.session_state.counters[item] * items[item] for item in items)

if st.checkbox("Finished? Review & Generate Summary"):
    st.success("Summary Ready!")
    
    # Displaying the results in a "Card" format
    with st.container(border=True):
        st.header(f"Results for {name}")
        st.write(f"**Weight Change:** {round(weight_pre - weight_post, 2)} kg")
        st.write("---")
        
        # List items consumed
        for item, count in st.session_state.counters.items():
            if count > 0:
                st.write(f"✅ {count}x {item}")
        
        st.metric(label="Total Carbohydrates", value=f"{total_carbs}g")
        
        if st.button("Reset Form"):
            for key in st.session_state.counters:
                st.session_state.counters[key] = 0
            st.rerun()
