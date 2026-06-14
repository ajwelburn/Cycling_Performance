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

header[data-testid="stHeader"],
footer, #MainMenu,
[data-testid="stSidebar"],
[data-testid="collapsedControl"] { display:none !important; }

[data-testid="stAppViewContainer"],
[data-testid="stMain"],
.main { background:#F4F1EA !important; }

[data-testid="block-container"] {
    max-width: 560px !important;
    padding: 0 12px 60px 12px !important;
}

/* ── all buttons base ── */
div.stButton > button {
    font-family: 'Hanken Grotesk', sans-serif !important;
    font-weight: 700 !important;
    background: #FBFAF6 !important;
    color: #16140F !important;
    border: 1.5px solid #E2DDD1 !important;
    border-radius: 10px !important;
    width: 100% !important;
    transition: 0.12s !important;
}
div.stButton > button:hover { background:#F0EDE5 !important; border-color:#2F3C82 !important; }
div.stButton > button:active { transform:scale(0.96) !important; }

/* ── stage chips ── */
.stage-col div.stButton > button {
    height: 52px !important;
    font-family: 'Anton', sans-serif !important;
    font-size: 20px !important;
    padding: 0 !important;
    border-radius: 10px !important;
}

/* ── stepper minus ── */
.stepper-minus div.stButton > button {
    height: 64px !important;
    font-size: 34px !important;
    font-weight: 900 !important;
    padding: 0 !important;
    border-radius: 12px !important;
    line-height: 1 !important;
    background: #FFF0F0 !important;
    color: #C0392B !important;
    border-color: #F5C6C6 !important;
}
/* ── stepper plus ── */
.stepper-plus div.stButton > button {
    height: 64px !important;
    font-size: 34px !important;
    font-weight: 900 !important;
    padding: 0 !important;
    border-radius: 12px !important;
    line-height: 1 !important;
    background: #F0F4FF !important;
    color: #2F3C82 !important;
    border-color: #C6CEEF !important;
}

/* ── number inputs ── */
input[type="number"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700 !important;
    font-size: 22px !important;
    text-align: center !important;
    background: #FBFAF6 !important;
    border: 1.5px solid #E2DDD1 !important;
    border-radius: 10px !important;
    color: #16140F !important;
    height: 56px !important;
}
input[type="number"]:focus {
    border-color: #2F3C82 !important;
    box-shadow: 0 0 0 3px rgba(47,60,130,.15) !important;
    background: #fff !important;
}
button[data-testid="stNumberInputStepUp"],
button[data-testid="stNumberInputStepDown"] { display:none !important; }

[data-testid="stWidgetLabel"] p {
    font-family: 'Hanken Grotesk', sans-serif !important;
    font-weight: 600 !important; font-size: 15px !important; color: #16140F !important;
}

/* ── urine buttons invisible overlay ── */
.urine-btn div.stButton > button {
    height: 2px !important; min-height: 2px !important;
    padding: 0 !important; background: transparent !important;
    border: none !important; opacity: 0 !important;
    margin-top: -2px !important;
}

hr { border:none; border-top:1px solid #E2DDD1 !important; margin:10px 0 !important; }

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

def g(f):      return sdata().get(f, field_default(f))
def sv(f, v):  sdata()[f] = v

# ══════════════════════════════════════════════════════════════════════
# CALCULATIONS  — called ONCE after all inputs are rendered
# ══════════════════════════════════════════════════════════════════════
def calc():
    bv    = g('bidonVol') or 500
    scale = bv / 500
    h     = (g('raceH') or 0) + (g('raceM') or 0) / 60
    carbs = (g('gels')*40 + g('chews')*35 + g('bars')*30
             + g('bidonsKH')*30*scale + g('bidons60')*60*scale)
    fluid = ((g('bidonsKH') + g('bidons60') + g('bidonsW')) * bv
             + (g('otherDrinks') or 0))
    pre_d  = g('preDrink') or 0
    post_f = g('soda')*330 + g('recup')*500 + (g('waterPost') or 0)
    pee    = (g('peeMl') or 0) if (g('peeMl') or 0) > 0 else g('peeStops') * 300
    pre, post = g('preW') or 0, g('postW') or 0
    m0 = (pre  + pre_d/1000)  if pre  > 0 else None
    m1 = (post - post_f/1000) if post > 0 else None
    deficit    = (m0 - m1)                        if m0 and m1           else None
    dehyd      = deficit / m0 * 100               if deficit and m0      else None
    sweat      = deficit + fluid/1000 - pee/1000  if deficit is not None else None
    sweat_rate = sweat / h                        if sweat and h > 0     else None
    return dict(bv=bv, scale=scale, h=h, carbs=carbs, fluid=fluid,
                carbs_h=carbs/h if h > 0 else None,
                fluid_h=fluid/h if h > 0 else None,
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
# UI HELPERS
# ══════════════════════════════════════════════════════════════════════
def section_header(num, title, subtitle):
    st.markdown(f"""
<div style="background:#fff;border:1px solid #E2DDD1;border-radius:14px;
     box-shadow:0 1px 2px rgba(22,20,15,.05),0 4px 16px rgba(22,20,15,.06);
     padding:14px 16px;margin:20px 0 14px 0;display:flex;align-items:center;gap:12px;">
  <div style="width:36px;height:36px;border-radius:9px;background:#1E274F;color:#fff;
       display:flex;align-items:center;justify-content:center;
       font-family:'Anton',sans-serif;font-size:18px;flex-shrink:0;">{num}</div>
  <div>
    <div style="font-family:'Anton',sans-serif;font-size:19px;letter-spacing:.5px;
         text-transform:uppercase;color:#16140F;line-height:1.1;">{title}</div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:.12em;
         text-transform:uppercase;color:#4A463C;margin-top:3px;">{subtitle}</div>
  </div>
</div>""", unsafe_allow_html=True)

def row_label(label, hint=""):
    hint_html = (f"<div style='font-size:12px;color:#6B6760;font-weight:500;"
                 f"margin-top:1px;'>{hint}</div>") if hint else ""
    st.markdown(
        f"<div style='font-family:Hanken Grotesk,sans-serif;font-weight:700;"
        f"font-size:16px;color:#16140F;margin-bottom:6px;'>{label}{hint_html}</div>",
        unsafe_allow_html=True)

def stepper(label, hint, field, carb_per_unit=0, fluid_per_unit=0, bv=500):
    """
    Large  −  VALUE  +  row with a live sub-total pill below.
    carb_per_unit / fluid_per_unit are used to show the running contribution.
    """
    row_label(label, hint)
    val = int(g(field) or 0)

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        st.markdown('<div class="stepper-minus">', unsafe_allow_html=True)
        if st.button("−", key=f"dec_{field}_{st.session_state.stage}"):
            sv(field, max(0, val - 1))
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        # Big centred value display
        st.markdown(f"""
<div style="height:64px;background:#fff;border:1.5px solid #E2DDD1;border-radius:12px;
     display:flex;align-items:center;justify-content:center;
     font-family:'JetBrains Mono',monospace;font-weight:700;font-size:32px;
     color:#16140F;">{val}</div>""", unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="stepper-plus">', unsafe_allow_html=True)
        if st.button("+", key=f"inc_{field}_{st.session_state.stage}"):
            sv(field, val + 1)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Running sub-total pill — shows contribution of this item
    parts = []
    if carb_per_unit > 0:
        total_carbs = round(val * carb_per_unit)
        parts.append(f"<b>{total_carbs} g carbs</b>")
    if fluid_per_unit > 0:
        total_ml = val * fluid_per_unit
        parts.append(f"{total_ml} ml")
    if parts:
        pill_color = "#E8F0FF" if val > 0 else "#F4F1EA"
        text_color = "#2F3C82" if val > 0 else "#9B9790"
        st.markdown(
            f"<div style='margin-top:6px;padding:5px 12px;border-radius:20px;"
            f"background:{pill_color};display:inline-block;"
            f"font-family:JetBrains Mono,monospace;font-size:12px;"
            f"font-weight:600;color:{text_color};'>"
            f"{'  ·  '.join(parts)}</div>",
            unsafe_allow_html=True)

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
    st.markdown('<hr>', unsafe_allow_html=True)

def num_input_with_unit(label, hint, field, unit, min_v, max_v, step,
                        fmt_str=None, is_float=False):
    row_label(label, hint)
    val = float(g(field) or 0) if is_float else int(g(field) or 0)
    c1, c2 = st.columns([5, 1])
    with c1:
        kwargs = dict(min_value=min_v, max_value=max_v, value=val, step=step,
                      label_visibility="collapsed",
                      key=f"{field}_{st.session_state.stage}")
        if fmt_str:
            kwargs['format'] = fmt_str
        nv = st.number_input(label, **kwargs)
        sv(field, nv)
    with c2:
        st.markdown(
            f"<div style='height:56px;display:flex;align-items:center;"
            f"justify-content:center;font-family:JetBrains Mono,monospace;"
            f"font-size:14px;font-weight:700;color:#4A463C;background:#F0EDE5;"
            f"border:1.5px solid #E2DDD1;border-radius:10px;'>{unit}</div>",
            unsafe_allow_html=True)
    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
    st.markdown('<hr>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="
  background:
    linear-gradient(157deg,rgba(8,9,24,.45),rgba(8,9,24,0) 58%),
    radial-gradient(120% 80% at 85% 110%,rgba(239,74,59,.55),transparent 60%),
    linear-gradient(157deg,#12122a 0%,#20264f 19%,#43275f 39%,#8a2a5e 57%,#cf2c47 77%,#ef4a3b 100%);
  border-bottom:5px solid #E5343A;
  margin:0 -12px 0 -12px;">
  <div style="height:6px;background:repeating-linear-gradient(
    135deg,#2F3C82 0 13px,#E5343A 13px 26px);"></div>
  <div style="padding:22px 20px 20px;">
    <div style="font-family:'Anton',sans-serif;font-size:clamp(36px,11vw,54px);
         line-height:.9;letter-spacing:.5px;text-transform:uppercase;
         color:#fff;text-shadow:0 2px 14px rgba(0,0,0,.3);">
      RIDE<span style="color:#FFD7CF;">·</span>LOG
    </div>
    <p style="margin:10px 0 0;color:rgba(255,255,255,.8);font-size:13px;
         font-family:'Hanken Grotesk',sans-serif;">
      Fill in after each stage and tap Send to share your data.
    </p>
  </div>
</div>
<div style="height:4px;"></div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# STAGE PICKER
# ══════════════════════════════════════════════════════════════════════
with st.container(border=True):
    st.markdown(
        "<p style='font-family:JetBrains Mono,monospace;font-size:11px;"
        "letter-spacing:.18em;text-transform:uppercase;color:#4A463C;"
        "font-weight:700;margin:0 0 10px 0;'>Stage</p>",
        unsafe_allow_html=True)
    cols = st.columns(8)
    for i, col in enumerate(cols):
        n = i + 1
        with col:
            if st.session_state.stage == n:
                st.markdown(f"""
<div style="height:52px;background:#2F3C82;color:#fff;
     border:1.5px solid #1E274F;border-radius:10px;
     display:flex;align-items:center;justify-content:center;
     font-family:'Anton',sans-serif;font-size:20px;
     box-shadow:0 3px 10px rgba(47,60,130,.4);">{n}</div>""",
                    unsafe_allow_html=True)
            else:
                st.markdown('<div class="stage-col">', unsafe_allow_html=True)
                if st.button(str(n), key=f"stage_{n}"):
                    st.session_state.stage = n
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# READ bottle volume NOW so hints are correct throughout the form
# ══════════════════════════════════════════════════════════════════════
bv    = g('bidonVol') or 500
scale = bv / 500
c30   = round(30 * scale)
c60   = round(60 * scale)

# ══════════════════════════════════════════════════════════════════════
# SECTION 1 — BEFORE THE START
# ══════════════════════════════════════════════════════════════════════
section_header("1", "Before the Start", "Pre-stage")

SWATCHES = ['#FFFDE8','#FFFAB6','#F8EF66','#FDE11C','#ECD247','#E4C306','#DAB002','#8C881C']
row_label("Urine colour", "1 = pale (well hydrated) → 8 = dark (dehydrated)")

ucols = st.columns(8)
for i, col in enumerate(ucols):
    v   = i + 1
    sel = sdata().get('urine') == v
    border = "2.5px solid #2F3C82" if sel else "2px solid rgba(0,0,0,.09)"
    shadow = "0 0 0 3px rgba(47,60,130,.22)" if sel else "none"
    lift   = "translateY(-4px)" if sel else "none"
    tick   = "✓" if sel else str(v)
    t_bg   = "#2F3C82" if sel else "rgba(255,255,255,.75)"
    t_col  = "#fff"    if sel else "#2b2a14"
    t_rad  = "50%"     if sel else "5px"
    with col:
        st.markdown(f"""
<div style="height:62px;border-radius:10px;background:{SWATCHES[i]};
     border:{border};box-shadow:{shadow};transform:{lift};
     display:flex;align-items:flex-end;justify-content:center;
     transition:.12s;cursor:pointer;">
  <span style="font-family:'JetBrains Mono',monospace;font-weight:700;font-size:11px;
       color:{t_col};background:{t_bg};border-radius:{t_rad};
       width:18px;height:18px;display:inline-flex;align-items:center;
       justify-content:center;margin-bottom:5px;">{tick}</span>
</div>""", unsafe_allow_html=True)
        st.markdown('<div class="urine-btn">', unsafe_allow_html=True)
        if st.button(f"{v}", key=f"uc_{v}_s{st.session_state.stage}"):
            sdata()['urine'] = v
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
st.markdown('<hr>', unsafe_allow_html=True)

num_input_with_unit("Weight before", "At the weigh-in, before the race",
                    'preW', "kg", 0.0, 200.0, 0.1, "%.1f", is_float=True)
num_input_with_unit("Drink before the start", "Between weigh-in and the start",
                    'preDrink', "ml", 0, 5000, 50)

# ══════════════════════════════════════════════════════════════════════
# SECTION 2 — DURING THE RIDE
# ══════════════════════════════════════════════════════════════════════
section_header("2", "During the Ride", "On the bike")

stepper("Gels",            "45 g · 40 g carbs",
        "gels",      carb_per_unit=40)
stepper("Chews",           "44 g · 35 g carbs",
        "chews",     carb_per_unit=35)
stepper("Bars",            "35 g · 30 g carbs",
        "bars",      carb_per_unit=30)
stepper(f"Bottles · 30 g", f"{c30} g carbs at {bv} ml",
        "bidonsKH",  carb_per_unit=c30, fluid_per_unit=bv, bv=bv)
stepper(f"Bottles · 60 g", f"{c60} g carbs at {bv} ml",
        "bidons60",  carb_per_unit=c60, fluid_per_unit=bv, bv=bv)
stepper("Bottles · water", "water only",
        "bidonsW",   fluid_per_unit=bv, bv=bv)

num_input_with_unit("Other food",   "Total weight of any extra food", 'otherFood',   "g",  0, 10000, 1)
num_input_with_unit("Other drinks", "Any extra drinks on the bike",   'otherDrinks', "ml", 0, 10000, 50)

with st.expander("⚙️  Bottle volume & pee settings"):
    num_input_with_unit("Volume per bottle", "Default 500 ml", 'bidonVol', "ml", 100, 2000, 50)
    stepper("Pee stops", "Number of toilet stops", "peeStops")
    num_input_with_unit("Pee volume", "Optional — if measured", 'peeMl', "ml", 0, 5000, 50)

# ══════════════════════════════════════════════════════════════════════
# SECTION 3 — AFTER THE RIDE
# ══════════════════════════════════════════════════════════════════════
section_header("3", "After the Ride", "Before weigh-in")

st.markdown("""
<div style="background:#FFF5F5;border:1px solid #F5C6C6;border-left:4px solid #E5343A;
     border-radius:10px;padding:12px 14px;margin-bottom:14px;
     font-family:'Hanken Grotesk',sans-serif;font-size:13px;font-weight:600;color:#6B1A1A;">
  ⚠️  Only log drinks consumed <strong>before</strong> the post-ride weigh-in.
</div>""", unsafe_allow_html=True)

stepper("Soda",           "330 ml each", "soda",  fluid_per_unit=330)
stepper("Recovery drink", "500 ml each", "recup", fluid_per_unit=500)
num_input_with_unit("Water", "Loose water after the finish", 'waterPost', "ml", 0, 5000, 50)

# ══════════════════════════════════════════════════════════════════════
# SECTION 4 — WEIGH-IN AFTER RIDE
# ══════════════════════════════════════════════════════════════════════
section_header("4", "Weigh-In After Ride", "Post weigh-in")
num_input_with_unit("Weight after", "At the weigh-in after the ride",
                    'postW', "kg", 0.0, 200.0, 0.1, "%.1f", is_float=True)

# ══════════════════════════════════════════════════════════════════════
# SECTION 5 — RACE TIME + LIVE RESULTS
# All inputs have now been written to sdata() — calc() reads final values
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

# ── calc() called here — after every input has been written to sdata() ──
cr = calc()

def dehyd_color(v):
    if v is None: return '#fff'
    if v > 3:     return '#FB7185'
    if v > 2:     return '#FBBF24'
    return '#5BE08A'

dc = dehyd_color(cr['dehyd'])

def result_tile(value, unit, label, color='#fff'):
    return (f"<div style='background:#14132A;border-radius:10px;padding:16px 14px;'>"
            f"<div style='font-family:JetBrains Mono,monospace;font-weight:700;"
            f"font-size:24px;color:{color};line-height:1;'>{value}"
            f"<span style='font-size:12px;font-weight:500;color:rgba(255,255,255,.5);"
            f"margin-left:3px;'>{unit}</span></div>"
            f"<div style='font-size:10px;letter-spacing:.07em;text-transform:uppercase;"
            f"color:rgba(255,255,255,.5);margin-top:8px;font-weight:600;'>{label}</div>"
            f"</div>")

carbs_v = fmt(cr['carbs'], 0)
carbs_h = '—' if cr['carbs_h']    is None else str(round(cr['carbs_h']))
fluid_v = fmt(cr['fluid']/1000, 2)
fluid_h = '—' if cr['fluid_h']    is None else str(round(cr['fluid_h']))
dehyd_v = '—' if cr['dehyd']      is None else fmt(cr['dehyd'], 1)
sweat_v = '—' if cr['sweat_rate'] is None else fmt(cr['sweat_rate'], 2)
c_h_u   = '' if cr['carbs_h']    is None else 'g/h'
f_h_u   = '' if cr['fluid_h']    is None else 'ml/h'
d_u     = '' if cr['dehyd']      is None else '%'
s_u     = '' if cr['sweat_rate'] is None else 'L/h'

st.markdown(f"""
<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:14px;">
  {result_tile(carbs_v,'g','Carbs · race')}
  {result_tile(carbs_h,c_h_u,'Carbs / h')}
  {result_tile(fluid_v,'L','Fluid · race')}
  {result_tile(fluid_h,f_h_u,'Fluid / h')}
  {result_tile(dehyd_v,d_u,'Dehydration',dc)}
  {result_tile(sweat_v,s_u,'Sweat rate')}
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# SEND + RESET
# ══════════════════════════════════════════════════════════════════════
st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)

report = build_report(cr)
wa_url = "https://wa.me/?text=" + urllib.parse.quote(report)

st.markdown(f"""
<a href="{wa_url}" target="_blank" rel="noopener" style="text-decoration:none;">
  <div style="background:#25D366;color:#063d1c;border-radius:14px;padding:18px;
       text-align:center;font-family:'Hanken Grotesk',sans-serif;font-weight:800;
       font-size:17px;box-shadow:0 4px 14px rgba(37,211,102,.3);margin-bottom:10px;">
    📱 Send via WhatsApp
  </div>
</a>""", unsafe_allow_html=True)

with st.expander("📋 Copy report text"):
    st.text_area("", value=report, height=280,
                 label_visibility="collapsed", key="report_area")

st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
st.caption(f"Stage {st.session_state.stage} · Fill in per stage, then send.")

if st.button(f"🔄 Reset stage {st.session_state.stage}", key="reset"):
    n = st.session_state.stage
    d = {f: field_default(f) for f in STEPPER_FIELDS + FLOAT_FIELDS + INT_FIELDS}
    d['urine'] = None
    st.session_state.stage_data[n] = d
    st.rerun()
