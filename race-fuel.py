import streamlit as st
import urllib.parse

st.set_page_config(
    page_title="FuelPro · Ride Log",
    page_icon="🚴",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── hide all Streamlit chrome ──────────────────────────────────────────
st.markdown("""
<style>
header[data-testid="stHeader"],footer,#MainMenu,
[data-testid="stSidebar"],[data-testid="collapsedControl"]{display:none!important}
[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:#F4F1EA!important}
[data-testid="block-container"]{max-width:560px!important;padding:0 0 40px 0!important}
[data-testid="stVerticalBlock"]{gap:0!important}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════
STEPPER = ['gels','chews','bars','bidonsKH','bidons60','bidonsW','peeStops','soda','recup']
FLOATS  = ['preW','postW']
INTS    = ['preDrink','otherFood','otherDrinks','bidonVol','peeMl','waterPost','raceH','raceM']

def default(f):
    if f == 'bidonVol': return 500
    if f in FLOATS: return 0.0
    return 0

for k,v in [('stage',1),('stage_data',{})]:
    if k not in st.session_state: st.session_state[k] = v

def sdata():
    n = st.session_state.stage
    if n not in st.session_state.stage_data:
        d = {f: default(f) for f in STEPPER+FLOATS+INTS}
        d['urine'] = None
        st.session_state.stage_data[n] = d
    return st.session_state.stage_data[n]

def g(f):     return sdata().get(f, default(f))
def sv(f,v):  sdata()[f] = v

# ── handle URL param actions (from HTML buttons) ───────────────────────
p = st.query_params
if 'stage' in p:
    st.session_state.stage = int(p['stage'])
    st.query_params.clear(); st.rerun()
if 'urine' in p:
    sdata()['urine'] = int(p['urine'])
    st.query_params.clear(); st.rerun()
if 'inc' in p:
    f = p['inc']; sv(f, int(g(f))+1)
    st.query_params.clear(); st.rerun()
if 'dec' in p:
    f = p['dec']; sv(f, max(0, int(g(f))-1))
    st.query_params.clear(); st.rerun()
if 'reset' in p:
    n = st.session_state.stage
    d = {f: default(f) for f in STEPPER+FLOATS+INTS}; d['urine'] = None
    st.session_state.stage_data[n] = d
    st.query_params.clear(); st.rerun()

# ══════════════════════════════════════════════════════════════════════
# CALCULATIONS
# ══════════════════════════════════════════════════════════════════════
def calc():
    bv = g('bidonVol') or 500; sc = bv/500
    h  = (g('raceH') or 0) + (g('raceM') or 0)/60
    carbs = g('gels')*40 + g('chews')*35 + g('bars')*30 + g('bidonsKH')*30*sc + g('bidons60')*60*sc
    fluid = (g('bidonsKH')+g('bidons60')+g('bidonsW'))*bv + (g('otherDrinks') or 0)
    pre_d = g('preDrink') or 0
    post_f= g('soda')*330 + g('recup')*500 + (g('waterPost') or 0)
    pee   = (g('peeMl') or 0) if (g('peeMl') or 0)>0 else g('peeStops')*300
    pre,post = g('preW') or 0, g('postW') or 0
    m0 = (pre+pre_d/1000)   if pre>0  else None
    m1 = (post-post_f/1000) if post>0 else None
    deficit = (m0-m1) if m0 and m1 else None
    dehyd   = deficit/m0*100 if deficit and m0 else None
    sweat   = deficit+fluid/1000-pee/1000 if deficit is not None else None
    sr      = sweat/h if sweat and h>0 else None
    return dict(bv=bv,sc=sc,h=h,carbs=carbs,fluid=fluid,
                carbs_h=carbs/h if h>0 else None,
                fluid_h=fluid/h if h>0 else None,
                dehyd=dehyd, sweat_rate=sr)

def fmt(v,dec=0): return '—' if v is None else f"{v:,.{dec}f}"

# ══════════════════════════════════════════════════════════════════════
# REPORT
# ══════════════════════════════════════════════════════════════════════
def report(c):
    bv=g('bidonVol') or 500; c30=round(30*(bv/500)); c60=round(60*(bv/500))
    u=sdata().get('urine')
    L=['🚴 FUELPRO — RIDE LOG',f"Stage {st.session_state.stage}",'',
       '— BEFORE THE START —',f"Urine colour: {u or '—'}",
       f"Weight before: {fmt(g('preW'),1)} kg",f"Drink before: {fmt(g('preDrink'),0)} ml",'',
       '— DURING THE RIDE —',
       f"Gels: {int(g('gels'))}  ({int(g('gels'))*40}g carbs)",
       f"Chews: {int(g('chews'))}  ({int(g('chews'))*35}g carbs)",
       f"Bars: {int(g('bars'))}  ({int(g('bars'))*30}g carbs)",
       f"Bottles 30g·{bv}ml: {int(g('bidonsKH'))}  ({int(g('bidonsKH'))*c30}g·{int(g('bidonsKH'))*bv}ml)",
       f"Bottles 60g·{bv}ml: {int(g('bidons60'))}  ({int(g('bidons60'))*c60}g·{int(g('bidons60'))*bv}ml)",
       f"Bottles water: {int(g('bidonsW'))}  ({int(g('bidonsW'))*bv}ml)",
       f"Other food: {fmt(g('otherFood'),0)}g", f"Other drinks: {fmt(g('otherDrinks'),0)}ml",
       f"Pee stops: {int(g('peeStops'))}",'',
       '— AFTER THE RIDE —',
       f"Soda: {int(g('soda'))}  ({int(g('soda'))*330}ml)",
       f"Recovery: {int(g('recup'))}  ({int(g('recup'))*500}ml)",
       f"Water: {fmt(g('waterPost'),0)}ml",'',
       '— WEIGH-IN —',f"Weight after: {fmt(g('postW'),1)} kg",'',
       '— RACE TIME —',f"{int(g('raceH'))}h {int(g('raceM'))}min"+(f" ({fmt(c['h'],2)}h)" if c['h']>0 else ''),'',
       '— RESULTS —',f"Carbs: {fmt(c['carbs'],0)}g",
       "Carbs/h: "+("—" if c['carbs_h'] is None else str(round(c['carbs_h']))+"g/h"),
       f"Fluid: {fmt(c['fluid']/1000,2)}L",
       "Fluid/h: "+("—" if c['fluid_h'] is None else str(round(c['fluid_h']))+"ml/h"),
       "Dehydration: "+("—" if c['dehyd'] is None else fmt(c['dehyd'],1)+"%"),
       "Sweat rate: "+("—" if c['sweat_rate'] is None else fmt(c['sweat_rate'],2)+"L/h")]
    return '\n'.join(L)

# ══════════════════════════════════════════════════════════════════════
# BUILD THE ENTIRE PAGE AS ONE HTML BLOCK
# ══════════════════════════════════════════════════════════════════════
cr  = calc()
bv  = g('bidonVol') or 500
sc  = bv/500
c30 = round(30*sc); c60 = round(60*sc)
u   = sdata().get('urine')
stg = st.session_state.stage

SWATCHES = ['#FFFDE8','#FFFAB6','#F8EF66','#FDE11C','#ECD247','#E4C306','#DAB002','#8C881C']
STXT     = ['#7a7440','#7a7440','#4a4810','#4a4810','#4a4810','#3d3a00','#fff','#fff']

def btn(label, param, value, style="", cls=""):
    url = f"?{param}={urllib.parse.quote(str(value))}"
    return f'<a href="{url}" class="btn {cls}" style="{style}">{label}</a>'

def stage_btn(n):
    if n == stg:
        return f'<div class="stage-chip stage-sel">{n}</div>'
    return btn(str(n), 'stage', n, cls='stage-chip')

def urine_btn(v):
    bg  = SWATCHES[v-1]; tc = STXT[v-1]
    sel = u == v
    ring = 'border:3px solid #2F3C82;box-shadow:0 0 0 3px rgba(47,60,130,.25);transform:translateY(-3px);' if sel else ''
    lbl = '✓' if sel else str(v)
    return (f'<a href="?urine={v}" class="btn urine-btn" '
            f'style="background:{bg};color:{tc};{ring}">{lbl}</a>')

def stepper_row(label, hint, field, carbs_each=0, fluid_each=0):
    val = int(g(field) or 0)
    parts = []
    if carbs_each > 0: parts.append(f"<b>{val*carbs_each}g</b>")
    if fluid_each > 0: parts.append(f"{val*fluid_each}ml")
    sub = f' <span class="sub">{"·".join(parts)}</span>' if parts and val>0 else ''
    return f"""
<div class="row">
  <div class="row-label">{label}{sub}<div class="row-hint">{hint}</div></div>
  <div class="stepper">
    {btn('−','dec',field,cls='s-btn s-minus')}
    <div class="s-val">{val}</div>
    {btn('+','inc',field,cls='s-btn s-plus')}
  </div>
</div>"""

def num_row(label, hint, val_str, unit):
    return f"""
<div class="row">
  <div class="row-label">{label}<div class="row-hint">{hint}</div></div>
  <div class="num-right">
    <div class="num-box">{val_str}</div>
    <div class="unit-box">{unit}</div>
  </div>
</div>"""

def res_tile(val, unit, label, color='#fff'):
    return (f'<div class="res-tile">'
            f'<div class="res-val" style="color:{color}">{val}'
            f'<span class="res-unit">{unit}</span></div>'
            f'<div class="res-label">{label}</div></div>')

def dc(v):
    if v is None: return '#fff'
    return '#FB7185' if v>3 else ('#FBBF24' if v>2 else '#5BE08A')

txt = report(cr)
wa  = "https://wa.me/?text=" + urllib.parse.quote(txt)

# bv settings (inside expander we'll do separately with st widgets)
preW_fmt  = fmt(g('preW'),1)  if (g('preW')  or 0)>0 else '0.0'
postW_fmt = fmt(g('postW'),1) if (g('postW') or 0)>0 else '0.0'

HTML = f"""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}}
body{{font-family:'Hanken Grotesk','Helvetica Neue',Arial,sans-serif;
      background:#F4F1EA;color:#16140F;padding-bottom:20px}}
a{{text-decoration:none;color:inherit}}

/* ── header ── */
.hdr{{background:
  linear-gradient(157deg,rgba(8,9,24,.45),rgba(8,9,24,0) 58%),
  radial-gradient(120% 80% at 85% 110%,rgba(239,74,59,.55),transparent 60%),
  linear-gradient(157deg,#12122a,#20264f 19%,#43275f 39%,#8a2a5e 57%,#cf2c47 77%,#ef4a3b);
  border-bottom:4px solid #E5343A}}
.stripe{{height:5px;background:repeating-linear-gradient(
  135deg,#2F3C82 0 12px,#E5343A 12px 24px)}}
.hdr-inner{{padding:20px 16px 18px}}
.hdr-title{{font-family:Anton,sans-serif;font-size:clamp(32px,10vw,48px);
  line-height:.9;text-transform:uppercase;color:#fff;
  text-shadow:0 2px 12px rgba(0,0,0,.3)}}
.hdr-title span{{color:#FFD7CF}}
.hdr-sub{{margin:10px 0 0;color:rgba(255,255,255,.78);font-size:13px}}

/* ── cards ── */
.card{{background:#fff;border:1px solid #E2DDD1;border-radius:14px;
  box-shadow:0 2px 12px rgba(22,20,15,.07);margin:12px 12px 0;padding:0;overflow:hidden}}
.sec-head{{display:flex;align-items:center;gap:12px;padding:14px 16px;
  border-bottom:1px solid #E2DDD1;
  background:linear-gradient(#fff,#FBFAF6)}}
.sec-num{{width:34px;height:34px;border-radius:9px;background:#1E274F;color:#fff;
  display:flex;align-items:center;justify-content:center;
  font-family:Anton,sans-serif;font-size:17px;flex-shrink:0}}
.sec-title{{font-family:Anton,sans-serif;font-size:18px;letter-spacing:.4px;
  text-transform:uppercase;color:#16140F;line-height:1.1}}
.sec-sub{{font-size:9px;letter-spacing:.12em;text-transform:uppercase;
  color:#6B6760;margin-top:2px;font-family:monospace}}
.card-body{{padding:8px 14px 6px}}

/* ── stage picker ── */
.stage-wrap{{background:#fff;border:1px solid #E2DDD1;border-radius:14px;
  margin:12px 12px 0;padding:14px}}
.stage-label{{font-size:10px;letter-spacing:.18em;text-transform:uppercase;
  color:#6B6760;font-weight:700;font-family:monospace;margin-bottom:8px}}
.stage-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}}
.stage-chip{{display:flex;align-items:center;justify-content:center;
  height:52px;border-radius:10px;border:1.5px solid #E2DDD1;
  background:#FBFAF6;font-family:Anton,sans-serif;font-size:20px;
  color:#16140F;cursor:pointer;transition:.1s}}
.stage-chip:active{{transform:scale(.94)}}
.stage-sel{{background:#2F3C82!important;color:#fff!important;
  border-color:#1E274F!important;box-shadow:0 2px 8px rgba(47,60,130,.4)}}

/* ── urine ── */
.urine-label{{font-weight:700;font-size:15px;margin:12px 0 2px}}
.urine-hint{{font-size:11px;color:#6B6760;margin-bottom:10px}}
.urine-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:8px}}
.urine-btn{{display:flex;align-items:center;justify-content:center;
  height:64px;border-radius:10px;border:2px solid rgba(0,0,0,.1);
  font-family:monospace;font-size:15px;font-weight:900;
  cursor:pointer;transition:.12s}}
.urine-btn:active{{transform:scale(.92)}}

/* ── rows ── */
.row{{display:flex;align-items:center;justify-content:space-between;
  gap:10px;padding:10px 0;border-bottom:1px solid #E2DDD1}}
.row:last-child{{border-bottom:none}}
.row-label{{font-weight:700;font-size:15px;flex:1}}
.row-hint{{font-size:11px;color:#6B6760;font-weight:500;margin-top:2px}}
.sub{{font-size:11px;font-weight:700;color:#2F3C82;margin-left:5px}}

/* ── stepper ── */
.stepper{{display:flex;align-items:center;gap:0;flex-shrink:0}}
.s-btn{{width:52px;height:52px;display:flex;align-items:center;justify-content:center;
  border-radius:10px;border:1.5px solid #E2DDD1;font-size:26px;font-weight:900;
  cursor:pointer;transition:.1s}}
.s-btn:active{{transform:scale(.9)}}
.s-minus{{background:#FFF0F0;color:#C0392B;border-color:#F5C6C6;border-radius:10px 0 0 10px}}
.s-plus{{background:#EEF2FF;color:#2F3C82;border-color:#C6CEEF;border-radius:0 10px 10px 0}}
.s-val{{width:56px;height:52px;display:flex;align-items:center;justify-content:center;
  background:#fff;border-top:1.5px solid #E2DDD1;border-bottom:1.5px solid #E2DDD1;
  font-family:monospace;font-weight:700;font-size:24px;color:#16140F}}

/* ── number rows ── */
.num-right{{display:flex;align-items:center;gap:0;flex-shrink:0}}
.num-box{{height:52px;min-width:90px;display:flex;align-items:center;justify-content:center;
  background:#FBFAF6;border:1.5px solid #E2DDD1;border-radius:10px 0 0 10px;
  font-family:monospace;font-weight:700;font-size:20px;color:#16140F;padding:0 12px}}
.unit-box{{height:52px;min-width:40px;display:flex;align-items:center;justify-content:center;
  background:#F0EDE5;border:1.5px solid #E2DDD1;border-left:none;border-radius:0 10px 10px 0;
  font-family:monospace;font-size:13px;font-weight:700;color:#4A463C;padding:0 8px}}

/* ── note ── */
.note{{background:#FFF5F5;border-left:4px solid #E5343A;border-radius:8px;
  padding:10px 12px;margin:8px 0;font-size:12px;font-weight:600;color:#6B1A1A}}

/* ── results ── */
.res-grid{{display:grid;grid-template-columns:1fr 1fr;gap:5px;margin:12px 0}}
.res-tile{{background:#14132A;border-radius:10px;padding:14px 12px}}
.res-val{{font-family:monospace;font-weight:700;font-size:22px;color:#fff;line-height:1}}
.res-unit{{font-size:11px;font-weight:500;color:rgba(255,255,255,.45);margin-left:3px}}
.res-label{{font-size:9px;letter-spacing:.07em;text-transform:uppercase;
  color:rgba(255,255,255,.45);margin-top:6px;font-weight:700}}

/* ── send bar ── */
.send-bar{{background:#fff;border-top:1px solid #E2DDD1;
  padding:12px 12px 24px;margin-top:16px;
  display:flex;gap:8px}}
.wa-btn{{flex:1;background:#25D366;color:#063d1c;border-radius:12px;
  padding:15px;text-align:center;font-weight:800;font-size:15px;
  box-shadow:0 3px 10px rgba(37,211,102,.3)}}
.copy-btn{{flex:1;background:#E5343A;color:#fff;border-radius:12px;
  padding:15px;text-align:center;font-weight:800;font-size:15px}}

/* ── reset ── */
.reset-btn{{display:block;text-align:center;padding:10px;
  color:#B11F26;font-size:13px;font-weight:700;text-decoration:underline}}

/* ── base btn reset ── */
.btn{{display:block;cursor:pointer}}
</style>
</head>
<body>

<!-- HEADER -->
<div class="hdr">
  <div class="stripe"></div>
  <div class="hdr-inner">
    <div class="hdr-title">RIDE<span>·</span>LOG</div>
    <p class="hdr-sub">Fill in after each stage · tap Send when done</p>
  </div>
</div>

<!-- STAGE PICKER -->
<div class="stage-wrap">
  <div class="stage-label">Stage</div>
  <div class="stage-grid">
    {stage_btn(1)}{stage_btn(2)}{stage_btn(3)}{stage_btn(4)}
  </div>
  <div style="height:8px"></div>
  <div class="stage-grid">
    {stage_btn(5)}{stage_btn(6)}{stage_btn(7)}{stage_btn(8)}
  </div>
</div>

<!-- SECTION 1 -->
<div class="card">
  <div class="sec-head">
    <div class="sec-num">1</div>
    <div><div class="sec-title">Before the Start</div><div class="sec-sub">Pre-stage</div></div>
  </div>
  <div class="card-body">
    <div class="urine-label">Urine colour</div>
    <div class="urine-hint">Tap the shade that matches yours — 1 = pale (well hydrated), 8 = dark (dehydrated)</div>
    <div class="urine-grid">
      {urine_btn(1)}{urine_btn(2)}{urine_btn(3)}{urine_btn(4)}
    </div>
    <div class="urine-grid">
      {urine_btn(5)}{urine_btn(6)}{urine_btn(7)}{urine_btn(8)}
    </div>
    {num_row("Weight before","At the weigh-in, just before the race", preW_fmt+" kg","kg")}
    {num_row("Drink before start","Fluid between weigh-in and start", fmt(g('preDrink'),0)+" ml","ml")}
  </div>
</div>

<!-- SECTION 2 -->
<div class="card">
  <div class="sec-head">
    <div class="sec-num">2</div>
    <div><div class="sec-title">During the Ride</div><div class="sec-sub">On the bike</div></div>
  </div>
  <div class="card-body">
    {stepper_row("Gels","45 g · 40 g carbs","gels",carbs_each=40)}
    {stepper_row("Chews","44 g · 35 g carbs","chews",carbs_each=35)}
    {stepper_row("Bars","35 g · 30 g carbs","bars",carbs_each=30)}
    {stepper_row("Bottles · 30 g",f"{c30} g carbs at {bv} ml","bidonsKH",carbs_each=c30,fluid_each=bv)}
    {stepper_row("Bottles · 60 g",f"{c60} g carbs at {bv} ml","bidons60",carbs_each=c60,fluid_each=bv)}
    {stepper_row("Bottles · water",f"water only · {bv} ml each","bidonsW",fluid_each=bv)}
    {num_row("Other food","Total weight of any extra food",fmt(g('otherFood'),0)+" g","g")}
    {num_row("Other drinks","Any extra drinks on the bike",fmt(g('otherDrinks'),0)+" ml","ml")}
  </div>
</div>

<!-- SECTION 3 -->
<div class="card">
  <div class="sec-head">
    <div class="sec-num">3</div>
    <div><div class="sec-title">After the Ride</div><div class="sec-sub">Before weigh-in</div></div>
  </div>
  <div class="card-body">
    <div class="note">⚠️ Only log drinks consumed <b>before</b> the post-ride weigh-in.</div>
    {stepper_row("Soda","330 ml each","soda",fluid_each=330)}
    {stepper_row("Recovery drink","500 ml each","recup",fluid_each=500)}
    {num_row("Water","Loose water after the finish",fmt(g('waterPost'),0)+" ml","ml")}
  </div>
</div>

<!-- SECTION 4 -->
<div class="card">
  <div class="sec-head">
    <div class="sec-num">4</div>
    <div><div class="sec-title">Weigh-In After Ride</div><div class="sec-sub">Post weigh-in</div></div>
  </div>
  <div class="card-body">
    {num_row("Weight after","At the weigh-in after the ride", postW_fmt+" kg","kg")}
  </div>
</div>

<!-- SECTION 5 -->
<div class="card">
  <div class="sec-head">
    <div class="sec-num">5</div>
    <div><div class="sec-title">Race Time</div><div class="sec-sub">Duration & results</div></div>
  </div>
  <div class="card-body">
    {num_row("Race time","Elapsed time of the stage",
             f"{int(g('raceH'))}h {int(g('raceM'))}min","")}
    <div class="res-grid">
      {res_tile(fmt(cr['carbs'],0),'g','Carbs · race')}
      {res_tile('—' if cr['carbs_h'] is None else str(round(cr['carbs_h'])),
                '' if cr['carbs_h'] is None else 'g/h','Carbs / h')}
      {res_tile(fmt(cr['fluid']/1000,2),'L','Fluid · race')}
      {res_tile('—' if cr['fluid_h'] is None else str(round(cr['fluid_h'])),
                '' if cr['fluid_h'] is None else 'ml/h','Fluid / h')}
      {res_tile('—' if cr['dehyd'] is None else fmt(cr['dehyd'],1),
                '' if cr['dehyd'] is None else '%','Dehydration',dc(cr['dehyd']))}
      {res_tile('—' if cr['sweat_rate'] is None else fmt(cr['sweat_rate'],2),
                '' if cr['sweat_rate'] is None else 'L/h','Sweat rate')}
    </div>
  </div>
</div>

<!-- SEND BAR -->
<div class="send-bar">
  <a href="{wa}" target="_blank" class="wa-btn">📱 WhatsApp</a>
  <div class="copy-btn" onclick="copyReport()">📋 Copy</div>
</div>

<a href="?reset=1" class="reset-btn">🔄 Reset stage {stg}</a>

<textarea id="rpt" style="position:absolute;left:-9999px">{txt}</textarea>
<script>
function copyReport(){{
  var t=document.getElementById('rpt');
  t.select(); t.setSelectionRange(0,99999);
  try{{navigator.clipboard.writeText(t.value)}}catch(e){{document.execCommand('copy')}}
  var b=document.querySelector('.copy-btn');
  b.textContent='✓ Copied!'; setTimeout(()=>b.textContent='📋 Copy',2000);
}}
</script>
</body>
</html>
"""

# ── render settings form for num inputs that need keyboard entry ────────
# Weight before, drink, other food/drinks, water post, weight after, race time
# These use st.number_input because keyboard entry is needed.
# Everything else is HTML links (no keyboard needed).

st.components.v1.html(HTML, height=2600, scrolling=True)

# Settings inputs rendered below via Streamlit for keyboard entry
with st.expander("⌨️  Enter values (weight, fluid amounts, race time)"):
    st.markdown("**Section 1 — Before the start**")
    c1,c2 = st.columns(2)
    with c1:
        v = st.number_input("Weight before (kg)", 0.0, 200.0, float(g('preW') or 0), 0.1, format="%.1f", key=f"preW_{stg}")
        sv('preW', v)
    with c2:
        v = st.number_input("Drink before start (ml)", 0, 5000, int(g('preDrink') or 0), 50, key=f"preDrink_{stg}")
        sv('preDrink', v)

    st.markdown("**Section 2 — During**")
    c1,c2,c3 = st.columns(3)
    with c1:
        v = st.number_input("Other food (g)", 0, 10000, int(g('otherFood') or 0), 1, key=f"of_{stg}")
        sv('otherFood', v)
    with c2:
        v = st.number_input("Other drinks (ml)", 0, 10000, int(g('otherDrinks') or 0), 50, key=f"od_{stg}")
        sv('otherDrinks', v)
    with c3:
        v = st.number_input("Bottle vol (ml)", 100, 2000, int(g('bidonVol') or 500), 50, key=f"bv_{stg}")
        sv('bidonVol', v)

    st.markdown("**Section 2 — Pee**")
    c1,c2 = st.columns(2)
    with c1:
        v = st.number_input("Pee volume (ml)", 0, 5000, int(g('peeMl') or 0), 50, key=f"pml_{stg}")
        sv('peeMl', v)

    st.markdown("**Section 3 — After ride**")
    v = st.number_input("Water after finish (ml)", 0, 5000, int(g('waterPost') or 0), 50, key=f"wp_{stg}")
    sv('waterPost', v)

    st.markdown("**Section 4 — Weight after**")
    v = st.number_input("Weight after (kg)", 0.0, 200.0, float(g('postW') or 0), 0.1, format="%.1f", key=f"postW_{stg}")
    sv('postW', v)

    st.markdown("**Section 5 — Race time**")
    c1,c2 = st.columns(2)
    with c1:
        v = st.number_input("Hours", 0, 24, int(g('raceH') or 0), key=f"rh_{stg}")
        sv('raceH', v)
    with c2:
        v = st.number_input("Minutes", 0, 59, int(g('raceM') or 0), key=f"rm_{stg}")
        sv('raceM', v)

    if st.button("↑ Update display", key="refresh"):
        st.rerun()
