import streamlit as st

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FuelPro · Ride Log",
    page_icon="🚴",
    layout="centered",
)

# ── Global CSS — exact colour/font tokens from the original HTML ─────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Anton&family=Hanken+Grotesk:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

/* ---------- design tokens ---------- */
:root {
  --paper:     #F4F1EA;
  --card:      #FFFFFF;
  --ink:       #16140F;
  --ink-soft:  #4A463C;
  --line:      #E2DDD1;
  --accent:    #E5343A;
  --accent-ink:#B11F26;
  --blue:      #2F3C82;
  --blue-deep: #1E274F;
  --navy:      #14132A;
  --good:      #1E7A4E;
  --radius:    16px;
  --shadow:    0 1px 2px rgba(22,20,15,.05), 0 8px 24px rgba(22,20,15,.07);
}

/* ---------- global resets ---------- */
html, body, [data-testid="stAppViewContainer"],
[data-testid="stMain"], [data-testid="block-container"] {
  background: var(--paper) !important;
  background-image: radial-gradient(rgba(22,20,15,.035) 1px, transparent 1px) !important;
  background-size: 18px 18px !important;
  font-family: 'Hanken Grotesk', system-ui, sans-serif !important;
  color: var(--ink) !important;
}
[data-testid="stSidebar"] { display: none; }
header[data-testid="stHeader"] { display: none; }
#MainMenu { display: none; }
footer { display: none; }
[data-testid="block-container"] {
  padding: 0 !important;
  max-width: 560px !important;
  margin: 0 auto !important;
}

/* ---------- hero header ---------- */
.fp-header {
  color: #fff;
  border-bottom: 5px solid var(--accent);
  background:
    linear-gradient(157deg, rgba(8,9,24,.45), rgba(8,9,24,0) 58%),
    radial-gradient(120% 80% at 85% 110%, rgba(239,74,59,.55), transparent 60%),
    linear-gradient(157deg,#12122a 0%,#20264f 19%,#43275f 39%,#8a2a5e 57%,#cf2c47 77%,#ef4a3b 100%);
  padding: 0 0 0 0;
  position: relative;
  overflow: hidden;
}
.fp-stripe {
  height: 6px;
  background: repeating-linear-gradient(135deg,var(--blue) 0 13px,var(--accent) 13px 26px);
}
.fp-header-inner {
  padding: 26px 20px 24px;
  display: flex;
  align-items: center;
  gap: 15px;
}
.fp-badge {
  width: 62px;
  height: 62px;
  flex: 0 0 62px;
  border-radius: 14px;
  background: rgba(255,255,255,.96);
  padding: 5px;
  box-shadow: 0 6px 18px rgba(0,0,0,.32), inset 0 0 0 1px rgba(255,255,255,.4);
  object-fit: contain;
}
.fp-team {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10.5px;
  letter-spacing: .16em;
  text-transform: uppercase;
  color: rgba(255,255,255,.92);
  font-weight: 500;
  margin: 0 0 5px;
}
.fp-team b { font-weight: 700; color: #fff; }
.fp-h1 {
  font-family: 'Anton', sans-serif;
  font-size: clamp(30px,9.5vw,46px);
  line-height: .9;
  letter-spacing: .5px;
  margin: 0;
  text-transform: uppercase;
  text-shadow: 0 2px 14px rgba(0,0,0,.28);
  color: #fff;
}
.fp-h1 span { color: #FFD7CF; }
.fp-sub {
  margin: 14px 20px 0;
  color: rgba(255,255,255,.82);
  font-size: 14px;
  max-width: 44ch;
  padding-bottom: 20px;
}

/* ---------- stage picker ---------- */
.stage-bar {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  margin: 18px 16px;
  padding: 14px 16px 16px;
}
.stage-bar-head {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: .18em;
  text-transform: uppercase;
  color: var(--ink-soft);
  font-weight: 700;
  margin-bottom: 10px;
}

/* ---------- section cards ---------- */
.sec-card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  margin: 18px 16px;
  overflow: hidden;
}
.sec-head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 18px;
  border-bottom: 1px solid var(--line);
  background: linear-gradient(var(--card), #FBFAF6);
}
.sec-num {
  font-family: 'Anton', sans-serif;
  font-size: 18px;
  width: 34px; height: 34px;
  flex: 0 0 34px;
  border-radius: 9px;
  background: var(--blue-deep);
  color: #fff;
  display: grid;
  place-items: center;
}
.sec-title {
  font-family: 'Anton', sans-serif;
  font-size: 19px;
  letter-spacing: .4px;
  text-transform: uppercase;
  line-height: 1;
}
.sec-when {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10.5px;
  letter-spacing: .1em;
  color: var(--ink-soft);
  text-transform: uppercase;
  margin-top: 3px;
}
.sec-body { padding: 8px 18px 18px; }

/* ---------- row layout ---------- */
.row-lbl   { font-weight: 600; font-size: 15.5px; }
.row-hint  { font-weight: 500; font-size: 12px; color: var(--ink-soft); margin-top: 1px; display: block; }

/* ---------- urine swatches ---------- */
.swatch-grid {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 6px;
  margin-top: 12px;
}
.swatch-btn {
  position: relative;
  height: 80px;
  border-radius: 9px;
  cursor: pointer;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  border: 2px solid rgba(0,0,0,.07);
  transition: transform .12s, box-shadow .15s, border-color .15s;
}
.swatch-btn.sel {
  border-color: var(--blue) !important;
  box-shadow: 0 0 0 3px rgba(47,60,130,.22);
  transform: translateY(-3px);
}
.swatch-num {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  font-size: 12px;
  color: #2b2a14;
  background: rgba(255,255,255,.62);
  border-radius: 6px;
  padding: 1px 0;
  margin-bottom: 6px;
  width: 20px;
  text-align: center;
}

/* ---------- results panel ---------- */
.results-grid {
  margin-top: 16px;
  border-radius: 14px;
  overflow: hidden;
  background: rgba(255,255,255,.09);
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  border: 1px solid var(--navy);
}
.res-cell { background: var(--navy); padding: 14px 15px; }
.res-v {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  font-size: 21px;
  color: #fff;
  line-height: 1;
}
.res-v small { font-size: 12px; font-weight: 500; color: rgba(255,255,255,.55); margin-left: 1px; }
.res-v.ok   { color: #5BE08A; }
.res-v.warn { color: #FBBF24; }
.res-v.bad  { color: #FB7185; }
.res-k {
  font-size: 10.5px;
  letter-spacing: .07em;
  text-transform: uppercase;
  color: rgba(255,255,255,.6);
  margin-top: 7px;
  font-weight: 600;
}

/* ---------- note box ---------- */
.note-box {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 11px 13px;
  margin: 6px 0 12px;
  background: rgba(47,60,130,.05);
  border: 1px solid var(--line);
  border-left: 3px solid var(--accent);
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-soft);
  line-height: 1.4;
}
.note-ico {
  flex: 0 0 20px;
  width: 20px; height: 20px;
  border-radius: 50%;
  background: var(--accent);
  color: #fff;
  font-size: 13px;
  font-weight: 800;
  display: grid;
  place-items: center;
  margin-top: 1px;
}

/* ---------- trackbox ---------- */
.trackbox {
  margin-top: 14px;
  padding: 2px 14px 6px;
  background: #FAF7F0;
  border: 1px solid var(--line);
  border-radius: 12px;
}

/* ---------- send bar (sticky bottom) ---------- */
.send-bar {
  position: fixed;
  left: 0; right: 0; bottom: 0;
  z-index: 30;
  background: rgba(244,241,234,.92);
  backdrop-filter: blur(10px);
  border-top: 1px solid var(--line);
  padding: 12px 16px 20px;
  display: flex;
  gap: 10px;
  max-width: 560px;
  margin: 0 auto;
}
.send-btn {
  flex: 1;
  border: none;
  border-radius: 13px;
  padding: 15px 8px;
  cursor: pointer;
  font-family: 'Hanken Grotesk', sans-serif;
  font-weight: 800;
  font-size: 14.5px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  text-decoration: none;
}
.btn-wa   { background: #25D366; color: #063d1c; }
.btn-copy { background: var(--accent); color: #fff; }

/* ---------- streamlit widget overrides ---------- */
div[data-testid="stNumberInput"] input,
div[data-testid="stTextInput"]   input {
  font-family: 'JetBrains Mono', monospace !important;
  font-weight: 700 !important;
  font-size: 18px !important;
  background: #FBFAF6 !important;
  border: 1.5px solid var(--line) !important;
  border-radius: 12px !important;
  color: var(--ink) !important;
}
div[data-testid="stNumberInput"] input:focus,
div[data-testid="stTextInput"]   input:focus {
  border-color: var(--blue) !important;
  box-shadow: 0 0 0 3px rgba(47,60,130,.18) !important;
}
/* hide stepper arrows on number inputs */
div[data-testid="stNumberInput"] button {
  background: #FBFAF6 !important;
  border: 1.5px solid var(--line) !important;
  color: var(--ink) !important;
  border-radius: 9px !important;
}
/* stage chip buttons */
.stButton > button {
  border-radius: 9px !important;
  border: 1.5px solid var(--line) !important;
  background: #FBFAF6 !important;
  font-family: 'Anton', sans-serif !important;
  font-size: 20px !important;
  color: var(--ink) !important;
  height: 46px !important;
  padding: 0 !important;
  width: 100% !important;
  transition: .12s !important;
}
.stButton > button:hover { background: #f0ede5 !important; }

/* selected stage button */
.chip-sel > button {
  background: var(--blue) !important;
  color: #fff !important;
  border-color: var(--blue-deep) !important;
  box-shadow: 0 4px 12px rgba(47,60,130,.28) !important;
  transform: translateY(-2px) !important;
}

/* WhatsApp / Copy action buttons */
.action-btn > button {
  border-radius: 13px !important;
  border: none !important;
  font-family: 'Hanken Grotesk', sans-serif !important;
  font-weight: 800 !important;
  font-size: 14.5px !important;
  height: 52px !important;
  width: 100% !important;
}
.wa-btn > button  { background: #25D366 !important; color: #063d1c !important; }
.copy-btn > button { background: var(--accent) !important; color: #fff !important; }
.reset-btn > button {
  background: none !important;
  border: none !important;
  color: var(--accent-ink) !important;
  text-decoration: underline !important;
  font-weight: 700 !important;
  font-size: 12px !important;
  width: auto !important;
  height: auto !important;
  padding: 0 !important;
}

/* spacer so fixed bar doesn't overlap */
.bottom-spacer { height: 80px; }

/* dividers between rows */
hr.row-div {
  border: none;
  border-top: 1px solid var(--line);
  margin: 0;
}

label, div[data-testid="stWidgetLabel"] {
  font-family: 'Hanken Grotesk', sans-serif !important;
  font-weight: 600 !important;
  color: var(--ink) !important;
}
</style>
""", unsafe_allow_html=True)

# ── Session state initialisation ─────────────────────────────────────────────
STAGES = list(range(1, 9))
FIELDS = [
    'preW', 'preDrink', 'gels', 'chews', 'bars',
    'bidonsKH', 'bidons60', 'bidonsW', 'otherFood', 'otherDrinks',
    'bidonVol', 'peeStops', 'peeMl', 'soda', 'recup',
    'waterPost', 'postW', 'raceH', 'raceM',
]
STEPPER_FIELDS = {'gels', 'chews', 'bars', 'bidonsKH', 'bidons60', 'bidonsW',
                  'peeStops', 'soda', 'recup'}

def default_value(field):
    return 500 if field == 'bidonVol' else (0 if field in STEPPER_FIELDS else 0.0)

if 'stage' not in st.session_state:
    st.session_state.stage = 1

if 'stage_data' not in st.session_state:
    st.session_state.stage_data = {}   # {stage: {field: value, 'urine': int/None}}

def current_data():
    s = st.session_state.stage
    if s not in st.session_state.stage_data:
        st.session_state.stage_data[s] = {f: default_value(f) for f in FIELDS}
        st.session_state.stage_data[s]['urine'] = None
    return st.session_state.stage_data[s]

def get(field, fallback=None):
    d = current_data()
    v = d.get(field, fallback if fallback is not None else default_value(field))
    return v

def set_field(field, value):
    current_data()[field] = value

# ── Calculation engine (mirrors JS calc() exactly) ───────────────────────────
def calc():
    bidon_vol = get('bidonVol') or 500
    scale = bidon_vol / 500

    raceH = get('raceH') or 0
    raceM = get('raceM') or 0
    h = raceH + raceM / 60

    carbs = (get('gels') * 40 + get('chews') * 35 + get('bars') * 30
             + get('bidonsKH') * 30 * scale
             + get('bidons60') * 60 * scale)

    fluid_race = ((get('bidonsKH') + get('bidons60') + get('bidonsW')) * bidon_vol
                  + (get('otherDrinks') or 0))

    pre_drink   = get('preDrink') or 0
    post_finish = (get('soda') * 330 + get('recup') * 500 + (get('waterPost') or 0))
    pee_ml      = (get('peeMl') or 0)
    urine_ml    = pee_ml if pee_ml > 0 else get('peeStops') * 300

    pre  = get('preW')  or 0
    post = get('postW') or 0
    m_start  = (pre  + pre_drink / 1000)   if pre  > 0 else None
    m_finish = (post - post_finish / 1000) if post > 0 else None

    deficit    = (m_start - m_finish)                  if (m_start is not None and m_finish is not None) else None
    dehyd      = (deficit / m_start * 100)             if (deficit is not None and m_start > 0)          else None
    sweat      = (deficit + fluid_race / 1000 - urine_ml / 1000) if deficit is not None else None
    sweat_rate = (sweat / h)                           if (sweat is not None and h > 0)                   else None

    return {
        'bidon_vol': bidon_vol, 'scale': scale,
        'carbs': carbs,
        'carbs_h': carbs / h if h > 0 else None,
        'fluid_race': fluid_race,
        'fluid_h': fluid_race / h if h > 0 else None,
        'h': h,
        'dehyd': dehyd,
        'sweat_rate': sweat_rate,
    }

def fmt(n, dec=0):
    if n is None:
        return '—'
    return f"{n:,.{dec}f}".replace(',', '\u2009')   # thin-space thousands sep

# ── Report text (mirrors JS report()) ────────────────────────────────────────
def build_report():
    stage = st.session_state.stage
    bv = get('bidonVol') or 500
    c  = calc()
    urine = current_data().get('urine')
    c30 = round(30 * (bv / 500))
    c60 = round(60 * (bv / 500))

    lines = [
        '🚴 DECATHLON CMA-CGM — RIDE LOG',
        f'Stage {stage}',
        '',
        '— BEFORE THE START —',
        f"Urine colour (1-8): {urine if urine else '—'}",
        f"Weight before: {fmt(get('preW') or 0, 1)} kg",
        f"Drink before start: {fmt(get('preDrink') or 0, 0)} ml",
        '',
        '— DURING THE RIDE —',
        f"Gels (45 g): {int(get('gels'))}  ({int(get('gels'))*40} g carbs)",
        f"Chews (44 g): {int(get('chews'))}  ({int(get('chews'))*35} g carbs)",
        f"Bars (35 g): {int(get('bars'))}  ({int(get('bars'))*30} g carbs)",
        f"Bottles 30 g · {bv} ml: {int(get('bidonsKH'))}  ({int(get('bidonsKH'))*c30} g carbs · {int(get('bidonsKH'))*bv} ml)",
        f"Bottles 60 g · {bv} ml: {int(get('bidons60'))}  ({int(get('bidons60'))*c60} g carbs · {int(get('bidons60'))*bv} ml)",
        f"Bottles water · {bv} ml: {int(get('bidonsW'))}  ({int(get('bidonsW'))*bv} ml)",
        f"Other food: {fmt(get('otherFood') or 0, 0)} g",
        f"Other drinks: {fmt(get('otherDrinks') or 0, 0)} ml",
        f"Pee stops: {int(get('peeStops'))}",
        f"Pee volume: {fmt(get('peeMl') or 0, 0)} ml",
        '',
        '— AFTER THE RIDE (before weigh-in) —',
        f"Soda (330 ml): {int(get('soda'))}  ({int(get('soda'))*330} ml)",
        f"Recovery (500 ml): {int(get('recup'))}  ({int(get('recup'))*500} ml)",
        f"Water: {fmt(get('waterPost') or 0, 0)} ml",
        '',
        '— WEIGH-IN AFTER RIDE —',
        f"Weight after: {fmt(get('postW') or 0, 1)} kg",
        '',
        '— RACE TIME —',
        f"Race time: {int(get('raceH'))}h {int(get('raceM'))}min" + (f"  ({fmt(c['h'], 2)} h)" if c['h'] > 0 else ''),
        '',
        '— CALCULATED —',
        f"Carbs (race): {fmt(c['carbs'], 0)} g",
        "Carbs/h: " + ("—" if c['carbs_h'] is None else str(round(c['carbs_h'])) + " g/h"),
        f"Fluid (race): {fmt(c['fluid_race']/1000, 2)} L",
        "Fluid/h: " + ("—" if c['fluid_h'] is None else str(round(c['fluid_h'])) + " ml/h"),
        "Dehydration: " + ("—" if c['dehyd'] is None else fmt(c['dehyd'], 1) + " %"),
        "Sweat rate: " + ("—" if c['sweat_rate'] is None else fmt(c['sweat_rate'], 2) + " L/h"),
    ]
    return '\n'.join(lines)

# ══════════════════════════════════════════════════════════════════════════════
#  RENDER
# ══════════════════════════════════════════════════════════════════════════════

# ── Header ───────────────────────────────────────────────────────────────────
BADGE_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/Decathlon_logo.svg/320px-Decathlon_logo.svg.png"

st.markdown(f"""
<div class="fp-header">
  <div class="fp-stripe"></div>
  <div class="fp-header-inner">
    <img class="fp-badge" src="{BADGE_URL}" alt="Decathlon">
    <div>
      <p class="fp-team">Decathlon · CMA-CGM · <b>Continental</b></p>
      <div class="fp-h1">RIDE<span>·</span>LOG</div>
    </div>
  </div>
  <p class="fp-sub">Fill this in after the ride and send it over. Track everything you drank and ate so we can work out your fluid balance and fueling.</p>
</div>
""", unsafe_allow_html=True)

# ── Stage picker ─────────────────────────────────────────────────────────────
st.markdown('<div class="stage-bar"><div class="stage-bar-head">Stage</div>', unsafe_allow_html=True)
cols = st.columns(8)
for i, col in enumerate(cols):
    stage_num = i + 1
    css_class = "chip-sel" if st.session_state.stage == stage_num else ""
    with col:
        st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
        if st.button(str(stage_num), key=f"chip_{stage_num}"):
            st.session_state.stage = stage_num
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

d = current_data()   # shorthand for current stage's data dict

# ══════ Section 1 — Before the start ════════════════════════════════════════
st.markdown("""
<div class="sec-card">
  <div class="sec-head">
    <div class="sec-num">1</div>
    <div>
      <div class="sec-title">Before the start</div>
      <div class="sec-when">Pre-stage</div>
    </div>
  </div>
  <div class="sec-body">
""", unsafe_allow_html=True)

# — Urine colour scale —
st.markdown("""
  <div style="padding:15px 0 8px 0; border-bottom:1px solid var(--line);">
    <span class="row-lbl">Urine colour</span>
    <span class="row-hint">Tap the shade that matches yours — 1 = pale (well hydrated), 8 = dark (dehydrated)</span>
  </div>
""", unsafe_allow_html=True)

SWATCHES = ['#FFFDE8','#FFFAB6','#F8EF66','#FDE11C','#ECD247','#E4C306','#DAB002','#8C881C']
ucols = st.columns(8)
for idx, ucol in enumerate(ucols):
    v = idx + 1
    sel = (d.get('urine') == v)
    outline = f"border: 2px solid #2F3C82; box-shadow: 0 0 0 3px rgba(47,60,130,.22); transform: translateY(-3px);" if sel else "border: 2px solid rgba(0,0,0,.07);"
    tick = "✓" if sel else str(v)
    tick_style = "background:#2F3C82;color:#fff;border-radius:50%;width:17px;height:17px;display:inline-flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;" if sel else "background:rgba(255,255,255,.62);border-radius:6px;padding:1px 0;width:20px;text-align:center;"
    # We use a small HTML button rendered via markdown + st.button overlay trick
    with ucol:
        if st.button(" ", key=f"urine_{v}_s{st.session_state.stage}",
                     help=f"Shade {v}"):
            d['urine'] = v
            st.rerun()
        st.markdown(f"""
        <div onclick="" style="
          height:70px; border-radius:9px; cursor:pointer;
          display:flex; align-items:flex-end; justify-content:center;
          background:{SWATCHES[idx]}; {outline}
          margin-top:-50px; pointer-events:none;">
          <span style="font-family:'JetBrains Mono',monospace;font-weight:700;font-size:12px;color:#2b2a14;
            {tick_style} margin-bottom:6px;">{tick}</span>
        </div>""", unsafe_allow_html=True)

st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)

# — Weight before —
st.markdown('<div style="padding:10px 0 4px 0;"><span class="row-lbl">Weight before</span><span class="row-hint">At the weigh-in, just before the race</span></div>', unsafe_allow_html=True)
pre_w = st.number_input("Weight before (kg)", min_value=0.0, max_value=200.0,
                         value=float(d.get('preW') or 0), step=0.1,
                         format="%.1f", label_visibility="collapsed",
                         key=f"preW_s{st.session_state.stage}")
d['preW'] = pre_w

st.markdown('<hr class="row-div">', unsafe_allow_html=True)

# — Drink before start —
st.markdown('<div style="padding:10px 0 4px 0;"><span class="row-lbl">Drink before the start</span><span class="row-hint">Fluid drunk between the weigh-in and the start</span></div>', unsafe_allow_html=True)
pre_drink = st.number_input("Drink before start (ml)", min_value=0, max_value=5000,
                             value=int(d.get('preDrink') or 0), step=50,
                             label_visibility="collapsed",
                             key=f"preDrink_s{st.session_state.stage}")
d['preDrink'] = pre_drink

st.markdown('</div></div>', unsafe_allow_html=True)

# ══════ Section 2 — During the ride ══════════════════════════════════════════
c_now = calc()
bottle_hint_30 = f"{round(30 * c_now['scale'])} g carbs at {int(c_now['bidon_vol'])} ml"
bottle_hint_60 = f"{round(60 * c_now['scale'])} g carbs at {int(c_now['bidon_vol'])} ml"

st.markdown("""
<div class="sec-card">
  <div class="sec-head">
    <div class="sec-num">2</div>
    <div>
      <div class="sec-title">During the ride</div>
      <div class="sec-when">On the bike</div>
    </div>
  </div>
  <div class="sec-body">
""", unsafe_allow_html=True)

def stepper_row(label, hint, field, unit=""):
    st.markdown(f'<div style="padding:6px 0 2px 0;"><span class="row-lbl">{label}</span><span class="row-hint">{hint}</span></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 1])
    val = int(d.get(field) or 0)
    with c1:
        if st.button("−", key=f"minus_{field}_s{st.session_state.stage}"):
            d[field] = max(0, val - 1)
            st.rerun()
    with c2:
        new_val = st.number_input(label, min_value=0, value=val,
                                   label_visibility="collapsed",
                                   key=f"{field}_s{st.session_state.stage}")
        d[field] = new_val
    with c3:
        if st.button("+", key=f"plus_{field}_s{st.session_state.stage}"):
            d[field] = val + 1
            st.rerun()
    st.markdown('<hr class="row-div">', unsafe_allow_html=True)

stepper_row("Gels", "45 g · 40 g carbs", "gels")
stepper_row("Chews", "44 g · 35 g carbs", "chews")
stepper_row("Bars", "35 g · 30 g carbs", "bars")
stepper_row("Bottles · 30 g", bottle_hint_30, "bidonsKH")
stepper_row("Bottles · 60 g", bottle_hint_60, "bidons60")
stepper_row("Bottles · water", "water only", "bidonsW")

# Other food / drinks
st.markdown('<div style="padding:6px 0 2px 0;"><span class="row-lbl">Other food</span><span class="row-hint">total weight of any extra food (g)</span></div>', unsafe_allow_html=True)
other_food = st.number_input("Other food (g)", min_value=0, max_value=10000,
                              value=int(d.get('otherFood') or 0), step=1,
                              label_visibility="collapsed",
                              key=f"otherFood_s{st.session_state.stage}")
d['otherFood'] = other_food
st.markdown('<hr class="row-div">', unsafe_allow_html=True)

st.markdown('<div style="padding:6px 0 2px 0;"><span class="row-lbl">Other drinks</span><span class="row-hint">any extra drinks on the bike</span></div>', unsafe_allow_html=True)
other_drinks = st.number_input("Other drinks (ml)", min_value=0, max_value=10000,
                                value=int(d.get('otherDrinks') or 0), step=50,
                                label_visibility="collapsed",
                                key=f"otherDrinks_s{st.session_state.stage}")
d['otherDrinks'] = other_drinks

# Trackbox
st.markdown('<div class="trackbox">', unsafe_allow_html=True)
st.markdown('<div style="padding:10px 0 4px 0; border-bottom:1px solid #ECE7DC;"><span class="row-lbl">Volume per bottle</span></div>', unsafe_allow_html=True)
bidon_vol = st.number_input("Volume per bottle (ml)", min_value=100, max_value=2000,
                             value=int(d.get('bidonVol') or 500), step=50,
                             label_visibility="collapsed",
                             key=f"bidonVol_s{st.session_state.stage}")
d['bidonVol'] = bidon_vol

stepper_row("Pee stops", "", "peeStops")

st.markdown('<div style="padding:6px 0 2px 0;"><span class="row-lbl" style="color:#A29D90;font-weight:500;">Pee volume <em style="font-style:normal;font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:#B8B3A5;margin-left:7px;font-weight:700;">optional</em></span></div>', unsafe_allow_html=True)
pee_ml = st.number_input("Pee volume (ml)", min_value=0, max_value=5000,
                          value=int(d.get('peeMl') or 0), step=50,
                          label_visibility="collapsed",
                          key=f"peeMl_s{st.session_state.stage}")
d['peeMl'] = pee_ml
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div></div>', unsafe_allow_html=True)

# ══════ Section 3 — After the ride (before weigh-in) ═════════════════════════
st.markdown("""
<div class="sec-card">
  <div class="sec-head">
    <div class="sec-num">3</div>
    <div>
      <div class="sec-title">After the ride</div>
      <div class="sec-when">Before weigh-in</div>
    </div>
  </div>
  <div class="sec-body">
    <div class="note-box">
      <div class="note-ico">!</div>
      <span>Only fill in drinks you had <b>before</b> the weigh-in. Anything consumed after the weigh-in should be left out.</span>
    </div>
""", unsafe_allow_html=True)

stepper_row("Soda", "330 ml each", "soda")
stepper_row("Recovery drink", "500 ml each", "recup")

st.markdown('<div style="padding:6px 0 2px 0;"><span class="row-lbl">Water</span><span class="row-hint">loose water after the finish</span></div>', unsafe_allow_html=True)
water_post = st.number_input("Water post (ml)", min_value=0, max_value=5000,
                              value=int(d.get('waterPost') or 0), step=50,
                              label_visibility="collapsed",
                              key=f"waterPost_s{st.session_state.stage}")
d['waterPost'] = water_post

st.markdown('</div></div>', unsafe_allow_html=True)

# ══════ Section 4 — Weigh-in after ride ═════════════════════════════════════
st.markdown("""
<div class="sec-card">
  <div class="sec-head">
    <div class="sec-num">4</div>
    <div>
      <div class="sec-title">Weigh-in after ride</div>
      <div class="sec-when">Post weigh-in</div>
    </div>
  </div>
  <div class="sec-body">
""", unsafe_allow_html=True)

st.markdown('<div style="padding:10px 0 4px 0;"><span class="row-lbl">Weight after</span><span class="row-hint">At the weigh-in after the ride</span></div>', unsafe_allow_html=True)
post_w = st.number_input("Weight after (kg)", min_value=0.0, max_value=200.0,
                          value=float(d.get('postW') or 0), step=0.1, format="%.1f",
                          label_visibility="collapsed",
                          key=f"postW_s{st.session_state.stage}")
d['postW'] = post_w

st.markdown('</div></div>', unsafe_allow_html=True)

# ══════ Section 5 — Race time + results ══════════════════════════════════════
st.markdown("""
<div class="sec-card">
  <div class="sec-head">
    <div class="sec-num">5</div>
    <div>
      <div class="sec-title">Race time</div>
      <div class="sec-when">Duration &amp; results</div>
    </div>
  </div>
  <div class="sec-body">
""", unsafe_allow_html=True)

st.markdown('<div style="padding:10px 0 4px 0;"><span class="row-lbl">Total race time</span><span class="row-hint">Elapsed time of the stage</span></div>', unsafe_allow_html=True)
t1, t2 = st.columns(2)
with t1:
    race_h = st.number_input("Hours", min_value=0, max_value=24,
                              value=int(d.get('raceH') or 0),
                              label_visibility="visible",
                              key=f"raceH_s{st.session_state.stage}")
    d['raceH'] = race_h
with t2:
    race_m = st.number_input("Minutes", min_value=0, max_value=59,
                              value=int(d.get('raceM') or 0),
                              label_visibility="visible",
                              key=f"raceM_s{st.session_state.stage}")
    d['raceM'] = race_m

# — Calculated results panel —
c_res = calc()

def res_class(key):
    if key != 'dehyd' or c_res['dehyd'] is None:
        return ''
    if c_res['dehyd'] > 3:
        return 'bad'
    if c_res['dehyd'] > 2:
        return 'warn'
    return 'ok'

carbs_str    = f"{fmt(c_res['carbs'], 0)} <small>g</small>"
carbs_h_str  = '—' if c_res['carbs_h'] is None else f"{round(c_res['carbs_h'])} <small>g/h</small>"
fluid_str    = f"{fmt(c_res['fluid_race']/1000, 2)} <small>L</small>"
fluid_h_str  = '—' if c_res['fluid_h'] is None else f"{round(c_res['fluid_h'])} <small>ml/h</small>"
dehyd_str    = '—' if c_res['dehyd'] is None else f"{fmt(c_res['dehyd'], 1)} <small>%</small>"
sweat_str    = '—' if c_res['sweat_rate'] is None else f"{fmt(c_res['sweat_rate'], 2)} <small>L/h</small>"
dehyd_cls    = res_class('dehyd')

st.markdown(f"""
<div class="results-grid">
  <div class="res-cell"><div class="res-v">{carbs_str}</div><div class="res-k">Carbs · race</div></div>
  <div class="res-cell"><div class="res-v">{carbs_h_str}</div><div class="res-k">Carbs / h</div></div>
  <div class="res-cell"><div class="res-v">{fluid_str}</div><div class="res-k">Fluid · race</div></div>
  <div class="res-cell"><div class="res-v">{fluid_h_str}</div><div class="res-k">Fluid / h</div></div>
  <div class="res-cell"><div class="res-v {dehyd_cls}">{dehyd_str}</div><div class="res-k">Dehydration</div></div>
  <div class="res-cell"><div class="res-v">{sweat_str}</div><div class="res-k">Sweat rate</div></div>
</div>
""", unsafe_allow_html=True)

st.markdown('</div></div>', unsafe_allow_html=True)

# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown('<div style="text-align:center;color:var(--ink-soft);font-size:12px;padding:8px 16px 4px;">Fill in per stage, then send.</div>', unsafe_allow_html=True)
st.markdown('<div class="bottom-spacer"></div>', unsafe_allow_html=True)

# ── Action bar ───────────────────────────────────────────────────────────────
report_text = build_report()
wa_url = f"https://wa.me/?text={report_text}"

# Show report in an expander (WhatsApp deep link + copy)
with st.expander("📤  Send / Copy report", expanded=False):
    st.markdown(f"""
    <div style="display:flex;gap:10px;margin-bottom:12px;">
      <a href="{wa_url}" target="_blank" style="flex:1;background:#25D366;color:#063d1c;border-radius:13px;
         padding:15px 8px;text-align:center;font-family:'Hanken Grotesk',sans-serif;
         font-weight:800;font-size:14.5px;text-decoration:none;display:block;">
        📱 WhatsApp
      </a>
    </div>
    """, unsafe_allow_html=True)
    st.text_area("Report text (select all & copy)", value=report_text, height=300,
                 key="report_text_area")

# ── Reset stage ───────────────────────────────────────────────────────────────
st.markdown('<div style="text-align:center;padding:4px 0 20px 0;">', unsafe_allow_html=True)
if st.button(f"🔄 Reset stage {st.session_state.stage}", key="reset_stage"):
    st.session_state.stage_data[st.session_state.stage] = {
        f: default_value(f) for f in FIELDS
    }
    st.session_state.stage_data[st.session_state.stage]['urine'] = None
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)
