import streamlit as st
import json, time, uuid
from pathlib import Path
import sys, importlib.util
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import load_state, save_state, STARTING_CASH, ROUND_DURATION
from streamlit_autorefresh import st_autorefresh

BREAK_DURATION = 300

st.set_page_config(page_title="Market Mayhem — Inceptia", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")
st_autorefresh(interval=1000, key="trade_refresh")

# FIX 1: JS-driven countdown — no Streamlit reruns needed for the timer
# Timer runs purely in JS, progress bar animates smoothly in CSS
# Streamlit only reruns for data (prices, news) every 8s — much less laggy

st.markdown("""
<style>
#MainMenu, header, footer { visibility: hidden; }
[data-testid="stSidebarNav"],[data-testid="stSidebar"],[data-testid="collapsedControl"],[data-testid="stToolbar"],.stDeployButton,div[data-testid="stDecoration"],div[data-testid="stStatusWidget"] { display: none !important; }
.block-container { padding-top: 0 !important; margin-top: 0 !important; }
div[data-testid="stAppViewContainer"] > section > div { padding-top: 0 !important; }

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&family=Space+Grotesk:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.ticker-wrap { width:100%; overflow:hidden; background:#0a0a0f; border-bottom:1px solid #1e2030; padding:12px 0; }
.ticker { display:flex; white-space:nowrap; animation:ticker 40s linear infinite; }
.ticker-item { display:inline-block; padding:0 40px; font-size:15px; font-family:'Space Grotesk',monospace; letter-spacing:0.5px; color:#888; }
.ticker-item .sym { color:#fff; font-weight:700; margin-right:8px; }
.ticker-item .up { color:#00C896; } .ticker-item .down { color:#FF4D6A; }
@keyframes ticker { 0%{transform:translateX(0)} 100%{transform:translateX(-50%)} }

.hero { background:linear-gradient(135deg,#0d0f1a 0%,#111420 50%,#0a1628 100%); border:1px solid #1e2535; border-radius:16px; padding:80px 48px; text-align:center; position:relative; overflow:hidden; margin-bottom:32px; }
.hero::before { content:''; position:absolute; top:-100px; left:50%; transform:translateX(-50%); width:600px; height:300px; background:radial-gradient(ellipse,rgba(0,200,150,0.08) 0%,transparent 70%); pointer-events:none; }
.hero-tag { display:inline-block; font-size:13px; font-weight:700; letter-spacing:4px; text-transform:uppercase; color:#00C896; border:1px solid rgba(0,200,150,0.3); padding:6px 18px; border-radius:99px; margin-bottom:20px; }
.hero h1 { font-family:'Space Grotesk',sans-serif; font-size:56px; font-weight:700; color:#ffffff; letter-spacing:-2px; line-height:1; margin-bottom:12px; }
.hero h1 span { color:#00C896; }
.hero p { font-size:16px; color:rgba(255,255,255,0.4); }

.phase-banner { padding:14px 20px; border-radius:10px; font-size:14px; font-weight:500; margin-bottom:16px; border:1px solid; }
.phase-lobby   { background:rgba(255,200,0,0.06);  border-color:rgba(255,200,0,0.2);  color:#ffd93d; }
.phase-trading { background:rgba(0,200,150,0.06);  border-color:rgba(0,200,150,0.2);  color:#00C896; }
.phase-between { background:rgba(255,140,0,0.06);  border-color:rgba(255,140,0,0.2);  color:#ff9a3c; }
.phase-ended   { background:rgba(255,77,106,0.06); border-color:rgba(255,77,106,0.2); color:#FF4D6A; }

/* JS countdown bar handled inline via components.html */

.metric-row { display:grid; gap:12px; margin-bottom:20px; }
.metric-card { background:#0d0f1a; border:1px solid #1e2535; border-radius:12px; padding:16px 20px; }
.metric-card .label { font-size:11px; color:rgba(255,255,255,0.35); font-weight:500; letter-spacing:1px; text-transform:uppercase; margin-bottom:6px; }
.metric-card .value { font-size:22px; font-weight:600; font-family:'Space Grotesk',monospace; }
.metric-card .delta { font-size:12px; margin-top:4px; }
.delta-up { color:#00C896; } .delta-down { color:#FF4D6A; } .delta-neutral { color:rgba(255,255,255,0.3); }

/* FIX 3: Nav buttons — no emojis, bigger font, coloured matching metric tiles */
.nav-row { display:grid; grid-template-columns:repeat(4,1fr); gap:0; margin-bottom:24px; border-radius:12px; overflow:hidden; border:1px solid #1e2535; }
.nav-btn { padding:16px 8px; text-align:center; cursor:pointer; font-size:15px; font-weight:700; letter-spacing:0.5px; text-transform:uppercase; border-right:1px solid #1e2535; transition:all 0.15s; user-select:none; }
.nav-btn:last-child { border-right:none; }
/* Colours match metric tiles: Market=green, Intel=yellow, Banks=purple, Portfolio=blue */
.nav-market  { background:rgba(0,200,150,0.07);  color:rgba(0,200,150,0.5); }
.nav-intel   { background:rgba(255,211,61,0.06); color:rgba(255,211,61,0.5); }
.nav-banks   { background:rgba(167,139,250,0.07);color:rgba(167,139,250,0.5); }
.nav-portf   { background:rgba(79,142,247,0.07); color:rgba(79,142,247,0.5); }
.nav-market.nav-active  { background:rgba(0,200,150,0.15);  color:#00C896; }
.nav-intel.nav-active   { background:rgba(255,211,61,0.14); color:#ffd93d; }
.nav-banks.nav-active   { background:rgba(167,139,250,0.15);color:#a78bfa; }
.nav-portf.nav-active   { background:rgba(79,142,247,0.15); color:#4f8ef7; }
.nav-notif { display:inline-block; background:#FF4D6A; color:#fff; font-size:9px; font-weight:700; padding:1px 5px; border-radius:99px; margin-left:5px; vertical-align:middle; }

.section-hdr { font-family:'Space Grotesk',sans-serif; font-size:18px; font-weight:600; color:#fff; margin:0 0 16px; letter-spacing:-0.3px; border-bottom:1px solid #1e2535; padding-bottom:10px; }

.company-card { background:#0d0f1a; border:1px solid #1e2535; padding:20px 24px; }
.company-name { font-size:16px; font-weight:600; color:#fff; }
.company-meta { font-size:12px; color:rgba(255,255,255,0.35); margin-top:2px; }
.company-trait { font-size:12px; color:rgba(255,255,255,0.45); font-style:italic; margin-top:4px; }
.price-main { font-size:22px; font-weight:700; color:#fff; font-family:'Space Grotesk',monospace; }
.price-chg { font-size:13px; margin-top:2px; }
.risk-badge { display:inline-block; font-size:10px; font-weight:600; padding:3px 10px; border-radius:99px; letter-spacing:0.5px; text-transform:uppercase; margin-left:8px; }
.risk-low         { background:rgba(0,200,150,0.1);  color:#00C896; border:1px solid rgba(0,200,150,0.2); }
.risk-medium      { background:rgba(255,200,0,0.1);  color:#ffd93d; border:1px solid rgba(255,200,0,0.2); }
.risk-high        { background:rgba(255,77,106,0.1); color:#FF4D6A; border:1px solid rgba(255,77,106,0.2); }
.risk-medium-high { background:rgba(255,140,0,0.1);  color:#ff9a3c; border:1px solid rgba(255,140,0,0.2); }
.company-bio { font-size:13px; color:rgba(255,255,255,0.45); line-height:1.6; margin:10px 0 14px; padding:12px 16px; background:rgba(255,255,255,0.02); border-radius:8px; border-left:3px solid #1e2535; }

.buy-btn  button { background:#0a4a35 !important; border:1px solid #00C896 !important; color:#00C896 !important; font-weight:700 !important; font-size:14px !important; height:42px !important; }
.buy-btn  button:hover { background:#0d5c42 !important; }
.sell-btn button { background:rgba(255,77,106,0.1) !important; border:1px solid rgba(255,77,106,0.35) !important; color:#FF4D6A !important; font-weight:700 !important; font-size:14px !important; height:42px !important; }
.sell-btn button:hover { background:rgba(255,77,106,0.2) !important; }
.sell-btn button:disabled { opacity:0.3 !important; }
.max-btn  button { background:rgba(255,200,0,0.07) !important; border:1px solid rgba(255,200,0,0.25) !important; color:#ffd93d !important; font-size:11px !important; font-weight:700 !important; height:42px !important; }

.port-card { background:#0d0f1a; border:1px solid #1e2535; border-radius:12px; padding:18px 22px; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; }
.port-name { font-size:15px; font-weight:600; color:#fff; }
.port-qty { font-size:12px; color:rgba(255,255,255,0.35); margin-top:2px; }
.port-stats { display:flex; gap:24px; flex-wrap:wrap; }
.port-stat .s-label { font-size:10px; color:rgba(255,255,255,0.3); text-transform:uppercase; letter-spacing:0.8px; margin-bottom:3px; }
.port-stat .s-val { font-size:15px; font-weight:600; font-family:'Space Grotesk',monospace; color:#fff; }

.news-card { background:#0d0f1a; border:1px solid #1e2535; border-radius:12px; padding:18px 22px; margin-bottom:12px; }
.news-label { display:inline-block; font-size:10px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; padding:3px 10px; border-radius:99px; margin-bottom:10px; }
.nl-insider { background:rgba(139,92,246,0.15); color:#a78bfa; border:1px solid rgba(139,92,246,0.2); }
.nl-rumour  { background:rgba(255,140,0,0.12);  color:#ff9a3c; border:1px solid rgba(255,140,0,0.2); }
.nl-event   { background:rgba(255,77,106,0.12); color:#FF4D6A; border:1px solid rgba(255,77,106,0.2); }
.nl-custom  { background:rgba(255,200,0,0.12);  color:#ffd93d; border:1px solid rgba(255,200,0,0.2); }
.news-text  { font-size:15px; color:rgba(255,255,255,0.88); line-height:1.65; }

.loan-card { background:#0d0f1a; border:1px solid rgba(139,92,246,0.25); border-radius:12px; padding:18px 22px; margin-bottom:16px; }
.loan-title { font-size:13px; font-weight:600; color:#a78bfa; letter-spacing:0.5px; text-transform:uppercase; margin-bottom:10px; }
.bank-grid { display:grid; grid-template-columns:1fr; gap:10px; margin-bottom:20px; }
.bank-card { background:#0d0f1a; border-radius:12px; padding:18px 20px; cursor:pointer; transition:all 0.2s; }
.bank-safe  { border:1px solid rgba(0,200,150,0.3); }
.bank-mid   { border:1px solid rgba(255,200,0,0.3); }
.bank-risky { border:1px solid rgba(255,77,106,0.3); }
.bank-card:hover { transform:translateY(-1px); box-shadow:0 4px 20px rgba(0,0,0,0.3); }
.bank-card .bk-name { font-size:14px; font-weight:700; color:#fff; margin-bottom:4px; }
.bank-card .bk-rate { font-size:22px; font-weight:700; font-family:'Space Grotesk',monospace; margin-bottom:6px; }
.bank-safe  .bk-rate { color:#00C896; }
.bank-mid   .bk-rate { color:#ffd93d; }
.bank-risky .bk-rate { color:#FF4D6A; }
.bank-card .bk-limit { font-size:12px; color:rgba(255,255,255,0.4); }
.bank-card .bk-note  { font-size:11px; color:rgba(255,255,255,0.25); margin-top:8px; font-style:italic; }
.bank-accordion { overflow:hidden; max-height:0; transition:max-height 0.4s cubic-bezier(0.16,1,0.3,1), opacity 0.3s ease; opacity:0; border-radius:0 0 12px 12px; margin-top:-4px; }
.bank-accordion.open { max-height:300px; opacity:1; }
.bank-accordion-inner { background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.07); border-top:none; border-radius:0 0 12px 12px; padding:16px 20px; }
.bk-chevron { float:right; font-size:16px; transition:transform 0.3s; color:rgba(255,255,255,0.3); }
.bk-chevron.open { transform:rotate(180deg); color:rgba(255,255,255,0.6); }
.loan-btn   button { background:rgba(139,92,246,0.12) !important; border:1px solid rgba(139,92,246,0.3) !important; color:#a78bfa !important; font-weight:600 !important; }
.repay-btn  button { background:rgba(255,77,106,0.08) !important; border:1px solid rgba(255,77,106,0.25) !important; color:#FF4D6A !important; font-weight:600 !important; }

/* Settings gear button — handled inside st.components.v1.html */

.short-btn button { background:rgba(255,140,0,0.1) !important; border:1px solid rgba(255,140,0,0.35) !important; color:#ff9a3c !important; font-weight:700 !important; font-size:14px !important; height:42px !important; }
.cover-btn button { background:rgba(56,189,248,0.1) !important; border:1px solid rgba(56,189,248,0.35) !important; color:#38bdf8 !important; font-weight:700 !important; font-size:14px !important; height:42px !important; }
.short-badge { display:inline-block; font-size:10px; font-weight:700; padding:2px 8px; border-radius:99px; background:rgba(255,140,0,0.12); color:#ff9a3c; border:1px solid rgba(255,140,0,0.25); margin-left:6px; letter-spacing:0.5px; text-transform:uppercase; }

.lb-card { background:#0d0f1a; border:1px solid #1e2535; border-radius:12px; padding:16px 20px; margin-bottom:10px; display:flex; align-items:center; gap:18px; flex-wrap:wrap; }
.lb-rank { font-size:26px; font-weight:900; font-family:'Space Grotesk',sans-serif; min-width:40px; color:rgba(255,255,255,0.15); }
.lb-rank.gold { color:#ffd700; } .lb-rank.silver { color:#c0c0c0; } .lb-rank.bronze { color:#cd7f32; }
.lb-name { font-size:16px; font-weight:700; color:#fff; flex:1; min-width:100px; }
.lb-stats { display:flex; gap:20px; flex-wrap:wrap; }
.lb-stat .ls2-label { font-size:10px; color:rgba(255,255,255,0.3); text-transform:uppercase; letter-spacing:0.8px; margin-bottom:3px; }
.lb-stat .ls2-val   { font-size:15px; font-weight:600; font-family:'Space Grotesk',monospace; color:#fff; }
.lb-nw { font-size:18px; font-weight:700; font-family:'Space Grotesk',monospace; color:#00C896; white-space:nowrap; }

.rule-card { background:#0d0f1a; border:1px solid #1e2535; border-radius:12px; padding:20px 24px; margin-bottom:12px; display:flex; gap:18px; align-items:flex-start; }
.rule-num { font-size:28px; font-weight:900; color:rgba(0,200,150,0.25); font-family:'Space Grotesk',sans-serif; min-width:36px; line-height:1; }
.rule-content h4 { font-size:14px; font-weight:600; color:#fff; margin-bottom:4px; }
.rule-content p { font-size:13px; color:rgba(255,255,255,0.45); line-height:1.6; }

/* FIX 4: Game over screen */
.gameover-screen { text-align:center; padding:80px 20px 40px; }
.gameover-screen h1 { font-family:'Space Grotesk',sans-serif; font-size:64px; font-weight:900; color:#fff; letter-spacing:-3px; margin-bottom:16px; }
.gameover-screen h1 span { color:#00C896; }
.gameover-screen p { font-size:18px; color:rgba(255,255,255,0.4); max-width:500px; margin:0 auto; line-height:1.7; }

/* ═══════════════════════════════════════════════════════
   LIGHT MODE — full off-white theme with dark-green accents
   ═══════════════════════════════════════════════════════ */
body.light-mode,
body.light-mode [data-testid="stAppViewContainer"],
body.light-mode [data-testid="stAppViewBlockContainer"],
body.light-mode section.main,
body.light-mode .block-container,
body.light-mode [data-testid="column"],
body.light-mode [data-testid="stVerticalBlock"] {
  background: #f0f4f0 !important; color: #1a2e1a !important;
}

/* Ticker */
body.light-mode .ticker-wrap { background:#d4e8d4; border-color:#a8cca8; }
body.light-mode .ticker-item { color:#2d5a2d; }
body.light-mode .ticker-item .sym { color:#0d2e0d; font-weight:800; }
body.light-mode .ticker-item .up   { color:#006b3c; }
body.light-mode .ticker-item .down { color:#c0392b; }

/* Phase banners */
body.light-mode .phase-lobby   { background:rgba(180,140,0,0.1); border-color:rgba(180,140,0,0.35); color:#7a5c00; }
body.light-mode .phase-trading { background:rgba(0,120,70,0.08); border-color:rgba(0,120,70,0.3);  color:#005c32; }
body.light-mode .phase-between { background:rgba(180,80,0,0.08); border-color:rgba(180,80,0,0.3);  color:#7a3800; }
body.light-mode .phase-ended   { background:rgba(160,0,30,0.07); border-color:rgba(160,0,30,0.25); color:#8b0000; }

/* All cards */
body.light-mode .metric-card,
body.light-mode .company-card,
body.light-mode .news-card,
body.light-mode .loan-card,
body.light-mode .port-card,
body.light-mode .lb-card,
body.light-mode .rule-card {
  background: #ffffff !important;
  border-color: #c2d9c2 !important;
  box-shadow: 0 1px 4px rgba(0,60,0,0.07);
}

/* Bank cards */
body.light-mode .bank-safe  { background:#f5fff8 !important; border-color:rgba(0,120,70,0.4) !important; }
body.light-mode .bank-mid   { background:#fffef0 !important; border-color:rgba(160,120,0,0.4) !important; }
body.light-mode .bank-risky { background:#fff5f5 !important; border-color:rgba(180,0,30,0.35) !important; }
body.light-mode .bank-card .bk-name { color:#0d2e0d !important; }
body.light-mode .bank-safe  .bk-rate { color:#006b3c !important; }
body.light-mode .bank-mid   .bk-rate { color:#7a5c00 !important; }
body.light-mode .bank-risky .bk-rate { color:#a0001e !important; }
body.light-mode .bank-card .bk-limit { color:#4a6a4a !important; }
body.light-mode .bank-card .bk-note  { color:#7a947a !important; }
body.light-mode .loan-card  { background:#f8f5ff !important; border-color:rgba(100,60,200,0.25) !important; }
body.light-mode .loan-title { color:#5b3fa0 !important; }

/* Text colours */
body.light-mode .section-hdr           { color:#0d2e0d !important; border-color:#c2d9c2 !important; }
body.light-mode .company-name,
body.light-mode .port-name,
body.light-mode .lb-name,
body.light-mode .rule-content h4       { color:#0d2e0d !important; }
body.light-mode .company-meta,
body.light-mode .company-trait,
body.light-mode .bk-limit,
body.light-mode .bk-note,
body.light-mode .port-qty,
body.light-mode .rule-content p        { color:#4a6a4a !important; }
body.light-mode .company-bio           { color:#3a5a3a !important; background:rgba(0,100,50,0.04); border-left-color:#a8cca8; }
body.light-mode .news-text             { color:#1a2e1a !important; }
body.light-mode .price-main            { color:#0d2e0d !important; }
body.light-mode .metric-card .label   { color:#4a6a4a !important; }
body.light-mode .metric-card .value,
body.light-mode .port-stat .s-val,
body.light-mode .lb-stat .ls2-val      { color:#0d2e0d !important; }
body.light-mode .metric-card .delta.delta-neutral { color:#7a947a !important; }
body.light-mode .lb-stat .ls2-label,
body.light-mode .port-stat .s-label    { color:#7a947a !important; }
body.light-mode .lb-nw                 { color:#006b3c !important; }
body.light-mode .lb-rank               { color:rgba(0,60,0,0.15) !important; }
body.light-mode .lb-rank.gold          { color:#b8860b !important; }
body.light-mode .lb-rank.silver        { color:#708090 !important; }
body.light-mode .lb-rank.bronze        { color:#8b5e3c !important; }
body.light-mode .rule-num              { color:rgba(0,120,60,0.2) !important; }

/* Nav buttons */
body.light-mode .nav-btn { border-right-color:#c2d9c2 !important; }
body.light-mode .nav-market  { background:rgba(0,120,70,0.07);  color:rgba(0,100,50,0.5); }
body.light-mode .nav-intel   { background:rgba(160,120,0,0.07); color:rgba(130,90,0,0.5); }
body.light-mode .nav-banks   { background:rgba(100,60,200,0.06);color:rgba(80,40,180,0.5); }
body.light-mode .nav-portf   { background:rgba(30,80,200,0.06); color:rgba(20,60,180,0.5); }
body.light-mode .nav-market.nav-active  { background:rgba(0,120,70,0.15);  color:#006b3c; }
body.light-mode .nav-intel.nav-active   { background:rgba(160,120,0,0.15); color:#7a5c00; }
body.light-mode .nav-banks.nav-active   { background:rgba(100,60,200,0.12);color:#4a24b0; }
body.light-mode .nav-portf.nav-active   { background:rgba(30,80,200,0.12); color:#1a3ea0; }

/* Nav row border */
body.light-mode .nav-row { border-color:#c2d9c2 !important; }

/* Buttons */
body.light-mode .buy-btn  button { background:#d4f0e4 !important; border-color:#006b3c !important; color:#006b3c !important; }
body.light-mode .sell-btn button { background:#fde8e8 !important; border-color:#c0392b !important; color:#c0392b !important; }
body.light-mode .max-btn  button { background:#fef9e0 !important; border-color:#a08000 !important; color:#7a5c00 !important; }
body.light-mode .loan-btn button { background:#ede8ff !important; border-color:#5b3fa0 !important; color:#5b3fa0 !important; }
body.light-mode .repay-btn button{ background:#fde8e8 !important; border-color:#c0392b !important; color:#c0392b !important; }

/* Risk badges */
body.light-mode .risk-low         { background:rgba(0,120,70,0.1);  color:#006b3c; border-color:rgba(0,120,70,0.3); }
body.light-mode .risk-medium      { background:rgba(160,120,0,0.1); color:#7a5c00; border-color:rgba(160,120,0,0.3); }
body.light-mode .risk-high        { background:rgba(160,0,30,0.08); color:#a0001e; border-color:rgba(160,0,30,0.25); }
body.light-mode .risk-medium-high { background:rgba(160,80,0,0.08); color:#8b4000; border-color:rgba(160,80,0,0.25); }

/* News labels */
body.light-mode .nl-insider { background:rgba(80,40,180,0.1); color:#4a24b0; border-color:rgba(80,40,180,0.25); }
body.light-mode .nl-rumour  { background:rgba(160,80,0,0.1);  color:#8b4000; border-color:rgba(160,80,0,0.25); }
body.light-mode .nl-event   { background:rgba(160,0,30,0.08); color:#a0001e; border-color:rgba(160,0,30,0.2); }
body.light-mode .nl-custom  { background:rgba(160,120,0,0.1); color:#7a5c00; border-color:rgba(160,120,0,0.25); }

/* Header text in light mode */
body.light-mode #mm-gear-btn { background:rgba(0,60,0,0.07) !important; border-color:rgba(0,60,0,0.2) !important; color:#1a3a1a !important; }

/* Override ALL inline white/grey text in the header area */
body.light-mode [data-testid="stMarkdownContainer"] div[style*="color:#fff"],
body.light-mode [data-testid="stMarkdownContainer"] div[style*="color: #fff"] { color:#0d2e0d !important; }
body.light-mode [data-testid="stMarkdownContainer"] div[style*="color:rgba(255,255,255,0.3)"],
body.light-mode [data-testid="stMarkdownContainer"] div[style*="color:rgba(255,255,255,0.25)"],
body.light-mode [data-testid="stMarkdownContainer"] div[style*="color:rgba(255,255,255,0.35)"],
body.light-mode [data-testid="stMarkdownContainer"] div[style*="color:rgba(255,255,255,0.45)"],
body.light-mode [data-testid="stMarkdownContainer"] div[style*="color:rgba(255,255,255,0.4)"],
body.light-mode [data-testid="stMarkdownContainer"] span[style*="color:rgba(255,255,255"] { color:#4a6a4a !important; }

/* Team name specifically */
body.light-mode [style*="font-size:26px"][style*="font-weight:700"] { color:#0d2e0d !important; }
body.light-mode [style*="font-size:12px"][style*="color:rgba(255,255,255,0.3)"] { color:#4a6a4a !important; }
body.light-mode [style*="font-size:12px"][style*="color:rgba(255,255,255,0.25)"] { color:#4a6a4a !important; }

/* "Trading is closed" and similar status text */
body.light-mode [style*="color:rgba(255,255,255,0.3)"] { color:#5a7a5a !important; }

/* Buy/sell panel backgrounds in light mode */
body.light-mode [style*="background:#0d0f1a"][style*="border:1px solid #1e2535"] {
  background:#f8fbf8 !important; border-color:#c2d9c2 !important;
}
body.light-mode [style*="font-size:10px"][style*="color:rgba(255,255,255,0.3)"] { color:#4a6a4a !important; }
body.light-mode [style*="font-size:11px"][style*="color:rgba(255,255,255"] { color:#4a6a4a !important; }

/* Streamlit-injected elements */
body.light-mode [data-testid="stMarkdownContainer"] p { color:#1a2e1a; }
body.light-mode div[data-testid="stHorizontalBlock"] { background:transparent !important; }
body.light-mode [data-baseweb="base-input"] { background:#fff !important; border-color:#c2d9c2 !important; color:#0d2e0d !important; }
body.light-mode [data-baseweb="base-input"] input { color:#0d2e0d !important; }
body.light-mode button[kind="secondary"] { background:#fff !important; border-color:#c2d9c2 !important; color:#0d2e0d !important; }

/* Settings panel in light mode */
body.light-mode #mm-spanel { background:#f5faf5 !important; border-color:#c2d9c2 !important; }
body.light-mode .mm-sph-title { color:#0d2e0d !important; }
body.light-mode .mm-slbl { color:#4a6a4a !important; }
body.light-mode .mm-stog { background:rgba(0,80,40,0.05) !important; border-color:#c2d9c2 !important; }
body.light-mode .mm-stog-txt { color:#1a2e1a !important; }
body.light-mode .mm-svlbl { color:#1a2e1a !important; }
body.light-mode .mm-svval { color:#4a6a4a !important; }

div[data-testid="stForm"] button[kind="primaryFormSubmit"] {
    background: #0a4a35 !important; border: 1px solid #00C896 !important;
    color: #00C896 !important; font-weight: 600 !important;
}
</style>
""", unsafe_allow_html=True)

BANKS = {
    "rbi_safe":     {"name":"RBI Trustbank",     "rate":0.07,  "cap":50000,  "css":"bank-safe",  "rate_label":"7% / round",  "note":"Regulated. Stable. Low ceiling but fair rates.",             "borrow_options":[5000,10000,25000,50000]},
    "axis_mid":     {"name":"Axis Capital",       "rate":0.12,  "cap":100000, "css":"bank-mid",   "rate_label":"12% / round", "note":"Mid-tier lender. Decent limit for growing teams.",           "borrow_options":[10000,25000,50000,75000,100000]},
    "hawala_risky": {"name":"BlackRock Ventures", "rate":0.18,  "cap":200000, "css":"bank-risky", "rate_label":"18% / round", "note":"High credit line. Aggressive interest. Not for the faint-hearted.", "borrow_options":[25000,50000,100000,150000,200000]},
}

def fmt(n): return f"₹{int(n):,}"
def risk_class(risk): return "risk-" + risk.lower().replace(" ", "-")
def news_label_class(ntype):
    return {"insider":"nl-insider","rumour":"nl-rumour","event":"nl-event"}.get(ntype,"nl-custom")
def should_show_news(n, current_phase):
    ntype = n.get("type", "custom")
    if ntype in ("event", "positive"): return current_phase in ("trading", "ended")
    if ntype == "rumour":              return current_phase in ("between", "ended")
    return True  # insider, custom — always visible

state = load_state()
tid = st.session_state.get("team_id")
if tid and tid not in state["teams"]:
    st.session_state.clear(); st.rerun()
team = state["teams"].get(tid) if tid else None

# ── Ticker ────────────────────────────────────────────────────────────────────
ticker_items = ""
for cid, c in state["companies"].items():
    chg = c["price"] - c.get("prev_price", c["price"])
    chg_pct = (chg / c["prev_price"] * 100) if c.get("prev_price") else 0
    direction = "up" if chg >= 0 else "down"
    arrow = "▲" if chg >= 0 else "▼"
    ticker_items += f'<span class="ticker-item"><span class="sym">{cid.upper()[:4]}</span><span class="{direction}">{fmt(c["price"])} {arrow} {abs(chg_pct):.1f}%</span></span>'
st.markdown(f'<div class="ticker-wrap"><div class="ticker">{ticker_items * 4}</div></div>', unsafe_allow_html=True)

# ── Registration ──────────────────────────────────────────────────────────────
if not team:
    st.markdown("""
    <div class="hero">
        <div class="hero-tag">Inceptia</div>
        <h1>Market <span>Mayhem</span></h1>
        <p>The floor is open. Only the sharpest portfolio wins.</p>
    </div>""", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        with st.form("register"):
            st.markdown('<p style="font-size:13px;color:rgba(255,255,255,0.35);letter-spacing:2px;text-transform:uppercase;font-weight:600;margin-bottom:4px">Enter the market</p>', unsafe_allow_html=True)
            team_name = st.text_input("Team name", placeholder="e.g. Delhi", label_visibility="collapsed")
            st.markdown('<p style="font-size:11px;color:rgba(255,255,255,0.2);margin:-6px 0 12px 2px">City name</p>', unsafe_allow_html=True)
            st.markdown('<p style="font-size:13px;color:rgba(255,255,255,0.35);letter-spacing:2px;text-transform:uppercase;font-weight:600;margin-bottom:4px">Participant number</p>', unsafe_allow_html=True)
            participant_num = st.number_input("Participant number", min_value=1, max_value=4, value=1, label_visibility="collapsed")
            st.markdown('<p style="font-size:11px;color:rgba(255,255,255,0.2);margin:-6px 0 12px 2px">Player 1–4 in your team</p>', unsafe_allow_html=True)
            submitted = st.form_submit_button("Enter the Market", type="primary", use_container_width=True)
            if submitted:
                if not team_name.strip():
                    st.error("Enter a team name to continue.")
                else:
                    state = load_state()
                    new_tid = str(uuid.uuid4())[:8]
                    state["teams"][new_tid] = {
                        "name": team_name.strip(),
                        "participant_num": int(participant_num),
                        "cash": 0, "loan_balance": 0,
                        "loan_rbi_safe": 0, "loan_axis_mid": 0, "loan_hawala_risky": 0,
                        "holdings": {cid: 0 for cid in state["companies"]},
                        "avg_cost": {cid: 0 for cid in state["companies"]},
                        "price_history": {cid: [c["price"]] for cid, c in state["companies"].items()},
                    }
                    save_state(state)
                    st.session_state["team_id"] = new_tid
                    st.rerun()
    st.markdown('<h2 style="font-family:Space Grotesk,sans-serif;font-size:28px;font-weight:700;color:#fff;margin:48px 0 20px;letter-spacing:-0.5px">How it works</h2>', unsafe_allow_html=True)
    rules = [
        ("Register", "Enter your city name. You start with ₹0 — take a loan to begin trading."),
        ("Pick your bank", "3 banks to borrow from. Each has its own terms, limits, and interest rates. Choose wisely."),
        ("Read the market", "9 companies across sectors. Each has a personality, risk level, and backstory."),
        ("Trade in rounds", "4 rounds of live trading. Buy, sell, or short before each round closes."),
        ("Navigate the news", "News drops throughout the game. Some is real. Some is noise. You decide."),
        ("Win by net worth", "Cash + portfolio − loan balance at the end of the final round. Highest wins."),
    ]
    for i, (title, desc) in enumerate(rules, 1):
        st.markdown(f'<div class="rule-card"><div class="rule-num">{str(i).zfill(2)}</div><div class="rule-content"><h4>{title}</h4><p>{desc}</p></div></div>', unsafe_allow_html=True)
    st.stop()

# ── Main dashboard ────────────────────────────────────────────────────────────
state = load_state()
team = state["teams"].get(tid)
phase = state["phase"]

# ── Music — loaded once into session state, played via JS in parent frame ─────
_MUSIC_PHASES = {"lobby", "between", "ended"}
_music_vol   = st.session_state.get("music_volume", 50)
_should_play = phase in _MUSIC_PHASES
_vol_f       = max(0.0, min(1.0, _music_vol / 100))

# Load MP3 as base64 once per session (not stored in .py source, loaded at runtime)
if "mm_music_src" not in st.session_state:
    import base64 as _b64
    _tried = [
        Path(__file__).parent.parent / "static" / "music.mp3",
        Path(__file__).parent / "music.mp3",
        Path(__file__).parent.parent / "music.mp3",
    ]
    st.session_state["mm_music_src"] = ""
    for _mp in _tried:
        if _mp.exists():
            _enc = _b64.b64encode(_mp.read_bytes()).decode()
            st.session_state["mm_music_src"] = f"data:audio/mpeg;base64,{_enc}"
            break

_music_src = st.session_state.get("mm_music_src", "")

import streamlit.components.v1 as _stc_music
_stc_music.html(f"""<script>
(function(){{
  var P = window.parent.document;
  var shouldPlay = {'true' if _should_play else 'false'};
  var vol = {_vol_f:.3f};
  var src = {repr(_music_src)};
  var FADE_STEPS = 52, FADE_INTERVAL = 25; // 1.3s fade

  function fade(a, to, cb) {{
    clearInterval(a._ft);
    var from = a.volume, step = 0;
    a._ft = setInterval(function() {{
      step++;
      a.volume = Math.max(0, Math.min(1, from + (to - from) * (step / FADE_STEPS)));
      if (step >= FADE_STEPS) {{ a.volume = to; clearInterval(a._ft); if (cb) cb(); }}
    }}, FADE_INTERVAL);
  }}

  function getOrCreateAudio() {{
    var a = P.getElementById('mm-bg-audio');
    if (!a && src) {{
      a = P.createElement('audio');
      a.id = 'mm-bg-audio';
      a.loop = true; a.preload = 'auto'; a.style.display = 'none';
      a.src = src;
      P.body.appendChild(a);
    }}
    return a;
  }}

  function tryPlay(a) {{
    if (!a) return;
    a.volume = 0;
    a.play().then(function() {{ fade(a, vol); }}).catch(function() {{
      var handler = function() {{
        a.play().then(function() {{ fade(a, vol); }}).catch(function(){{}});
        P.removeEventListener('click', handler);
        var hint = P.getElementById('mm-play-hint');
        if (hint) hint.remove();
      }};
      P.addEventListener('click', handler);
      if (!P.getElementById('mm-play-hint')) {{
        var hint = P.createElement('div');
        hint.id = 'mm-play-hint';
        hint.textContent = '🎵 Tap anywhere to enable music';
        hint.style.cssText = 'position:fixed;bottom:14px;left:50%;transform:translateX(-50%);' +
          'background:rgba(0,200,150,0.15);border:1px solid rgba(0,200,150,0.3);' +
          'color:#00C896;font-size:13px;font-family:Inter,sans-serif;font-weight:500;' +
          'padding:8px 18px;border-radius:99px;z-index:9997;pointer-events:none;';
        P.body.appendChild(hint);
      }}
    }});
  }}

  function sync() {{
    var a = getOrCreateAudio();
    if (!a) return;
    if (shouldPlay) {{
      if (a.paused) {{ tryPlay(a); }}
      else {{ fade(a, vol); }}
    }} else {{
      if (!a.paused) {{ fade(a, 0, function() {{ a.pause(); }}); }}
    }}
    // Keep volume in sync with slider
    a._targetVol = vol;
  }}

  setTimeout(sync, 200);
}})();
</script>""", height=0)

# ── Live micro-fluctuation engine ────────────────────────────────────────────
# Real prices only change at round start (host). This adds visual micro-ticks
# every ~3s during trading so charts show live movement. Stored in session state
# only — never written to game_state.json, so it doesn't affect real prices.
import random as _random

MICRO_VOL = {  # per-tick max % move (purely visual)
    "zora":0.004, "streamvx":0.018, "freshco":0.003, "voltex":0.012,
    "mediq":0.015, "skylink":0.022, "swifthaul":0.008, "crownmart":0.016, "shieldgen":0.004,
}

if "micro_prices" not in st.session_state or st.session_state.get("micro_phase") != phase:
    # Initialise from real prices
    st.session_state["micro_prices"] = {cid: c["price"] for cid, c in state["companies"].items()}
    st.session_state["micro_phase"] = phase
    st.session_state["micro_tick"] = 0

# Sync if real price drifts far from micro price (e.g. after round start)
for cid, c in state["companies"].items():
    mp = st.session_state["micro_prices"].get(cid, c["price"])
    if abs(mp - c["price"]) / c["price"] > 0.08:  # >8% drift → resync
        st.session_state["micro_prices"][cid] = c["price"]

if phase == "trading":
    st.session_state["micro_tick"] = st.session_state.get("micro_tick", 0) + 1
    tick = st.session_state["micro_tick"]
    if tick % 3 == 0:  # fluctuate every 3 refreshes (~3s)
        for cid in state["companies"]:
            mp = st.session_state["micro_prices"][cid]
            vol = MICRO_VOL.get(cid, 0.008)
            direction = 1 if _random.random() > 0.5 else -1
            change = direction * _random.uniform(vol * 0.3, vol)
            st.session_state["micro_prices"][cid] = max(10, round(mp * (1 + change), 1))

# Build display_hist: real price history + live micro price as last point
if "price_history" not in team:
    team["price_history"] = {cid: [c["price"]] for cid, c in state["companies"].items()}
if phase == "trading":
    changed = False
    for cid, c in state["companies"].items():
        hist = team["price_history"].get(cid, [])
        # Append micro price every tick for a smooth live chart
        micro_p = st.session_state["micro_prices"].get(cid, c["price"])
        hist.append(micro_p)
        if len(hist) > 60: hist = hist[-60:]  # keep last 60 points
        team["price_history"][cid] = hist
        changed = True
    if changed:
        state["teams"][tid] = team
        save_state(state)

# FIX 4: Game over screen — show immediately after ticker, no banner, no progress
if phase == "ended":
    port_val = sum(team["holdings"].get(cid,0) * state["companies"][cid]["price"] for cid in state["companies"])
    loan_balance = team.get("loan_balance", 0)
    net_worth = team["cash"] + port_val - loan_balance
    st.markdown(f"""
    <div class="gameover-screen">
      <h1>Thank <span>You</span></h1>
      <p>Results will be announced shortly by your event coordinator.</p>
      <p style="margin-top:24px;font-size:14px;color:rgba(255,255,255,0.2)">Your final net worth: <strong style="color:#00C896">{fmt(net_worth)}</strong></p>
    </div>""", unsafe_allow_html=True)
    st.stop()  # Don't render anything else after game over

# ── Header + Settings (non-ended phases only) ────────────────────────────────
participant_tag = f' &nbsp;<span style="font-size:13px;font-weight:500;color:rgba(255,255,255,0.35)">· P{team.get("participant_num","")}</span>' if team.get("participant_num") else ""

# Settings state — read from query params so JS can write them without a rerun
_qp = st.query_params
if "music_volume" not in st.session_state:
    st.session_state["music_volume"] = int(_qp.get("vol", 50))
if "light_mode" not in st.session_state:
    st.session_state["light_mode"] = _qp.get("theme", "dark") == "light"

# Handle query param updates from the JS settings panel
_qp_vol   = _qp.get("vol")
_qp_theme = _qp.get("theme")
if _qp_vol is not None:
    try:
        _v = int(_qp_vol)
        if _v != st.session_state["music_volume"]:
            st.session_state["music_volume"] = _v
    except ValueError:
        pass
if _qp_theme is not None:
    _lm = (_qp_theme == "light")
    if _lm != st.session_state["light_mode"]:
        st.session_state["light_mode"] = _lm

_vol   = st.session_state["music_volume"]
_light = st.session_state["light_mode"]

# Header (plain HTML — renders fine, no scripts needed here)
st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;margin:14px 0 20px;flex-wrap:wrap;gap:10px">
  <div>
    <div style="font-family:Space Grotesk,sans-serif;font-size:26px;font-weight:700;color:#fff;letter-spacing:-0.5px">{team['name']}{participant_tag}</div>
    <div style="font-size:12px;color:rgba(255,255,255,0.3);margin-top:2px">Market Mayhem · Inceptia</div>
  </div>
  <div style="display:flex;align-items:center;gap:14px">
    <div style="font-size:12px;color:rgba(255,255,255,0.25);font-family:Space Grotesk,monospace">Round {state['round']} / 4</div>
    <div id="mm-gear-btn"
         style="width:38px;height:38px;border-radius:50%;background:rgba(255,255,255,0.05);
                border:1px solid rgba(255,255,255,0.12);color:rgba(255,255,255,0.55);
                font-size:18px;cursor:pointer;display:flex;align-items:center;
                justify-content:center;user-select:none;transition:background 0.15s,color 0.15s"
         title="Settings">⚙</div>
  </div>
</div>
""", unsafe_allow_html=True)

# Settings panel — inject CSS + DOM + JS all into the PARENT document from the iframe
import streamlit.components.v1 as _stc
_stc.html(f"""
<!DOCTYPE html><html><body style="margin:0;padding:0;background:transparent">
<script>
(function(){{
  var P = window.parent.document;

  // ── Inject CSS into parent <head> once ──────────────────────────────────
  if (!P.getElementById('mm-settings-css')) {{
    var s = P.createElement('style');
    s.id = 'mm-settings-css';
    s.textContent = `
      #mm-soverlay {{
        display:none;position:fixed;inset:0;z-index:9998;
        background:rgba(0,0,0,0.55);backdrop-filter:blur(4px);
      }}
      #mm-spanel {{
        position:fixed;top:0;right:0;width:300px;height:100vh;
        background:#0d0f1a;border-left:1px solid #1e2535;
        z-index:9999;padding:28px 22px;overflow-y:auto;box-sizing:border-box;
        transform:translateX(100%);transition:transform 0.28s cubic-bezier(0.16,1,0.3,1);
      }}
      #mm-spanel.sp-open {{ transform:translateX(0); }}
      #mm-soverlay.sp-open {{ display:block; }}
      .mm-sph {{ display:flex;justify-content:space-between;align-items:center;margin-bottom:28px; }}
      .mm-sph-title {{ font-family:Space Grotesk,sans-serif;font-size:18px;font-weight:700;color:#fff;letter-spacing:-0.3px; }}
      .mm-sph-x {{ width:30px;height:30px;border-radius:50%;border:1px solid rgba(255,255,255,0.12);
                   background:rgba(255,255,255,0.05);color:rgba(255,255,255,0.5);font-size:15px;
                   cursor:pointer;display:flex;align-items:center;justify-content:center;
                   transition:background .15s,color .15s,border-color .15s; }}
      .mm-sph-x:hover {{ background:rgba(255,77,106,0.15);color:#FF4D6A;border-color:rgba(255,77,106,0.3); }}
      .mm-ssec {{ margin-bottom:22px;padding-bottom:22px;border-bottom:1px solid rgba(255,255,255,0.05); }}
      .mm-slbl {{ font-size:11px;color:rgba(255,255,255,0.35);text-transform:uppercase;letter-spacing:1.5px;font-weight:600;margin-bottom:12px; }}
      .mm-theme-row {{ display:flex;gap:10px; }}
      .mm-tbtn {{ flex:1;padding:14px 8px;border-radius:12px;border:1.5px solid rgba(255,255,255,0.1);background:rgba(255,255,255,0.04);cursor:pointer;display:flex;flex-direction:column;align-items:center;gap:8px;transition:all 0.18s;user-select:none; }}
      .mm-tbtn:hover {{ background:rgba(255,255,255,0.08); }}
      .mm-tbtn.t-active-light {{ border-color:#ffd93d;background:rgba(255,211,61,0.1); }}
      .mm-tbtn.t-active-dark  {{ border-color:#a78bfa;background:rgba(167,139,250,0.1); }}
      .mm-tbtn svg {{ width:28px;height:28px; }}
      .mm-tbtn span {{ font-size:12px;font-weight:600;color:rgba(255,255,255,0.45);letter-spacing:0.3px; }}
      .mm-tbtn.t-active-light span {{ color:#ffd93d; }}
      .mm-tbtn.t-active-dark  span {{ color:#a78bfa; }}
      .mm-svlbl {{ font-size:14px;color:rgba(255,255,255,0.8);font-weight:500;margin-bottom:12px; }}
      .mm-svrow {{ display:flex;align-items:center;gap:10px; }}
      .mm-svrow input[type=range] {{
        flex:1;-webkit-appearance:none;height:4px;border-radius:2px;
        background:rgba(255,255,255,0.12);outline:none;cursor:pointer;
      }}
      .mm-svrow input[type=range]::-webkit-slider-thumb {{
        -webkit-appearance:none;width:18px;height:18px;border-radius:50%;
        background:#00C896;cursor:pointer;box-shadow:0 0 0 3px rgba(0,200,150,0.2);
      }}
      .mm-svval {{ font-size:13px;color:rgba(255,255,255,0.4);min-width:28px;text-align:right;font-family:monospace; }}
    `;
    P.head.appendChild(s);
  }}

  // ── Build overlay + panel DOM once ──────────────────────────────────────
  var isLight = {'true' if _light else 'false'};
  var vol = {_vol};

  var SVG_SUN  = '<svg viewBox="0 0 24 24" fill="none" stroke="#ffd93d" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>';
  var SVG_MOON = '<svg viewBox="0 0 24 24" fill="none" stroke="#a78bfa" stroke-width="2" stroke-linecap="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';

  if (!P.getElementById('mm-spanel')) {{
    var ov = P.createElement('div'); ov.id = 'mm-soverlay';
    var pn = P.createElement('div'); pn.id = 'mm-spanel';
    pn.innerHTML =
      '<div class="mm-sph">' +
        '<span class="mm-sph-title">Settings</span>' +
        '<div class="mm-sph-x" id="mm-sclose">&#x2715;</div>' +
      '</div>' +
      '<div class="mm-ssec">' +
        '<div class="mm-slbl">Appearance</div>' +
        '<div class="mm-theme-row">' +
          '<div class="mm-tbtn ' + (!isLight ? '' : 't-active-light') + '" id="mm-btn-light">' +
            SVG_SUN + '<span>Light</span>' +
          '</div>' +
          '<div class="mm-tbtn ' + (isLight ? '' : 't-active-dark') + '" id="mm-btn-dark">' +
            SVG_MOON + '<span>Dark</span>' +
          '</div>' +
        '</div>' +
      '</div>' +
      '<div class="mm-ssec" style="border-bottom:none">' +
        '<div class="mm-slbl">Music Volume</div>' +
        '<div class="mm-svlbl">Background music <span style="color:rgba(255,255,255,0.35);font-size:12px">(lobby &amp; breaks)</span></div>' +
        '<div class="mm-svrow">' +
          '<span style="font-size:15px">&#x1F508;</span>' +
          '<input type="range" id="mm-vol-sl" min="0" max="100" value="' + vol + '">' +
          '<span style="font-size:15px">&#x1F50A;</span>' +
          '<span class="mm-svval" id="mm-vval">' + vol + '</span>' +
        '</div>' +
      '</div>';
    P.body.appendChild(ov);
    P.body.appendChild(pn);

    // Events
    function openPanel()  {{ pn.classList.add('sp-open'); ov.classList.add('sp-open'); }}
    function closePanel() {{ pn.classList.remove('sp-open'); ov.classList.remove('sp-open'); }}
    ov.addEventListener('click', closePanel);
    P.getElementById('mm-sclose').addEventListener('click', closePanel);

    // Gear button — poll until the gear div exists in the parent page
    (function tryGear() {{
      var g = P.getElementById('mm-gear-btn');
      if (g) {{ g.onclick = openPanel; }}
      else   {{ setTimeout(tryGear, 150); }}
    }})();

    // Sun/Moon theme buttons
    function setTheme(light) {{
      isLight = light;
      P.getElementById('mm-btn-light').className = 'mm-tbtn' + (light ? ' t-active-light' : '');
      P.getElementById('mm-btn-dark').className  = 'mm-tbtn' + (!light ? ' t-active-dark'  : '');
      if (light) P.body.classList.add('light-mode');
      else       P.body.classList.remove('light-mode');
    }}
    P.getElementById('mm-btn-light').addEventListener('click', function() {{ setTheme(true);  }});
    P.getElementById('mm-btn-dark').addEventListener('click',  function() {{ setTheme(false); }});

    // Volume slider
    P.getElementById('mm-vol-sl').addEventListener('input', function() {{
      P.getElementById('mm-vval').textContent = this.value;
      var audio = P.getElementById('mm-bg-audio');
      if (audio) audio.volume = parseInt(this.value) / 100;
    }});
  }} else {{
    // Panel already in DOM — just sync volume slider
    var sl = P.getElementById('mm-vol-sl');
    if (sl) sl.value = vol;
  }}

  if (isLight) P.body.classList.add('light-mode');
}})();
</script>
</body></html>
""", height=0)

phase_map = {
    "lobby":   ("phase-lobby",   "WAITING FOR HOST",               "The trading floor opens shortly."),
    "trading": ("phase-trading", f"ROUND {state['round']} — LIVE", "Trading is open. Buy and sell before the round ends."),
    "between": ("phase-between", f"ROUND {state['round']} CLOSED", "Round ended. Host will start the next round shortly."),
}
p_class, p_title, p_sub = phase_map.get(phase, ("phase-lobby","—","—"))
st.markdown(f'<div class="phase-banner {p_class}"><strong>{p_title}</strong> &nbsp;—&nbsp; {p_sub}</div>', unsafe_allow_html=True)

# Python-driven countdown — reliable, same approach as host
if phase == "trading" and state.get("round_end_time"):
    remaining = max(0, state["round_end_time"] - time.time())
    if remaining > 0:
        mins, secs = divmod(int(remaining), 60)
        time_label = f"{mins}m {secs:02d}s" if mins > 0 else f"{secs}s"
        progress_val = max(0.0, min(1.0, 1.0 - (remaining / ROUND_DURATION)))
        bar_color = "#00C896" if progress_val < 0.5 else ("#ffd93d" if progress_val < 0.75 else "#FF4D6A")
        st.markdown(f'<p style="font-size:30px;color:rgba(255,255,255,0.7);margin-bottom:6px">⏱ Round closes in <strong style="color:#fff">{time_label}</strong></p>', unsafe_allow_html=True)
        st.markdown(f"""<style>div[data-testid="stProgress"]>div>div>div>div{{background:{bar_color}!important}}div[data-testid="stProgress"]>div>div{{background:rgba(255,255,255,0.08)!important}}</style>""", unsafe_allow_html=True)
        st.progress(progress_val)
    else:
        st.markdown('<p style="font-size:20px;color:#FF4D6A;margin-bottom:6px">⏰ Round time is up — waiting for host to close.</p>', unsafe_allow_html=True)
elif phase == "between" and state.get("break_end_time"):
    remaining = max(0, state["break_end_time"] - time.time())
    if remaining > 0:
        mins, secs = divmod(int(remaining), 60)
        time_label = f"{mins}m {secs:02d}s" if mins > 0 else f"{secs}s"
        progress_val = max(0.0, min(1.0, 1.0 - (remaining / BREAK_DURATION)))
        st.markdown(f'<p style="font-size:30px;color:rgba(255,255,255,0.7);margin-bottom:6px">☕ Break ends in <strong style="color:#fff">{time_label}</strong></p>', unsafe_allow_html=True)
        st.markdown(f"""<style>div[data-testid="stProgress"]>div>div>div>div{{background:#a78bfa!important}}div[data-testid="stProgress"]>div>div{{background:rgba(255,255,255,0.08)!important}}</style>""", unsafe_allow_html=True)
        st.progress(progress_val)

# Metrics
port_val = sum(team["holdings"].get(cid,0) * state["companies"][cid]["price"] for cid in state["companies"])
loan_balance = team.get("loan_balance", 0)
net_worth = team["cash"] + port_val - loan_balance
st.markdown(f"""
<div class="metric-row" style="grid-template-columns:repeat(4,1fr)">
  <div class="metric-card"><div class="label">Cash</div><div class="value" style="color:#00C896">{fmt(team['cash'])}</div><div class="delta" style="color:rgba(0,200,150,0.45)">Available</div></div>
  <div class="metric-card"><div class="label">Portfolio</div><div class="value" style="color:#ffd93d">{fmt(port_val)}</div><div class="delta" style="color:rgba(255,211,61,0.45)">Holdings value</div></div>
  <div class="metric-card"><div class="label">Loan Balance</div><div class="value" style="color:#a78bfa">{fmt(loan_balance)}</div><div class="delta" style="color:rgba(167,139,250,0.4)">Outstanding debt</div></div>
  <div class="metric-card"><div class="label">Net Worth</div><div class="value" style="color:#4f8ef7">{fmt(net_worth)}</div><div class="delta" style="color:rgba(79,142,247,0.45)">Cash + portfolio − loan</div></div>
</div>""", unsafe_allow_html=True)

can_trade = phase == "trading"
can_bank  = phase in ("trading", "between")

all_news = state.get("news", [])
visible_news = [n for n in all_news if should_show_news(n, phase)]
new_count = len(visible_news)
if "intel_seen_count" not in st.session_state:
    st.session_state["intel_seen_count"] = 0
unseen_intel = max(0, new_count - st.session_state["intel_seen_count"])

if "active_panel" not in st.session_state:
    st.session_state["active_panel"] = "market"
if st.session_state["active_panel"] == "news":
    st.session_state["intel_seen_count"] = new_count

# Nav tabs — pure Streamlit buttons styled to match metric tile colours
active = st.session_state["active_panel"]

nav_cols = st.columns(4)
panel_keys  = ["market",  "news",   "loans",  "portfolio"]
panel_labels = ["Market", "Intel", "Banks", "Portfolio"]
for i, (p, lbl) in enumerate(zip(panel_keys, panel_labels)):
    with nav_cols[i]:
        is_active = active == p
        color_map = {"market":"#00C896","news":"#ffd93d","loans":"#a78bfa","portfolio":"#4f8ef7"}
        bg_map    = {"market":"rgba(0,200,150","news":"rgba(255,211,61","loans":"rgba(167,139,250","portfolio":"rgba(79,142,247"}
        col = color_map[p]; bg = bg_map[p]
        opacity = "0.15" if is_active else "0.07"
        border_opacity = "0.5" if is_active else "0.2"
        st.markdown(f"""<style>
        div[data-testid="stHorizontalBlock"] > div:nth-child({i+1}) button {{
            background:{bg},{opacity}) !important;
            border:1px solid {bg},{border_opacity}) !important;
            color:{''+col+'' if is_active else bg+',0.6)'} !important;
            font-weight:{'700' if is_active else '500'} !important;
            font-size:13px !important;
            letter-spacing:0.5px !important;
            text-transform:uppercase !important;
            height:48px !important;
            position:relative !important;
        }}
        </style>""", unsafe_allow_html=True)
        if st.button(lbl, key=f"nav_{p}", use_container_width=True):
            st.session_state["active_panel"] = p
            if p == "news": st.session_state["intel_seen_count"] = new_count
            st.rerun()
        # Corner badge for Intel — overlaid via negative margin trick
        if p == "news" and unseen_intel > 0:
            st.markdown(f"""
            <div style="position:relative;height:0;overflow:visible">
              <div style="position:absolute;top:-46px;right:8px;
                background:#FF4D6A;color:#fff;
                font-size:11px;font-weight:800;font-family:Inter,sans-serif;
                min-width:20px;height:20px;border-radius:99px;
                display:flex;align-items:center;justify-content:center;
                padding:0 5px;
                box-shadow:0 0 0 2px #0d0f1a;
                pointer-events:none;z-index:999">
                {unseen_intel}
              </div>
            </div>""", unsafe_allow_html=True)

active = st.session_state["active_panel"]
if active == "news": st.session_state["intel_seen_count"] = new_count
st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)

# ══ PANEL: MARKET ═════════════════════════════════════════════════════════════
if active == "market":
    if phase == "between":
        st.markdown("""
        <div style="background:linear-gradient(135deg,#0d0f1a 0%,#0a1220 100%);border:1px solid rgba(56,189,248,0.2);border-radius:16px;padding:40px 48px;text-align:center;margin:0 0 24px">
          <h2 style="font-family:Space Grotesk,sans-serif;font-size:32px;font-weight:700;color:#fff;letter-spacing:-1px;margin-bottom:10px">Round Over</h2>
          <p style="font-size:15px;color:rgba(255,255,255,0.4)">Check Banks to repay loans · Check Intel for new rumours · Next round starts soon</p>
        </div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-hdr">Live Market</div>', unsafe_allow_html=True)
    if not can_trade:
        st.markdown('<p style="font-size:13px;color:rgba(255,255,255,0.3);margin-bottom:16px">Trading is closed. Study the companies below.</p>', unsafe_allow_html=True)

    for cid, c in state["companies"].items():
        price = c["price"]; prev = c.get("prev_price", price)
        chg = price - prev; chg_pct = (chg/prev*100) if prev else 0
        chg_class = "delta-up" if chg >= 0 else "delta-down"
        arrow = "▲" if chg >= 0 else "▼"
        held = team["holdings"].get(cid, 0)
        rclass = risk_class(c.get("risk","Medium"))
        br = "border-radius:12px;" if not can_trade else "border-radius:12px 12px 0 0;"
        left_col, right_col = st.columns([1.1, 1])
        with left_col:
            # Header + bio unified in left col
            st.markdown(f"""
            <div class="company-card" style="{br}margin-bottom:0">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;margin-bottom:10px">
                <div>
                  <div style="display:flex;align-items:center;flex-wrap:wrap;gap:6px">
                    <span class="company-name">{c['name']}</span>
                    <span class="risk-badge {rclass}">{c.get('risk','Medium')} risk</span>
                  </div>
                  <div class="company-meta">{c['sector']} · {c.get('age','—')} · {c.get('size','—')}</div>
                  <div class="company-trait">{c.get('trait','')}</div>
                </div>
                <div style="text-align:right">
                  <div class="price-main">{fmt(price)}</div>
                  <div class="price-chg {chg_class}">{arrow} {abs(chg):.0f} ({chg_pct:+.1f}%)</div>
                  <div style="font-size:11px;color:rgba(255,255,255,0.25);margin-top:4px">{held} held</div>
                </div>
              </div>
              <div class="company-bio" style="margin-bottom:0">{c.get('bio','')}</div>
            </div>""", unsafe_allow_html=True)
            if can_trade:
                max_buy  = max(1, int(team["cash"] // price)) if team["cash"] >= price else 1
                max_sell = max(1, held)
                bmax_key = f"_bmax_{cid}"; smax_key = f"_smax_{cid}"
                buy_qty_key = f"buy_qty_{cid}"; sell_qty_key = f"sell_qty_{cid}"
                # ── MAX flag: apply BEFORE widgets render so no re-entrancy ──
                if st.session_state.pop(bmax_key, False):
                    st.session_state[buy_qty_key]  = max(1, max_buy)
                if st.session_state.pop(smax_key, False):
                    st.session_state[sell_qty_key] = max(1, max_sell)
                st.markdown('<div style="background:#0d0f1a;border:1px solid #1e2535;border-top:none;border-radius:0 0 12px 12px;padding:14px 24px 18px">', unsafe_allow_html=True)
                buy_col, sell_col = st.columns(2)
                with buy_col:
                    st.markdown('<div style="font-size:10px;color:rgba(255,255,255,0.3);text-transform:uppercase;letter-spacing:0.8px;margin-bottom:6px">Buy</div>', unsafe_allow_html=True)
                    b1,b2,b3 = st.columns([2,1,1])
                    with b1:
                        buy_qty = st.number_input("bq", min_value=1, max_value=max(1,max_buy), value=min(st.session_state.get(buy_qty_key,1),max(1,max_buy)), key=buy_qty_key, label_visibility="collapsed")
                    with b2:
                        st.markdown('<div class="max-btn">', unsafe_allow_html=True)
                        if st.button("MAX", key=f"bmax_btn_{cid}", use_container_width=True):
                            st.session_state[bmax_key] = True; st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    with b3:
                        st.markdown('<div class="buy-btn">', unsafe_allow_html=True)
                        if st.button("Buy", key=f"buy_{cid}", use_container_width=True):
                            cost = buy_qty * price; state = load_state(); team = state["teams"][tid]
                            if cost > team["cash"]: st.error("Not enough cash.")
                            else:
                                ph = team["holdings"].get(cid,0); pc = team["avg_cost"].get(cid,0)*ph
                                team["holdings"][cid] = ph+buy_qty
                                team["avg_cost"][cid] = (pc+cost)/team["holdings"][cid]
                                team["cash"] -= cost; state["teams"][tid] = team; save_state(state)
                                st.success(f"Bought {buy_qty} × {c['name']} @ {fmt(price)}"); st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown(f'<div style="font-size:11px;color:rgba(255,255,255,0.25);margin-top:4px">Cost: {fmt(buy_qty*price)}</div>', unsafe_allow_html=True)
                with sell_col:
                    st.markdown('<div style="font-size:10px;color:rgba(255,255,255,0.3);text-transform:uppercase;letter-spacing:0.8px;margin-bottom:6px">Sell</div>', unsafe_allow_html=True)
                    s1,s2,s3 = st.columns([2,1,1])
                    with s1:
                        sell_qty = st.number_input("sq", min_value=1, max_value=max(1,max_sell), value=min(st.session_state.get(sell_qty_key,1),max(1,max_sell)), key=sell_qty_key, label_visibility="collapsed", disabled=(held==0))
                    with s2:
                        st.markdown('<div class="max-btn">', unsafe_allow_html=True)
                        if st.button("MAX", key=f"smax_btn_{cid}", use_container_width=True, disabled=(held==0)):
                            st.session_state[smax_key] = True; st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    with s3:
                        st.markdown('<div class="sell-btn">', unsafe_allow_html=True)
                        if st.button("Sell", key=f"sell_{cid}", use_container_width=True, disabled=(held==0)):
                            state = load_state(); team = state["teams"][tid]
                            hn = team["holdings"].get(cid,0); sq = min(sell_qty,hn)
                            team["holdings"][cid] = hn-sq; team["cash"] += sq*price
                            if team["holdings"][cid]==0: team["avg_cost"][cid]=0
                            state["teams"][tid] = team; save_state(state)
                            st.success(f"Sold {sq} × {c['name']} @ {fmt(price)}"); st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown(f'<div style="font-size:11px;color:rgba(255,255,255,0.25);margin-top:4px">{"Value: "+fmt(sell_qty*price) if held>0 else "None held"}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="background:#0d0f1a;border:1px solid #1e2535;border-top:none;border-radius:0 0 12px 12px;height:4px"></div>', unsafe_allow_html=True)
        with right_col:
            import pandas as pd, altair as alt
            hist = team.get("price_history",{}).get(cid,[])
            if not hist: hist = [c.get("prev_price",price), price]
            elif len(hist)==1: hist = [hist[0], price]
            display_price = st.session_state["micro_prices"].get(cid, price) if phase == "trading" else price
            display_hist = hist[:-1] + [display_price] if hist else [display_price]
            chart_color = "#00C896" if display_hist[-1] >= display_hist[0] else "#FF4D6A"
            mn = min(display_hist); mx = max(display_hist)
            pad = max((mx - mn) * 0.6, price * 0.03)
            df = pd.DataFrame({"i": range(len(display_hist)), "Price": display_hist})
            _is_light = st.session_state.get("light_mode", False)
            _label_col = "rgba(30,60,30,0.7)"  if _is_light else "rgba(255,255,255,0.35)"
            _grid_col  = "rgba(0,80,0,0.08)"   if _is_light else "rgba(255,255,255,0.05)"
            _tick_col  = "rgba(30,60,30,0.5)"  if _is_light else "rgba(255,255,255,0.2)"
            chart = alt.Chart(df).mark_line(color=chart_color, strokeWidth=2).encode(
                x=alt.X("i:Q", axis=None),
                y=alt.Y("Price:Q", scale=alt.Scale(domain=[mn-pad, mx+pad]),
                        axis=alt.Axis(grid=True, gridColor=_grid_col,
                                      labelColor=_label_col, tickColor=_tick_col,
                                      domainColor=_tick_col,
                                      tickCount=4, format=",.0f",
                                      labelFont="Space Grotesk", labelFontSize=11)),
            ).properties(height=220, background="transparent").configure_view(strokeWidth=0)
            st.altair_chart(chart, use_container_width=True)
        st.markdown("<div style='margin-bottom:20px'></div>", unsafe_allow_html=True)

elif active == "news":
    st.markdown('<div class="section-hdr">Market Intelligence</div>', unsafe_allow_html=True)
    if not visible_news:
        st.markdown('<div style="text-align:center;padding:60px 20px"><p style="font-size:28px;font-weight:700;color:#fff;font-family:Space Grotesk,sans-serif">Nothing yet</p><p style="color:rgba(255,255,255,0.4);margin-top:8px">Intelligence drops as the game progresses.</p></div>', unsafe_allow_html=True)
    else:
        ctx_text = {
            "trading": "📡 Live feed: <strong>market events</strong> and <strong>insider hints</strong> only. Rumours surface during the break.",
            "between": "🌙 Break feed: <strong>rumours</strong> and <strong>insider hints</strong>. Market events resume next round.",
        }.get(phase, "Some of this was real. Some was noise.")
        st.markdown(f'<p style="font-size:13px;color:rgba(255,255,255,0.4);margin-bottom:16px">{ctx_text}</p>', unsafe_allow_html=True)
        for n in reversed(visible_news):
            ntype = n.get("type","custom"); lclass = news_label_class(ntype)
            st.markdown(f'<div class="news-card"><span class="news-label {lclass}">{n.get("label","News")}</span><div class="news-text">{n["text"]}</div></div>', unsafe_allow_html=True)

elif active == "loans":
    st.markdown('<div class="section-hdr">Bank Loans</div>', unsafe_allow_html=True)
    if "bank_open" not in st.session_state:
        st.session_state["bank_open"] = None

    if loan_balance > 0:
        st.markdown(f'<div class="loan-card"><div class="loan-title">Total Outstanding Loan</div><span style="font-size:28px;font-weight:700;font-family:Space Grotesk,monospace;color:#a78bfa">{fmt(loan_balance)}</span><div style="font-size:11px;color:rgba(255,255,255,0.2);margin-top:10px">Interest charged per bank at round-end.</div></div>', unsafe_allow_html=True)

    st.markdown("""<style>
    .bk-wrap { margin-bottom:12px; }
    .bk-head { padding:22px 24px; cursor:pointer; transition:filter 0.15s; border-radius:14px; }
    .bk-head.open { border-radius:14px 14px 0 0; }
    .bk-head:hover { filter:brightness(1.12); }
    .bk-head-top { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }
    .bk-hname  { font-size:16px; font-weight:700; font-family:'Space Grotesk',sans-serif; color:#fff; }
    .bk-hchev  { font-size:18px; color:rgba(255,255,255,0.4); transition:transform 0.25s; }
    .bk-hrate  { font-size:28px; font-weight:800; font-family:'Space Grotesk',monospace; margin-bottom:8px; }
    .bk-hmeta  { font-size:12px; color:rgba(255,255,255,0.45); margin-bottom:4px; }
    .bk-hnote  { font-size:11px; color:rgba(255,255,255,0.25); font-style:italic; }
    .bk-body   { padding:18px 24px; border-top:none; border-radius:0 0 14px 14px; }
    .bk-s .bk-head { background:#0a1a14; border:1px solid rgba(0,200,150,0.3); }
    .bk-m .bk-head { background:#18160a; border:1px solid rgba(255,217,61,0.3); }
    .bk-r .bk-head { background:#1a0a0e; border:1px solid rgba(255,77,106,0.3); }
    .bk-s .bk-body { background:#071210; border:1px solid rgba(0,200,150,0.2); }
    .bk-m .bk-body { background:#121005; border:1px solid rgba(255,217,61,0.2); }
    .bk-r .bk-body { background:#120508; border:1px solid rgba(255,77,106,0.2); }
    .bk-s .bk-hrate { color:#00C896; }
    .bk-m .bk-hrate { color:#ffd93d; }
    .bk-r .bk-hrate { color:#FF4D6A; }
    /* Invisible overlay button that covers the card */
    .bk-trigger { position:relative; margin-bottom:12px; }
    .bk-trigger button { position:absolute !important; inset:0 !important; width:100% !important; height:100% !important; opacity:0 !important; cursor:pointer !important; border:none !important; background:transparent !important; z-index:5 !important; margin:0 !important; padding:0 !important; min-height:unset !important; }
    /* light mode */
    body.light-mode .bk-s .bk-head { background:#f0fff8; border-color:rgba(0,150,90,0.4); }
    body.light-mode .bk-m .bk-head { background:#fffde8; border-color:rgba(160,120,0,0.4); }
    body.light-mode .bk-r .bk-head { background:#fff0f3; border-color:rgba(180,0,30,0.4); }
    body.light-mode .bk-s .bk-body { background:#e8faf2; border-color:rgba(0,150,90,0.25); }
    body.light-mode .bk-m .bk-body { background:#fdfae0; border-color:rgba(160,120,0,0.25); }
    body.light-mode .bk-r .bk-body { background:#fde8ed; border-color:rgba(180,0,30,0.25); }
    body.light-mode .bk-hname { color:#0d2e0d; }
    body.light-mode .bk-hmeta { color:#4a6a4a; }
    body.light-mode .bk-hnote { color:#7a947a; }
    body.light-mode .bk-hchev { color:rgba(0,60,0,0.35); }
    body.light-mode .bk-s .bk-hrate { color:#006b3c; }
    body.light-mode .bk-m .bk-hrate { color:#7a5c00; }
    body.light-mode .bk-r .bk-hrate { color:#a0001e; }
    </style>""", unsafe_allow_html=True)

    css_map = {"bank-safe": "bk-s", "bank-mid": "bk-m", "bank-risky": "bk-r"}

    for bk_id, bk in BANKS.items():
        bank_bal  = team.get(f"loan_{bk_id}", 0)
        used_pct  = int(bank_bal / bk["cap"] * 100) if bk["cap"] else 0
        available = max(0, bk["cap"] - bank_bal)
        is_open   = st.session_state["bank_open"] == bk_id
        cls       = css_map.get(bk["css"], "bk-s")
        btn_key   = f"bk_btn_{bk_id}"
        chev_rot  = "180deg" if is_open else "0deg"

        # Full HTML card — clicking fires hidden Streamlit button via JS
        st.markdown(f"""
        <div class="bk-wrap {cls}" id="bkwrap-{bk_id}" onclick="(function(){{
          var wrap = document.getElementById('bkwrap-{bk_id}');
          var container = wrap ? wrap.nextElementSibling : null;
          if (container) {{
            var btn = container.querySelector('button');
            if (btn) {{ btn.click(); return; }}
          }}
          // fallback: search whole page
          var all = document.querySelectorAll('.bk-trigger button');
          for (var i=0; i<all.length; i++) {{
            var p = all[i].closest('.bk-trigger');
            if (p && p.previousElementSibling && p.previousElementSibling.id === 'bkwrap-{bk_id}') {{
              all[i].click(); return;
            }}
          }}
        }})()">
          <div class="bk-head {'open' if is_open else ''}">
            <div class="bk-head-top">
              <span class="bk-hname">{bk['name']}</span>
              <span class="bk-hchev" style="transform:rotate({chev_rot})">▾</span>
            </div>
            <div class="bk-hrate">{bk['rate_label']}</div>
            <div class="bk-hmeta">Limit: {fmt(bk['cap'])} &nbsp;·&nbsp; Borrowed: {fmt(bank_bal)} ({used_pct}%)</div>
            <div class="bk-hnote">{bk['note']}</div>
          </div>
        </div>""", unsafe_allow_html=True)

        # Zero-size absolutely positioned container — truly invisible, no X shown
        st.markdown('<div style="position:absolute;width:0;height:0;overflow:hidden;opacity:0;pointer-events:none">', unsafe_allow_html=True)
        if st.button("x", key=btn_key):
            st.session_state["bank_open"] = bk_id if not is_open else None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # Accordion
        if is_open:
            st.markdown(f'<div class="bk-body {cls}">', unsafe_allow_html=True)
            if not can_bank:
                st.markdown('<p style="font-size:13px;color:rgba(255,255,255,0.4);margin:0">Borrowing is only available during trading rounds and breaks.</p>', unsafe_allow_html=True)
            elif available <= 0:
                st.markdown('<p style="font-size:13px;color:rgba(255,255,255,0.3);margin:0">Credit limit reached.</p>', unsafe_allow_html=True)
            else:
                valid_amts = [a for a in bk["borrow_options"] if a <= available]
                if valid_amts:
                    st.markdown('<p style="font-size:12px;color:rgba(255,255,255,0.4);margin:0 0 12px">Choose amount to borrow:</p>', unsafe_allow_html=True)
                    bcols = st.columns(len(valid_amts))
                    for i, amt in enumerate(valid_amts):
                        with bcols[i]:
                            st.markdown('<div class="loan-btn">', unsafe_allow_html=True)
                            if st.button(fmt(amt), key=f"borrow_{bk_id}_{amt}", use_container_width=True):
                                state = load_state(); team = state["teams"][tid]
                                team["cash"] = team.get("cash", 0) + amt
                                team["loan_balance"] = team.get("loan_balance", 0) + amt
                                team[f"loan_{bk_id}"] = team.get(f"loan_{bk_id}", 0) + amt
                                state["teams"][tid] = team; save_state(state)
                                st.session_state["bank_open"] = None
                                st.success(f"Borrowed {fmt(amt)} from {bk['name']}"); st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<p style="font-size:13px;color:rgba(255,255,255,0.3);margin:0">No valid amounts available.</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    if phase == "between" and loan_balance > 0:
        st.markdown('<p style="font-size:13px;color:rgba(255,255,255,0.5);margin:20px 0 8px">Repay now to reduce interest before next round:</p>', unsafe_allow_html=True)
        repay_options = []
        if loan_balance >= 4: repay_options.append(("Pay ¼", loan_balance//4))
        if loan_balance >= 2: repay_options.append(("Pay ½", loan_balance//2))
        repay_options.append(("Pay full", loan_balance))
        rcols = st.columns(len(repay_options))
        for i, (label, amount) in enumerate(repay_options):
            with rcols[i]:
                st.markdown('<div class="repay-btn">', unsafe_allow_html=True)
                if st.button(f"{label} ({fmt(amount)})", key=f"repay_{i}", use_container_width=True, disabled=(team["cash"]<amount)):
                    state = load_state(); team = state["teams"][tid]
                    if team["cash"] >= amount:
                        team["cash"] -= amount; team["loan_balance"] = max(0,team.get("loan_balance",0)-amount)
                        rem = amount
                        for bk_id in ["hawala_risky","axis_mid","rbi_safe"]:
                            bk_bal = team.get(f"loan_{bk_id}",0); red = min(bk_bal,rem)
                            team[f"loan_{bk_id}"] = bk_bal-red; rem -= red
                            if rem <= 0: break
                        state["teams"][tid] = team; save_state(state)
                        st.success(f"Repaid {fmt(amount)}."); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

elif active == "portfolio":
    st.markdown('<div class="section-hdr">Your Portfolio</div>', unsafe_allow_html=True)
    has = any(team["holdings"].get(cid,0) > 0 for cid in state["companies"])
    if not has:
        st.markdown('<div style="text-align:center;padding:60px 20px"><p style="font-size:28px;font-weight:700;color:#fff;font-family:Space Grotesk,sans-serif">No holdings</p><p style="color:rgba(255,255,255,0.4);margin-top:8px">Buy stocks from the Market panel.</p></div>', unsafe_allow_html=True)
    else:
        for cid, c in state["companies"].items():
            qty = team["holdings"].get(cid,0)
            if qty == 0: continue
            cp = c["price"]; avg = team["avg_cost"].get(cid,0); cv = qty*cp; pl = cv-qty*avg
            plc = "delta-up" if pl>=0 else "delta-down"; pls = "+" if pl>=0 else ""
            st.markdown(f'<div class="port-card"><div><div class="port-name">{c["name"]}</div><div class="port-qty">{qty} shares · {c["sector"]}</div></div><div class="port-stats"><div class="port-stat"><div class="s-label">Avg cost</div><div class="s-val">{fmt(avg)}</div></div><div class="port-stat"><div class="s-label">Current</div><div class="s-val">{fmt(cp)}</div></div><div class="port-stat"><div class="s-label">Value</div><div class="s-val">{fmt(cv)}</div></div><div class="port-stat"><div class="s-label">P / L</div><div class="s-val {plc}">{pls}{fmt(pl)}</div></div></div></div>', unsafe_allow_html=True)

# Auto-refresh handled by st_autorefresh(interval=1000) at top of file
