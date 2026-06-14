
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

/* ── hide chrome ── */
header[data-testid="stHeader"],
footer, #MainMenu,
[data-testid="stSidebar"],
[data-testid="collapsedControl"] { display:none !important; }

/* ── page background ── */
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
.main { background:#F4F1EA !important; }

[data-testid="block-container"] {
    max-width: 560px !important;
    padding: 0 16px 40px 16px !important;
}

/* ── typography ── */
body, p, span, label, div {
    font-family: 'Hanken Grotesk', sans-serif !important;
}

/* ── ALL buttons default: chip style ── */
div.stButton > button {
    font-family: 'Hanken Grotesk', sans-serif !important;
    font-weight: 700 !important;
    font-size: 15px !important;
    background: #FBFAF6 !important;
    color: #16140F !important;
    border: 1.5px solid #E2DDD1 !important;
    border-radius: 10px !important;
    width: 100% !important;
    padding: 10px 4px !important;
    transition: 0.12s !important;
}
div.stButton > button:hover {
    background: #F0EDE5 !important;
    border-color: #2F3C82 !important;
}

/* ── number inputs ── */
input[type="number"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700 !important;
    font-size: 20px !important;
    text-align: center !important;
    background: #FBFAF6 !important;
    border: 1.5px solid #E2DDD1 !important;
    border-radius: 10px !important;
    color: #16140F !important;
}
input[type="number"]:focus {
    border-color: #2F3C82 !important;
    box-shadow: 0 0 0 3px rgba(47,60,130,.15) !important;
}

/* ── labels ── */
[data-testid="stWidgetLabel"] p {
    font-family: 'Hanken Grotesk', sans-serif !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    color: #16140F !important;
}

/* ── hide streamlit number input steppers (we make our own) ── */
button[data-testid="stNumberInputStepUp"],
button[data-testid="stNumberInputStepDown"] { display: none !important; }

/* ── section divider ── */
hr { border:none; border-top:1px solid #E2DDD1 !important; margin: 8px 0 !important; }

/* ── expander ── */
[data-testid="stExpander"] {
    background: #fff !important;
    border: 1px solid #E2DDD1 !important;
    border-radius: 12px !important;
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════
STEPPER_FIELDS = [
    'gels','chews','bars','bidonsKH','bidons60','bidonsW',
    'peeStops','soda','recup'
]
FLOAT_FIELDS   = ['preW', 'postW']
INT_FIELDS     = ['preDrink','otherFood','otherDrinks','bidonVol','peeMl','waterPost','raceH','raceM']

def field_default(f):
    if f == 'bidonVol': return 500
    if f in FLOAT_FIELDS: return 0.0
    return 0

if 'stage'      not in st.session_state: st.session_state.stage = 1
if 'stage_data' not in st.session_state: st.session_state.stage_data = {}

def sdata():
    """Return mutable dict for current stage."""
    n = st.session_state.stage
    if n not in st.session_state.stage_data:
        d = {f: field_default(f) for f in STEPPER_FIELDS + FLOAT_FIELDS + INT_FIELDS}
        d['urine'] = None
        st.session_state.stage_data[n] = d
    return st.session_state.stage_data[n]

def g(f):  return sdata().get(f, field_default(f))
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
    fluid = ((g('bidonsKH') + g('bidons60') + g('bidonsW')) * bv
             + (g('otherDrinks') or 0))
    pre_d   = g('preDrink') or 0
    post_f  = g('soda')*330 + g('recup')*500 + (g('waterPost') or 0)
    pee     = (g('peeMl') or 0) if (g('peeMl') or 0) > 0 else g('peeStops') * 300
    pre, post = g('preW') or 0, g('postW') or 0
    m0 = (pre  + pre_d / 1000)  if pre  > 0 else None
    m1 = (post - post_f / 1000) if post > 0 else None
    deficit    = (m0 - m1)                           if m0 and m1        else None
    dehyd      = deficit / m0 * 100                  if deficit and m0   else None
    sweat      = deficit + fluid/1000 - pee/1000     if deficit is not None else None
    sweat_rate = sweat / h                           if sweat and h > 0  else None
    return dict(bv=bv, scale=scale, h=h, carbs=carbs, fluid=fluid,
                carbs_h=carbs/h if h > 0 else None,
                fluid_h=fluid/h if h > 0 else None,
                dehyd=dehyd, sweat_rate=sweat_rate)

def fmt(v, dec=0):
    return '—' if v is None else f"{v:,.{dec}f}"

# ══════════════════════════════════════════════════════════════════════
# REPORT
# ══════════════════════════════════════════════════════════════════════
def build_report():
    c   = calc()
    bv  = g('bidonVol') or 500
    c30 = round(30*(bv/500));  c60 = round(60*(bv/500))
    u   = sdata().get('urine')
    L   = [
        '🚴 FUELPRO — RIDE LOG',
        f"Stage {st.session_state.stage}", '',
        '— BEFORE THE START —',
        f"Urine colour (1-8): {u or '—'}",
        f"Weight before: {fmt(g('preW'),1)} kg",
        f"Drink before start: {fmt(g('preDrink'),0)} ml", '',
        '— DURING THE RIDE —',
        f"Gels: {int(g('gels'))}  ({int(g('gels'))*40} g carbs)",
        f"Chews: {int(g('chews'))}  ({int(g('chews'))*35} g carbs)",
        f"Bars: {int(g('bars'))}  ({int(g('bars'))*30} g carbs)",
        f"Bottles 30g · {bv}ml: {int(g('bidonsKH'))}  ({int(g('bidonsKH'))*c30} g carbs · {int(g('bidonsKH'))*bv} ml)",
        f"Bottles 60g · {bv}ml: {int(g('bidons60'))}  ({int(g('bidons60'))*c60} g carbs · {int(g('bidons60'))*bv} ml)",
        f"Bottles water · {bv}ml: {int(g('bidonsW'))}  ({int(g('bidonsW'))*bv} ml)",
        f"Other food: {fmt(g('otherFood'),0)} g",
        f"Other drinks: {fmt(g('otherDrinks'),0)} ml",
        f"Pee stops: {int(g('peeStops'))}",
        f"Pee volume: {fmt(g('peeMl'),0)} ml", '',
        '— AFTER THE RIDE (before weigh-in) —',
        f"Soda (330ml): {int(g('soda'))}  ({int(g('soda'))*330} ml)",
        f"Recovery (500ml): {int(g('recup'))}  ({int(g('recup'))*500} ml)",
        f"Water: {fmt(g('waterPost'),0)} ml", '',
        '— WEIGH-IN AFTER RIDE —',
        f"Weight after: {fmt(g('postW'),1)} kg", '',
        '— RACE TIME —',
        f"Race time: {int(g('raceH'))}h {int(g('raceM'))}min"
        + (f"  ({fmt(c['h'],2)} h)" if c['h'] > 0 else ''), '',
        '— CALCULATED —',
        f"Carbs (race): {fmt(c['carbs'],0)} g",
        "Carbs/h: " + ("—" if c['carbs_h'] is None else str(round(c['carbs_h'])) + " g/h"),
        f"Fluid (race): {fmt(c['fluid']/1000,2)} L",
        "Fluid/h: " + ("—" if c['fluid_h'] is None else str(round(c['fluid_h'])) + " ml/h"),
        "Dehydration: " + ("—" if c['dehyd'] is None else fmt(c['dehyd'],1) + " %"),
        "Sweat rate: " + ("—" if c['sweat_rate'] is None else fmt(c['sweat_rate'],2) + " L/h"),
    ]
    return '\n'.join(L)

# ══════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════
def section_header(num, title, subtitle):
    st.markdown(f"""
<div style="background:#fff;border:1px solid #E2DDD1;border-radius:14px;
     box-shadow:0 1px 2px rgba(22,20,15,.05),0 4px 16px rgba(22,20,15,.06);
     padding:14px 16px;margin:18px 0 10px 0;
     display:flex;align-items:center;gap:12px;">
  <div style="width:34px;height:34px;border-radius:9px;background:#1E274F;
       color:#fff;display:flex;align-items:center;justify-content:center;
       font-family:'Anton',sans-serif;font-size:17px;flex-shrink:0;">{num}</div>
  <div>
    <div style="font-family:'Anton',sans-serif;font-size:18px;letter-spacing:.5px;
         text-transform:uppercase;color:#16140F;line-height:1.1;">{title}</div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:10px;
         letter-spacing:.12em;text-transform:uppercase;color:#4A463C;
         margin-top:2px;">{subtitle}</div>
  </div>
</div>""", unsafe_allow_html=True)

def row_header(label, hint=""):
    st.markdown(
        f"**{label}**" + (f"  \n<small style='color:#4A463C'>{hint}</small>" if hint else ""),
        unsafe_allow_html=True
    )

def stepper(label, hint, field):
    """A clean −  n  + row using 3 native columns."""
    row_header(label, hint)
    val = int(g(field) or 0)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        if st.button("−", key=f"dec_{field}_{st.session_state.stage}"):
            sv(field, max(0, val - 1)); st.rerun()
    with c2:
        # number_input without the built-in steppers (hidden via CSS)
        nv = st.number_input("_", min_value=0, value=val,
                             label_visibility="collapsed",
                             key=f"inp_{field}_{st.session_state.stage}")
        sv(field, nv)
    with c3:
        if st.button("+", key=f"inc_{field}_{st.session_state.stage}"):
            sv(field, val + 1); st.rerun()
    st.divider()

# ══════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="
  background:linear-gradient(157deg,rgba(8,9,24,.45),rgba(8,9,24,0) 58%),
             radial-gradient(120% 80% at 85% 110%,rgba(239,74,59,.55),transparent 60%),
             linear-gradient(157deg,#12122a 0%,#20264f 19%,#43275f 39%,#8a2a5e 57%,#cf2c47 77%,#ef4a3b 100%);
  border-bottom:5px solid #E5343A;
  border-radius:0 0 0 0;
  margin:0 -16px 0 -16px;
  padding:0;">
  <div style="height:6px;background:repeating-linear-gradient(
    135deg,#2F3C82 0 13px,#E5343A 13px 26px);"></div>
  <div style="padding:24px 20px 20px;">
    <div style="font-family:'Anton',sans-serif;font-size:clamp(34px,10vw,52px);
         line-height:.9;letter-spacing:.5px;text-transform:uppercase;
         color:#fff;text-shadow:0 2px 14px rgba(0,0,0,.3);">
      RIDE<span style="color:#FFD7CF;">·</span>LOG
    </div>
    <p style="margin:12px 0 0;color:rgba(255,255,255,.8);font-size:13px;
         font-family:'Hanken Grotesk',sans-serif;max-width:40ch;">
      Fill in after each stage and tap Send to share your data.
    </p>
  </div>
</div>
<div style="margin-bottom:4px;"></div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# STAGE PICKER
# ══════════════════════════════════════════════════════════════════════
with st.container(border=True):
    st.markdown(
        "<p style='font-family:JetBrains Mono,monospace;font-size:11px;"
        "letter-spacing:.18em;text-transform:uppercase;color:#4A463C;"
        "font-weight:700;margin:0 0 8px 0;'>Stage</p>",
        unsafe_allow_html=True
    )
    cols = st.columns(8)
    for i, col in enumerate(cols):
        n = i + 1
        with col:
            if st.session_state.stage == n:
                # Selected: show coloured block, not a pressable button
                st.markdown(f"""
<div style="background:#2F3C82;color:#fff;border:1.5px solid #1E274F;
     border-radius:10px;height:42px;display:flex;align-items:center;
     justify-content:center;font-family:'Anton',sans-serif;font-size:18px;
     box-shadow:0 3px 10px rgba(47,60,130,.35);">{n}</div>""",
                    unsafe_allow_html=True)
            else:
                if st.button(str(n), key=f"stage_{n}"):
                    st.session_state.stage = n
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════
# SECTION 1 — BEFORE THE START
# ══════════════════════════════════════════════════════════════════════
section_header("1", "Before the Start", "Pre-stage")

# Urine colour — 8 tap buttons, coloured via markdown label trick
SWATCHES = ['#FFFDE8','#FFFAB6','#F8EF66','#FDE11C','#ECD247','#E4C306','#DAB002','#8C881C']
st.markdown("**Urine colour**  \n<small style='color:#4A463C'>1 = pale (hydrated) → 8 = dark (dehydrated)</small>",
            unsafe_allow_html=True)

ucols = st.columns(8)
for i, col in enumerate(ucols):
    v = i + 1
    sel = sdata().get('urine') == v
    with col:
        # Coloured swatch as button label via markdown above the button
        border = "2.5px solid #2F3C82" if sel else "2px solid rgba(0,0,0,.08)"
        shadow = "0 0 0 3px rgba(47,60,130,.2)" if sel else "none"
        lift   = "translateY(-3px)" if sel else "none"
        tick   = "✓" if sel else str(v)
        t_bg   = "#2F3C82" if sel else "rgba(255,255,255,.7)"
        t_col  = "#fff" if sel else "#2b2a14"
        t_rad  = "50%" if sel else "5px"
        st.markdown(f"""
<div style="height:60px;border-radius:9px;background:{SWATCHES[i]};
     border:{border};box-shadow:{shadow};transform:{lift};
     display:flex;align-items:flex-end;justify-content:center;
     margin-bottom:2px;transition:.12s;">
  <span style="font-family:'JetBrains Mono',monospace;font-weight:700;
       font-size:11px;color:{t_col};background:{t_bg};
       border-radius:{t_rad};width:17px;height:17px;
       display:inline-flex;align-items:center;justify-content:center;
       margin-bottom:4px;">{tick}</span>
</div>""", unsafe_allow_html=True)
        # Invisible label button to capture tap
        if st.button(str(v), key=f"uc_{v}_s{st.session_state.stage}",
                     help=f"Shade {v}"):
            sdata()['urine'] = v
            st.rerun()

st.divider()

c1, c2 = st.columns([3, 1])
with c1:
    row_header("Weight before", "At the weigh-in, before the race")
    pre_w = st.number_input("Weight before", min_value=0.0, max_value=200.0,
                             value=float(g('preW') or 0), step=0.1, format="%.1f",
                             label_visibility="collapsed",
                             key=f"preW_{st.session_state.stage}")
    sv('preW', pre_w)
with c2:
    st.markdown("<div style='padding-top:28px;color:#4A463C;font-family:JetBrains Mono,monospace;font-size:13px;'>kg</div>",
                unsafe_allow_html=True)

st.divider()

c1, c2 = st.columns([3, 1])
with c1:
    row_header("Drink before the start", "Between weigh-in and the start")
    pre_drink = st.number_input("Drink before", min_value=0, max_value=5000,
                                 value=int(g('preDrink') or 0), step=50,
                                 label_visibility="collapsed",
                                 key=f"preDrink_{st.session_state.stage}")
    sv('preDrink', pre_drink)
with c2:
    st.markdown("<div style='padding-top:28px;color:#4A463C;font-family:JetBrains Mono,monospace;font-size:13px;'>ml</div>",
                unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# SECTION 2 — DURING THE RIDE
# ══════════════════════════════════════════════════════════════════════
section_header("2", "During the Ride", "On the bike")

c_now  = calc()
h30    = f"{round(30*c_now['scale'])} g carbs at {int(c_now['bv'])} ml"
h60    = f"{round(60*c_now['scale'])} g carbs at {int(c_now['bv'])} ml"

stepper("Gels",            "45 g · 40 g carbs",  "gels")
stepper("Chews",           "44 g · 35 g carbs",  "chews")
stepper("Bars",            "35 g · 30 g carbs",  "bars")
stepper("Bottles · 30 g",  h30,                   "bidonsKH")
stepper("Bottles · 60 g",  h60,                   "bidons60")
stepper("Bottles · water", "water only",           "bidonsW")

c1, c2 = st.columns([3, 1])
with c1:
    row_header("Other food", "Total weight of any extra food")
    of = st.number_input("Other food", min_value=0, max_value=10000,
                          value=int(g('otherFood') or 0), step=1,
                          label_visibility="collapsed",
                          key=f"otherFood_{st.session_state.stage}")
    sv('otherFood', of)
with c2:
    st.markdown("<div style='padding-top:28px;color:#4A463C;font-family:JetBrains Mono,monospace;font-size:13px;'>g</div>",
                unsafe_allow_html=True)

st.divider()

c1, c2 = st.columns([3, 1])
with c1:
    row_header("Other drinks", "Any extra drinks on the bike")
    od = st.number_input("Other drinks", min_value=0, max_value=10000,
                          value=int(g('otherDrinks') or 0), step=50,
                          label_visibility="collapsed",
                          key=f"otherDrinks_{st.session_state.stage}")
    sv('otherDrinks', od)
with c2:
    st.markdown("<div style='padding-top:28px;color:#4A463C;font-family:JetBrains Mono,monospace;font-size:13px;'>ml</div>",
                unsafe_allow_html=True)

st.divider()

# Trackbox
with st.expander("⚙️  Bottle & pee settings"):
    c1, c2 = st.columns([3, 1])
    with c1:
        row_header("Volume per bottle")
        bv_val = st.number_input("Bottle vol", min_value=100, max_value=2000,
                                  value=int(g('bidonVol') or 500), step=50,
                                  label_visibility="collapsed",
                                  key=f"bidonVol_{st.session_state.stage}")
        sv('bidonVol', bv_val)
    with c2:
        st.markdown("<div style='padding-top:28px;color:#4A463C;font-family:JetBrains Mono,monospace;font-size:13px;'>ml</div>",
                    unsafe_allow_html=True)

    st.divider()
    stepper("Pee stops", "Number of toilet stops", "peeStops")

    c1, c2 = st.columns([3, 1])
    with c1:
        row_header("Pee volume", "Optional — if measured")
        pee = st.number_input("Pee vol", min_value=0, max_value=5000,
                               value=int(g('peeMl') or 0), step=50,
                               label_visibility="collapsed",
                               key=f"peeMl_{st.session_state.stage}")
        sv('peeMl', pee)
    with c2:
        st.markdown("<div style='padding-top:28px;color:#4A463C;font-family:JetBrains Mono,monospace;font-size:13px;'>ml</div>",
                    unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# SECTION 3 — AFTER THE RIDE
# ══════════════════════════════════════════════════════════════════════
section_header("3", "After the Ride", "Before weigh-in")

st.info("⚠️  Only log drinks consumed **before** the post-ride weigh-in.", icon=None)

stepper("Soda",           "330 ml each", "soda")
stepper("Recovery drink", "500 ml each", "recup")

c1, c2 = st.columns([3, 1])
with c1:
    row_header("Water", "Loose water after the finish")
    wp = st.number_input("Water post", min_value=0, max_value=5000,
                          value=int(g('waterPost') or 0), step=50,
                          label_visibility="collapsed",
                          key=f"waterPost_{st.session_state.stage}")
    sv('waterPost', wp)
with c2:
    st.markdown("<div style='padding-top:28px;color:#4A463C;font-family:JetBrains Mono,monospace;font-size:13px;'>ml</div>",
                unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# SECTION 4 — WEIGH-IN AFTER RIDE
# ══════════════════════════════════════════════════════════════════════
section_header("4", "Weigh-In After Ride", "Post weigh-in")

c1, c2 = st.columns([3, 1])
with c1:
    row_header("Weight after", "At the weigh-in after the ride")
    post_w = st.number_input("Weight after", min_value=0.0, max_value=200.0,
                              value=float(g('postW') or 0), step=0.1, format="%.1f",
                              label_visibility="collapsed",
                              key=f"postW_{st.session_state.stage}")
    sv('postW', post_w)
with c2:
    st.markdown("<div style='padding-top:28px;color:#4A463C;font-family:JetBrains Mono,monospace;font-size:13px;'>kg</div>",
                unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# SECTION 5 — RACE TIME + LIVE RESULTS
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

# Results grid
cr = calc()

def dehyd_color(v):
    if v is None:    return '#fff'
    if v > 3:        return '#FB7185'
    if v > 2:        return '#FBBF24'
    return '#5BE08A'

dc = dehyd_color(cr['dehyd'])

def result_tile(value, unit, label, color='#fff'):
    return f"""
<div style="background:#14132A;border-radius:10px;padding:14px 12px;">
  <div style="font-family:'JetBrains Mono',monospace;font-weight:700;
       font-size:22px;color:{color};line-height:1;">
    {value}<span style="font-size:11px;font-weight:500;
    color:rgba(255,255,255,.5);margin-left:2px;">{unit}</span>
  </div>
  <div style="font-size:10px;letter-spacing:.07em;text-transform:uppercase;
       color:rgba(255,255,255,.55);margin-top:6px;font-weight:600;">{label}</div>
</div>"""

carbs_v = fmt(cr['carbs'], 0)
carbs_h = '—' if cr['carbs_h']   is None else str(round(cr['carbs_h']))
fluid_v = fmt(cr['fluid']/1000, 2)
fluid_h = '—' if cr['fluid_h']   is None else str(round(cr['fluid_h']))
dehyd_v = '—' if cr['dehyd']     is None else fmt(cr['dehyd'], 1)
sweat_v = '—' if cr['sweat_rate'] is None else fmt(cr['sweat_rate'], 2)
c_h_u   = '' if cr['carbs_h']    is None else 'g/h'
f_h_u   = '' if cr['fluid_h']    is None else 'ml/h'
d_u     = '' if cr['dehyd']      is None else '%'
s_u     = '' if cr['sweat_rate'] is None else 'L/h'

st.markdown(f"""
<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:12px;">
  {result_tile(carbs_v, 'g',    'Carbs · race')}
  {result_tile(carbs_h, c_h_u, 'Carbs / h')}
  {result_tile(fluid_v, 'L',   'Fluid · race')}
  {result_tile(fluid_h, f_h_u, 'Fluid / h')}
  {result_tile(dehyd_v, d_u,   'Dehydration', dc)}
  {result_tile(sweat_v, s_u,   'Sweat rate')}
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# SEND + RESET
# ══════════════════════════════════════════════════════════════════════
st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)

report  = build_report()
wa_url  = "https://wa.me/?text=" + urllib.parse.quote(report)

# WhatsApp as a proper anchor — works natively on mobile
st.markdown(f"""
<a href="{wa_url}" target="_blank" rel="noopener" style="text-decoration:none;">
  <div style="background:#25D366;color:#063d1c;border-radius:14px;
       padding:16px;text-align:center;font-family:'Hanken Grotesk',sans-serif;
       font-weight:800;font-size:16px;box-shadow:0 4px 14px rgba(37,211,102,.3);
       margin-bottom:10px;">
    📱 Send via WhatsApp
  </div>
</a>""", unsafe_allow_html=True)

with st.expander("📋 Copy report text"):
    st.text_area("", value=report, height=280, label_visibility="collapsed",
                 key="report_area")

st.markdown("<div style='margin-top:6px;'></div>", unsafe_allow_html=True)
st.caption(f"Fill in per stage, then send.")

if st.button(f"🔄 Reset stage {st.session_state.stage}", key="reset"):
    n = st.session_state.stage
    d = {f: field_default(f) for f in STEPPER_FIELDS + FLOAT_FIELDS + INT_FIELDS}
    d['urine'] = None
    st.session_state.stage_data[n] = d
    st.rerun()
