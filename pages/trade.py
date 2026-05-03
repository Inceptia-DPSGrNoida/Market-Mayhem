import streamlit as st
import json, time, uuid
from pathlib import Path
import sys, importlib.util
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import load_state, save_state, STARTING_CASH, ROUND_DURATION
from streamlit_autorefresh import st_autorefresh

# Load music_player from root dir (works whether it lives in pages/ or root)
def _load_music_player():
    for candidate in [
        Path(__file__).parent / "music_player.py",        # pages/music_player.py
        Path(__file__).parent.parent / "music_player.py", # root/music_player.py
    ]:
        if candidate.exists():
            spec = importlib.util.spec_from_file_location("music_player", candidate)
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.inject_music
    return lambda phase, volume=50: None  # graceful no-op if file missing

inject_music = _load_music_player()

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

/* Settings gear button */
.settings-gear-btn { background:rgba(255,255,255,0.05) !important; border:1px solid rgba(255,255,255,0.12) !important; color:rgba(255,255,255,0.5) !important; font-size:18px !important; width:38px !important; height:38px !important; border-radius:50% !important; padding:0 !important; min-height:unset !important; }
.settings-gear-btn:hover { background:rgba(255,255,255,0.1) !important; color:#fff !important; }

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

/* Settings panel */
.settings-overlay { position:fixed; top:0; left:0; right:0; bottom:0; z-index:9998; background:rgba(0,0,0,0.4); backdrop-filter:blur(4px); animation:fadeIn 0.2s ease; }
.settings-panel { position:fixed; top:0; right:0; width:320px; height:100vh; background:rgba(13,15,26,0.97); border-left:1px solid #1e2535; z-index:9999; padding:28px 24px; animation:slideIn 0.25s cubic-bezier(0.16,1,0.3,1); overflow-y:auto; }
@keyframes fadeIn { from{opacity:0} to{opacity:1} }
@keyframes slideIn { from{transform:translateX(100%);opacity:0} to{transform:translateX(0);opacity:1} }
.settings-panel h3 { font-family:'Space Grotesk',sans-serif; font-size:18px; font-weight:700; color:#fff; margin-bottom:24px; letter-spacing:-0.3px; }
.settings-row { margin-bottom:24px; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:24px; }
.settings-label { font-size:11px; color:rgba(255,255,255,0.35); text-transform:uppercase; letter-spacing:1.5px; font-weight:600; margin-bottom:10px; }
.toggle-row { display:flex; align-items:center; justify-content:space-between; }
.toggle-text { font-size:14px; color:rgba(255,255,255,0.7); font-weight:500; }

/* Light mode overrides */
body.light-mode { background:#f0f2f5 !important; }
body.light-mode .ticker-wrap { background:#e8eaf0; border-color:#d0d4e0; }
body.light-mode .ticker-item { color:#555; }
body.light-mode .ticker-item .sym { color:#111; }
body.light-mode .company-card,body.light-mode .metric-card,body.light-mode .news-card,body.light-mode .bank-card,body.light-mode .loan-card,body.light-mode .port-card,body.light-mode .lb-card,body.light-mode .rule-card { background:#fff; border-color:#e0e4ef; }
body.light-mode .company-name,body.light-mode .port-name,body.light-mode .lb-name,body.light-mode .rule-content h4,body.light-mode .bk-name { color:#0d0f1a; }
body.light-mode .company-meta,body.light-mode .company-trait,body.light-mode .company-bio,body.light-mode .bk-limit,body.light-mode .bk-note,body.light-mode .port-qty { color:#666; }
body.light-mode .price-main { color:#0d0f1a; }
body.light-mode .value { color:#0d0f1a !important; }
body.light-mode .section-hdr { color:#0d0f1a; border-color:#e0e4ef; }
body.light-mode .settings-panel { background:rgba(240,242,245,0.98); border-color:#d0d4e0; }
body.light-mode .settings-panel h3 { color:#0d0f1a; }
body.light-mode .settings-label { color:rgba(0,0,0,0.4); }
body.light-mode .toggle-text { color:rgba(0,0,0,0.65); }
body.light-mode [class*="css"] { color:#0d0f1a; }

div[data-testid="stForm"] button[kind="primaryFormSubmit"] {
    background: #0a4a35 !important; border: 1px solid #00C896 !important;
    color: #00C896 !important; font-weight: 600 !important;
}
</style>
""", unsafe_allow_html=True)

BANKS = {
    "rbi_safe":     {"name":"RBI Trustbank",     "rate":0.07,  "cap":50000,  "min_borrow":5000,  "max_borrow":50000,  "css":"bank-safe",  "rate_label":"7% / round",  "note":"Regulated. Stable. Low ceiling but fair rates.",  "borrow_options":[5000,10000,25000,50000]},
    "axis_mid":     {"name":"Axis Capital",       "rate":0.12,  "cap":100000, "min_borrow":40000, "max_borrow":100000, "css":"bank-mid",   "rate_label":"12% / round", "note":"Mid-tier lender. Decent limit for growing teams.", "borrow_options":[40000,60000,80000,100000]},
    "hawala_risky": {"name":"BlackRock Ventures", "rate":0.18,  "cap":200000, "min_borrow":90000, "max_borrow":200000, "css":"bank-risky", "rate_label":"18% / round", "note":"High credit line. Aggressive interest. Not for the faint-hearted.", "borrow_options":[90000,120000,160000,200000]},
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

# ── Music ─────────────────────────────────────────────────────────────────────
_music_vol = st.session_state.get("music_volume", 50)
inject_music(phase, _music_vol)

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

# ── Header (non-ended phases only) ───────────────────────────────────────────
participant_tag = f' &nbsp;<span style="font-size:13px;font-weight:500;color:rgba(255,255,255,0.35)">· P{team.get("participant_num","")}</span>' if team.get("participant_num") else ""

# Settings state
if "settings_open" not in st.session_state: st.session_state["settings_open"] = False
if "music_volume" not in st.session_state: st.session_state["music_volume"] = 50
if "light_mode" not in st.session_state: st.session_state["light_mode"] = False

hcol_left, hcol_mid, hcol_right = st.columns([6, 2, 1])
with hcol_left:
    st.markdown(f"""
    <div style="margin:14px 0 20px">
      <div style="font-family:Space Grotesk,sans-serif;font-size:26px;font-weight:700;color:#fff;letter-spacing:-0.5px">{team['name']}{participant_tag}</div>
      <div style="font-size:12px;color:rgba(255,255,255,0.3);margin-top:2px">Market Mayhem · Inceptia</div>
    </div>""", unsafe_allow_html=True)
with hcol_mid:
    st.markdown(f'<div style="font-size:12px;color:rgba(255,255,255,0.25);font-family:Space Grotesk,monospace;margin-top:22px;text-align:right">Round {state["round"]} / 4</div>', unsafe_allow_html=True)
with hcol_right:
    st.markdown('<div style="margin-top:14px">', unsafe_allow_html=True)
    st.markdown('<style>.gear-col button { background:rgba(255,255,255,0.05) !important; border:1px solid rgba(255,255,255,0.12) !important; color:rgba(255,255,255,0.6) !important; font-size:18px !important; border-radius:50% !important; height:38px !important; } .gear-col button:hover { background:rgba(255,255,255,0.1) !important; color:#fff !important; }</style>', unsafe_allow_html=True)
    st.markdown('<div class="gear-col">', unsafe_allow_html=True)
    if st.button("⚙", key="open_settings_btn", use_container_width=False):
        st.session_state["settings_open"] = not st.session_state["settings_open"]
        st.rerun()
    st.markdown('</div></div>', unsafe_allow_html=True)

# Settings panel (slide-in overlay using Streamlit widgets positioned via CSS)
if st.session_state["settings_open"]:
    light_mode = st.session_state["light_mode"]
    music_vol   = st.session_state["music_volume"]
    toggle_label = "☀️ Light" if not light_mode else "🌙 Dark"
    st.markdown("""<div class="settings-overlay"></div>
    <div class="settings-panel">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px">
        <h3 style="margin:0">Settings</h3>
      </div>
      <div class="settings-row">
        <div class="settings-label">Appearance</div>
      </div>
      <div class="settings-row">
        <div class="settings-label">Music Volume</div>
        <div style="font-size:13px;color:rgba(255,255,255,0.5);margin-bottom:8px">Background music level (lobby &amp; breaks)</div>
      </div>
    </div>""", unsafe_allow_html=True)
    s1, s2, s3 = st.columns([1, 1, 1])
    with s1:
        if st.button("✕ Close", key="close_settings_btn"):
            st.session_state["settings_open"] = False
            st.rerun()
    with s2:
        if st.button(toggle_label, key="toggle_theme_btn"):
            st.session_state["light_mode"] = not st.session_state["light_mode"]
            st.rerun()
    new_vol = st.slider("Volume", 0, 100, music_vol, key="music_vol_slider")
    if new_vol != music_vol:
        st.session_state["music_volume"] = new_vol

# Apply light mode
if st.session_state.get("light_mode"):
    st.markdown('<script>document.body.classList.add("light-mode")</script>', unsafe_allow_html=True)

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
            chart = alt.Chart(df).mark_line(color=chart_color, strokeWidth=2).encode(
                x=alt.X("i:Q", axis=None),
                y=alt.Y("Price:Q", scale=alt.Scale(domain=[mn-pad, mx+pad]), axis=alt.Axis(grid=True, gridColor="rgba(255,255,255,0.05)", labelColor="rgba(255,255,255,0.3)", tickCount=4, format=",.0f")),
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

    st.markdown('<div class="bank-grid">', unsafe_allow_html=True)
    for bk_id, bk in BANKS.items():
        bank_bal = team.get(f"loan_{bk_id}", 0)
        used_pct = int(bank_bal / bk["cap"] * 100) if bk["cap"] else 0
        available = max(0, bk["cap"] - bank_bal)
        is_open = st.session_state["bank_open"] == bk_id
        chevron_cls = "bk-chevron open" if is_open else "bk-chevron"
        st.markdown(f"""
        <div class="bank-card {bk['css']}" style="border-radius:{'12px 12px 0 0' if is_open else '12px'}">
          <div class="bk-name">{bk['name']} <span class="{chevron_cls}">▾</span></div>
          <div class="bk-rate">{bk['rate_label']}</div>
          <div class="bk-limit">Limit: {fmt(bk['cap'])} · Borrowed: {fmt(bank_bal)} ({used_pct}%)</div>
          <div class="bk-note">{bk['note']}</div>
        </div>""", unsafe_allow_html=True)

        # Toggle button (invisible, full-width, sits over the card visually)
        toggle_key = f"bank_toggle_{bk_id}"
        st.markdown(f'<style>div[data-testid="element-container"]:has(button[kind="secondary"][data-testid="{toggle_key}"]) button {{ position:relative;margin-top:-80px;height:80px;width:100%;background:transparent !important;border:none !important;color:transparent !important;cursor:pointer !important;z-index:10; }}</style>', unsafe_allow_html=True)
        if st.button(" ", key=toggle_key, use_container_width=True):
            st.session_state["bank_open"] = bk_id if not is_open else None
            st.rerun()

        # Accordion content
        if is_open:
            st.markdown('<div class="bank-accordion-inner">', unsafe_allow_html=True)
            if not can_bank:
                st.markdown('<p style="font-size:13px;color:rgba(255,255,255,0.35);padding:4px 0">Borrowing is only available during trading rounds and breaks.</p>', unsafe_allow_html=True)
            elif available <= 0:
                st.markdown('<p style="font-size:13px;color:rgba(255,255,255,0.25);padding:4px 0">Credit limit reached for this bank.</p>', unsafe_allow_html=True)
            else:
                valid_amts = [a for a in bk["borrow_options"] if a <= available]
                if valid_amts:
                    st.markdown('<p style="font-size:12px;color:rgba(255,255,255,0.4);margin-bottom:10px">Choose amount to borrow:</p>', unsafe_allow_html=True)
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
                    st.markdown('<p style="font-size:13px;color:rgba(255,255,255,0.25)">No valid borrow amounts available.</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

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
