import streamlit as st
import urllib.parse

st.set_page_config(
    page_title="FuelPro · Ride Log",
    page_icon="🚴",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Anton&family=Hanken+Grotesk:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

header[data-testid="stHeader"], footer, #MainMenu,
[data-testid="stSidebar"], [data-testid="collapsedControl"] { display:none !important; }

[data-testid="stAppViewContainer"],[data-testid="stMain"],.main {
    background:#F4F1EA !important;
}
[data-testid="block-container"] {
    max-width:560px !important;
    padding:0 10px 80px 10px !important;
}
[data-testid="stVerticalBlock"] { gap:0 !important; }

/* ── all st.button base ── */
div.stButton > button {
    font-family:'Hanken Grotesk',sans-serif !important;
    font-weight:800 !important;
    background:#FBFAF6 !important;
    color:#16140F !important;
    border:1.5px solid #E2DDD1 !important;
    border-radius:10px !important;
    width:100% !important;
    transition:0.1s !important;
    padding:0 !important;
}
div.stButton > button:hover { background:#F0EDE5 !important; }
div.stButton > button:active { transform:scale(0.94) !important; }

/* ── MINUS button ── */
.btn-minus div.stButton > button {
    height:56px !important;
    font-size:30px !important;
    background:#FFF0F0 !important;
    color:#C0392B !important;
    border-color:#F5C6C6 !important;
    border-radius:12px !important;
}
/* ── PLUS button ── */
.btn-plus div.stButton > button {
    height:56px !important;
    font-size:30px !important;
    background:#F0F4FF !important;
    color:#2F3C82 !important;
    border-color:#C6CEEF !important;
    border-radius:12px !important;
}

/* hide built-in number steppers */
button[data-testid="stNumberInputStepUp"],
button[data-testid="stNumberInputStepDown"] { display:none !important; }

input[type="number"] {
    font-family:'JetBrains Mono',monospace !important;
    font-weight:700 !important;
    font-size:20px !important;
    text-align:center !important;
    background:#fff !important;
    border:1.5px solid #E2DDD1 !important;
    border-radius:10px !important;
    color:#16140F !important;
    height:56px !important;
}
input[type="number"]:focus {
    border-color:#2F3C82 !important;
    box-shadow:0 0 0 3px rgba(47,60,130,.15) !important;
}

[data-testid="stWidgetLabel"] p {
    font-family:'Hanken Grotesk',sans-serif !important;
    font-weight:600 !important; font-size:14px !important;
}

[data-testid="stExpander"] {
    background:#fff !important;
    border:1px solid #E2DDD1 !important;
    border-radius:12px !important;
    margin-top:6px !important;
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════
STEPPER_FIELDS = ['gels','chews','bars','bidonsKH','bidons60','bidonsW','peeStops','soda','recup']
FLOAT_FIELDS   = ['preW','postW']
INT_FIELDS     = ['preDrink','otherFood','otherDrinks','bidonVol','peeMl','waterPost','raceH','raceM']

def field_default(f):
    if f == 'bidonVol': return 500
    if f in FLOAT_FIELDS: return 0.0
    return 0

if 'stage'      not in st.session_state: st.session_state.stage = 1
if 'stage_data' not in st.session_state: st.session_state.stage_data = {}

def sdata():
    n = st.session_state.stage
    if n not in st.session_state.stage_data:
        d = {f: field_default(f) for f in STEPPER_FIELDS + FLOAT_FIELDS + INT_FIELDS}
        d['urine'] = None
        st.session_state.stage_data[n] = d
    return st.session_state.stage_data[n]

def g(f):     return sdata().get(f, field_default(f))
def sv(f, v): sdata()[f] = v

# ══════════════════════════════════════════════════════════════════════
# CALCULATIONS
# ══════════════════════════════════════════════════════════════════════
def calc():
    bv    = g('bidonVol') or 500
    scale = bv / 500
    h     = (g('raceH') or 0) + (g('raceM') or 0) / 60
    carbs = (g('gels')*40 + g('chews')*35 + g('bars')*30
             + g('bidonsKH')*30*scale + g('bidons60')*60*scale)
    fluid = ((g('bidonsKH')+g('bidons60')+g('bidonsW'))*bv + (g('otherDrinks') or 0))
    pre_d  = g('preDrink') or 0
    post_f = g('soda')*330 + g('recup')*500 + (g('waterPost') or 0)
    pee    = (g('peeMl') or 0) if (g('peeMl') or 0) > 0 else g('peeStops')*300
    pre, post = g('preW') or 0, g('postW') or 0
    m0 = (pre  + pre_d/1000)  if pre  > 0 else None
    m1 = (post - post_f/1000) if post > 0 else None
    deficit    = (m0-m1)                       if m0 and m1           else None
    dehyd      = deficit/m0*100                if deficit and m0      else None
    sweat      = deficit+fluid/1000-pee/1000   if deficit is not None else None
    sweat_rate = sweat/h                       if sweat and h > 0     else None
    return dict(bv=bv, scale=scale, h=h, carbs=carbs, fluid=fluid,
                carbs_h=carbs/h if h>0 else None,
                fluid_h=fluid/h if h>0 else None,
                dehyd=dehyd, sweat_rate=sweat_rate)

def fmt(v, dec=0):
    return '—' if v is None else f"{v:,.{dec}f}"

# ══════════════════════════════════════════════════════════════════════
# REPORT
# ══════════════════════════════════════════════════════════════════════
def build_report(c):
    bv  = g('bidonVol') or 500
    c30 = round(30*(bv/500)); c60 = round(60*(bv/500))
    u   = sdata().get('urine')
    L = [
        '🚴 FUELPRO — RIDE LOG', f"Stage {st.session_state.stage}", '',
        '— BEFORE THE START —',
        f"Urine colour (1-8): {u or '—'}",
        f"Weight before: {fmt(g('preW'),1)} kg",
        f"Drink before start: {fmt(g('preDrink'),0)} ml", '',
        '— DURING THE RIDE —',
        f"Gels: {int(g('gels'))}  ({int(g('gels'))*40} g carbs)",
        f"Chews: {int(g('chews'))}  ({int(g('chews'))*35} g carbs)",
        f"Bars: {int(g('bars'))}  ({int(g('bars'))*30} g carbs)",
        f"Bottles 30g·{bv}ml: {int(g('bidonsKH'))}  ({int(g('bidonsKH'))*c30}g carbs · {int(g('bidonsKH'))*bv}ml)",
        f"Bottles 60g·{bv}ml: {int(g('bidons60'))}  ({int(g('bidons60'))*c60}g carbs · {int(g('bidons60'))*bv}ml)",
        f"Bottles water·{bv}ml: {int(g('bidonsW'))}  ({int(g('bidonsW'))*bv}ml)",
        f"Other food: {fmt(g('otherFood'),0)} g",
        f"Other drinks: {fmt(g('otherDrinks'),0)} ml",
        f"Pee stops: {int(g('peeStops'))}",
        f"Pee volume: {fmt(g('peeMl'),0)} ml", '',
        '— AFTER THE RIDE (before weigh-in) —',
        f"Soda (330ml): {int(g('soda'))}  ({int(g('soda'))*330}ml)",
        f"Recovery (500ml): {int(g('recup'))}  ({int(g('recup'))*500}ml)",
        f"Water: {fmt(g('waterPost'),0)} ml", '',
        '— WEIGH-IN AFTER RIDE —',
        f"Weight after: {fmt(g('postW'),1)} kg", '',
        '— RACE TIME —',
        f"Race time: {int(g('raceH'))}h {int(g('raceM'))}min"+(f"  ({fmt(c['h'],2)}h)" if c['h']>0 else ''), '',
        '— CALCULATED —',
        f"Carbs (race): {fmt(c['carbs'],0)} g",
        "Carbs/h: "+("—" if c['carbs_h'] is None else str(round(c['carbs_h']))+" g/h"),
        f"Fluid (race): {fmt(c['fluid']/1000,2)} L",
        "Fluid/h: "+("—" if c['fluid_h'] is None else str(round(c['fluid_h']))+" ml/h"),
        "Dehydration: "+("—" if c['dehyd'] is None else fmt(c['dehyd'],1)+" %"),
        "Sweat rate: "+("—" if c['sweat_rate'] is None else fmt(c['sweat_rate'],2)+" L/h"),
    ]
    return '\n'.join(L)

# ══════════════════════════════════════════════════════════════════════
# UI HELPERS
# ══════════════════════════════════════════════════════════════════════
def section_header(num, title, sub):
    st.markdown(f"""
<div style="background:#fff;border:1px solid #E2DDD1;border-radius:12px;
     box-shadow:0 2px 12px rgba(22,20,15,.07);
     padding:12px 14px;margin:16px 0 10px;
     display:flex;align-items:center;gap:10px;">
  <div style="width:32px;height:32px;border-radius:8px;background:#1E274F;color:#fff;
       display:flex;align-items:center;justify-content:center;
       font-family:'Anton',sans-serif;font-size:16px;flex-shrink:0;">{num}</div>
  <div>
    <div style="font-family:'Anton',sans-serif;font-size:17px;letter-spacing:.4px;
         text-transform:uppercase;color:#16140F;line-height:1.1;">{title}</div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:9px;
         letter-spacing:.12em;text-transform:uppercase;color:#6B6760;margin-top:2px;">{sub}</div>
  </div>
</div>""", unsafe_allow_html=True)

def row_label(label, hint=""):
    h = f"<span style='font-size:11px;color:#6B6760;font-weight:500;margin-left:6px;'>{hint}</span>" if hint else ""
    st.markdown(
        f"<div style='font-family:Hanken Grotesk,sans-serif;font-weight:700;"
        f"font-size:14px;color:#16140F;margin:10px 0 4px;'>{label}{h}</div>",
        unsafe_allow_html=True)

def divider():
    st.markdown("<hr style='border:none;border-top:1px solid #E2DDD1;margin:8px 0;'>",
                unsafe_allow_html=True)

def stepper(label, hint, field, carb_per_unit=0, fluid_per_unit=0):
    """Compact single-row: LABEL · hint  [−] [  N  ] [+]  subtotal"""
    val = int(g(field) or 0)

    # Full-width row: label takes left space, controls take right
    col_label, col_minus, col_val, col_plus = st.columns([3, 1, 1, 1])

    with col_label:
        # Build subtotal string
        parts = []
        if carb_per_unit > 0: parts.append(f"{val*carb_per_unit}g")
        if fluid_per_unit > 0: parts.append(f"{val*fluid_per_unit}ml")
        sub_html = ""
        if parts:
            c = "#2F3C82" if val > 0 else "#9B9790"
            sub_html = f"<span style='color:{c};font-family:JetBrains Mono,monospace;font-size:11px;font-weight:700;margin-left:4px;'>{'·'.join(parts)}</span>"
        hint_html = f"<div style='font-size:11px;color:#6B6760;margin-top:1px;'>{hint}</div>" if hint else ""
        st.markdown(
            f"<div style='padding:6px 0;'>"
            f"<span style='font-family:Hanken Grotesk,sans-serif;font-weight:700;"
            f"font-size:14px;color:#16140F;'>{label}</span>{sub_html}"
            f"{hint_html}</div>",
            unsafe_allow_html=True)

    with col_minus:
        st.markdown('<div class="btn-minus">', unsafe_allow_html=True)
        if st.button("−", key=f"dec_{field}_{st.session_state.stage}"):
            sv(field, max(0, val-1)); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with col_val:
        st.markdown(
            f"<div style='height:56px;background:#fff;border:1.5px solid #E2DDD1;"
            f"border-radius:10px;display:flex;align-items:center;justify-content:center;"
            f"font-family:JetBrains Mono,monospace;font-weight:700;font-size:26px;"
            f"color:#16140F;'>{val}</div>",
            unsafe_allow_html=True)

    with col_plus:
        st.markdown('<div class="btn-plus">', unsafe_allow_html=True)
        if st.button("+", key=f"inc_{field}_{st.session_state.stage}"):
            sv(field, val+1); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    divider()

def num_row(label, hint, field, unit, min_v, max_v, step, fmt_str=None, is_float=False):
    """Compact row: label/hint left, [input][unit] right."""
    val = float(g(field) or 0) if is_float else int(g(field) or 0)
    col_label, col_input, col_unit = st.columns([3, 2, 1])
    with col_label:
        hint_html = f"<div style='font-size:11px;color:#6B6760;margin-top:1px;'>{hint}</div>" if hint else ""
        st.markdown(
            f"<div style='padding:6px 0;'>"
            f"<span style='font-family:Hanken Grotesk,sans-serif;font-weight:700;"
            f"font-size:14px;color:#16140F;'>{label}</span>{hint_html}</div>",
            unsafe_allow_html=True)
    with col_input:
        kwargs = dict(min_value=min_v, max_value=max_v, value=val, step=step,
                      label_visibility="collapsed",
                      key=f"{field}_{st.session_state.stage}")
        if fmt_str: kwargs['format'] = fmt_str
        nv = st.number_input(label, **kwargs)
        sv(field, nv)
    with col_unit:
        st.markdown(
            f"<div style='height:56px;display:flex;align-items:center;justify-content:center;"
            f"font-family:JetBrains Mono,monospace;font-size:13px;font-weight:700;"
            f"color:#4A463C;background:#F0EDE5;border:1.5px solid #E2DDD1;"
            f"border-radius:10px;margin-top:1px;'>{unit}</div>",
            unsafe_allow_html=True)
    divider()

# ══════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="background:
  linear-gradient(157deg,rgba(8,9,24,.45),rgba(8,9,24,0) 58%),
  radial-gradient(120% 80% at 85% 110%,rgba(239,74,59,.55),transparent 60%),
  linear-gradient(157deg,#12122a 0%,#20264f 19%,#43275f 39%,#8a2a5e 57%,#cf2c47 77%,#ef4a3b 100%);
  border-bottom:4px solid #E5343A;margin:0 -10px;">
  <div style="height:5px;background:repeating-linear-gradient(
    135deg,#2F3C82 0 12px,#E5343A 12px 24px);"></div>
  <div style="padding:18px 16px 16px;">
    <div style="font-family:'Anton',sans-serif;font-size:clamp(32px,10vw,48px);
         line-height:.9;text-transform:uppercase;color:#fff;
         text-shadow:0 2px 12px rgba(0,0,0,.3);">
      RIDE<span style="color:#FFD7CF;">·</span>LOG</div>
    <p style="margin:8px 0 0;color:rgba(255,255,255,.75);font-size:12px;
       font-family:'Hanken Grotesk',sans-serif;">
      Fill in after each stage · tap Send when done</p>
  </div>
</div>
<div style="height:6px;"></div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# STAGE PICKER  — pure HTML buttons, all identical size
# ══════════════════════════════════════════════════════════════════════
stage = st.session_state.stage

# Render 8 stage buttons in one tight row using st.columns
# All columns equal width — no HTML tricks needed
st.markdown(
    "<div style='font-family:JetBrains Mono,monospace;font-size:10px;"
    "letter-spacing:.18em;text-transform:uppercase;color:#6B6760;"
    "font-weight:700;margin:0 0 6px 0;'>Stage</div>",
    unsafe_allow_html=True)

stage_cols = st.columns(8)
for i, col in enumerate(stage_cols):
    n = i + 1
    with col:
        sel = (stage == n)
        # Use st.markdown for selected (can't click it anyway) and st.button for unselected
        if sel:
            st.markdown(f"""
<div style="height:44px;background:#2F3C82;color:#fff;
     border:2px solid #1E274F;border-radius:10px;
     display:flex;align-items:center;justify-content:center;
     font-family:'Anton',sans-serif;font-size:18px;
     box-shadow:0 2px 8px rgba(47,60,130,.4);">✓</div>""",
                unsafe_allow_html=True)
        else:
            # Inject CSS just for these to be the right height
            st.markdown("""
<style>
div[data-testid="column"] div.stButton > button {
    height:44px !important;
    font-family:'Anton',sans-serif !important;
    font-size:18px !important;
    border-radius:10px !important;
    padding:0 !important;
}
</style>""", unsafe_allow_html=True)
            if st.button(str(n), key=f"stage_{n}"):
                st.session_state.stage = n
                st.rerun()

st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# SECTION 1 — BEFORE THE START
# ══════════════════════════════════════════════════════════════════════
section_header("1", "Before the Start", "Pre-stage")

# URINE — 8 buttons in a row, the coloured swatch IS the button
# We render each as an st.button whose label is the number,
# then use CSS to make them tall and coloured via a data attribute trick.
# Simplest reliable approach: render the colour as the button background via per-button CSS.

SWATCHES = ['#FFFDE8','#FFFAB6','#F8EF66','#FDE11C','#ECD247','#E4C306','#DAB002','#8C881C']
SWATCH_TEXT = ['#5a5830','#5a5830','#3d3b10','#3d3b10','#3d3b10','#3d3b10','#fff','#fff']

st.markdown("<div style='font-family:Hanken Grotesk,sans-serif;font-weight:700;"
            "font-size:14px;color:#16140F;margin:8px 0 2px;'>Urine colour</div>"
            "<div style='font-size:11px;color:#6B6760;margin-bottom:6px;'>"
            "1 = pale (hydrated) → 8 = dark (dehydrated)</div>",
            unsafe_allow_html=True)

# Inject per-button background colours. Each button gets a unique key we can target.
urine_val = sdata().get('urine')
for i in range(8):
    v   = i + 1
    sel = urine_val == v
    bg  = SWATCHES[i]
    tc  = SWATCH_TEXT[i]
    bdr = "#2F3C82" if sel else "rgba(0,0,0,.08)"
    bw  = "3px" if sel else "1.5px"
    shd = "0 0 0 3px rgba(47,60,130,.25)" if sel else "none"
    lbl = "✓" if sel else str(v)
    st.markdown(f"""
<style>
div[data-testid="column"]:nth-of-type({i+1}) .stButton > button {{
    background:{bg} !important;
    color:{tc} !important;
    border:{bw} solid {bdr} !important;
    box-shadow:{shd} !important;
    height:52px !important;
    font-family:'JetBrains Mono',monospace !important;
    font-size:14px !important;
    font-weight:900 !important;
    border-radius:10px !important;
    transform:{'translateY(-3px)' if sel else 'none'} !important;
}}
</style>""", unsafe_allow_html=True)

u_cols = st.columns(8)
for i, col in enumerate(u_cols):
    v = i + 1
    sel = urine_val == v
    lbl = "✓" if sel else str(v)
    with col:
        if st.button(lbl, key=f"uc_{v}_s{st.session_state.stage}"):
            sdata()['urine'] = v
            st.rerun()

divider()

# Weight & drink
bv  = g('bidonVol') or 500
num_row("Weight before",       "Before the race",    'preW',     "kg", 0.0, 200.0, 0.1, "%.1f", True)
num_row("Drink before start",  "Weigh-in → start",   'preDrink', "ml", 0, 5000, 50)

# ══════════════════════════════════════════════════════════════════════
# SECTION 2 — DURING THE RIDE
# ══════════════════════════════════════════════════════════════════════
section_header("2", "During the Ride", "On the bike")

scale = bv / 500
c30   = round(30*scale)
c60   = round(60*scale)

stepper("Gels",            "40g carbs each",         "gels",     carb_per_unit=40)
stepper("Chews",           "35g carbs each",         "chews",    carb_per_unit=35)
stepper("Bars",            "30g carbs each",         "bars",     carb_per_unit=30)
stepper(f"Bottles 30g",    f"{c30}g carbs · {bv}ml", "bidonsKH", carb_per_unit=c30, fluid_per_unit=bv)
stepper(f"Bottles 60g",    f"{c60}g carbs · {bv}ml", "bidons60", carb_per_unit=c60, fluid_per_unit=bv)
stepper("Bottles water",   f"{bv}ml each",           "bidonsW",  fluid_per_unit=bv)
num_row("Other food",      "Extra food weight",      'otherFood',   "g",  0, 10000, 1)
num_row("Other drinks",    "Extra drinks on bike",   'otherDrinks', "ml", 0, 10000, 50)

with st.expander("⚙️  Bottle & pee settings"):
    num_row("Bottle volume", "", 'bidonVol', "ml", 100, 2000, 50)
    stepper("Pee stops",    "Toilet stops",           "peeStops")
    num_row("Pee volume",   "Optional",               'peeMl', "ml", 0, 5000, 50)

# ══════════════════════════════════════════════════════════════════════
# SECTION 3 — AFTER THE RIDE
# ══════════════════════════════════════════════════════════════════════
section_header("3", "After the Ride", "Before weigh-in")

st.markdown("""
<div style="background:#FFF5F5;border-left:4px solid #E5343A;border-radius:8px;
     padding:10px 12px;margin-bottom:8px;font-size:12px;font-weight:600;color:#6B1A1A;">
  ⚠️ Only log drinks consumed <b>before</b> the post-ride weigh-in.
</div>""", unsafe_allow_html=True)

stepper("Soda",           "330ml each",  "soda",  fluid_per_unit=330)
stepper("Recovery drink", "500ml each",  "recup", fluid_per_unit=500)
num_row("Water",          "After finish",'waterPost', "ml", 0, 5000, 50)

# ══════════════════════════════════════════════════════════════════════
# SECTION 4 — WEIGH-IN AFTER RIDE
# ══════════════════════════════════════════════════════════════════════
section_header("4", "Weigh-In After Ride", "Post weigh-in")
num_row("Weight after", "After the ride", 'postW', "kg", 0.0, 200.0, 0.1, "%.1f", True)

# ══════════════════════════════════════════════════════════════════════
# SECTION 5 — RACE TIME + RESULTS
# calc() called here — all inputs now written to sdata()
# ══════════════════════════════════════════════════════════════════════
section_header("5", "Race Time", "Duration & results")

c1, c2 = st.columns(2)
with c1:
    rh = st.number_input("Hours", min_value=0, max_value=24,
                          value=int(g('raceH') or 0),
                          key=f"raceH_{st.session_state.stage}")
    sv('raceH', rh)
with c2:
    rm = st.number_input("Minutes", min_value=0, max_value=59,
                          value=int(g('raceM') or 0),
                          key=f"raceM_{st.session_state.stage}")
    sv('raceM', rm)

# ── all inputs written → run calc ──
cr = calc()

def dehyd_color(v):
    if v is None: return '#fff'
    if v > 3:     return '#FB7185'
    if v > 2:     return '#FBBF24'
    return '#5BE08A'

def rtile(value, unit, label, color='#fff'):
    return (f"<div style='background:#14132A;border-radius:10px;padding:14px 12px;'>"
            f"<div style='font-family:JetBrains Mono,monospace;font-weight:700;"
            f"font-size:22px;color:{color};line-height:1;'>{value}"
            f"<span style='font-size:11px;font-weight:500;color:rgba(255,255,255,.45);"
            f"margin-left:3px;'>{unit}</span></div>"
            f"<div style='font-size:9px;letter-spacing:.07em;text-transform:uppercase;"
            f"color:rgba(255,255,255,.45);margin-top:6px;font-weight:700;'>{label}</div>"
            f"</div>")

dc      = dehyd_color(cr['dehyd'])
carbs_v = fmt(cr['carbs'],0)
carbs_h = '—' if cr['carbs_h']    is None else str(round(cr['carbs_h']))
fluid_v = fmt(cr['fluid']/1000,2)
fluid_h = '—' if cr['fluid_h']    is None else str(round(cr['fluid_h']))
dehyd_v = '—' if cr['dehyd']      is None else fmt(cr['dehyd'],1)
sweat_v = '—' if cr['sweat_rate'] is None else fmt(cr['sweat_rate'],2)
c_h_u   = '' if cr['carbs_h']    is None else 'g/h'
f_h_u   = '' if cr['fluid_h']    is None else 'ml/h'
d_u     = '' if cr['dehyd']      is None else '%'
s_u     = '' if cr['sweat_rate'] is None else 'L/h'

st.markdown(f"""
<div style="display:grid;grid-template-columns:1fr 1fr;gap:5px;margin-top:12px;">
  {rtile(carbs_v,'g','Carbs · race')}
  {rtile(carbs_h,c_h_u,'Carbs / h')}
  {rtile(fluid_v,'L','Fluid · race')}
  {rtile(fluid_h,f_h_u,'Fluid / h')}
  {rtile(dehyd_v,d_u,'Dehydration',dc)}
  {rtile(sweat_v,s_u,'Sweat rate')}
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# SEND + RESET
# ══════════════════════════════════════════════════════════════════════
st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

report = build_report(cr)
wa_url = "https://wa.me/?text=" + urllib.parse.quote(report)

st.markdown(f"""
<a href="{wa_url}" target="_blank" rel="noopener" style="text-decoration:none;">
  <div style="background:#25D366;color:#063d1c;border-radius:12px;padding:16px;
       text-align:center;font-family:'Hanken Grotesk',sans-serif;font-weight:800;
       font-size:16px;box-shadow:0 4px 12px rgba(37,211,102,.3);margin-bottom:8px;">
    📱 Send via WhatsApp
  </div>
</a>""", unsafe_allow_html=True)

with st.expander("📋 Copy report text"):
    st.text_area("", value=report, height=260,
                 label_visibility="collapsed", key="report_area")

st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
st.caption(f"Stage {st.session_state.stage} · Fill in per stage, then send.")

if st.button(f"🔄 Reset stage {st.session_state.stage}", key="reset"):
    n = st.session_state.stage
    d = {f: field_default(f) for f in STEPPER_FIELDS + FLOAT_FIELDS + INT_FIELDS}
    d['urine'] = None
    st.session_state.stage_data[n] = d
    st.rerun()
