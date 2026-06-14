import streamlit as st
import urllib.parse

st.set_page_config(
    page_title="FuelPro · Ride Log",
    page_icon="🚴",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Anton&family=Hanken+Grotesk:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

:root {
  --paper:      #F4F1EA;
  --card:       #FFFFFF;
  --ink:        #16140F;
  --ink-soft:   #4A463C;
  --line:       #E2DDD1;
  --accent:     #E5343A;
  --accent-ink: #B11F26;
  --blue:       #2F3C82;
  --blue-deep:  #1E274F;
  --navy:       #14132A;
  --good:       #1E7A4E;
  --radius:     16px;
  --shadow:     0 1px 2px rgba(22,20,15,.05), 0 8px 24px rgba(22,20,15,.07);
}

/* ── chrome removal ── */
header[data-testid="stHeader"],
footer,
#MainMenu,
[data-testid="stSidebar"],
[data-testid="collapsedControl"] { display: none !important; }

/* ── page background ── */
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {
  background: var(--paper) !important;
  background-image: radial-gradient(rgba(22,20,15,.035) 1px, transparent 1px) !important;
  background-size: 18px 18px !important;
}

/* ── block container — max 560 px centred, zero padding ── */
[data-testid="block-container"] {
  max-width: 560px !important;
  padding: 0 0 120px 0 !important;
  margin: 0 auto !important;
}
[data-testid="stVerticalBlock"] { gap: 0 !important; }

/* ── inputs & number inputs ── */
input[type="number"], input[type="text"] {
  font-family: 'JetBrains Mono', monospace !important;
  font-weight: 700 !important;
  font-size: 20px !important;
  background: #FBFAF6 !important;
  border: 1.5px solid var(--line) !important;
  border-radius: 12px !important;
  color: var(--ink) !important;
  text-align: right !important;
}
input[type="number"]:focus, input[type="text"]:focus {
  border-color: var(--blue) !important;
  box-shadow: 0 0 0 3px rgba(47,60,130,.18) !important;
  background: #fff !important;
}

/* ── all labels ── */
label, [data-testid="stWidgetLabel"] p {
  font-family: 'Hanken Grotesk', sans-serif !important;
  font-weight: 600 !important;
  font-size: 15px !important;
  color: var(--ink) !important;
}

/* ── stepper +/- buttons ── */
button[data-testid="stNumberInputStepUp"],
button[data-testid="stNumberInputStepDown"] {
  background: #FBFAF6 !important;
  border: 1.5px solid var(--line) !important;
  color: var(--ink) !important;
}

/* ── all st.button buttons ── */
.stButton > button {
  font-family: 'Hanken Grotesk', sans-serif !important;
  font-weight: 700 !important;
  border-radius: 10px !important;
  border: 1.5px solid var(--line) !important;
  background: #FBFAF6 !important;
  color: var(--ink) !important;
  transition: .12s !important;
  width: 100% !important;
}
.stButton > button:hover {
  border-color: var(--blue) !important;
  background: #f0ede5 !important;
}
.stButton > button:active { transform: scale(.95) !important; }

/* ── stage chip selected ── */
div[data-chip="sel"] .stButton > button {
  background: var(--blue) !important;
  color: #fff !important;
  border-color: var(--blue-deep) !important;
  box-shadow: 0 4px 12px rgba(47,60,130,.28) !important;
  transform: translateY(-2px) !important;
}

/* ── minus button ── */
div[data-stepper="minus"] .stButton > button {
  border-radius: 12px 0 0 12px !important;
  border-right: none !important;
  font-size: 22px !important;
  height: 46px !important;
  padding: 0 !important;
}
/* ── plus button ── */
div[data-stepper="plus"] .stButton > button {
  border-radius: 0 12px 12px 0 !important;
  border-left: none !important;
  font-size: 22px !important;
  height: 46px !important;
  padding: 0 !important;
  color: var(--blue) !important;
}
/* ── stepper number input ── */
div[data-stepper="val"] input {
  border-radius: 0 !important;
  border-left: none !important;
  border-right: none !important;
  text-align: center !important;
  height: 46px !important;
}

/* ── WhatsApp send button ── */
div[data-action="wa"] .stButton > button {
  background: #25D366 !important;
  color: #063d1c !important;
  border: none !important;
  border-radius: 13px !important;
  font-size: 15px !important;
  font-weight: 800 !important;
  padding: 14px 8px !important;
  height: 52px !important;
}
/* ── Copy button ── */
div[data-action="copy"] .stButton > button {
  background: var(--accent) !important;
  color: #fff !important;
  border: none !important;
  border-radius: 13px !important;
  font-size: 15px !important;
  font-weight: 800 !important;
  padding: 14px 8px !important;
  height: 52px !important;
}
/* ── Reset button ── */
div[data-action="reset"] .stButton > button {
  background: none !important;
  border: none !important;
  color: var(--accent-ink) !important;
  text-decoration: underline !important;
  font-size: 12px !important;
  width: auto !important;
}

/* ── expander for report text ── */
[data-testid="stExpander"] {
  background: var(--card) !important;
  border: 1px solid var(--line) !important;
  border-radius: var(--radius) !important;
  margin: 0 16px 18px !important;
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
STEPPER_FIELDS = {
    'gels','chews','bars','bidonsKH','bidons60','bidonsW',
    'peeStops','soda','recup'
}
ALL_FIELDS = list(STEPPER_FIELDS) + [
    'preW','preDrink','otherFood','otherDrinks',
    'bidonVol','peeMl','waterPost','postW','raceH','raceM'
]

def field_default(f):
    if f == 'bidonVol': return 500
    if f in STEPPER_FIELDS: return 0
    return 0.0

if 'stage' not in st.session_state:
    st.session_state.stage = 1
if 'stage_data' not in st.session_state:
    st.session_state.stage_data = {}
if 'copy_done' not in st.session_state:
    st.session_state.copy_done = False

def stage_dict():
    s = st.session_state.stage
    if s not in st.session_state.stage_data:
        st.session_state.stage_data[s] = {f: field_default(f) for f in ALL_FIELDS}
        st.session_state.stage_data[s]['urine'] = None
    return st.session_state.stage_data[s]

def g(field):
    return stage_dict().get(field, field_default(field))

def s(field, value):
    stage_dict()[field] = value

# ══════════════════════════════════════════════════════════════════════════════
# CALCULATIONS
# ══════════════════════════════════════════════════════════════════════════════
def calc():
    bv    = g('bidonVol') or 500
    scale = bv / 500
    h     = (g('raceH') or 0) + (g('raceM') or 0) / 60

    carbs = (g('gels')*40 + g('chews')*35 + g('bars')*30
             + g('bidonsKH')*30*scale + g('bidons60')*60*scale)
    fluid = ((g('bidonsKH')+g('bidons60')+g('bidonsW'))*bv + (g('otherDrinks') or 0))

    pre_drink   = g('preDrink') or 0
    post_finish = g('soda')*330 + g('recup')*500 + (g('waterPost') or 0)
    pee_ml      = (g('peeMl') or 0) if (g('peeMl') or 0) > 0 else g('peeStops')*300

    pre  = g('preW')  or 0
    post = g('postW') or 0
    m0   = (pre  + pre_drink/1000)   if pre  > 0 else None
    m1   = (post - post_finish/1000) if post > 0 else None

    deficit    = (m0 - m1)                         if (m0 and m1)              else None
    dehyd      = deficit / m0 * 100                if (deficit is not None and m0) else None
    sweat      = deficit + fluid/1000 - pee_ml/1000 if deficit is not None      else None
    sweat_rate = sweat / h                          if (sweat is not None and h>0) else None

    return dict(bv=bv, scale=scale, h=h, carbs=carbs, fluid=fluid,
                carbs_h=carbs/h if h>0 else None,
                fluid_h=fluid/h if h>0 else None,
                dehyd=dehyd, sweat_rate=sweat_rate)

def fmt(n, dec=0):
    if n is None: return '—'
    return f"{n:,.{dec}f}"

# ══════════════════════════════════════════════════════════════════════════════
# REPORT
# ══════════════════════════════════════════════════════════════════════════════
def build_report():
    c   = calc()
    bv  = g('bidonVol') or 500
    c30 = round(30*(bv/500))
    c60 = round(60*(bv/500))
    u   = stage_dict().get('urine')
    L   = [
        '🚴 DECATHLON CMA-CGM — RIDE LOG',
        f"Stage {st.session_state.stage}", '',
        '— BEFORE THE START —',
        f"Urine colour (1-8): {u if u else '—'}",
        f"Weight before: {fmt(g('preW') or 0, 1)} kg",
        f"Drink before start: {fmt(g('preDrink') or 0, 0)} ml", '',
        '— DURING THE RIDE —',
        f"Gels (45 g): {int(g('gels'))}  ({int(g('gels'))*40} g carbs)",
        f"Chews (44 g): {int(g('chews'))}  ({int(g('chews'))*35} g carbs)",
        f"Bars (35 g): {int(g('bars'))}  ({int(g('bars'))*30} g carbs)",
        f"Bottles 30 g · {bv} ml: {int(g('bidonsKH'))}  ({int(g('bidonsKH'))*c30} g carbs · {int(g('bidonsKH'))*bv} ml)",
        f"Bottles 60 g · {bv} ml: {int(g('bidons60'))}  ({int(g('bidons60'))*c60} g carbs · {int(g('bidons60'))*bv} ml)",
        f"Bottles water · {bv} ml: {int(g('bidonsW'))}  ({int(g('bidonsW'))*bv} ml)",
        f"Other food: {fmt(g('otherFood') or 0, 0)} g",
        f"Other drinks: {fmt(g('otherDrinks') or 0, 0)} ml",
        f"Pee stops: {int(g('peeStops'))}",
        f"Pee volume: {fmt(g('peeMl') or 0, 0)} ml", '',
        '— AFTER THE RIDE (before weigh-in) —',
        f"Soda (330 ml): {int(g('soda'))}  ({int(g('soda'))*330} ml)",
        f"Recovery (500 ml): {int(g('recup'))}  ({int(g('recup'))*500} ml)",
        f"Water: {fmt(g('waterPost') or 0, 0)} ml", '',
        '— WEIGH-IN AFTER RIDE —',
        f"Weight after: {fmt(g('postW') or 0, 1)} kg", '',
        '— RACE TIME —',
        f"Race time: {int(g('raceH'))}h {int(g('raceM'))}min" + (f"  ({fmt(c['h'],2)} h)" if c['h']>0 else ''), '',
        '— CALCULATED —',
        f"Carbs (race): {fmt(c['carbs'],0)} g",
        "Carbs/h: " + ("—" if c['carbs_h'] is None else str(round(c['carbs_h'])) + " g/h"),
        f"Fluid (race): {fmt(c['fluid']/1000,2)} L",
        "Fluid/h: " + ("—" if c['fluid_h'] is None else str(round(c['fluid_h'])) + " ml/h"),
        "Dehydration: " + ("—" if c['dehyd'] is None else fmt(c['dehyd'],1) + " %"),
        "Sweat rate: " + ("—" if c['sweat_rate'] is None else fmt(c['sweat_rate'],2) + " L/h"),
    ]
    return '\n'.join(L)

# ══════════════════════════════════════════════════════════════════════════════
# REUSABLE COMPONENTS
# ══════════════════════════════════════════════════════════════════════════════

def sec_header(num, title, when):
    st.markdown(f"""
<div style="display:flex;align-items:center;gap:12px;padding:16px 18px;
     border-bottom:1px solid var(--line);
     background:linear-gradient(#fff,#FBFAF6);
     border-radius:var(--radius) var(--radius) 0 0;">
  <div style="font-family:'Anton',sans-serif;font-size:18px;
       width:34px;height:34px;flex:0 0 34px;border-radius:9px;
       background:var(--blue-deep);color:#fff;
       display:grid;place-items:center;">{num}</div>
  <div>
    <div style="font-family:'Anton',sans-serif;font-size:19px;
         letter-spacing:.4px;text-transform:uppercase;line-height:1;
         color:var(--ink);">{title}</div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:10.5px;
         letter-spacing:.1em;color:var(--ink-soft);text-transform:uppercase;
         margin-top:3px;">{when}</div>
  </div>
</div>""", unsafe_allow_html=True)

def row_label(label, hint=""):
    hint_html = f'<span style="display:block;font-weight:500;font-size:12px;color:var(--ink-soft);margin-top:1px;">{hint}</span>' if hint else ''
    st.markdown(f"""
<div style="padding:12px 0 4px 0;">
  <span style="font-weight:600;font-size:15.5px;color:var(--ink);">{label}</span>
  {hint_html}
</div>""", unsafe_allow_html=True)

def row_divider():
    st.markdown('<hr style="border:none;border-top:1px solid var(--line);margin:0;">', unsafe_allow_html=True)

def card_start():
    st.markdown("""
<div style="background:var(--card);border:1px solid var(--line);
     border-radius:var(--radius);box-shadow:var(--shadow);
     margin:18px 16px;overflow:hidden;">""", unsafe_allow_html=True)

def card_end():
    st.markdown('</div>', unsafe_allow_html=True)

def body_start():
    st.markdown('<div style="padding:8px 18px 18px;">', unsafe_allow_html=True)

def body_end():
    st.markdown('</div>', unsafe_allow_html=True)

def stepper_row(label, hint, field):
    row_label(label, hint)
    val = int(g(field) or 0)
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        st.markdown('<div data-stepper="minus">', unsafe_allow_html=True)
        if st.button("−", key=f"m_{field}_{st.session_state.stage}"):
            s(field, max(0, val - 1)); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div data-stepper="val">', unsafe_allow_html=True)
        nv = st.number_input("v", min_value=0, value=val,
                              label_visibility="collapsed",
                              key=f"n_{field}_{st.session_state.stage}")
        s(field, nv)
        st.markdown('</div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div data-stepper="plus">', unsafe_allow_html=True)
        if st.button("+", key=f"p_{field}_{st.session_state.stage}"):
            s(field, val + 1); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    row_divider()

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
BADGE = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='14' fill='%230082C3'/%3E%3Ctext x='50' y='68' text-anchor='middle' font-size='52' font-family='Arial Black' fill='white'%3ED%3C/text%3E%3C/svg%3E"

st.markdown(f"""
<div style="color:#fff;border-bottom:5px solid var(--accent);position:relative;overflow:hidden;
  background:linear-gradient(157deg,rgba(8,9,24,.45),rgba(8,9,24,0) 58%),
             radial-gradient(120% 80% at 85% 110%,rgba(239,74,59,.55),transparent 60%),
             linear-gradient(157deg,#12122a 0%,#20264f 19%,#43275f 39%,#8a2a5e 57%,#cf2c47 77%,#ef4a3b 100%);">
  <div style="height:6px;background:repeating-linear-gradient(135deg,#2F3C82 0 13px,#E5343A 13px 26px);"></div>
  <div style="padding:26px 20px 0;display:flex;align-items:center;gap:15px;">
    <img src="{BADGE}" style="width:62px;height:62px;flex:0 0 62px;border-radius:14px;
         background:rgba(255,255,255,.96);padding:5px;
         box-shadow:0 6px 18px rgba(0,0,0,.32);">
    <div>
      <p style="font-family:'JetBrains Mono',monospace;font-size:10.5px;letter-spacing:.16em;
           text-transform:uppercase;color:rgba(255,255,255,.92);font-weight:500;margin:0 0 5px;">
        Decathlon · CMA-CGM · <b>Continental</b></p>
      <div style="font-family:'Anton',sans-serif;font-size:clamp(30px,9.5vw,46px);line-height:.9;
           letter-spacing:.5px;text-transform:uppercase;text-shadow:0 2px 14px rgba(0,0,0,.28);">
        RIDE<span style="color:#FFD7CF;">·</span>LOG</div>
    </div>
  </div>
  <p style="margin:14px 20px 0;color:rgba(255,255,255,.82);font-size:14px;
       max-width:44ch;padding-bottom:20px;">
    Fill this in after the ride and send it over. Track everything you drank
    and ate so we can work out your fluid balance and fueling.</p>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# STAGE PICKER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
     box-shadow:var(--shadow);margin:18px 16px 0;padding:14px 16px 16px;">
  <div style="font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.18em;
       text-transform:uppercase;color:var(--ink-soft);font-weight:700;margin-bottom:10px;">Stage</div>
""", unsafe_allow_html=True)

cols = st.columns(8)
for i, col in enumerate(cols):
    n = i + 1
    sel = st.session_state.stage == n
    with col:
        st.markdown(f'<div data-chip="{"sel" if sel else "unsel"}">', unsafe_allow_html=True)
        # Render selected chip as coloured HTML button (Streamlit button stays for click handling)
        if sel:
            st.markdown(f"""
<div style="background:var(--blue);color:#fff;border:1.5px solid var(--blue-deep);
     border-radius:9px;height:46px;display:grid;place-items:center;
     font-family:'Anton',sans-serif;font-size:20px;
     box-shadow:0 4px 12px rgba(47,60,130,.28);transform:translateY(-2px);
     cursor:default;">{n}</div>""", unsafe_allow_html=True)
        else:
            if st.button(str(n), key=f"chip_{n}"):
                st.session_state.stage = n
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — BEFORE THE START
# ══════════════════════════════════════════════════════════════════════════════
card_start()
sec_header("1", "Before the start", "Pre-stage")
body_start()

# Urine colour
st.markdown("""
<div style="padding:14px 0 10px 0;border-bottom:1px solid var(--line);">
  <span style="font-weight:600;font-size:15.5px;color:var(--ink);">Urine colour</span>
  <span style="display:block;font-weight:500;font-size:12px;color:var(--ink-soft);margin-top:2px;">
    Tap the shade that matches yours — 1 = pale (well hydrated), 8 = dark (dehydrated)</span>
</div>""", unsafe_allow_html=True)

SWATCHES = ['#FFFDE8','#FFFAB6','#F8EF66','#FDE11C','#ECD247','#E4C306','#DAB002','#8C881C']
u_cols = st.columns(8)
for i, col in enumerate(u_cols):
    v   = i + 1
    sel = (stage_dict().get('urine') == v)
    col_border  = "2.5px solid #2F3C82" if sel else "2px solid rgba(0,0,0,.07)"
    col_shadow  = "0 0 0 3px rgba(47,60,130,.22)" if sel else "none"
    col_tf      = "translateY(-3px)" if sel else "none"
    tick_bg     = "#2F3C82" if sel else "rgba(255,255,255,.62)"
    tick_color  = "#fff" if sel else "#2b2a14"
    tick_radius = "50%" if sel else "6px"
    tick_label  = "✓" if sel else str(v)
    with col:
        st.markdown(f"""
<div style="height:68px;border-radius:9px;background:{SWATCHES[i]};
     border:{col_border};box-shadow:{col_shadow};transform:{col_tf};
     display:flex;align-items:flex-end;justify-content:center;
     cursor:pointer;transition:.12s;margin-bottom:2px;">
  <span style="font-family:'JetBrains Mono',monospace;font-weight:700;font-size:11px;
       color:{tick_color};background:{tick_bg};border-radius:{tick_radius};
       width:18px;height:18px;display:inline-flex;align-items:center;
       justify-content:center;margin-bottom:5px;">{tick_label}</span>
</div>""", unsafe_allow_html=True)
        if st.button(f" ", key=f"u{v}_s{st.session_state.stage}",
                     help=f"Shade {v}"):
            stage_dict()['urine'] = v
            st.rerun()

row_divider()

# Weight before
row_label("Weight before", "At the weigh-in, just before the race")
pre_w = st.number_input("Weight before", min_value=0.0, max_value=200.0,
                         value=float(g('preW') or 0), step=0.1, format="%.1f",
                         label_visibility="collapsed",
                         key=f"preW_{st.session_state.stage}")
s('preW', pre_w)
st.markdown('<div style="text-align:right;margin-top:-8px;font-family:\'JetBrains Mono\',monospace;font-size:12px;color:var(--ink-soft);">kg</div>', unsafe_allow_html=True)
row_divider()

# Drink before
row_label("Drink before the start", "Fluid drunk between the weigh-in and the start")
pre_drink = st.number_input("Drink before", min_value=0, max_value=5000,
                             value=int(g('preDrink') or 0), step=50,
                             label_visibility="collapsed",
                             key=f"preDrink_{st.session_state.stage}")
s('preDrink', pre_drink)
st.markdown('<div style="text-align:right;margin-top:-8px;font-family:\'JetBrains Mono\',monospace;font-size:12px;color:var(--ink-soft);">ml</div>', unsafe_allow_html=True)

body_end()
card_end()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — DURING THE RIDE
# ══════════════════════════════════════════════════════════════════════════════
c_now = calc()
bv_hint = int(c_now['bv'])
h30 = f"{round(30*c_now['scale'])} g carbs at {bv_hint} ml"
h60 = f"{round(60*c_now['scale'])} g carbs at {bv_hint} ml"

card_start()
sec_header("2", "During the ride", "On the bike")
body_start()

stepper_row("Gels",           "45 g · 40 g carbs",  "gels")
stepper_row("Chews",          "44 g · 35 g carbs",  "chews")
stepper_row("Bars",           "35 g · 30 g carbs",  "bars")
stepper_row("Bottles · 30 g", h30,                   "bidonsKH")
stepper_row("Bottles · 60 g", h60,                   "bidons60")
stepper_row("Bottles · water","water only",           "bidonsW")

row_label("Other food", "total weight of any extra food (g)")
of = st.number_input("Other food", min_value=0, max_value=10000,
                      value=int(g('otherFood') or 0), step=1,
                      label_visibility="collapsed",
                      key=f"otherFood_{st.session_state.stage}")
s('otherFood', of)
st.markdown('<div style="text-align:right;margin-top:-8px;font-family:\'JetBrains Mono\',monospace;font-size:12px;color:var(--ink-soft);">g</div>', unsafe_allow_html=True)
row_divider()

row_label("Other drinks", "any extra drinks on the bike")
od = st.number_input("Other drinks", min_value=0, max_value=10000,
                      value=int(g('otherDrinks') or 0), step=50,
                      label_visibility="collapsed",
                      key=f"otherDrinks_{st.session_state.stage}")
s('otherDrinks', od)
st.markdown('<div style="text-align:right;margin-top:-8px;font-family:\'JetBrains Mono\',monospace;font-size:12px;color:var(--ink-soft);">ml</div>', unsafe_allow_html=True)

# Trackbox
st.markdown("""
<div style="margin-top:14px;padding:2px 14px 6px;background:#FAF7F0;
     border:1px solid var(--line);border-radius:12px;">""", unsafe_allow_html=True)

row_label("Volume per bottle")
bv_val = st.number_input("Bottle vol", min_value=100, max_value=2000,
                          value=int(g('bidonVol') or 500), step=50,
                          label_visibility="collapsed",
                          key=f"bidonVol_{st.session_state.stage}")
s('bidonVol', bv_val)
st.markdown('<div style="text-align:right;margin-top:-8px;font-family:\'JetBrains Mono\',monospace;font-size:12px;color:var(--ink-soft);">ml</div>', unsafe_allow_html=True)
row_divider()

stepper_row("Pee stops", "", "peeStops")

st.markdown("""
<div style="padding:12px 0 4px 0;">
  <span style="font-weight:500;font-size:15px;color:#A29D90;">Pee volume
    <em style="font-style:normal;font-size:10px;letter-spacing:.08em;
         text-transform:uppercase;color:#B8B3A5;margin-left:7px;font-weight:700;">optional</em>
  </span>
</div>""", unsafe_allow_html=True)
pee = st.number_input("Pee vol", min_value=0, max_value=5000,
                       value=int(g('peeMl') or 0), step=50,
                       label_visibility="collapsed",
                       key=f"peeMl_{st.session_state.stage}")
s('peeMl', pee)
st.markdown('<div style="text-align:right;margin-top:-8px;font-family:\'JetBrains Mono\',monospace;font-size:12px;color:#B5B0A3;">ml</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)  # close trackbox
body_end()
card_end()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — AFTER THE RIDE
# ══════════════════════════════════════════════════════════════════════════════
card_start()
sec_header("3", "After the ride", "Before weigh-in")
body_start()

st.markdown("""
<div style="display:flex;gap:10px;align-items:flex-start;padding:11px 13px;margin:6px 0 14px;
     background:rgba(47,60,130,.05);border:1px solid var(--line);
     border-left:3px solid var(--accent);border-radius:10px;
     font-size:13px;font-weight:600;color:var(--ink-soft);line-height:1.4;">
  <div style="flex:0 0 20px;width:20px;height:20px;border-radius:50%;
       background:var(--accent);color:#fff;font-size:13px;font-weight:800;
       display:grid;place-items:center;margin-top:1px;">!</div>
  <span>Only fill in drinks you had <b style="color:var(--accent-ink);">before</b>
    the weigh-in. Anything consumed after the weigh-in should be left out.</span>
</div>""", unsafe_allow_html=True)

stepper_row("Soda",            "330 ml each", "soda")
stepper_row("Recovery drink",  "500 ml each", "recup")

row_label("Water", "loose water after the finish")
wp = st.number_input("Water post", min_value=0, max_value=5000,
                      value=int(g('waterPost') or 0), step=50,
                      label_visibility="collapsed",
                      key=f"waterPost_{st.session_state.stage}")
s('waterPost', wp)
st.markdown('<div style="text-align:right;margin-top:-8px;font-family:\'JetBrains Mono\',monospace;font-size:12px;color:var(--ink-soft);">ml</div>', unsafe_allow_html=True)

body_end()
card_end()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — WEIGH-IN AFTER RIDE
# ══════════════════════════════════════════════════════════════════════════════
card_start()
sec_header("4", "Weigh-in after ride", "Post weigh-in")
body_start()

row_label("Weight after", "At the weigh-in after the ride")
post_w = st.number_input("Weight after", min_value=0.0, max_value=200.0,
                          value=float(g('postW') or 0), step=0.1, format="%.1f",
                          label_visibility="collapsed",
                          key=f"postW_{st.session_state.stage}")
s('postW', post_w)
st.markdown('<div style="text-align:right;margin-top:-8px;font-family:\'JetBrains Mono\',monospace;font-size:12px;color:var(--ink-soft);">kg</div>', unsafe_allow_html=True)

body_end()
card_end()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — RACE TIME + RESULTS
# ══════════════════════════════════════════════════════════════════════════════
card_start()
sec_header("5", "Race time", "Duration &amp; results")
body_start()

row_label("Total race time", "Elapsed time of the stage")
t1, t2 = st.columns(2)
with t1:
    rh = st.number_input("Hours", min_value=0, max_value=24,
                          value=int(g('raceH') or 0),
                          key=f"raceH_{st.session_state.stage}")
    s('raceH', rh)
with t2:
    rm = st.number_input("Minutes", min_value=0, max_value=59,
                          value=int(g('raceM') or 0),
                          key=f"raceM_{st.session_state.stage}")
    s('raceM', rm)

# Results panel
cr = calc()

def dehyd_cls(v):
    if v is None: return '#fff', ''
    if v > 3:     return '#FB7185', 'bad'
    if v > 2:     return '#FBBF24', 'warn'
    return '#5BE08A', 'ok'

dc, _ = dehyd_cls(cr['dehyd'])

def res_cell(value, unit, label, color='#fff'):
    return f"""
<div style="background:var(--navy);padding:14px 15px;">
  <div style="font-family:'JetBrains Mono',monospace;font-weight:700;
       font-size:21px;color:{color};line-height:1;">
    {value}<small style="font-size:12px;font-weight:500;color:rgba(255,255,255,.55);margin-left:1px;">{unit}</small>
  </div>
  <div style="font-size:10.5px;letter-spacing:.07em;text-transform:uppercase;
       color:rgba(255,255,255,.6);margin-top:7px;font-weight:600;">{label}</div>
</div>"""

carbs_v  = fmt(cr['carbs'], 0)
carbs_h  = '—' if cr['carbs_h']  is None else str(round(cr['carbs_h']))
fluid_v  = fmt(cr['fluid']/1000, 2)
fluid_h  = '—' if cr['fluid_h']  is None else str(round(cr['fluid_h']))
dehyd_v  = '—' if cr['dehyd']    is None else fmt(cr['dehyd'], 1)
sweat_v  = '—' if cr['sweat_rate'] is None else fmt(cr['sweat_rate'], 2)
carbs_u  = '' if cr['carbs_h']    is None else ''
fluid_hu = '' if cr['fluid_h']    is None else ''

st.markdown(f"""
<div style="margin-top:16px;border-radius:14px;overflow:hidden;
     display:grid;grid-template-columns:1fr 1fr;gap:1px;
     border:1px solid var(--navy);background:var(--navy);">
  {res_cell(carbs_v,  'g',    'Carbs · race')}
  {res_cell(carbs_h,  '' if cr['carbs_h'] is None else 'g/h', 'Carbs / h')}
  {res_cell(fluid_v,  'L',    'Fluid · race')}
  {res_cell(fluid_h,  '' if cr['fluid_h'] is None else 'ml/h','Fluid / h')}
  {res_cell(dehyd_v,  '' if cr['dehyd'] is None else '%',     'Dehydration', dc)}
  {res_cell(sweat_v,  '' if cr['sweat_rate'] is None else 'L/h','Sweat rate')}
</div>""", unsafe_allow_html=True)

body_end()
card_end()

# ══════════════════════════════════════════════════════════════════════════════
# SEND / COPY
# ══════════════════════════════════════════════════════════════════════════════
report = build_report()
wa_url = "https://wa.me/?text=" + urllib.parse.quote(report)

st.markdown('<div style="margin:4px 16px 0;">', unsafe_allow_html=True)
a1, a2 = st.columns(2)
with a1:
    st.markdown(f"""
<a href="{wa_url}" target="_blank" rel="noopener"
   style="display:block;background:#25D366;color:#063d1c;border-radius:13px;
          padding:0;height:52px;line-height:52px;text-align:center;
          font-family:'Hanken Grotesk',sans-serif;font-weight:800;font-size:14.5px;
          text-decoration:none;">📱 WhatsApp</a>""", unsafe_allow_html=True)
with a2:
    with st.expander("📋 Copy report"):
        st.text_area("", value=report, height=260, key="report_area",
                     label_visibility="collapsed")

st.markdown('</div>', unsafe_allow_html=True)

# Reset
st.markdown('<div style="text-align:center;padding:8px 16px 12px;color:var(--ink-soft);font-size:12px;">Fill in per stage, then send. &nbsp;', unsafe_allow_html=True)
if st.button(f"Reset stage {st.session_state.stage}", key="reset"):
    st.session_state.stage_data[st.session_state.stage] = {
        f: field_default(f) for f in ALL_FIELDS
    }
    st.session_state.stage_data[st.session_state.stage]['urine'] = None
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)
