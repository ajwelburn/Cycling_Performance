import streamlit as st
import streamlit.components.v1 as components
import urllib.parse
import json

st.set_page_config(
    page_title="FuelPro · Ride Log",
    page_icon="🚴",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
header[data-testid="stHeader"],footer,#MainMenu,
[data-testid="stSidebar"],[data-testid="collapsedControl"]{display:none!important}
[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:#F4F1EA!important}
[data-testid="block-container"]{max-width:580px!important;padding:0!important}
[data-testid="stVerticalBlock"]{gap:0!important}
iframe{display:block;border:none}
</style>
""", unsafe_allow_html=True)

HTML = """<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<style>
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
body{font-family:-apple-system,'Hanken Grotesk',Arial,sans-serif;
     background:#F4F1EA;color:#16140F;padding-bottom:30px;font-size:15px}

/* HEADER */
.hdr{background:
  linear-gradient(157deg,rgba(8,9,24,.45),rgba(8,9,24,0) 58%),
  radial-gradient(120% 80% at 85% 110%,rgba(239,74,59,.55),transparent 60%),
  linear-gradient(157deg,#12122a,#20264f 19%,#43275f 39%,#8a2a5e 57%,#cf2c47 77%,#ef4a3b);
  border-bottom:4px solid #E5343A}
.stripe{height:5px;background:repeating-linear-gradient(135deg,#2F3C82 0 12px,#E5343A 12px 24px)}
.hdr-inner{padding:18px 16px 16px}
.hdr-title{font-family:Anton,Impact,sans-serif;font-size:42px;line-height:.9;
  text-transform:uppercase;color:#fff;text-shadow:0 2px 12px rgba(0,0,0,.3)}
.hdr-title span{color:#FFD7CF}
.hdr-sub{margin:10px 0 0;color:rgba(255,255,255,.78);font-size:13px}

/* CARDS */
.card{background:#fff;border:1px solid #E2DDD1;border-radius:14px;
  box-shadow:0 2px 12px rgba(22,20,15,.07);margin:12px 12px 0;overflow:hidden}
.sec-head{display:flex;align-items:center;gap:12px;padding:14px 16px;
  border-bottom:1px solid #E2DDD1;background:linear-gradient(#fff,#FBFAF6)}
.sec-num{width:34px;height:34px;min-width:34px;border-radius:9px;
  background:#1E274F;color:#fff;display:flex;align-items:center;
  justify-content:center;font-family:Anton,sans-serif;font-size:17px}
.sec-title{font-family:Anton,sans-serif;font-size:18px;letter-spacing:.4px;
  text-transform:uppercase;color:#16140F;line-height:1.1}
.sec-sub{font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:#6B6760;
  margin-top:2px;font-family:monospace}
.card-body{padding:6px 14px 10px}

/* STAGE */
.stage-wrap{background:#fff;border:1px solid #E2DDD1;border-radius:14px;
  margin:12px 12px 0;padding:12px 14px}
.stage-lbl{font-size:10px;letter-spacing:.18em;text-transform:uppercase;
  color:#6B6760;font-weight:700;font-family:monospace;margin-bottom:8px}
.stage-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:8px}
.chip{height:48px;border-radius:10px;border:1.5px solid #E2DDD1;
  background:#FBFAF6;font-family:Anton,sans-serif;font-size:20px;
  color:#16140F;cursor:pointer;display:flex;align-items:center;
  justify-content:center;user-select:none;transition:.1s}
.chip:active{transform:scale(.93)}
.chip.active{background:#2F3C82;color:#fff;border-color:#1E274F;
  box-shadow:0 2px 8px rgba(47,60,130,.4)}

/* URINE */
.urine-lbl{font-weight:700;font-size:15px;margin:10px 0 3px}
.urine-hint{font-size:11px;color:#6B6760;margin-bottom:10px;line-height:1.4}
.urine-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:8px}
.swatch{height:64px;border-radius:10px;border:2px solid rgba(0,0,0,.1);
  display:flex;align-items:center;justify-content:center;
  font-family:monospace;font-size:15px;font-weight:900;
  cursor:pointer;user-select:none;transition:.12s}
.swatch:active{transform:scale(.92)}
.swatch.active{border:3px solid #2F3C82;box-shadow:0 0 0 3px rgba(47,60,130,.25);
  transform:translateY(-3px)}

/* ROWS */
hr{border:none;border-top:1px solid #E2DDD1;margin:0}
.row{display:flex;align-items:center;justify-content:space-between;
  gap:10px;padding:10px 0}
.row-left{flex:1;min-width:0}
.row-lbl{font-weight:700;font-size:15px}
.row-hint{font-size:11px;color:#6B6760;margin-top:2px}
.row-sub{font-size:11px;font-weight:700;color:#2F3C82;margin-left:4px}

/* STEPPER */
.stepper{display:flex;align-items:center;flex-shrink:0}
.s-btn{width:52px;height:52px;display:flex;align-items:center;justify-content:center;
  font-size:26px;font-weight:900;cursor:pointer;user-select:none;
  border:1.5px solid #E2DDD1;transition:.1s}
.s-btn:active{opacity:.7}
.s-minus{background:#FFF0F0;color:#C0392B;border-color:#F5C6C6;
  border-radius:10px 0 0 10px}
.s-plus{background:#EEF2FF;color:#2F3C82;border-color:#C6CEEF;
  border-radius:0 10px 10px 0}
.s-val{width:56px;height:52px;display:flex;align-items:center;justify-content:center;
  background:#fff;border-top:1.5px solid #E2DDD1;border-bottom:1.5px solid #E2DDD1;
  font-family:monospace;font-weight:700;font-size:24px;color:#16140F;
  text-align:center;line-height:52px}

/* NUMBER INPUT ROW */
.num-right{display:flex;align-items:center;flex-shrink:0}
.num-input{height:52px;width:100px;border:1.5px solid #E2DDD1;
  border-radius:10px 0 0 10px;border-right:none;
  font-family:monospace;font-weight:700;font-size:20px;
  text-align:center;background:#fff;color:#16140F;
  display:flex;align-items:center;justify-content:center;
  padding:0;line-height:52px;
  -moz-appearance:textfield}
.num-input::-webkit-inner-spin-button,.num-input::-webkit-outer-spin-button{display:none}
.num-input:focus{outline:none;border-color:#2F3C82;
  box-shadow:0 0 0 3px rgba(47,60,130,.15)}
.unit-box{height:52px;min-width:42px;display:flex;align-items:center;
  justify-content:center;background:#F0EDE5;border:1.5px solid #E2DDD1;
  border-radius:0 10px 10px 0;font-family:monospace;font-size:13px;
  font-weight:700;color:#4A463C;padding:0 10px}

/* NOTE */
.note{background:#FFF5F5;border-left:4px solid #E5343A;border-radius:8px;
  padding:10px 12px;margin:8px 0;font-size:12px;font-weight:600;color:#6B1A1A}

/* RESULTS */
.res-grid{display:grid;grid-template-columns:1fr 1fr;gap:5px;margin-top:10px}
.res-tile{background:#14132A;border-radius:10px;padding:14px 12px}
.res-val{font-family:monospace;font-weight:700;font-size:22px;
  color:#fff;line-height:1;display:flex;align-items:baseline;gap:3px}
.res-unit{font-size:11px;font-weight:500;color:rgba(255,255,255,.45)}
.res-lbl{font-size:9px;letter-spacing:.07em;text-transform:uppercase;
  color:rgba(255,255,255,.45);margin-top:6px;font-weight:700}

/* SEND */
.send-wrap{margin:16px 12px 0;display:flex;gap:8px}
.wa-btn{flex:1;background:#25D366;color:#063d1c;border-radius:14px;
  padding:17px 8px;text-align:center;font-weight:800;font-size:15px;
  cursor:pointer;user-select:none;
  box-shadow:0 4px 14px rgba(37,211,102,.35);
  display:flex;align-items:center;justify-content:center;gap:6px;
  transition:.15s}
.wa-btn:active{transform:scale(.97);box-shadow:0 2px 6px rgba(37,211,102,.2)}
.copy-btn{flex:1;background:#2F3C82;color:#fff;border-radius:14px;
  padding:17px 8px;text-align:center;font-weight:800;font-size:15px;
  cursor:pointer;user-select:none;
  box-shadow:0 4px 14px rgba(47,60,130,.3);
  display:flex;align-items:center;justify-content:center;gap:6px;
  transition:.15s}
.copy-btn:active{transform:scale(.97)}
.reset-wrap{margin:10px 12px 4px;display:flex;align-items:center;
  background:#fff;border:1.5px solid #E2DDD1;border-radius:12px;
  overflow:hidden}
.reset-btn{flex:1;display:flex;align-items:center;justify-content:center;
  gap:8px;padding:14px;cursor:pointer;user-select:none;
  font-weight:700;font-size:14px;color:#B11F26;transition:.12s}
.reset-btn:active{background:#FFF5F5}
.reset-divider{width:1px;background:#E2DDD1;align-self:stretch}

/* TOAST */
.toast{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);
  background:#1E7A4E;color:#fff;padding:10px 20px;border-radius:30px;
  font-weight:700;font-size:14px;opacity:0;transition:.3s;pointer-events:none;
  white-space:nowrap;z-index:99}
.toast.show{opacity:1}
</style>
</head>
<body>

<div class="hdr">
  <div class="stripe"></div>
  <div class="hdr-inner">
    <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px">
      <div>
        <div class="hdr-title">RIDE<span>·</span>LOG</div>
        <p class="hdr-sub">Fill in after each stage · tap Send when done</p>
      </div>
      <div onclick="resetStage()" style="flex-shrink:0;margin-top:4px;
           background:rgba(255,255,255,.15);border:1.5px solid rgba(255,255,255,.35);
           border-radius:10px;padding:9px 13px;cursor:pointer;
           font-size:12px;font-weight:700;color:#fff;white-space:nowrap;
           display:flex;align-items:center;gap:5px;backdrop-filter:blur(4px);
           transition:.12s" onmouseover="this.style.background='rgba(255,255,255,.25)'"
           onmouseout="this.style.background='rgba(255,255,255,.15)'"
           onmousedown="this.style.transform='scale(.94)'"
           onmouseup="this.style.transform='scale(1)'">
        🔄 Reset
      </div>
    </div>
  </div>
</div>

<!-- STAGE -->
<div class="stage-wrap">
  <div class="stage-lbl">Stage</div>
  <div class="stage-grid" id="stageRow1"></div>
  <div class="stage-grid" id="stageRow2"></div>
</div>

<!-- SECTION 1 -->
<div class="card">
  <div class="sec-head">
    <div class="sec-num">1</div>
    <div><div class="sec-title">Before the Start</div><div class="sec-sub">Pre-stage</div></div>
  </div>
  <div class="card-body">
    <div class="urine-lbl">Urine colour</div>
    <div class="urine-hint">Tap the shade that matches — 1 = pale (well hydrated), 8 = dark (dehydrated)</div>
    <div class="urine-grid" id="urineRow1"></div>
    <div class="urine-grid" id="urineRow2"></div>

    <hr>
    <div class="row">
      <div class="row-left">
        <div class="row-lbl">Weight before</div>
        <div class="row-hint">At the weigh-in, just before the race</div>
      </div>
      <div class="num-right">
        <input class="num-input" type="number" id="preW" min="0" max="200" step="0.1"
               inputmode="decimal" placeholder="0.0">
        <div class="unit-box">kg</div>
      </div>
    </div>
    <hr>
    <div class="row">
      <div class="row-left">
        <div class="row-lbl">Drink before start</div>
        <div class="row-hint">Between weigh-in and the start</div>
      </div>
      <div class="num-right">
        <input class="num-input" type="number" id="preDrink" min="0" max="5000" step="50"
               inputmode="numeric" placeholder="0">
        <div class="unit-box">ml</div>
      </div>
    </div>
  </div>
</div>

<!-- SECTION 2 -->
<div class="card">
  <div class="sec-head">
    <div class="sec-num">2</div>
    <div><div class="sec-title">During the Ride</div><div class="sec-sub">On the bike</div></div>
  </div>
  <div class="card-body" id="section2body">
    <!-- steppers injected by JS -->
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
    <div id="section3body"></div>
    <hr>
    <div class="row">
      <div class="row-left">
        <div class="row-lbl">Water</div>
        <div class="row-hint">Loose water after the finish</div>
      </div>
      <div class="num-right">
        <input class="num-input" type="number" id="waterPost" min="0" max="5000" step="50"
               inputmode="numeric" placeholder="0">
        <div class="unit-box">ml</div>
      </div>
    </div>
  </div>
</div>

<!-- SECTION 4 -->
<div class="card">
  <div class="sec-head">
    <div class="sec-num">4</div>
    <div><div class="sec-title">Weigh-In After Ride</div><div class="sec-sub">Post weigh-in</div></div>
  </div>
  <div class="card-body">
    <div class="row">
      <div class="row-left">
        <div class="row-lbl">Weight after</div>
        <div class="row-hint">At the weigh-in after the ride</div>
      </div>
      <div class="num-right">
        <input class="num-input" type="number" id="postW" min="0" max="200" step="0.1"
               inputmode="decimal" placeholder="0.0">
        <div class="unit-box">kg</div>
      </div>
    </div>
  </div>
</div>

<!-- SECTION 5 -->
<div class="card">
  <div class="sec-head">
    <div class="sec-num">5</div>
    <div><div class="sec-title">Race Time</div><div class="sec-sub">Duration &amp; results</div></div>
  </div>
  <div class="card-body">
    <div class="row">
      <div class="row-left">
        <div class="row-lbl">Total race time</div>
        <div class="row-hint">Elapsed time of the stage</div>
      </div>
      <div style="display:flex;gap:6px;flex-shrink:0">
        <div class="num-right">
          <input class="num-input" type="number" id="raceH" min="0" max="24" step="1"
                 inputmode="numeric" placeholder="0" style="width:70px">
          <div class="unit-box">h</div>
        </div>
        <div class="num-right">
          <input class="num-input" type="number" id="raceM" min="0" max="59" step="1"
                 inputmode="numeric" placeholder="0" style="width:70px">
          <div class="unit-box">min</div>
        </div>
      </div>
    </div>
    <div class="res-grid" id="results"></div>
  </div>
</div>

<!-- SEND -->
<div class="send-wrap">
  <div class="wa-btn" onclick="openWhatsApp()">📱 WhatsApp</div>
  <div class="copy-btn" onclick="copyReport()">📋 Copy</div>
</div>
<div class="reset-wrap">
  <div class="reset-btn" onclick="resetStage()">
    <span style="font-size:18px">🔄</span>
    <span>Reset Stage <span id="resetStageNum">1</span></span>
  </div>
</div>

<div class="toast" id="toast">Copied ✓</div>
<textarea id="rptArea" style="position:absolute;opacity:0;pointer-events:none;top:0;left:0;width:1px;height:1px"></textarea>

<script>
// ── SWATCHES ─────────────────────────────────────────────────────────
const SWATCHES=[
  {bg:'#FFFDE8',tc:'#7a7440'},{bg:'#FFFAB6',tc:'#7a7440'},
  {bg:'#F8EF66',tc:'#4a4810'},{bg:'#FDE11C',tc:'#4a4810'},
  {bg:'#ECD247',tc:'#4a4810'},{bg:'#E4C306',tc:'#3d3a00'},
  {bg:'#DAB002',tc:'#fff'},{bg:'#8C881C',tc:'#fff'}
];

// ── STATE ─────────────────────────────────────────────────────────────
const KEY = 'fuelpro_v2';
function blankStage(){
  return {gels:0,chews:0,bars:0,bidonsKH:0,bidons60:0,bidonsW:0,
          peeStops:0,peeMl:0,soda:0,recup:0,
          preW:'',preDrink:'',otherFood:'',otherDrinks:'',
          bidonVol:500,waterPost:'',postW:'',raceH:'',raceM:'',urine:null};
}
function load(){
  try{return JSON.parse(sessionStorage.getItem(KEY))||{stage:1,stages:{}};}catch{return{stage:1,stages:{}};}
}
function save(state){sessionStorage.setItem(KEY,JSON.stringify(state));}
function stageData(state){
  if(!state.stages[state.stage]) state.stages[state.stage]=blankStage();
  return state.stages[state.stage];
}

let STATE=load();

// ── CALC ──────────────────────────────────────────────────────────────
function calc(d){
  const bv=parseFloat(d.bidonVol)||500, sc=bv/500;
  const h=(parseFloat(d.raceH)||0)+(parseFloat(d.raceM)||0)/60;
  const carbs=d.gels*40+d.chews*35+d.bars*30+d.bidonsKH*30*sc+d.bidons60*60*sc;
  const fluid=(d.bidonsKH+d.bidons60+d.bidonsW)*bv+(parseFloat(d.otherDrinks)||0);
  const preD=parseFloat(d.preDrink)||0;
  const postF=d.soda*330+d.recup*500+(parseFloat(d.waterPost)||0);
  const pee=parseFloat(d.peeMl)>0?parseFloat(d.peeMl):d.peeStops*300;
  const pre=parseFloat(d.preW)||0, post=parseFloat(d.postW)||0;
  const m0=pre>0?pre+preD/1000:null;
  const m1=post>0?post-postF/1000:null;
  const deficit=(m0&&m1)?m0-m1:null;
  const dehyd=(deficit!==null&&m0)?deficit/m0*100:null;
  const sweat=deficit!==null?deficit+fluid/1000-pee/1000:null;
  const sr=(sweat!==null&&h>0)?sweat/h:null;
  return{bv,sc,h,carbs,fluid,
    carbs_h:h>0?carbs/h:null,fluid_h:h>0?fluid/h:null,
    dehyd,sweat_rate:sr};
}

function fmt(v,dec){
  if(v===null||v===undefined||isNaN(v))return'—';
  return v.toFixed(dec);
}

// ── RENDER STAGES ─────────────────────────────────────────────────────
function renderStages(){
  for(let row=0;row<2;row++){
    const el=document.getElementById('stageRow'+(row+1));
    el.innerHTML='';
    for(let i=1;i<=4;i++){
      const n=row*4+i;
      const d=document.createElement('div');
      d.className='chip'+(STATE.stage===n?' active':'');
      d.textContent=n;
      d.onclick=()=>{STATE.stage=n;save(STATE);renderAll();};
      el.appendChild(d);
    }
  }
}

// ── RENDER URINE ──────────────────────────────────────────────────────
function renderUrine(){
  const d=stageData(STATE);
  for(let row=0;row<2;row++){
    const el=document.getElementById('urineRow'+(row+1));
    el.innerHTML='';
    for(let i=1;i<=4;i++){
      const v=row*4+i;
      const sw=SWATCHES[v-1];
      const sel=d.urine===v;
      const div=document.createElement('div');
      div.className='swatch'+(sel?' active':'');
      div.style.background=sw.bg;
      div.style.color=sw.tc;
      div.textContent=sel?'✓':String(v);
      div.onclick=()=>{d.urine=v;save(STATE);renderUrine();updateResults();};
      el.appendChild(div);
    }
  }
}

// ── RENDER STEPPERS ───────────────────────────────────────────────────
function makeStepperHTML(label,hint,field,carbsEach,fluidEach){
  const d=stageData(STATE);
  const val=d[field]||0;
  const bv=parseFloat(d.bidonVol)||500;
  const parts=[];
  if(carbsEach>0)parts.push('<b>'+val*carbsEach+'g</b>');
  if(fluidEach>0)parts.push(val*fluidEach+'ml');
  const sub=parts.length&&val>0?'<span class="row-sub">'+parts.join('·')+'</span>':'';
  return `<hr><div class="row">
  <div class="row-left">
    <div class="row-lbl">${label}${sub}</div>
    <div class="row-hint">${hint}</div>
  </div>
  <div class="stepper">
    <div class="s-btn s-minus" onclick="step('${field}',-1)">−</div>
    <div class="s-val" id="sv_${field}">${val}</div>
    <div class="s-btn s-plus" onclick="step('${field}',1)">+</div>
  </div>
</div>`;
}

function step(field,delta){
  const d=stageData(STATE);
  d[field]=Math.max(0,(d[field]||0)+delta);
  save(STATE);
  // update just the value display and subtotal — no full re-render
  const el=document.getElementById('sv_'+field);
  if(el)el.textContent=d[field];
  // re-render the label to update subtotal
  renderSection2();
  renderSection3();
  updateResults();
}

function renderSection2(){
  const d=stageData(STATE);
  const bv=parseFloat(d.bidonVol)||500, sc=bv/500;
  const c30=Math.round(30*sc), c60=Math.round(60*sc);
  document.getElementById('section2body').innerHTML=
    makeStepperHTML('Gels','45 g · 40 g carbs','gels',40,0)+
    makeStepperHTML('Chews','44 g · 35 g carbs','chews',35,0)+
    makeStepperHTML('Bars','35 g · 30 g carbs','bars',30,0)+
    makeStepperHTML('Bottles · 30 g',c30+' g carbs at '+bv+' ml','bidonsKH',c30,bv)+
    makeStepperHTML('Bottles · 60 g',c60+' g carbs at '+bv+' ml','bidons60',c60,bv)+
    makeStepperHTML('Bottles · water','water only · '+bv+' ml each','bidonsW',0,bv)+
    `<hr><div class="row">
      <div class="row-left"><div class="row-lbl">Other food</div>
        <div class="row-hint">Total weight of any extra food</div></div>
      <div class="num-right">
        <input class="num-input" type="number" id="otherFood" min="0" max="10000" step="1"
               inputmode="numeric" placeholder="0">
        <div class="unit-box">g</div></div></div>
    <hr><div class="row">
      <div class="row-left"><div class="row-lbl">Other drinks</div>
        <div class="row-hint">Any extra drinks on the bike</div></div>
      <div class="num-right">
        <input class="num-input" type="number" id="otherDrinks" min="0" max="10000" step="50"
               inputmode="numeric" placeholder="0">
        <div class="unit-box">ml</div></div></div>
    <hr><div class="row">
      <div class="row-left"><div class="row-lbl">Volume per bottle</div>
        <div class="row-hint">Default 500 ml</div></div>
      <div class="num-right">
        <input class="num-input" type="number" id="bidonVol" min="100" max="2000" step="50"
               inputmode="numeric">
        <div class="unit-box">ml</div></div></div>
    <hr><div class="row">
      <div class="row-left"><div class="row-lbl">Pee stops</div></div>
      <div class="stepper">
        <div class="s-btn s-minus" onclick="step('peeStops',-1)">−</div>
        <div class="s-val" id="sv_peeStops">${d.peeStops||0}</div>
        <div class="s-btn s-plus" onclick="step('peeStops',1)">+</div>
      </div></div>
    <hr><div class="row">
      <div class="row-left"><div class="row-lbl">Pee volume</div>
        <div class="row-hint">Optional — if measured</div></div>
      <div class="num-right">
        <input class="num-input" type="number" id="peeMl" min="0" max="5000" step="50"
               inputmode="numeric" placeholder="0">
        <div class="unit-box">ml</div></div></div>`;
  bindInputs();
}

function renderSection3(){
  const d=stageData(STATE);
  document.getElementById('section3body').innerHTML=
    makeStepperHTML('Soda','330 ml each','soda',0,330)+
    makeStepperHTML('Recovery drink','500 ml each','recup',0,500);
}

// ── BIND INPUTS ───────────────────────────────────────────────────────
function bindInputs(){
  const d=stageData(STATE);
  const ids=['preW','preDrink','otherFood','otherDrinks','bidonVol',
             'peeMl','waterPost','postW','raceH','raceM'];
  ids.forEach(id=>{
    const el=document.getElementById(id);
    if(!el)return;
    el.value=d[id]!==''&&d[id]!==null&&d[id]!==undefined?d[id]:'';
    el.oninput=()=>{
      d[id]=el.value===''?'':parseFloat(el.value)||el.value;
      save(STATE);
      if(id==='bidonVol'){renderSection2();}
      updateResults();
    };
  });
}

// ── RESULTS ───────────────────────────────────────────────────────────
function dehColor(v){
  if(v===null)return'#fff';
  return v>3?'#FB7185':v>2?'#FBBF24':'#5BE08A';
}
function tile(val,unit,lbl,col){
  col=col||'#fff';
  return`<div class="res-tile">
    <div class="res-val" style="color:${col}">${val}<span class="res-unit">${unit}</span></div>
    <div class="res-lbl">${lbl}</div></div>`;
}
function updateResults(){
  const d=stageData(STATE);
  const c=calc(d);
  const dc=dehColor(c.dehyd);
  document.getElementById('results').innerHTML=
    tile(fmt(c.carbs,0),'g','Carbs · race')+
    tile(c.carbs_h===null?'—':Math.round(c.carbs_h),c.carbs_h===null?'':'g/h','Carbs / h')+
    tile(fmt(c.fluid/1000,2),'L','Fluid · race')+
    tile(c.fluid_h===null?'—':Math.round(c.fluid_h),c.fluid_h===null?'':'ml/h','Fluid / h')+
    tile(c.dehyd===null?'—':fmt(c.dehyd,1),c.dehyd===null?'':'%','Dehydration',dc)+
    tile(c.sweat_rate===null?'—':fmt(c.sweat_rate,2),c.sweat_rate===null?'':'L/h','Sweat rate');
}

// ── REPORT ────────────────────────────────────────────────────────────
function buildReport(){
  const d=stageData(STATE);
  const c=calc(d);
  const bv=parseFloat(d.bidonVol)||500;
  const c30=Math.round(30*(bv/500)), c60=Math.round(60*(bv/500));
  const h=Math.floor(c.h), m=Math.round((c.h-h)*60);
  const lines=[
    '🚴 FUELPRO — RIDE LOG','Stage '+STATE.stage,'',
    '— BEFORE THE START —',
    'Urine colour: '+(d.urine||'—'),
    'Weight before: '+(d.preW||0)+' kg',
    'Drink before: '+(d.preDrink||0)+' ml','',
    '— DURING THE RIDE —',
    'Gels: '+d.gels+'  ('+(d.gels*40)+'g carbs)',
    'Chews: '+d.chews+'  ('+(d.chews*35)+'g carbs)',
    'Bars: '+d.bars+'  ('+(d.bars*30)+'g carbs)',
    'Bottles 30g·'+bv+'ml: '+d.bidonsKH+'  ('+(d.bidonsKH*c30)+'g·'+(d.bidonsKH*bv)+'ml)',
    'Bottles 60g·'+bv+'ml: '+d.bidons60+'  ('+(d.bidons60*c60)+'g·'+(d.bidons60*bv)+'ml)',
    'Bottles water: '+d.bidonsW+'  ('+(d.bidonsW*bv)+'ml)',
    'Other food: '+(d.otherFood||0)+'g',
    'Other drinks: '+(d.otherDrinks||0)+'ml',
    'Pee stops: '+d.peeStops,'',
    '— AFTER THE RIDE —',
    'Soda: '+d.soda+'  ('+(d.soda*330)+'ml)',
    'Recovery: '+d.recup+'  ('+(d.recup*500)+'ml)',
    'Water: '+(d.waterPost||0)+'ml','',
    '— WEIGH-IN —','Weight after: '+(d.postW||0)+' kg','',
    '— RACE TIME —',h+'h '+m+'min','',
    '— RESULTS —',
    'Carbs: '+fmt(c.carbs,0)+'g',
    'Carbs/h: '+(c.carbs_h===null?'—':Math.round(c.carbs_h)+'g/h'),
    'Fluid: '+fmt(c.fluid/1000,2)+'L',
    'Fluid/h: '+(c.fluid_h===null?'—':Math.round(c.fluid_h)+'ml/h'),
    'Dehydration: '+(c.dehyd===null?'—':fmt(c.dehyd,1)+'%'),
    'Sweat rate: '+(c.sweat_rate===null?'—':fmt(c.sweat_rate,2)+'L/h')
  ];
  return lines.join('\\n');
}

function openWhatsApp(){
  const txt = buildReport();
  const url = 'https://wa.me/?text=' + encodeURIComponent(txt);
  window.open(url, '_blank');
}

function copyReport(){
  const txt=buildReport();
  const area=document.getElementById('rptArea');
  area.value=txt;
  if(navigator.clipboard){
    navigator.clipboard.writeText(txt).then(showToast).catch(()=>fallbackCopy(area));
  } else {fallbackCopy(area);}
}
function fallbackCopy(area){
  area.select();area.setSelectionRange(0,99999);
  document.execCommand('copy');showToast();
}
function showToast(){
  const t=document.getElementById('toast');
  t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'),2000);
}

function resetStage(){
  if(!confirm('Reset Stage '+STATE.stage+'?')) return;
  STATE.stages[STATE.stage]=blankStage();
  save(STATE);renderAll();
}

// ── FULL RENDER ───────────────────────────────────────────────────────
function renderAll(){
  renderStages();
  renderUrine();
  renderSection2();
  renderSection3();
  bindInputs();
  updateResults();
  const el = document.getElementById('resetStageNum');
  if(el) el.textContent = STATE.stage;
}

// ── AUTO-RESIZE: tell parent iframe how tall we are ───────────────────
function sendHeight(){
  const h = document.body.scrollHeight;
  window.parent.postMessage({type:'setHeight',height:h},'*');
}
// Send after every render and on any DOM mutation
const ro = new ResizeObserver(sendHeight);
ro.observe(document.body);

// ── INIT ──────────────────────────────────────────────────────────────
renderAll();
sendHeight();
</script>
</body>
</html>"""

# Receive height messages and resize the iframe via a wrapper component
import streamlit.components.v1 as components

# Inject a listener in the Streamlit page that resizes the iframe
st.markdown("""
<style>
#fuelpro-frame { width:100%; border:none; display:block; }
</style>
<script>
window.addEventListener('message', function(e){
  if(e.data && e.data.type === 'setHeight'){
    var f = document.getElementById('fuelpro-frame');
    if(f) f.style.height = (e.data.height + 8) + 'px';
  }
});
</script>
""", unsafe_allow_html=True)

components.html(HTML, height=2900, scrolling=False)
