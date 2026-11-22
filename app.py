from pathlib import Path
from io import BytesIO
import html
import hashlib
import re

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# =============================================================================
# PetroTrade Intelligence
# Supports one source CSV with unknown direction, or separate import/export CSVs.
# Source columns: HS Code, HS Description, Country Name, Month-Year_USD_Mn
# =============================================================================
st.set_page_config(
    page_title="PetroTrade Intelligence",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DATA_FILE = Path(__file__).parent / "DGCIS_DATA.csv"
MONTH_RE = re.compile(r"^[A-Za-z]+-\d{4}_USD_Mn$")
MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

COMMODITY_INFO = {
    27: {
        "commodity": "Mineral fuels & oils",
        "category": "Petroleum & energy feedstocks",
        "description": "Mineral fuels, mineral oils and related distillation products. This is a broad HS chapter, not only petrochemicals.",
    },
    28: {
        "commodity": "Inorganic chemicals",
        "category": "Basic chemicals",
        "description": "Inorganic chemical elements, compounds and related products.",
    },
    29: {
        "commodity": "Organic chemicals",
        "category": "Chemical intermediates",
        "description": "Organic chemical compounds that may serve as industrial and chemical intermediates.",
    },
    39: {
        "commodity": "Plastics & articles",
        "category": "Polymers & plastics",
        "description": "Plastics in primary forms and articles made from plastics.",
    },
    40: {
        "commodity": "Rubber & articles",
        "category": "Rubber & elastomers",
        "description": "Rubber and articles of rubber, including a range of downstream products.",
    },
}

COUNTRY_ALIASES = {
    "U S A": "United States", "USA": "United States", "U ARAB EMTS": "United Arab Emirates",
    "NETHERLAND": "Netherlands", "SAUDI ARAB": "Saudi Arabia", "SRI LANKA DSR": "Sri Lanka",
    "YEMEN REPUBLC": "Yemen", "KYRGHYZSTAN": "Kyrgyzstan", "C AFRI REP": "Central African Republic",
    "BOSNIA-HRZGOVIN": "Bosnia and Herzegovina", "MACEDONIA": "North Macedonia",
    "CHINA P RP": "China", "TANZANIA REP": "Tanzania", "U S A": "United States",
}
EXCLUDED_MARKETS = {
    "TOTAL", "ALL COUNTRIES", "WORLD TOTAL", "UNSPECIFIED", "NOT SPECIFIED", "OTHERS", "OTHER", ""
}
FLOW_NAMES = ["Imports", "Exports", "Direction not verified"]
PALETTE = ["#55D7C4", "#9A8CFF", "#F2B66D", "#6FA7F8", "#D985A5", "#91A8C4"]
TEAL = "#55D7C4"
NAVY = "#DCE6F2"
SLATE = "#91A1B7"
GREEN = "#36C995"
RED = "#FF7182"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');
:root { color-scheme: light; }
html, body, [class*="css"], [data-testid="stAppViewContainer"] {
  font-family: 'DM Sans', 'Segoe UI', sans-serif !important;
}
[data-testid="stAppViewContainer"] { background: #F5F3EE; color: #172A3A; }
.block-container { padding-top: 1.1rem; padding-bottom: 3rem; max-width: 1660px; }
h1, h2, h3, h4, h5, h6, .hero-title, .section-title, .control-deck-title {
  font-family: 'Space Grotesk', 'DM Sans', 'Segoe UI', sans-serif !important;
  letter-spacing: -0.035em;
}
[data-testid="stSidebar"] { background: #ECE8E0; border-right: 1px solid #E3DED4; }
[data-testid="stSidebar"] > div { padding-top: 1.15rem; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #53616D; }
[data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
.eyebrow { font-size: .70rem; letter-spacing: .17em; font-weight: 800; color: #E46F4A; text-transform: uppercase; }

/* Landing / welcome page */
.landing-shell { max-width: 1500px; margin: 0 auto; }
.landing-topline { display:flex; align-items:center; justify-content:space-between; gap:1rem; margin:0 0 1rem; padding:.15rem .15rem; }
.landing-brand { display:flex; align-items:center; gap:.7rem; color:#172A3A; font-weight:850; letter-spacing:-.025em; }
.landing-brand-mark { width:36px; height:36px; display:flex; align-items:center; justify-content:center; border-radius:10px; background:#172A3A; color:#F2A78E; font-size:1rem; }
.landing-brand small { display:block; color:#7B858D; font-size:.64rem; letter-spacing:.13em; text-transform:uppercase; font-weight:800; margin-top:.08rem; }
.landing-top-status { color:#66727B; font-size:.74rem; letter-spacing:.06em; font-weight:700; text-transform:uppercase; }
.landing-question { padding:.85rem 0; border-bottom:1px solid rgba(255,255,255,.12); }
.landing-question:last-child { border-bottom:0; }
.landing-question-title { color:#FFFFFF; font-size:.89rem; font-weight:750; margin-bottom:.2rem; }
.landing-question-copy { color:#CCD8DC; font-size:.77rem; line-height:1.45; }
.landing-feature { min-height:150px; }
.landing-bottom { display:flex; align-items:center; justify-content:space-between; gap:1rem; flex-wrap:wrap; margin-top:.8rem; padding-top:.75rem; border-top:1px solid #DED9CF; color:#7B858D; font-size:.75rem; }
.landing-workflow { background:#FFFEFC; border:1px solid #DED9CF; border-radius:12px; padding:1rem 1.1rem; min-height:105px; }
.landing-workflow-num { color:#C95C3B; font-family:'Space Grotesk','DM Sans',sans-serif; font-size:1.35rem; font-weight:800; margin-bottom:.25rem; }
.landing-workflow-title { color:#172A3A; font-weight:800; font-size:.9rem; margin-bottom:.2rem; }
.landing-workflow-copy { color:#68727D; font-size:.78rem; line-height:1.5; }
.workspace-masthead { display:flex; align-items:center; justify-content:space-between; gap:1.2rem; padding:.65rem 0 .9rem; margin:0 0 .65rem; border-bottom:1px solid #DED9CF; }
.workspace-brandline { display:flex; align-items:center; gap:.75rem; min-width:0; }
.workspace-monogram { display:flex; align-items:center; justify-content:center; flex:0 0 42px; width:42px; height:42px; border-radius:12px; background:#172A3A; color:#F2A78E; font-family:'Space Grotesk',sans-serif; font-size:1rem; font-weight:800; letter-spacing:-.06em; }
.workspace-brandname { color:#172A3A; font-family:'Space Grotesk','DM Sans',sans-serif; font-size:1.12rem; line-height:1.2; font-weight:800; letter-spacing:-.045em; }
.workspace-brandname span { color:#C95C3B; }
.workspace-overline { color:#8A7066; font-size:.62rem; font-weight:850; letter-spacing:.15em; text-transform:uppercase; margin-top:.22rem; }
.workspace-current { flex:0 1 420px; text-align:right; }
.workspace-current-label { color:#C95C3B; font-size:.62rem; font-weight:850; letter-spacing:.15em; text-transform:uppercase; }
.workspace-current-title { color:#172A3A; font-family:'Space Grotesk','DM Sans',sans-serif; font-weight:750; font-size:1.05rem; line-height:1.2; margin-top:.18rem; }
.workspace-current-copy { color:#68727D; font-size:.75rem; margin-top:.2rem; line-height:1.4; }
.navbar-heading { margin:.15rem 0 .35rem; }
.navbar-hint { font-size:.70rem; }
@media (max-width:900px) { .workspace-masthead { align-items:flex-start; flex-direction:column; } .workspace-current { text-align:left; flex:auto; } .landing-topline { align-items:flex-start; flex-direction:column; } }

.landing-hero {
  position: relative; overflow: hidden; display: grid;
  grid-template-columns: minmax(0, 1.38fr) minmax(270px, .62fr); gap: 2.1rem;
  padding: clamp(1.8rem, 4vw, 3.6rem); min-height: 380px;
  border-radius: 16px 30px 16px 30px;
  background: linear-gradient(118deg, #172A3A 0%, #243847 60%, #344E5B 100%);
  color: #F5F3EE; border-left: 6px solid #E46F4A;
  box-shadow: 0 18px 45px rgba(23,42,58,.14); animation: fadeSlideIn .38s ease both;
}
.landing-hero:before { content:""; position:absolute; width:390px; height:390px; border-radius:50%; right:-105px; top:-170px; border:1px solid rgba(242,167,142,.25); box-shadow:0 0 0 42px rgba(242,167,142,.035),0 0 0 90px rgba(242,167,142,.025); pointer-events:none; }
.landing-main, .landing-aside { position:relative; z-index:1; }
.landing-kicker { color:#F2A78E; font-size:.7rem; font-weight:850; letter-spacing:.2em; text-transform:uppercase; margin-bottom:1.1rem; }
.landing-title { max-width:800px; font-family:'Space Grotesk','DM Sans','Segoe UI',sans-serif; font-size:clamp(2.4rem,4.8vw,4.45rem); line-height:1.02; font-weight:750; letter-spacing:-.065em; margin-bottom:1.15rem; }
.landing-title span { color:#F2A78E; }
.landing-copy { max-width:760px; color:#D7E1E4; font-size:1rem; line-height:1.75; }
.landing-chips { display:flex; flex-wrap:wrap; gap:.55rem; margin-top:1.35rem; }
.landing-chip { border:1px solid rgba(255,255,255,.20); background:rgba(255,255,255,.065); border-radius:7px; padding:.42rem .68rem; font-size:.76rem; color:#F4ECE8; }
.landing-aside { align-self:stretch; display:flex; flex-direction:column; justify-content:center; padding:1.3rem 1.4rem; border:1px solid rgba(255,255,255,.18); border-radius:14px; background:rgba(255,255,255,.055); backdrop-filter:blur(4px); }
.landing-aside-title { color:#F2A78E; font-size:.68rem; letter-spacing:.17em; font-weight:850; text-transform:uppercase; margin-bottom:1rem; }
.landing-route { display:grid; grid-template-columns:34px 1fr; gap:.8rem; padding:.9rem 0; border-bottom:1px solid rgba(255,255,255,.12); }
.landing-route:last-of-type { border-bottom:0; }
.landing-route-num { width:30px; height:30px; display:flex; align-items:center; justify-content:center; border-radius:8px; background:rgba(242,167,142,.15); color:#F2A78E; font-weight:850; font-size:.78rem; }
.landing-route-title { font-weight:750; font-size:.91rem; color:#FFFFFF; margin-bottom:.2rem; }
.landing-route-copy { color:#CCD8DC; font-size:.79rem; line-height:1.45; }
.landing-stat { min-height:100px; background:#FFFEFC; border:1px solid #DED9CF; border-radius:12px; padding:1rem 1.05rem; box-shadow:0 3px 10px rgba(23,42,58,.035); }
.landing-stat-label { color:#68727D; font-weight:750; font-size:.7rem; letter-spacing:.08em; text-transform:uppercase; margin-bottom:.55rem; }
.landing-stat-value { color:#172A3A; font-family:'Space Grotesk','DM Sans','Segoe UI',sans-serif; font-size:1.6rem; line-height:1.15; font-weight:750; letter-spacing:-.04em; }
.landing-stat-foot { color:#7B858D; font-size:.75rem; line-height:1.45; margin-top:.45rem; }
.landing-section-title { color:#172A3A; font-family:'Space Grotesk','DM Sans','Segoe UI',sans-serif; font-size:1.35rem; font-weight:750; letter-spacing:-.035em; margin:.35rem 0 .25rem; }
.landing-section-copy { color:#68727D; font-size:.9rem; line-height:1.6; margin-bottom:1rem; }
.landing-feature { height:100%; min-height:165px; padding:1.15rem; background:#FFFEFC; border:1px solid #DED9CF; border-radius:12px; transition:transform .2s ease, box-shadow .2s ease, border-color .2s ease; }
.landing-feature:hover { transform:translateY(-4px); box-shadow:0 12px 24px rgba(23,42,58,.07); border-color:#E5B19D; }
.landing-feature-icon { width:38px; height:38px; display:flex; align-items:center; justify-content:center; background:#FBE8DF; color:#A94328; border-radius:9px; font-size:1.1rem; margin-bottom:.8rem; }
.landing-feature-title { font-size:.98rem; font-weight:780; color:#172A3A; margin-bottom:.4rem; }
.landing-feature-copy { font-size:.82rem; color:#68727D; line-height:1.55; }
.landing-footnote { background:#FDF4E4; border:1px solid #EED7A7; color:#6E531F; border-radius:10px; padding:.8rem 1rem; font-size:.82rem; line-height:1.55; }
@media (max-width: 900px) { .landing-hero { grid-template-columns:1fr; gap:1.3rem; } .landing-title { font-size:2.55rem; } .landing-aside { padding:1rem; } }

.hero {
  background: linear-gradient(115deg, #172A3A 0%, #243847 68%, #344E5B 100%);
  color: white; padding: 1.9rem 2rem; border-radius: 13px 26px 13px 26px;
  margin: .1rem 0 1rem; border-left: 5px solid #E46F4A;
  box-shadow: 0 14px 32px rgba(23,42,58,.12); animation: fadeSlideIn .32s ease both;
}
.hero .hero-eyebrow { color: #F2A78E; font-size: .69rem; font-weight: 800; letter-spacing: .19em; text-transform: uppercase; margin-bottom: .6rem; }
.hero .hero-title { font-size: 2.45rem; font-weight: 750; line-height: 1.07; letter-spacing: -.055em; margin: 0 0 .55rem; }
.hero .hero-sub { max-width: 940px; color: #E0E7E9; font-size: .98rem; line-height: 1.65; }
.hero-meta { display: flex; gap: .55rem; flex-wrap: wrap; margin-top: 1.15rem; }
.hero-chip { display: inline-block; border: 1px solid rgba(255,255,255,.20); color: #F5F3EE; background: rgba(255,255,255,.075); padding: .35rem .68rem; border-radius: 6px; font-size: .73rem; }
/* Main application navigation bar */
.navbar-heading { display:flex; align-items:center; justify-content:space-between; gap:1rem; margin:.25rem 0 .45rem; }
.navbar-kicker { color:#A35A43; text-transform:uppercase; letter-spacing:.16em; font-size:.66rem; font-weight:850; }
.navbar-hint { color:#7B858D; font-size:.73rem; }
div[data-testid="stButton"] > button {
  min-height:2.65rem; white-space:normal; line-height:1.12; padding:.48rem .42rem;
  border-radius:9px; border:1px solid #DED9CF; background:#FFFEFC; color:#53616D;
  font-size:.78rem; font-weight:700; transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease, background .18s ease;
}
div[data-testid="stButton"] > button:hover { transform:translateY(-2px); border-color:#E46F4A; color:#A94328; box-shadow:0 5px 14px rgba(23,42,58,.07); }
div[data-testid="stButton"] > button[kind="primary"] { background:#FBE8DF !important; border:1px solid #E46F4A !important; color:#A94328 !important; box-shadow:inset 0 0 0 1px rgba(228,111,74,.08); }
div[data-testid="stButton"] > button[kind="primary"]:hover { background:#F7DCCF !important; border-color:#C95C3B !important; }
.navbar-divider { height:1px; background:#DED9CF; margin:.6rem 0 .95rem; }
@media (max-width: 1050px) {
  div[data-testid="stButton"] > button { font-size:.70rem; padding:.42rem .25rem; min-height:2.8rem; }
}
div[data-testid="stButton"] > button:focus-visible,
[data-baseweb="select"] > div:focus-within,
[data-testid="stTextInput"] input:focus-visible {
  outline:2px solid #C95C3B !important;
  outline-offset:2px !important;
}
[data-testid="stFormSubmitButton"] button { min-height:2.55rem; }
/* Inputs and selections */
[data-baseweb="select"] > div { border-color:#DED9CF !important; border-radius:8px !important; }
[data-baseweb="tag"] { background:#E46F4A !important; border-radius:5px !important; }
[data-baseweb="tag"] span { color:#FFFFFF !important; }
button[kind="primary"] { background:#E46F4A !important; border-color:#E46F4A !important; }
button[kind="primary"]:hover { background:#C95C3B !important; border-color:#C95C3B !important; }
.section-kicker { font-size:.68rem; letter-spacing:.16em; text-transform:uppercase; font-weight:850; color:#C95C3B; margin:.25rem 0 .28rem; }
.section-title { font-size:1.4rem; letter-spacing:-.04em; font-weight:750; color:#172A3A; margin:0 0 .22rem; }
.section-note { font-size:.88rem; line-height:1.58; color:#68727D; margin:0 0 .9rem; }
.kpi-card { background:#FFFEFC; border:1px solid #E3DED4; border-top:3px solid #E46F4A; border-radius:10px 18px 10px 18px; padding:1.1rem 1.15rem 1rem; min-height:128px; box-shadow:0 4px 12px rgba(23,42,58,.035); animation:fadeSlideIn .32s ease both; transition:transform .2s ease,box-shadow .2s ease; }
.kpi-card:hover { transform:translateY(-3px); box-shadow:0 12px 25px rgba(23,42,58,.09); }
.kpi-label { color:#68727D; font-size:.75rem; font-weight:750; margin-bottom:.52rem; letter-spacing:.045em; cursor:help; text-decoration:underline dotted #A9A39A; text-underline-offset:3px; }
.kpi-value { color:#172A3A; font-family:'Space Grotesk','DM Sans',sans-serif; font-size:1.82rem; line-height:1.1; letter-spacing:-.045em; font-weight:700; }
.kpi-foot { color:#737C84; font-size:.76rem; margin-top:.6rem; line-height:1.4; }
.insight-grid-card { background:#FFFEFC; border:1px solid #E3DED4; border-radius:10px 16px 10px 16px; padding:1rem; min-height:118px; box-shadow:0 2px 8px rgba(23,42,58,.025); animation:fadeSlideIn .32s ease both; transition:transform .18s ease,box-shadow .18s ease; }
.insight-grid-card:hover { transform:translateY(-3px); box-shadow:0 10px 20px rgba(23,42,58,.065); }
.insight-mark { display:inline-flex; align-items:center; justify-content:center; width:31px; height:31px; background:#FBE8DF; color:#C95C3B; border-radius:8px; font-size:.9rem; font-weight:850; margin-bottom:.62rem; }
.insight-label { color:#68727D; text-transform:uppercase; letter-spacing:.11em; font-size:.65rem; font-weight:850; margin-bottom:.35rem; }
.insight-text { color:#263844; font-size:.88rem; line-height:1.55; }
.callout { background:#FFF5E7; border:1px solid #E7C98C; color:#74532B; border-radius:8px; padding:.75rem .95rem; font-size:.83rem; line-height:1.55; margin:.4rem 0 .85rem; }
/* Custom empty states */
.empty-state {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    background: #FFFEFC;
    border: 1px dashed #D6CFC3;
    border-left: 4px solid #E46F4A;
    border-radius: 10px 16px 10px 16px;
    padding: 18px 20px;
    margin: 10px 0 18px;
    box-shadow: 0 3px 10px rgba(23,42,58,.025);
}

.empty-state-mark {
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 0 0 36px;
    height: 36px;
    border-radius: 9px;
    background: #FBE8DF;
    color: #C95C3B;
    font-size: 17px;
    font-weight: 800;
}

.empty-state-content {
    flex: 1;
}

.empty-state-title {
    color: #172A3A;
    font-size: .95rem;
    font-weight: 750;
    margin-bottom: 4px;
}

.empty-state-message {
    color: #68727D;
    font-size: .84rem;
    line-height: 1.55;
}

.empty-state-action {
    color: #C95C3B;
    font-size: .78rem;
    font-weight: 650;
    margin-top: 8px;
}
.info-panel { background:#F0EEE8; border:1px solid #E3DED4; border-left:3px solid #E46F4A; border-radius:8px 14px 8px 14px; padding:1rem 1.15rem; margin:.4rem 0 .95rem; color:#4B5D68; line-height:1.6; }
.info-panel b { color:#172A3A; }
.panel-note { color:#7A838B; font-size:.75rem; line-height:1.48; }
/* Chart cards */
div[data-testid="stPlotlyChart"] { background:#FFFEFC; border:1px solid #E3DED4; border-radius:10px 18px 10px 18px; padding:.38rem .42rem .08rem; box-shadow:0 3px 11px rgba(23,42,58,.025); animation:chartEnter .30s cubic-bezier(.2,.75,.3,1) both; transition:transform .2s ease,box-shadow .2s ease,border-color .2s ease; }
div[data-testid="stPlotlyChart"]:hover { transform:translateY(-1px); box-shadow:0 8px 18px rgba(23,42,58,.06); border-color:#E8B6A5; }
div[data-testid="stDataFrame"] { border:1px solid #E3DED4; border-radius:9px; overflow:hidden; }
.control-deck { background:linear-gradient(180deg,#FFFEFC 0%,#F8F6F1 100%); border:1px solid #E3DED4; border-radius:12px 20px 12px 20px; padding:1.1rem 1.2rem .5rem; margin:.7rem 0 1rem; box-shadow:0 6px 18px rgba(23,42,58,.04); }
.control-deck-title { color:#172A3A; font-size:1.08rem; font-weight:750; margin-bottom:.12rem; }
.control-deck-sub { color:#68727D; font-size:.82rem; margin-bottom:.8rem; line-height:1.5; }
.scope-strip { display:flex; align-items:center; flex-wrap:wrap; gap:.55rem; background:#F0EEE8; border:1px solid #E3DED4; color:#405461; border-radius:8px; padding:.62rem .85rem; margin:.65rem 0 .95rem; font-size:.79rem; }
.scope-pill { background:#FFFEFC; border:1px solid #DED9CF; border-radius:6px; padding:.27rem .58rem; color:#263844; font-weight:700; }
.scope-pill-status { background:#E7F0EA; border-color:#D4E2D8; color:#315D49; }
.scope-pill-muted { background:transparent; border-style:dashed; color:#68727D; font-weight:600; }
div[data-testid="stForm"] { background:#F8F6F1; border:1px solid #E3DED4; border-radius:10px; padding:.75rem; }
hr { border-color:#E3DED4; }
@keyframes fadeSlideIn { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
@keyframes chartEnter { from { opacity:.35; transform:translateY(8px) scale(.996); } to { opacity:1; transform:translateY(0) scale(1); } }
@media (prefers-reduced-motion:reduce) { *,*::before,*::after { animation-duration:.01ms !important; transition-duration:.01ms !important; } }
@media (max-width:900px) { .hero .hero-title { font-size:1.85rem; } .kpi-value { font-size:1.48rem; } }

/* COMMIT 14: MODERN DARK VISUAL REFRESH */
:root {
  color-scheme: dark;
  --pt-page: #0A1020;
  --pt-panel: #111C30;
  --pt-panel-raised: #16243A;
  --pt-soft: #0E192B;
  --pt-border: #263750;
  --pt-text: #E8EEF7;
  --pt-muted: #91A1B7;
  --pt-accent: #55D7C4;
  --pt-accent-strong: #35BFAE;
  --pt-accent-soft: rgba(85, 215, 196, .12);
  --pt-violet: #9A8CFF;
}
html, body, [class*="css"], [data-testid="stAppViewContainer"],
[data-testid="stMarkdownContainer"], input, textarea, button, label {
  font-family: 'DM Sans', 'Segoe UI', sans-serif !important;
}
html, body { background: var(--pt-page) !important; color: var(--pt-text) !important; }
[data-testid="stAppViewContainer"], .main, section.main, [data-testid="stMain"] {
  background:
    radial-gradient(ellipse at 8% 0%, rgba(65, 103, 173, .19), transparent 34%),
    radial-gradient(ellipse at 94% 7%, rgba(119, 89, 194, .13), transparent 30%),
    linear-gradient(180deg, #0A1020 0%, #0D1728 55%, #0A1221 100%) !important;
  color: var(--pt-text) !important;
}
[data-testid="stHeader"] { background: rgba(10,16,32,.72) !important; }
[data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }
#MainMenu, footer { visibility: hidden; }
.block-container { padding-top: 1.15rem; padding-bottom: 3rem; max-width: 1660px; }
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0D182B 0%, #0A1425 100%) !important;
  border-right: 1px solid #24344D !important;
}
[data-testid="stSidebar"] > div { background: transparent !important; padding-top: 1.15rem; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] label { color: #A8B7C9 !important; }
[data-testid="stMarkdownContainer"], [data-testid="stText"], p, li { color: #C8D3E2; }
small, .stCaption, [data-testid="stCaptionContainer"] { color: var(--pt-muted) !important; }
h1, h2, h3, h4, h5, h6,
.hero-title, .section-title, .control-deck-title,
.landing-title, .landing-stat-value, .landing-section-title,
.landing-workflow-num, .workspace-monogram, .workspace-brandname,
.workspace-current-title, .kpi-value {
  font-family: 'Space Grotesk', 'DM Sans', sans-serif !important;
  letter-spacing: -.035em !important;
  color: #F0F5FC !important;
}
.eyebrow, .landing-kicker, .landing-aside-title, .workspace-overline,
.workspace-current-label, .navbar-kicker, .section-kicker { color: var(--pt-accent) !important; }

/* Product identity and navigation */
.landing-shell { color: var(--pt-text); }
.landing-topline { border-bottom: 1px solid rgba(133,157,190,.17); padding-bottom: .75rem; }
.landing-brand { color: #F0F5FC !important; }
.landing-brand-mark, .workspace-monogram {
  background: linear-gradient(145deg, rgba(85,215,196,.22), rgba(154,140,255,.20)) !important;
  border: 1px solid rgba(85,215,196,.35) !important;
  color: #78E7D5 !important;
  border-radius: 13px !important;
  box-shadow: 0 8px 24px rgba(29, 191, 174, .10);
}
.landing-brand small, .landing-top-status, .workspace-current-copy,
.navbar-hint, .section-note, .landing-bottom { color: #8FA0B7 !important; }
.workspace-masthead { border-bottom: 1px solid rgba(133,157,190,.18) !important; }
.workspace-brandname { color: #F0F5FC !important; }
.workspace-brandname span { color: var(--pt-accent) !important; }
.workspace-current-title { color: #EAF1FA !important; }
.navbar-divider, hr { background: rgba(133,157,190,.2) !important; border-color: rgba(133,157,190,.2) !important; }

/* Welcome hero and in-page page headers */
.landing-hero, .hero {
  position: relative;
  overflow: hidden;
  background: linear-gradient(118deg, #14233B 0%, #1B2D49 52%, #2B3157 100%) !important;
  color: #F2F6FC !important;
  border: 1px solid rgba(125,153,191,.22) !important;
  border-left: 4px solid var(--pt-accent) !important;
  border-radius: 18px 30px 18px 30px !important;
  box-shadow: 0 20px 55px rgba(0,0,0,.24), inset 0 1px 0 rgba(255,255,255,.04) !important;
  animation: fadeSlideIn .38s ease both !important;
}
.landing-hero:before {
  display: block !important;
  border-color: rgba(85,215,196,.24) !important;
  box-shadow: 0 0 0 42px rgba(85,215,196,.035), 0 0 0 90px rgba(154,140,255,.035) !important;
}
.landing-title { color: #F5F8FD !important; font-size: clamp(2.45rem, 4.9vw, 4.55rem) !important; line-height: 1.02 !important; }
.landing-title span, .landing-kicker, .hero .hero-eyebrow { color: #72E4D3 !important; }
.landing-copy, .hero .hero-sub { color: #C0CDDE !important; }
.landing-aside { background: rgba(7,14,28,.30) !important; border: 1px solid rgba(184,202,226,.19) !important; border-radius: 16px !important; backdrop-filter: blur(10px) !important; }
.landing-aside-title { color: #73E4D3 !important; }
.landing-question { border-bottom-color: rgba(184,202,226,.14) !important; }
.landing-question-title, .landing-route-title { color: #F0F5FC !important; }
.landing-question-copy, .landing-route-copy { color: #AEBED1 !important; }
.landing-route-num { background: rgba(85,215,196,.13) !important; color: #79E8D7 !important; }
.landing-chip, .hero-chip {
  background: rgba(255,255,255,.065) !important;
  border: 1px solid rgba(197,213,235,.20) !important;
  color: #E5EDF8 !important;
  border-radius: 999px !important;
  padding: .4rem .75rem !important;
}
.hero .hero-title { color: #F5F8FD !important; }
.hero-meta { gap: .55rem; }

/* Feature cards, stats and insight tiles */
.landing-stat, .landing-feature, .landing-workflow,
.kpi-card, .insight-grid-card, .control-deck, .info-panel,
.empty-state, div[data-testid="stPlotlyChart"],
div[data-testid="stDataFrame"], [data-testid="stTable"] {
  background: linear-gradient(155deg, rgba(21,34,55,.96), rgba(15,27,46,.96)) !important;
  border: 1px solid rgba(117,145,181,.20) !important;
  color: #D7E1EF !important;
  border-radius: 15px !important;
  box-shadow: 0 10px 28px rgba(0,0,0,.15), inset 0 1px 0 rgba(255,255,255,.025) !important;
}
.landing-stat, .landing-feature, .landing-workflow { padding: 1.05rem 1.15rem !important; }
.landing-feature { transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease !important; }
.landing-feature:hover, .landing-stat:hover, .landing-workflow:hover,
.kpi-card:hover, .insight-grid-card:hover {
  transform: translateY(-3px) !important;
  border-color: rgba(85,215,196,.42) !important;
  box-shadow: 0 16px 36px rgba(0,0,0,.24), 0 0 0 1px rgba(85,215,196,.05) !important;
}
.landing-feature-icon, .insight-mark, .empty-state-mark {
  background: rgba(85,215,196,.13) !important;
  color: #6CE1D0 !important;
  border: 1px solid rgba(85,215,196,.18) !important;
  border-radius: 11px !important;
}
.landing-stat-label, .kpi-label, .insight-label { color: #91A3BA !important; }
.landing-stat-value, .kpi-value { color: #F2F6FC !important; }
.landing-stat-foot, .landing-feature-copy, .landing-workflow-copy,
.kpi-foot, .panel-note, .control-deck-sub { color: #91A1B7 !important; }
.landing-section-title, .landing-workflow-title, .landing-feature-title { color: #EAF1FA !important; }
.landing-section-copy { color: #9CAEC3 !important; }
.landing-footnote, .callout {
  background: rgba(245,177,92,.10) !important;
  border: 1px solid rgba(245,177,92,.27) !important;
  color: #F3CC91 !important;
  border-radius: 12px !important;
}
.kpi-card { border-top: 2px solid var(--pt-accent) !important; min-height: 128px; }
.kpi-label { text-decoration-color: rgba(145,161,183,.65) !important; }
.insight-text { color: #D6E1EF !important; }
.control-deck { background: linear-gradient(145deg, rgba(20,34,56,.98), rgba(14,26,44,.98)) !important; padding: 1.1rem 1.2rem .5rem !important; }
.control-deck-title, .section-title { color: #F0F5FC !important; }
.section-note { color: #97A9BF !important; }
.scope-strip { background: rgba(85,215,196,.075) !important; border: 1px solid rgba(85,215,196,.19) !important; color: #C2D2E2 !important; border-radius: 11px !important; }
.scope-pill { background: rgba(255,255,255,.06) !important; border: 1px solid rgba(166,188,217,.18) !important; color: #E1EAF5 !important; border-radius: 999px !important; }
.scope-pill-status { background: rgba(54,201,149,.13) !important; border-color: rgba(54,201,149,.28) !important; color: #7CE0B7 !important; }
.scope-pill-muted { color: #91A1B7 !important; }
.info-panel { border-left: 3px solid var(--pt-accent) !important; }
.info-panel b, .empty-state-title { color: #F0F5FC !important; }
.info-panel, .empty-state-message { color: #B4C3D6 !important; }
.empty-state { border-style: dashed !important; border-left: 3px solid var(--pt-accent) !important; }
.empty-state-action { color: #70E2D1 !important; }

/* Buttons and interactive controls */
div[data-testid="stButton"] > button,
[data-testid="stDownloadButton"] button,
[data-testid="stFormSubmitButton"] button {
  background: linear-gradient(145deg, #1B2A43, #15243B) !important;
  color: #DCE7F4 !important;
  border: 1px solid #344966 !important;
  border-radius: 10px !important;
  min-height: 2.55rem;
  font-family: 'DM Sans', sans-serif !important;
  font-weight: 700 !important;
  box-shadow: 0 5px 14px rgba(0,0,0,.12) !important;
  transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease, background .18s ease !important;
}
div[data-testid="stButton"] > button:hover,
[data-testid="stDownloadButton"] button:hover,
[data-testid="stFormSubmitButton"] button:hover {
  transform: translateY(-2px) !important;
  border-color: rgba(85,215,196,.65) !important;
  color: #FFFFFF !important;
  box-shadow: 0 9px 22px rgba(0,0,0,.22), 0 0 0 1px rgba(85,215,196,.08) !important;
}
div[data-testid="stButton"] > button[kind="primary"],
[data-testid="stDownloadButton"] button[kind="primary"], button[kind="primary"] {
  background: linear-gradient(135deg, #58DDC9, #35BFAE) !important;
  border: 1px solid #62E5D2 !important;
  color: #08201F !important;
  box-shadow: 0 7px 20px rgba(53,191,174,.20) !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover,
[data-testid="stDownloadButton"] button[kind="primary"]:hover,
button[kind="primary"]:hover { background: linear-gradient(135deg, #78E9D8, #4ACDBB) !important; color: #061B1B !important; }
[data-baseweb="select"] > div,
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stDateInput"] input {
  background: #0D192B !important;
  border: 1px solid #30445F !important;
  border-radius: 10px !important;
  color: #E7EEF8 !important;
}
[data-baseweb="select"] > div:hover,
[data-testid="stTextInput"] input:hover,
[data-testid="stNumberInput"] input:hover { border-color: #4B6689 !important; }
[data-baseweb="select"] *, [data-baseweb="popover"] *, [role="listbox"] * { color: #DCE7F4 !important; }
[data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"] {
  background: #142238 !important;
  border: 1px solid #344966 !important;
}
[data-baseweb="option"] { background: #142238 !important; }
[data-baseweb="option"]:hover, [aria-selected="true"] { background: #203652 !important; }
[data-baseweb="tag"] { background: #1F716B !important; border-radius: 7px !important; }
[data-baseweb="tag"] span { color: #E9FFFB !important; }
input::placeholder, textarea::placeholder { color: #71849D !important; }
[data-testid="stForm"], [data-testid="stExpander"] {
  background: rgba(17,28,48,.86) !important;
  border: 1px solid rgba(117,145,181,.22) !important;
  border-radius: 13px !important;
}
[data-testid="stExpander"] details, [data-testid="stExpander"] summary { background: transparent !important; color: #DCE7F4 !important; }
[data-testid="stExpander"] svg { fill: #AFC0D5 !important; }
[data-testid="stDataFrame"] { border-radius: 13px !important; overflow: hidden !important; }

/* Chart frames, data areas and typography */
div[data-testid="stPlotlyChart"] { padding: .4rem .42rem .08rem !important; transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease !important; }
div[data-testid="stPlotlyChart"]:hover { transform: translateY(-2px) !important; border-color: rgba(85,215,196,.36) !important; }
[data-testid="stDataFrame"] [role="grid"], [data-testid="stTable"] { color: #DCE7F4 !important; }
[data-testid="stDataFrame"] { background: #111C30 !important; }
[data-testid="stMarkdownContainer"] table { border-color: #30445F !important; }
[data-testid="stMarkdownContainer"] th { background: #1A2B44 !important; color: #EAF1FA !important; }
[data-testid="stMarkdownContainer"] td { background: #111C30 !important; color: #C8D5E5 !important; }
code, pre { background: #0A1425 !important; color: #BCEDE5 !important; border: 1px solid #263750 !important; border-radius: 8px !important; }
a { color: #75E2D2 !important; }
a:hover { color: #A5F3E7 !important; }
button:focus-visible, [data-baseweb="select"] > div:focus-within,
[data-testid="stTextInput"] input:focus-visible {
  outline: 2px solid var(--pt-accent) !important;
  outline-offset: 2px !important;
}
@keyframes softGlow { 0%,100% { box-shadow: 0 0 0 rgba(85,215,196,0); } 50% { box-shadow: 0 0 24px rgba(85,215,196,.08); } }
@media (max-width: 900px) {
  .landing-hero { grid-template-columns: 1fr !important; gap: 1.3rem !important; }
  .landing-title { font-size: 2.55rem !important; }
  .landing-aside { padding: 1rem !important; }
  .hero .hero-title { font-size: 1.9rem !important; }
  .kpi-value { font-size: 1.5rem !important; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .01ms !important; transition-duration: .01ms !important; }
}

/* COMMIT 15: INTERACTIVE MICRO-INTERACTIONS */
/* Compact arrow affordances appear only while a button is hovered. */
div[data-testid="stButton"] > button,
[data-testid="stDownloadButton"] button,
[data-testid="stFormSubmitButton"] button {
  position: relative !important;
  overflow: hidden !important;
  will-change: transform, box-shadow;
}
div[data-testid="stButton"] > button::after,
[data-testid="stFormSubmitButton"] button::after {
  content: "↗";
  display: inline-block;
  width: 0;
  margin-left: 0;
  opacity: 0;
  transform: translateX(-5px);
  font-size: .9em;
  line-height: 1;
  transition: width .18s ease, margin-left .18s ease, opacity .18s ease, transform .18s ease;
}
[data-testid="stDownloadButton"] button::after {
  content: "↓";
  display: inline-block;
  width: 0;
  margin-left: 0;
  opacity: 0;
  transform: translateY(-3px);
  font-size: .95em;
  line-height: 1;
  transition: width .18s ease, margin-left .18s ease, opacity .18s ease, transform .18s ease;
}
div[data-testid="stButton"] > button:hover::after,
[data-testid="stFormSubmitButton"] button:hover::after,
[data-testid="stDownloadButton"] button:hover::after {
  width: .9em;
  margin-left: .35rem;
  opacity: 1;
  transform: translate(0, 0);
}
div[data-testid="stButton"] > button:active,
[data-testid="stDownloadButton"] button:active,
[data-testid="stFormSubmitButton"] button:active {
  transform: translateY(0) scale(.975) !important;
  box-shadow: 0 2px 7px rgba(0,0,0,.2) !important;
  transition-duration: .07s !important;
}
div[data-testid="stButton"] > button:disabled,
[data-testid="stDownloadButton"] button:disabled,
[data-testid="stFormSubmitButton"] button:disabled {
  cursor: not-allowed !important;
  transform: none !important;
  box-shadow: none !important;
}

/* Plotly modebar controls get a subtle accent on hover. */
div[data-testid="stPlotlyChart"] .modebar-btn {
  border-radius: 7px !important;
  transition: background .16s ease, transform .16s ease !important;
}
div[data-testid="stPlotlyChart"] .modebar-btn:hover {
  background: rgba(85,215,196,.15) !important;
  transform: translateY(-1px);
}
div[data-testid="stPlotlyChart"] .modebar-btn:hover path {
  fill: #75E6D6 !important;
}
div[data-testid="stPlotlyChart"]:active {
  transform: translateY(-1px) scale(.997) !important;
  border-color: rgba(85,215,196,.72) !important;
  box-shadow: 0 0 0 2px rgba(85,215,196,.10), 0 14px 34px rgba(0,0,0,.25) !important;
  transition-duration: .08s !important;
}
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def read_local_source(file_path: str, modified_ns: int, file_size: int) -> bytes:
    """Read a local CSV once per file version; mtime and size invalidate the cache."""
    return Path(file_path).read_bytes()


@st.cache_data(show_spinner=False)
def parse_trade_csv(file_bytes: bytes, flow_label: str) -> pd.DataFrame:
    """Parse a DGCIS-style wide monthly CSV to a long monthly table."""
    raw = pd.read_csv(BytesIO(file_bytes), low_memory=False)
    raw.columns = raw.columns.astype(str).str.strip()
    required = ["HS Code", "HS Description", "Country Name"]
    missing = [col for col in required if col not in raw.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))

    month_cols = [col for col in raw.columns if MONTH_RE.match(col)]
    if not month_cols:
        raise ValueError("No monthly USD_Mn columns found. Expected columns like January-2025_USD_Mn.")

    raw["HS Code"] = pd.to_numeric(raw["HS Code"], errors="coerce")
    raw["Country Name"] = raw["Country Name"].fillna("").astype(str).str.strip()
    raw["HS Description"] = raw["HS Description"].fillna("").astype(str).str.strip()
    raw = raw.dropna(subset=["HS Code"]).copy()

    long_df = raw.melt(
        id_vars=required,
        value_vars=month_cols,
        var_name="Period",
        value_name="Value_USD_Mn",
    )
    long_df["Value_USD_Mn"] = pd.to_numeric(
        long_df["Value_USD_Mn"].astype(str).str.replace(",", "", regex=False),
        errors="coerce",
    )
    long_df["Date"] = pd.to_datetime(
        long_df["Period"].str.replace("_USD_Mn", "", regex=False),
        format="%B-%Y",
        errors="coerce",
    )
    long_df = long_df.dropna(subset=["Date", "Value_USD_Mn", "HS Code"]).copy()
    long_df["HS Code"] = long_df["HS Code"].astype(int)
    long_df["Year"] = long_df["Date"].dt.year.astype(int)
    long_df["MonthNum"] = long_df["Date"].dt.month.astype(int)
    long_df["Month"] = long_df["Date"].dt.strftime("%b")
    long_df["Value_USD_Bn"] = long_df["Value_USD_Mn"] / 1000
    long_df["Trade Flow"] = flow_label

    def commodity_name(code, description):
        return COMMODITY_INFO.get(code, {}).get("commodity", description.rstrip(" ."))

    def category_name(code, description):
        return COMMODITY_INFO.get(code, {}).get("category", "Other / unclassified HS chapter")

    long_df["Commodity"] = [commodity_name(code, desc) for code, desc in zip(long_df["HS Code"], long_df["HS Description"])]
    long_df["Commodity Category"] = [category_name(code, desc) for code, desc in zip(long_df["HS Code"], long_df["HS Description"])]
    long_df["CountryKey"] = long_df["Country Name"].str.upper().str.strip()
    long_df["DisplayCountry"] = long_df["CountryKey"].map(COUNTRY_ALIASES).fillna(long_df["Country Name"])
    # The TOTAL row is an aggregate and should never be summed with country rows.
    long_df = long_df[~long_df["CountryKey"].isin({"TOTAL", "ALL COUNTRIES", "WORLD TOTAL"})].copy()
    return long_df.sort_values("Date").reset_index(drop=True)


@st.cache_data(show_spinner=False)
def assemble_trade_data(primary_bytes, primary_flow, imports_bytes=None, exports_bytes=None):
    """Build and cache the combined trade table from the supplied CSV bytes."""
    frames = []

    # Explicit flow uploads take precedence over the direction assigned to the
    # primary file. The app never infers a flow from the numeric values.
    if imports_bytes is not None:
        frames.append(parse_trade_csv(imports_bytes, "Imports"))
    elif primary_flow == "Imports":
        frames.append(parse_trade_csv(primary_bytes, "Imports"))

    if exports_bytes is not None:
        frames.append(parse_trade_csv(exports_bytes, "Exports"))
    elif primary_flow == "Exports":
        frames.append(parse_trade_csv(primary_bytes, "Exports"))

    if not frames:
        frames.append(parse_trade_csv(primary_bytes, "Direction not verified"))

    combined = pd.concat(frames, ignore_index=True)
    return combined.sort_values("Date", kind="stable").reset_index(drop=True)


def fmt_money_mn(value, decimals=1):
    if value is None or pd.isna(value):
        return "—"
    value = float(value)
    if abs(value) >= 1000:
        return f"US${value / 1000:,.{decimals}f}B"
    return f"US${value:,.{decimals}f}M"


def fmt_money_bn(value, decimals=2):
    if value is None or pd.isna(value):
        return "—"
    return f"US${float(value):,.{decimals}f}B"


def fmt_pct(value, decimals=1):
    return "—" if value is None or pd.isna(value) else f"{float(value):+,.{decimals}f}%"


def safe(value):
    return html.escape(str(value))


def section(kicker, title, note=""):
    st.markdown(
        f"<div class='section-kicker'>{safe(kicker)}</div><div class='section-title'>{safe(title)}</div>",
        unsafe_allow_html=True,
    )
    if note:
        st.markdown(f"<div class='section-note'>{safe(note)}</div>", unsafe_allow_html=True)


def kpi_card(label, value, foot, accent=TEAL):
    # The tooltip reuses the KPI's existing supporting text for a quick explanation.
    tooltip = f"{label}. {foot}" if foot else label

    st.markdown(
        f"<div class='kpi-card' style='border-top-color:{safe(accent)}'>"
        f"<div class='kpi-label' title='{safe(tooltip)}' "
        f"aria-label='{safe(tooltip)}'>{safe(label)} ⓘ</div>"
        f"<div class='kpi-value'>{safe(value)}</div>"
        f"<div class='kpi-foot'>{safe(foot)}</div></div>",
        unsafe_allow_html=True,
    )


def insight_card(mark, label, text):
    st.markdown(
        f"<div class='insight-grid-card'><div class='insight-mark'>{safe(mark)}</div>"
        f"<div class='insight-label'>{safe(label)}</div><div class='insight-text'>{safe(text)}</div></div>",
        unsafe_allow_html=True,
    )

def empty_state(title, message, next_step=None):
    """
    Display a consistent, user-friendly empty state.
    """

    action_html = (
        f"<div class='empty-state-action'>"
        f"{safe(next_step)}</div>"
        if next_step else ""
    )

    st.markdown(
        f"""
        <div class="empty-state">
            <div class="empty-state-mark">i</div>

            <div class="empty-state-content">
                <div class="empty-state-title">
                    {safe(title)}
                </div>

                <div class="empty-state-message">
                    {safe(message)}
                </div>

                {action_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )



def style_fig(fig, height=360, legend=True):
    # Give selectable bar/scatter marks a clear active state when clicked.
    # Other Plotly trace types (pie, heatmap, treemap) retain their native behavior.
    for trace in fig.data:
        if trace.type == "bar":
            trace.update(
                selected=dict(marker=dict(color=TEAL, opacity=1)),
                unselected=dict(marker=dict(opacity=.42)),
            )
        elif trace.type in {"scatter", "scattergl"}:
            trace.update(
                selected=dict(marker=dict(color=TEAL, opacity=1, size=11)),
                unselected=dict(marker=dict(opacity=.28)),
            )

    fig.update_layout(
        template="plotly_dark",
        height=height,
        margin=dict(l=18, r=28, t=40, b=24),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color="#D4DFED", size=12),
        hoverlabel=dict(bgcolor="#17263D", font_color="#F1F6FC", bordercolor="#55D7C4"),
        legend=dict(font=dict(color="#B8C7D9", size=11), bgcolor="rgba(0,0,0,0)"),
        showlegend=legend,
        clickmode="event+select",
        hovermode="closest",
        transition=dict(duration=360, easing="cubic-in-out"),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="#3B4F6A", tickfont=dict(color="#A9B9CC"), title_font=dict(color="#C2CFDE"), ticks="outside")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(139,160,188,.16)", zeroline=False, linecolor="#3B4F6A", tickfont=dict(color="#A9B9CC"), title_font=dict(color="#C2CFDE"), ticks="outside")
    return fig


def render_chart(fig, key, height=360, legend=True):
    st.plotly_chart(
        style_fig(fig, height=height, legend=legend),
        use_container_width=True,
        key=key,
        config={
            "displayModeBar": "hover",
            "responsive": True,
            "scrollZoom": False,
            "displaylogo": False,
        },
    )

# ============================================================
# COMMIT 08: CACHED PLOTLY PNG EXPORT
# ============================================================

@st.cache_data(show_spinner=False, max_entries=12)
def export_chart_png(
    figure_json: str,
    width: int = 1800,
    height: int = 1125,
    scale: int = 2,
) -> bytes:
    """Convert a Plotly figure to a cached, presentation-ready PNG.

    Static image rendering is provided by Kaleido. With Kaleido 1.x,
    a compatible Chrome/Chromium installation is also required.
    """
    import json

    figure_payload = json.loads(figure_json)
    export_figure = go.Figure(figure_payload)
    export_figure.update_layout(
        width=width,
        height=height,
        autosize=False,
    )
    image_bytes = export_figure.to_image(
        format="png",
        width=width,
        height=height,
        scale=scale,
    )
    if not image_bytes:
        raise RuntimeError("The chart renderer returned an empty PNG image.")
    return image_bytes



def named_rows(frame):
    if frame.empty:
        return frame.copy()
    return frame[~frame["CountryKey"].isin(EXCLUDED_MARKETS)].copy()


def compact_height(rows, min_height=120, max_height=440):
    return min(max_height, max(min_height, 42 + rows * 35))


def select_months_for_flows(df, selected_year):
    """Use months common to every loaded flow for fair side-by-side comparisons."""
    year_data = df[df["Year"] == selected_year]
    flow_month_sets = []
    for flow_name in sorted(year_data["Trade Flow"].dropna().unique()):
        months = set(year_data.loc[year_data["Trade Flow"] == flow_name, "MonthNum"].unique().tolist())
        if months:
            flow_month_sets.append(months)
    if not flow_month_sets:
        return []
    common = set.intersection(*flow_month_sets)
    if common:
        return sorted(common)
    # Defensive fallback for files whose coverage doesn't overlap at all.
    return sorted(set.union(*flow_month_sets))


def build_commodity_ledger(current_data, prior_data, commodity_names, available_flows):
    rows = []
    has_imports = "Imports" in available_flows
    has_exports = "Exports" in available_flows
    for commodity in commodity_names:
        cur = current_data[current_data["Commodity"] == commodity]
        prev = prior_data[prior_data["Commodity"] == commodity]
        recorded = cur["Value_USD_Mn"].sum()
        prior_recorded = prev["Value_USD_Mn"].sum()
        import_value = cur.loc[cur["Trade Flow"] == "Imports", "Value_USD_Mn"].sum() if has_imports else np.nan
        export_value = cur.loc[cur["Trade Flow"] == "Exports", "Value_USD_Mn"].sum() if has_exports else np.nan
        prior_import = prev.loc[prev["Trade Flow"] == "Imports", "Value_USD_Mn"].sum() if has_imports else np.nan
        prior_export = prev.loc[prev["Trade Flow"] == "Exports", "Value_USD_Mn"].sum() if has_exports else np.nan
        balance = export_value - import_value if has_imports and has_exports else np.nan
        rows.append({
            "Commodity": commodity,
            "Commodity category": cur["Commodity Category"].iloc[0] if not cur.empty else "—",
            "Recorded value (US$ B)": recorded / 1000,
            "Imports (US$ B)": import_value / 1000 if has_imports else np.nan,
            "Exports (US$ B)": export_value / 1000 if has_exports else np.nan,
            "Export − import (US$ B)": balance / 1000 if has_imports and has_exports else np.nan,
            "YoY recorded change (%)": (recorded / prior_recorded - 1) * 100 if prior_recorded > 0 else np.nan,
            "Import YoY (%)": (import_value / prior_import - 1) * 100 if has_imports and prior_import > 0 else np.nan,
            "Export YoY (%)": (export_value / prior_export - 1) * 100 if has_exports and prior_export > 0 else np.nan,
        })
    return pd.DataFrame(rows)


def build_excel_report(
    current_data,
    prior_data,
    filtered_records,
    metadata
):
    """Generate a formatted multi-sheet PetroTrade analytics workbook."""

    output = BytesIO()

    # ---------------------------------------------------------
    # 1. COMMODITY SUMMARY
    # ---------------------------------------------------------

    group_columns = [
        "HS Code",
        "Commodity",
        "Commodity Category",
        "Trade Flow"
    ]

    current_summary = (
        current_data
        .groupby(group_columns, as_index=False)["Value_USD_Mn"]
        .sum()
        .rename(columns={
            "Value_USD_Mn": "Current value (USD Mn)"
        })
    )

    prior_summary = (
        prior_data
        .groupby(group_columns, as_index=False)["Value_USD_Mn"]
        .sum()
        .rename(columns={
            "Value_USD_Mn": "Comparable prior value (USD Mn)"
        })
    )

    commodity_summary = current_summary.merge(
        prior_summary,
        on=group_columns,
        how="left"
    )

    commodity_summary["YoY change (%)"] = np.nan
    valid = commodity_summary["Comparable prior value (USD Mn)"].gt(0)
    commodity_summary.loc[valid, "YoY change (%)"] = (
        commodity_summary.loc[valid, "Current value (USD Mn)"]
        / commodity_summary.loc[valid, "Comparable prior value (USD Mn)"]
        - 1
    ) * 100

    # ---------------------------------------------------------
    # 2. PARTNER MARKET SUMMARY
    # ---------------------------------------------------------

    valid_partners = named_rows(current_data)
    partner_summary = (
        valid_partners
        .groupby(["DisplayCountry", "Trade Flow"], as_index=False)["Value_USD_Mn"]
        .sum()
        .rename(columns={
            "DisplayCountry": "Partner market",
            "Value_USD_Mn": "Recorded value (USD Mn)"
        })
        .sort_values("Recorded value (USD Mn)", ascending=False)
    )

    # ---------------------------------------------------------
    # 3. TRADE FLOW SUMMARY
    # ---------------------------------------------------------

    flow_summary = (
        current_data
        .groupby("Trade Flow", as_index=False)["Value_USD_Mn"]
        .sum()
        .rename(columns={"Value_USD_Mn": "Recorded value (USD Mn)"})
    )

    # ---------------------------------------------------------
    # 4. MONTHLY TRENDS
    # ---------------------------------------------------------

    monthly_summary = (
        current_data
        .groupby(["MonthNum", "Month", "Commodity", "Trade Flow"], as_index=False)["Value_USD_Mn"]
        .sum()
        .sort_values(["MonthNum", "Commodity", "Trade Flow"])
    )

    # ---------------------------------------------------------
    # 5. EXECUTIVE SUMMARY
    # ---------------------------------------------------------

    executive_summary = pd.DataFrame(
        list(metadata.items()),
        columns=["Metric", "Value"]
    )

    # ---------------------------------------------------------
    # 6. WORKBOOK GUIDE (NEW ENHANCEMENT)
    # ---------------------------------------------------------

    workbook_guide = pd.DataFrame(
        [
            ("How to use", "Start here", "This sheet explains the workbook tabs, key measures and colour cues."),
            ("Workbook tabs", "Executive Summary", "Selected reporting scope, headline totals, comparison figures and source metadata."),
            ("Workbook tabs", "Commodity Summary", "Current and comparable prior values, grouped by HS code, commodity and trade flow."),
            ("Workbook tabs", "Partner Markets", "Recorded trade value by partner market and trade flow, sorted from highest to lowest value."),
            ("Workbook tabs", "Trade Flow Summary", "Recorded value grouped by the trade-flow label available in the loaded data."),
            ("Workbook tabs", "Monthly Trends", "Monthly value totals by commodity and trade flow, with month number retained for sorting."),
            ("Workbook tabs", "Filtered Records", "Source observations remaining after the current app filters are applied."),
            ("Key measure", "YoY change (%)", "Calculated as (current value / comparable prior value - 1) × 100. A value is shown only when the comparable prior value is greater than zero."),
            ("Units", "USD Mn", "Values are expressed in US$ million where the column heading says USD Mn."),
            ("Units", "US$ B", "Values are expressed in US$ billion where the column heading says US$ B."),
            ("Comparison", "Comparable prior period", "The app compares the selected months with the same months in the prior year; check the Executive Summary for the selected reporting period."),
            ("Trade direction", "Direction not verified", "This label is retained when the source data has not been confirmed as imports or exports. It should not be interpreted as either flow."),
            ("Colour cue", "Green YoY cell", "Positive year-on-year change."),
            ("Colour cue", "Red YoY cell", "Negative year-on-year change."),
            ("Colour cue", "Blank YoY cell", "No comparable positive prior-period value was available; blank does not mean zero change."),
            ("Interpretation", "Scope", "Commodity groups are based on the HS chapters selected in the app. They are broad analytical groupings, not a complete product-level definition of petrochemicals."),
        ],
        columns=["Section", "Field / sheet", "Explanation"]
    )

    # ---------------------------------------------------------
    # 7. WRITE EXCEL WORKBOOK
    # ---------------------------------------------------------

    with pd.ExcelWriter(output, engine="openpyxl") as writer:

        # Put the guide first so the workbook is self-explanatory when opened.
        workbook_guide.to_excel(writer, sheet_name="Workbook Guide", index=False)
        executive_summary.to_excel(writer, sheet_name="Executive Summary", index=False)
        commodity_summary.to_excel(writer, sheet_name="Commodity Summary", index=False)
        partner_summary.to_excel(writer, sheet_name="Partner Markets", index=False)
        flow_summary.to_excel(writer, sheet_name="Trade Flow Summary", index=False)
        monthly_summary.to_excel(writer, sheet_name="Monthly Trends", index=False)
        filtered_records.to_excel(writer, sheet_name="Filtered Records", index=False)

        # -----------------------------------------------------
        # WORKBOOK FORMATTING
        # -----------------------------------------------------

        from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
        from openpyxl.formatting.rule import CellIsRule

        header_fill = PatternFill(fill_type="solid", fgColor="172A3A")
        header_font = Font(bold=True, color="FFFFFF", size=10)
        positive_fill = PatternFill(fill_type="solid", fgColor="E2F0D9")
        negative_fill = PatternFill(fill_type="solid", fgColor="FCE4D6")
        thin_border = Border(bottom=Side(style="thin", color="D9DDE3"))

        for worksheet in writer.book.worksheets:
            worksheet.freeze_panes = "A2"

            if worksheet.max_row >= 1 and worksheet.max_column >= 1:
                worksheet.auto_filter.ref = worksheet.dimensions

            for cell in worksheet[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(
                    horizontal="center",
                    vertical="center",
                    wrap_text=True
                )

            worksheet.row_dimensions[1].height = 26

            headers = {
                cell.column: str(cell.value)
                for cell in worksheet[1]
            }

            for col_index, header in headers.items():
                column_letter = worksheet.cell(row=1, column=col_index).column_letter

                max_length = max(
                    len(str(worksheet.cell(row=row, column=col_index).value or ""))
                    for row in range(1, worksheet.max_row + 1)
                )

                worksheet.column_dimensions[column_letter].width = min(
                    max(max_length + 3, 13),
                    42
                )

                for row in range(2, worksheet.max_row + 1):
                    cell = worksheet.cell(row=row, column=col_index)
                    cell.border = thin_border
                    cell.alignment = Alignment(vertical="top")

                    if "(USD Mn)" in header or "(US$ million)" in header:
                        cell.number_format = '#,##0.00;[Red]-#,##0.00'
                    elif "(US$ B)" in header:
                        cell.number_format = '#,##0.000;[Red]-#,##0.000'
                    elif "(%)" in header:
                        # Percentage values are stored as 11.5, not 0.115.
                        cell.number_format = '0.0"%"'

                # Highlight positive and negative year-on-year changes in Excel.
                header_lower = header.lower()
                is_growth_column = (
                    "(%)" in header
                    and ("yoy" in header_lower or "year-on-year" in header_lower)
                )
                if is_growth_column and worksheet.max_row >= 2:
                    data_range = (
                        f"{column_letter}2:{column_letter}{worksheet.max_row}"
                    )
                    worksheet.conditional_formatting.add(
                        data_range,
                        CellIsRule(
                            operator="greaterThan",
                            formula=["0"],
                            fill=positive_fill
                        )
                    )
                    worksheet.conditional_formatting.add(
                        data_range,
                        CellIsRule(
                            operator="lessThan",
                            formula=["0"],
                            fill=negative_fill
                        )
                    )

        # Make the guide comfortable to read without excessively wide columns.
        guide_sheet = writer.book["Workbook Guide"]
        guide_sheet.column_dimensions["A"].width = 20
        guide_sheet.column_dimensions["B"].width = 30
        guide_sheet.column_dimensions["C"].width = 92
        for row in range(2, guide_sheet.max_row + 1):
            guide_sheet.row_dimensions[row].height = 32
            for cell in guide_sheet[row]:
                cell.alignment = Alignment(vertical="top", wrap_text=True)

    output.seek(0)
    return output.getvalue()



# =============================================================================
# Landing / welcome page (shown before the analytics workspace)
# =============================================================================
if "petrotrade_workspace_entered" not in st.session_state:
    st.session_state["petrotrade_workspace_entered"] = False

if not st.session_state["petrotrade_workspace_entered"]:
    # Use the real local CSV for a compact preview, but do not label its
    # direction as imports or exports unless the user verifies the source query.
    preview = None
    preview_error = None
    if DATA_FILE.exists():
        try:
            preview_stat = DATA_FILE.stat()
            preview_bytes = read_local_source(str(DATA_FILE), preview_stat.st_mtime_ns, preview_stat.st_size)
            preview = parse_trade_csv(preview_bytes, "Direction not verified")
        except Exception as exc:
            preview_error = str(exc)

    if preview is not None and not preview.empty:
        preview_year = int(preview["Year"].max())
        preview_latest = preview[preview["Year"] == preview_year].copy()
        preview_months = int(preview_latest["MonthNum"].nunique())
        preview_value = float(preview_latest["Value_USD_Mn"].sum())
        preview_partners = int(named_rows(preview_latest).loc[lambda x: x["Value_USD_Mn"] > 0, "DisplayCountry"].nunique())
        preview_hs = int(preview["HS Code"].nunique())
        preview_year_text = f"{preview_year} · {preview_months} month{'s' if preview_months != 1 else ''}"
        preview_value_text = fmt_money_mn(preview_value)
        preview_partner_text = f"{preview_partners:,}"
        preview_hs_text = f"{preview_hs}"
        preview_range = f"{int(preview['Year'].min())}–{int(preview['Year'].max())}"
        source_status = "DGCIS source file detected"
    else:
        preview_year_text = "Awaiting data"
        preview_value_text = "—"
        preview_partner_text = "—"
        preview_hs_text = "5"
        preview_range = "Monthly records"
        source_status = "Connect a DGCIS CSV to begin"

    st.markdown(
        "<div class='landing-shell'>"
        "<div class='landing-topline'><div class='landing-brand'><div class='landing-brand-mark'>PT</div>"
        "<div>PetroTrade Intelligence<small>India trade data · Market exploration</small></div></div>"
        "<div class='landing-top-status'>Commodity trade intelligence workspace</div></div>"
        "<div class='landing-hero'>"
        "<div class='landing-main'>"
        "<div class='landing-kicker'>A clearer view of commodity trade</div>"
        "<div class='landing-title'>Explore the market. <span>Understand the movement.</span></div>"
        "<div class='landing-copy'>PetroTrade Intelligence brings monthly trade records across selected petroleum-related, chemical, plastics and rubber HS chapters into one analytical workspace. Move from a broad market snapshot to commodity-level and partner-market analysis, with every view tied to the reporting period and records you select.</div>"
        f"<div class='landing-chips'><span class='landing-chip'>{safe(source_status)}</span>"
        f"<span class='landing-chip'>Coverage · {safe(preview_range)}</span>"
        "<span class='landing-chip'>5 selected HS chapters</span><span class='landing-chip'>Monthly USD values</span></div>"
        "</div>"
        "<div class='landing-aside'>"
        "<div class='landing-aside-title'>Questions you can explore</div>"
        "<div class='landing-question'><div class='landing-question-title'>Which commodity drives recorded value?</div><div class='landing-question-copy'>Compare size, contribution and year-on-year movement.</div></div>"
        "<div class='landing-question'><div class='landing-question-title'>Where is market value concentrated?</div><div class='landing-question-copy'>Inspect partner shares, HHI and concentration signals.</div></div>"
        "<div class='landing-question'><div class='landing-question-title'>Which markets show stronger momentum?</div><div class='landing-question-copy'>Screen value against comparable-period growth.</div></div>"
        "</div></div></div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)
    stat_cols = st.columns(4, gap="medium")
    stat_items = [
        ("LATEST PERIOD", preview_year_text, "Latest year and available monthly coverage"),
        ("RECORDED VALUE", preview_value_text, "Source value; trade direction must be verified"),
        ("NAMED MARKETS", preview_partner_text, "Positive-value named partner labels"),
        ("HS CHAPTERS", preview_hs_text, "Commodity chapters present in the source extract"),
    ]
    for col, (label, value, foot) in zip(stat_cols, stat_items):
        with col:
            st.markdown(
                f"<div class='landing-stat'><div class='landing-stat-label'>{safe(label)}</div>"
                f"<div class='landing-stat-value'>{safe(value)}</div>"
                f"<div class='landing-stat-foot'>{safe(foot)}</div></div>",
                unsafe_allow_html=True,
            )

    st.markdown("<div class='landing-section-title'>One workspace, six connected analytical views</div>", unsafe_allow_html=True)
    st.markdown("<div class='landing-section-copy'>Each page answers a different question, while sharing the same reporting period, commodity scope and source records.</div>", unsafe_allow_html=True)
    feature_items = [
        ("◈", "Market overview", "Start with headline value, year-on-year movement, commodity mix and the selected-period trend."),
        ("▥", "Commodity breakdown", "Compare HS chapters, category contribution and monthly movement across groups."),
        ("⌕", "Commodity deep dive", "Inspect one commodity's history, leading partners, monthly profile and year-on-year change."),
        ("⌖", "Opportunity matrix", "Screen commodity groups or partner markets by recorded value and comparable growth."),
        ("⚑", "Concentration & risk", "Review top-market shares, HHI and changes in partner-value concentration."),
        ("◎", "Partner & trade flows", "Explore country rankings and compare import/export flows when direction is verified."),
    ]
    for row_start in range(0, len(feature_items), 3):
        feature_cols = st.columns(3, gap="medium")
        for col, (icon, title, copy) in zip(feature_cols, feature_items[row_start:row_start + 3]):
            with col:
                st.markdown(
                    f"<div class='landing-feature'><div class='landing-feature-icon'>{safe(icon)}</div>"
                    f"<div class='landing-feature-title'>{safe(title)}</div>"
                    f"<div class='landing-feature-copy'>{safe(copy)}</div></div>",
                    unsafe_allow_html=True,
                )

    st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)
    st.markdown("<div class='landing-section-title'>How the analysis works</div>", unsafe_allow_html=True)
    st.markdown("<div class='landing-section-copy'>A simple path from the source extract to an interpretable market view.</div>", unsafe_allow_html=True)
    workflow_cols = st.columns(3, gap="medium")
    workflow_items = [
        ("01", "Set the scope", "Choose a year, months, commodity chapters and partner market."),
        ("02", "Read the evidence", "Compare value, growth, market mix and concentration across the selected data."),
        ("03", "Export the analysis", "Inspect source rows and download filtered tables for further work."),
    ]
    for col, (num, title, copy) in zip(workflow_cols, workflow_items):
        with col:
            st.markdown(
                f"<div class='landing-workflow'><div class='landing-workflow-num'>{num}</div>"
                f"<div class='landing-workflow-title'>{safe(title)}</div><div class='landing-workflow-copy'>{safe(copy)}</div></div>",
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    action_cols = st.columns([1.15, 1.35, 1.25, 2.5], gap="medium")
    with action_cols[0]:
        enter_clicked = st.button("Open workspace  →", type="primary", use_container_width=True, key="landing_enter_dashboard")
    with action_cols[1]:
        opportunity_clicked = st.button("Explore opportunities", use_container_width=True, key="landing_open_opportunity")
    with action_cols[2]:
        method_clicked = st.button("Data methodology", use_container_width=True, key="landing_open_methodology")
    with action_cols[3]:
        st.caption("Trade values remain labelled as recorded values until the source query direction is verified. Partial-year comparisons use matching months.")

    with st.expander("About the data and how to use PetroTrade", expanded=False):
        st.markdown(
            "**Source and scope:** the current extract contains monthly values for selected HS chapters 27, 28, 29, 39 and 40. The categories are broad HS chapters and are not a complete list of products exclusively used in petrochemicals.\n\n"
            "**Use the workspace:** choose the reporting year and months, narrow the commodity scope, and then move between Overview, Commodity breakdown, Commodity deep dive, Opportunity matrix, Concentration & risk, Partner markets, Trade flows, and Data & methodology.\n\n"
            "**Comparison rule:** year-on-year figures use the same months in the previous year. An incomplete year is shown as year-to-date, not as a full annual total.\n\n"
            "**Trade direction:** the source CSV does not encode import/export direction. Load direction-verified files before interpreting values as imports or exports or calculating trade balance."
        )

    if enter_clicked or method_clicked or opportunity_clicked:
        st.session_state["petrotrade_workspace_entered"] = True
        if method_clicked:
            landing_target = "Data & methodology"
        elif opportunity_clicked:
            landing_target = "Market opportunity matrix"
        else:
            landing_target = "Overview"
        st.session_state["petrotrade_active_page"] = landing_target
        st.rerun()

    st.markdown(
        "<div class='landing-bottom'><span>PetroTrade Intelligence · Academic project prototype</span>"
        "<span>Source: DGCIS monthly trade extract · Values in US$ million unless stated otherwise</span></div>",
        unsafe_allow_html=True,
    )
    if preview_error:
        st.caption(f"Preview metrics could not be calculated from the source file: {preview_error}")
    st.stop()

# =============================================================================
# Main-canvas intro + data-source setup

# =============================================================================
workspace_page_for_header = st.session_state.get("petrotrade_active_page", "Overview")
PAGE_DESCRIPTIONS = {
    "Overview": "Headline indicators, historical context and a guided market snapshot.",
    "Commodity breakdown": "Compare commodity chapters, category mix and monthly patterns.",
    "Commodity deep dive": "Explore one HS chapter through its trend and partner-market profile.",
    "Market opportunity matrix": "Screen market size against comparable-period growth.",
    "Concentration & risk": "Measure partner-value concentration and review screening signals.",
    "Imports vs exports": "Compare direction-verified import and export observations.",
    "Partner markets": "Explore named partner rankings and country-level trade patterns.",
    "Data & methodology": "Inspect the source records, calculations, definitions and limitations.",
}
workspace_description = PAGE_DESCRIPTIONS.get(workspace_page_for_header, "Explore the selected trade records and analytical views.")
st.markdown(
    "<div class='workspace-masthead'>"
    "<div class='workspace-brandline'><div class='workspace-monogram'>PT</div><div>"
    "<div class='workspace-brandname'>PetroTrade <span>Intelligence</span></div>"
    "<div class='workspace-overline'>India trade data · Analysis workspace</div></div></div>"
    f"<div class='workspace-current'><div class='workspace-current-label'>CURRENT VIEW</div>"
    f"<div class='workspace-current-title'>{safe(workspace_page_for_header)}</div>"
    f"<div class='workspace-current-copy'>{safe(workspace_description)}</div></div></div>",
    unsafe_allow_html=True,
)

# =============================================================================
# Unified top navigation: every user-facing workspace feature is reachable here.
# =============================================================================
NAV_ITEMS = [
    ("Welcome", "⌂ Home", "Return to the PetroTrade introduction and preview"),
    ("Overview", "◈ Overview", "Executive market overview and headline KPIs"),
    ("Commodity breakdown", "▤ Commodities", "Compare HS chapters and commodity categories"),
    ("Commodity deep dive", "⌕ Deep dive", "Inspect one commodity in detail"),
    ("Market opportunity matrix", "⌖ Opportunity", "Screen value against comparable-period growth"),
    ("Concentration & risk", "⚑ Risk", "Review partner concentration and HHI signals"),
    ("Imports vs exports", "⇄ Trade flows", "Compare verified imports and exports"),
    ("Partner markets", "◎ Markets", "Explore partner-country rankings and trends"),
    ("Data & methodology", "≡ Methods", "Inspect records, calculations and limitations"),
]

if "petrotrade_active_page" not in st.session_state:
    legacy_page = st.session_state.get("main_navigation", "Overview")
    valid_pages = [item[0] for item in NAV_ITEMS]
    st.session_state["petrotrade_active_page"] = legacy_page if legacy_page in valid_pages else "Overview"

active_page = st.session_state.get("petrotrade_active_page", "Overview")
st.markdown(
    "<div class='navbar-heading'><span class='navbar-kicker'>Navigate workspace</span>"
    "<span class='navbar-hint'>Select a section to explore the data</span></div>",
    unsafe_allow_html=True,
)
nav_weights = [0.72, 0.82, 1.02, 0.90, 1.05, 0.80, 1.00, 0.78, 0.82]
nav_columns = st.columns(nav_weights, gap="small")
for nav_col, (target_page, nav_label, nav_help) in zip(nav_columns, NAV_ITEMS):
    with nav_col:
        clicked = st.button(
            nav_label,
            key="petro_nav_" + re.sub(r"[^a-z0-9]+", "_", target_page.lower()).strip("_"),
            type="primary" if active_page == target_page else "secondary",
            use_container_width=True,
            help=nav_help,
        )
    if clicked and target_page != active_page:
        if target_page == "Welcome":
            st.session_state["petrotrade_workspace_entered"] = False
        else:
            st.session_state["petrotrade_active_page"] = target_page
        st.rerun()

st.markdown("<div class='navbar-divider'></div>", unsafe_allow_html=True)

with st.expander("Data sources · verify direction or connect import/export files", expanded=False):
    source_left, source_right = st.columns([1, 1.35], gap="large")
    with source_left:
        if DATA_FILE.exists():
            source_stat = DATA_FILE.stat()
            base_bytes = read_local_source(str(DATA_FILE), source_stat.st_mtime_ns, source_stat.st_size)
            st.caption("Primary dataset found: DGCIS_DATA.csv")
        else:
            primary_upload = st.file_uploader("Upload primary DGCIS CSV", type=["csv"], key="primary_trade_csv_main")
            base_bytes = primary_upload.getvalue() if primary_upload is not None else None
        base_flow = st.selectbox(
            "Primary dataset direction",
            ["Direction not verified", "Imports", "Exports"],
            index=0,
            key="primary_flow_direction_main",
            help="Choose Imports or Exports only after confirming the DGCIS query settings used to download this file.",
        )
    with source_right:
        upload_a, upload_b = st.columns(2)
        with upload_a:
            imports_upload = st.file_uploader("Additional imports CSV", type=["csv"], key="imports_csv_main")
        with upload_b:
            exports_upload = st.file_uploader("Additional exports CSV", type=["csv"], key="exports_csv_main")
        st.caption("For a real import/export comparison, load direction-verified files with matching HS chapters and comparable reporting months. The app never infers direction from values.")

if not DATA_FILE.exists() and base_bytes is None:
    st.info("Upload a primary DGCIS CSV in Data connections to start the analysis.")
    st.stop()

try:
    import_bytes = imports_upload.getvalue() if imports_upload is not None else None
    export_bytes = exports_upload.getvalue() if exports_upload is not None else None
    data = assemble_trade_data(base_bytes, base_flow, import_bytes, export_bytes)
except Exception as exc:
    st.error(f"Unable to read one of the DGCIS files: {exc}")
    st.info("Check that each file has HS Code, HS Description, Country Name, and monthly *_USD_Mn columns.")
    st.stop()

if data.empty:
    st.error("No valid trade records were found in the selected CSV files.")
    st.stop()

years = sorted(data["Year"].unique().tolist())
latest_year = max(years)


def year_label(y):
    months = sorted(data.loc[data["Year"] == y, "MonthNum"].unique().tolist())
    return f"{y} · YTD ({len(months)} months)" if len(months) < 12 else str(y)


commodity_options = sorted(
    data["Commodity"].dropna().unique().tolist(),
    key=lambda c: next((k for k, v in COMMODITY_INFO.items() if v["commodity"] == c), 999),
)
category_options = sorted(data["Commodity Category"].dropna().unique().tolist())
market_options = sorted(named_rows(data)["DisplayCountry"].dropna().unique().tolist())
available_flows = sorted(data["Trade Flow"].dropna().unique().tolist())
# =============================================================================
# GLOBAL FILTER RESET
# =============================================================================

def reset_global_filters():
    """Restore all global analysis filters to their default values."""

    # Remove saved month selections for different reporting years.
    for key in list(st.session_state.keys()):
        if key.startswith("workspace_months_"):
            del st.session_state[key]

    # Restore latest available reporting year.
    st.session_state["workspace_year_main"] = latest_year

    # Restore all months available in the latest year.
    latest_months = [
        MONTH_ORDER[m - 1]
        for m in select_months_for_flows(data, latest_year)
    ]

    st.session_state[
        f"workspace_months_{latest_year}"
    ] = latest_months

    # Restore all partner markets.
    st.session_state["workspace_market_main"] = "All partner markets"

    # Restore all commodity families and chapters.
    st.session_state["workspace_categories_main"] = category_options
    st.session_state["workspace_commodities_main"] = commodity_options

    # Restore chart preferences.
    st.session_state["workspace_trend_style_main"] = "Line"
    st.session_state["workspace_top_markets_main"] = 10
heading_col, reset_col = st.columns([5, 1])

with heading_col:
    section(
        "LIVE ANALYSIS CONTROLS",
        "Build your market view",
        "Set your reporting period, commodity scope, partner market and chart preferences."
    )

with reset_col:
    st.markdown("<div style='height: 1.45rem'></div>", unsafe_allow_html=True)

    st.button(
        "↺ Reset filters",
        key="reset_global_filters_button",
        on_click=reset_global_filters,
        use_container_width=True,
        help="Restore all global analysis filters to their defaults."
    )
with st.form("global_market_filters", border=True):
    row_one = st.columns([0.8, 1.45, 1.35], gap="medium")
    with row_one[0]:
        selected_year = st.selectbox(
            "Reporting year",
            years,
            index=years.index(latest_year),
            format_func=year_label,
            key="workspace_year_main",
        )
    available_month_nums = select_months_for_flows(data, selected_year)
    available_month_labels = [MONTH_ORDER[m - 1] for m in available_month_nums]
    with row_one[1]:
        selected_month_labels = st.multiselect(
            "Months included",
            options=available_month_labels,
            default=available_month_labels,
            key=f"workspace_months_{selected_year}",
            help="Choose a custom time window. Year-on-year comparison will use these same months in the prior year.",
        )
    with row_one[2]:
        selected_market = st.selectbox(
            "Partner market",
            ["All partner markets"] + market_options,
            index=0,
            key="workspace_market_main",
            help="Choose a country to focus all KPIs and charts on that market, or keep All partner markets.",
        )

    row_two = st.columns([1.15, 1.45, 0.8, 0.9], gap="medium")
    with row_two[0]:
        selected_categories = st.multiselect(
            "Commodity families",
            options=category_options,
            default=category_options,
            key="workspace_categories_main",
            help="High-level grouping for the selected HS chapters.",
        )
    # Keep the chapter selector consistent with the selected families.
    family_chapter_options = sorted(
        data.loc[data["Commodity Category"].isin(selected_categories), "Commodity"].dropna().unique().tolist(),
        key=lambda name: int(data.loc[data["Commodity"] == name, "HS Code"].iloc[0]),
    )
    prior_chapter_state = st.session_state.get("workspace_commodities_main", commodity_options)
    if "workspace_commodities_main" in st.session_state:
        cleaned_chapters = [name for name in prior_chapter_state if name in family_chapter_options]
        if cleaned_chapters != prior_chapter_state:
            st.session_state["workspace_commodities_main"] = cleaned_chapters or family_chapter_options
    with row_two[1]:
        selected_commodities = st.multiselect(
            "HS commodity chapters",
            options=family_chapter_options,
            default=family_chapter_options,
            key="workspace_commodities_main",
            help="Choose HS chapters within the selected families. Available groups: 27, 28, 29, 39 and 40.",
            format_func=lambda name: f"HS {int(data.loc[data['Commodity'] == name, 'HS Code'].iloc[0])} · {name}" if not data.loc[data["Commodity"] == name, "HS Code"].empty else name,
        )
    with row_two[2]:
        selected_trend_style = st.selectbox(
            "Trend chart style",
            ["Line", "Area", "Grouped bars"],
            index=0,
            key="workspace_trend_style_main",
        )
    with row_two[3]:
        top_partner_count = st.selectbox(
            "Markets to rank",
            [5, 10, 15, 20],
            index=1,
            key="workspace_top_markets_main",
        )
    filter_action_cols = st.columns([1.25, 4], gap="medium")
    with filter_action_cols[0]:
        st.form_submit_button("Apply analysis filters  →", type="primary", use_container_width=True)
    with filter_action_cols[1]:
        st.caption("Choose several filters, then apply them together. This avoids a full dashboard refresh after every individual selection.")

if not selected_categories:
    empty_state(
        "No commodity family selected",
        "The dashboard needs at least one commodity family to calculate market analytics.",
        "Select one or more commodity families in Live Analysis Controls and apply the filters."
    )
    st.stop()

if not selected_commodities:
    empty_state(
        "No commodity chapter selected",
        "There are no HS chapters selected for the current analysis.",
        "Choose at least one HS chapter and apply the filters."
    )
    st.stop()

if not selected_month_labels:
    empty_state(
        "No reporting months selected",
        "The selected reporting period does not contain any active months.",
        "Select one or more months to continue."
    )
    st.stop()

months_present = sorted([MONTH_ORDER.index(m) + 1 for m in selected_month_labels])
if not months_present:
    st.error("No months are available for the selected reporting year.")
    st.stop()

# Apply the same months to all flows for fair import/export and YoY comparisons.
base_filtered = data[
    data["Commodity"].isin(selected_commodities)
    & data["Commodity Category"].isin(selected_categories)
].copy()
if selected_market != "All partner markets":
    base_filtered = base_filtered[base_filtered["DisplayCountry"] == selected_market].copy()
current = base_filtered[(base_filtered["Year"] == selected_year) & base_filtered["MonthNum"].isin(months_present)].copy()
prior_year = selected_year - 1
prior = base_filtered[(base_filtered["Year"] == prior_year) & base_filtered["MonthNum"].isin(months_present)].copy()
if current.empty:
    empty_state(
        "No matching trade records",
        "The selected combination of reporting period, commodity groups and partner market did not produce any records.",
        "Try selecting a different reporting year, widening the month range, or choosing All partner markets."
    )
    st.stop()
month_labels = [pd.Timestamp(year=2000, month=m, day=1).strftime("%b") for m in months_present]
full_year_selected = months_present == list(range(1, 13))
contiguous_month_selection = months_present == list(range(min(months_present), max(months_present) + 1))
partial = not full_year_selected
if full_year_selected:
    period_label = f"Jan–Dec {selected_year}"
elif contiguous_month_selection:
    period_label = f"{month_labels[0]}–{month_labels[-1]} {selected_year}"
else:
    period_label = f"Custom months · {selected_year}"

current_total_mn = current["Value_USD_Mn"].sum()
prior_total_mn = prior["Value_USD_Mn"].sum()
yoy_total = (current_total_mn / prior_total_mn - 1) * 100 if prior_total_mn > 0 else np.nan
commodity_totals = current.groupby(["Commodity", "Commodity Category"], as_index=False)["Value_USD_Mn"].sum().sort_values("Value_USD_Mn", ascending=False)
leader = commodity_totals.iloc[0] if not commodity_totals.empty else None
leader_share = leader["Value_USD_Mn"] / current_total_mn * 100 if leader is not None and current_total_mn > 0 else np.nan
named_current = named_rows(current)
named_prior = named_rows(prior)
partner_totals = named_current.groupby(["Country Name", "DisplayCountry"], as_index=False)["Value_USD_Mn"].sum().sort_values("Value_USD_Mn", ascending=False)
partner_sum = partner_totals["Value_USD_Mn"].sum() if not partner_totals.empty else 0
active_markets = int(partner_totals["Country Name"].nunique()) if not partner_totals.empty else 0
top_partner = partner_totals.iloc[0] if not partner_totals.empty else None
top5_share = partner_totals.head(5)["Value_USD_Mn"].sum() / partner_sum * 100 if partner_sum > 0 else np.nan
monthly_current = current.groupby(["MonthNum", "Month"], as_index=False)["Value_USD_Mn"].sum().sort_values("MonthNum")
peak = monthly_current.loc[monthly_current["Value_USD_Mn"].idxmax()] if not monthly_current.empty else None
known_flows = set(data["Trade Flow"].unique())
has_imports = "Imports" in known_flows
has_exports = "Exports" in known_flows
has_both_flows = has_imports and has_exports

# =============================================================================
# Applied scope ribbon and top navigation
# =============================================================================
market_label = selected_market if selected_market != "All partner markets" else "All partner markets"
# Keep persistent context visible without placing large warning banners between
# navigation and the active analysis. Full explanations live in Data & methodology.
if has_both_flows:
    flow_status_label = "Imports + exports loaded"
elif "Direction not verified" in known_flows:
    flow_status_label = "Direction not verified"
else:
    flow_status_label = ", ".join(available_flows) + " only"
comparison_status_label = f"YoY basis · same months vs {prior_year}"

st.markdown(
    "<div class='scope-strip'><b>LIVE VIEW</b>"
    f"<span class='scope-pill'>{safe(period_label)}</span>"
    f"<span class='scope-pill'>{len(selected_commodities)} HS chapters</span>"
    f"<span class='scope-pill'>{safe(market_label)}</span>"
    f"<span class='scope-pill scope-pill-status'>{safe('Flow · ' + flow_status_label)}</span>"
    f"<span class='scope-pill scope-pill-muted'>{safe(comparison_status_label)}</span></div>",
    unsafe_allow_html=True,
)

page = st.session_state.get("petrotrade_active_page", "Overview")

# =============================================================================
# PAGE 1: OVERVIEW
# =============================================================================
if page == "Overview":
    section("WELCOME / START HERE", "From raw trade records to market signals", "Use the live controls above to set the year, months, commodity families, HS chapters, partner market, chart style and market-ranking depth, then select Apply analysis filters. This page recalculates headline KPIs and the scenario lab from the applied data.")
    st.markdown(
        "<div class='info-panel'><b>How to use PetroTrade:</b><br>"
        "<b>1. Set your filters and apply them</b> to choose year, months, commodity families, HS chapters, and partner market. All metrics and charts respond to the applied selection.<br>"
        "<b>2. Read the signals</b> to see the largest commodity group, the leading named partner, and the strongest month in the selected period.<br>"
        "<b>3. Explore a question</b> using Commodity breakdown, Commodity deep dive, Market opportunity matrix, Concentration & risk, or Partner markets in the top navigation.<br>"
        "<b>4. Export evidence</b> from Data & methodology for further analysis. Values are in US dollars; chart scales use billions for readability.</div>",
        unsafe_allow_html=True,
    )

    combined_label = "Combined value in loaded flow data" if len(known_flows) > 1 else "Recorded value"
    c1, c2, c3, c4 = st.columns(4, gap="medium")
    with c1:
        kpi_card(combined_label.upper(), fmt_money_mn(current_total_mn), f"{period_label} · selected groups", TEAL)
    with c2:
        kpi_card("YEAR-ON-YEAR CHANGE", fmt_pct(yoy_total), f"vs. comparable months in {prior_year}", GREEN if pd.notna(yoy_total) and yoy_total >= 0 else RED)
    with c3:
        kpi_card("LEADING COMMODITY SHARE", f"{leader_share:.1f}%" if pd.notna(leader_share) else "—", f"{leader['Commodity']} · {fmt_money_mn(leader['Value_USD_Mn'])}" if leader is not None else "No value available", "#365B78")
    with c4:
        kpi_card("NAMED PARTNER MARKETS", f"{active_markets:,}", "Positive-value named markets", "#E0B15A")

    st.write("")
    section("EXECUTIVE READOUT", "Signals worth noticing", "These are descriptive observations from the selected data; they do not establish causes or forecast future performance.")
    i1, i2, i3 = st.columns(3, gap="medium")
    with i1:
        insight_card("01", "Commodity mix", f"{leader['Commodity']} represents {leader_share:.1f}% of the selected-period value ({fmt_money_mn(leader['Value_USD_Mn'])})." if leader is not None and pd.notna(leader_share) else "No commodity leader is available for this selection.")
    with i2:
        insight_card("02", "Largest named partner", f"{top_partner['DisplayCountry']} is the largest named market at {fmt_money_mn(top_partner['Value_USD_Mn'])}. The top five markets represent {top5_share:.1f}% of named-market value." if top_partner is not None else "No named markets are available for this selection.")
    with i3:
        insight_card("03", "Monthly high", f"{peak['Month']} is the strongest month in {selected_year} at {fmt_money_mn(peak['Value_USD_Mn'])}. This is a descriptive peak, not a forecast." if peak is not None else "No monthly peak is available.")

    st.write("")
    section("01 / TIME SERIES", "Is recorded value moving up or down?", "Monthly values compare the selected year with the same months in the preceding year.")
    left, right = st.columns([1.35, 1], gap="large")
    with left:
        chart_data = []
        for period_df, period_name in [(prior, f"{prior_year} · comparable"), (current, f"{selected_year}{' · YTD' if partial else ''}")]:
            if period_df.empty:
                continue
            if len(known_flows) > 1:
                monthly_flow = period_df.groupby(["MonthNum", "Month", "Trade Flow"], as_index=False)["Value_USD_Bn"].sum()
                monthly_flow["Period"] = period_name
                chart_data.append(monthly_flow)
            else:
                monthly_flow = period_df.groupby(["MonthNum", "Month"], as_index=False)["Value_USD_Bn"].sum()
                monthly_flow["Trade Flow"] = period_name
                chart_data.append(monthly_flow)
        if chart_data:
            line_data = pd.concat(chart_data, ignore_index=True)
            if len(known_flows) > 1:
                line_data["Series"] = line_data["Period"] + " · " + line_data["Trade Flow"]
                color_field = "Series"
                chart_labels = {"Value_USD_Bn": "Value (US$ billion)", "Month": "Month"}
                chart_colors = PALETTE
            else:
                color_field = "Trade Flow"
                chart_labels = {"Value_USD_Bn": "Value (US$ billion)", "Month": "Month", "Trade Flow": "Period"}
                chart_colors = ["#71849B", TEAL]

            if selected_trend_style == "Area":
                fig = px.area(line_data, x="Month", y="Value_USD_Bn", color=color_field,
                              category_orders={"Month": month_labels}, color_discrete_sequence=chart_colors,
                              labels=chart_labels)
            elif selected_trend_style == "Grouped bars":
                fig = px.bar(line_data, x="Month", y="Value_USD_Bn", color=color_field, barmode="group",
                             category_orders={"Month": month_labels}, color_discrete_sequence=chart_colors,
                             labels=chart_labels)
            else:
                fig = px.line(line_data, x="Month", y="Value_USD_Bn", color=color_field, markers=True,
                              category_orders={"Month": month_labels}, color_discrete_sequence=chart_colors,
                              labels=chart_labels)
                fig.update_traces(line_width=3, marker_size=7)
            fig.update_traces(hovertemplate="%{x}<br>US$%{y:,.2f}B<extra>%{fullData.name}</extra>")
            fig.update_layout(hovermode="x unified", legend_title_text="", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0))
            fig.update_yaxes(tickprefix="$", ticksuffix="B", title="Value (US$ billion)")
            render_chart(fig, "overview_monthly_trend", 380)
        else:
            st.info("No monthly values are available for this period.")
    with right:
        if not commodity_totals.empty:
            mix = commodity_totals.copy()
            mix["Value_USD_Bn"] = mix["Value_USD_Mn"] / 1000
            fig = px.pie(mix, names="Commodity", values="Value_USD_Bn", hole=.68, color="Commodity", color_discrete_sequence=PALETTE)
            fig.update_traces(textposition="inside", textinfo="percent", marker=dict(line=dict(color="white", width=2)),
                              hovertemplate="%{label}<br>US$%{value:,.2f}B<br>%{percent}<extra></extra>")
            fig.add_annotation(text=f"{fmt_money_mn(current_total_mn)}<br><sup>recorded value</sup>", x=.5, y=.5, showarrow=False,
                               font=dict(size=16, color=NAVY), align="center")
            fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=-.15, xanchor="center", x=.5))
            render_chart(fig, "overview_commodity_mix", 380)

    st.write("")
    section("02 / HISTORICAL CONTEXT", "How does the selected period compare with earlier years?", "A partial year is marked YTD and should not be read as a complete annual total.")
    annual_scope = base_filtered[base_filtered["MonthNum"].isin(months_present)].copy()
    annual = annual_scope.groupby(["Year", "Trade Flow"], as_index=False)["Value_USD_Bn"].sum()
    annual_months = annual_scope.groupby(["Year", "Trade Flow"])["MonthNum"].nunique().reset_index(name="Months")
    annual = annual.merge(annual_months, on=["Year", "Trade Flow"], how="left")
    annual["Period"] = annual.apply(lambda r: f"{int(r['Year'])} · YTD" if int(r["Months"]) < 12 else str(int(r["Year"])), axis=1)
    if len(known_flows) > 1:
        fig = px.bar(annual, x="Period", y="Value_USD_Bn", color="Trade Flow", barmode="group", color_discrete_sequence=PALETTE,
                     labels={"Value_USD_Bn": "Recorded value (US$ billion)", "Period": "Reporting period"})
    else:
        annual_sum = annual_scope.groupby("Year", as_index=False)["Value_USD_Bn"].sum()
        annual_sum["Period"] = annual_sum["Year"].astype(str)
        annual_sum.loc[annual_sum["Year"] == selected_year, "Period"] = f"{selected_year} · selected" if len(months_present) < 12 else str(selected_year)
        fig = px.bar(annual_sum, x="Period", y="Value_USD_Bn", color="Period", color_discrete_sequence=[TEAL, "#365B78", "#6E9F93", "#E0B15A", "#83919B"],
                     labels={"Value_USD_Bn": "Recorded value (US$ billion)", "Period": "Reporting period"})
    fig.update_traces(texttemplate="US$%{y:.1f}B", textposition="outside", cliponaxis=False, hovertemplate="%{x}<br>US$%{y:,.2f}B<extra></extra>")
    fig.update_layout(showlegend=len(known_flows) > 1, yaxis_title="Value (US$ billion)", xaxis_title="Reporting period")
    render_chart(fig, "overview_annual_context", 360, legend=len(known_flows) > 1)

    st.write("")
    section("03 / LEADING MARKETS", "Which named markets have the largest recorded values?", "Aggregate labels are excluded from the ranking. Change the live scope above to recalculate these rankings.")
    top_markets = partner_totals.head(top_partner_count).sort_values("Value_USD_Mn")
    if not top_markets.empty:
        top_markets["Value_USD_Bn"] = top_markets["Value_USD_Mn"] / 1000
        fig = px.bar(top_markets, x="Value_USD_Bn", y="DisplayCountry", orientation="h", text="Value_USD_Bn",
                     color="Value_USD_Bn", color_continuous_scale=["#F8D6CA", TEAL, NAVY],
                     labels={"Value_USD_Bn": "Value (US$ billion)", "DisplayCountry": "Partner market"})
        fig.update_traces(texttemplate="US$%{x:.2f}B", textposition="outside", cliponaxis=False,
                          hovertemplate="%{y}<br>US$%{x:,.2f}B<extra></extra>")
        fig.update_layout(coloraxis_showscale=False, yaxis_title="", xaxis_title="Value (US$ billion)")
        render_chart(fig, "overview_top_markets", 400, legend=False)

    st.write("")
    section("SCENARIO LAB", "Test a what-if change for one commodity", "Adjust the growth assumption to see how a hypothetical change would affect the selected-period value. This is a sensitivity exercise, not a forecast.")
    with st.container(border=True):
        scenario_left, scenario_right = st.columns([1.0, 1.5], gap="large")
        with scenario_left:
            scenario_commodity = st.selectbox(
                "Commodity to stress-test",
                options=selected_commodities,
                key="scenario_commodity_main",
                format_func=lambda name: f"HS {int(data.loc[data['Commodity'] == name, 'HS Code'].iloc[0])} · {name}" if not data.loc[data["Commodity"] == name, "HS Code"].empty else name,
            )
            scenario_growth = st.slider(
                "Assumed value change (%)",
                min_value=-50,
                max_value=100,
                value=10,
                step=5,
                key="scenario_growth_main",
                help="For example, +10% tests a scenario where the selected commodity's value is 10% higher than its recorded baseline.",
            )
        scenario_base = current.loc[current["Commodity"] == scenario_commodity, "Value_USD_Mn"].sum()
        scenario_result = scenario_base * (1 + scenario_growth / 100)
        scenario_delta = scenario_result - scenario_base
        with scenario_right:
            s1, s2, s3 = st.columns(3)
            s1.metric("Recorded baseline", fmt_money_mn(scenario_base))
            s2.metric("Scenario value", fmt_money_mn(scenario_result), delta=fmt_money_mn(scenario_delta))
            s3.metric("Assumption", f"{scenario_growth:+d}%")
            scenario_plot = pd.DataFrame({
                "Scenario": ["Recorded baseline", f"What-if {scenario_growth:+d}%"],
                "Value (US$ billion)": [scenario_base / 1000, scenario_result / 1000],
            })
            fig = px.bar(
                scenario_plot, x="Scenario", y="Value (US$ billion)", color="Scenario",
                color_discrete_sequence=["#71849B", TEAL], text="Value (US$ billion)",
                labels={"Value (US$ billion)": "Value (US$ billion)"},
            )
            fig.update_traces(texttemplate="US$%{y:.2f}B", textposition="outside", cliponaxis=False,
                              hovertemplate="%{x}<br>US$%{y:,.2f}B<extra></extra>")
            fig.update_layout(showlegend=False, yaxis_title="Value (US$ billion)", xaxis_title="", margin=dict(l=10, r=15, t=25, b=15))
            render_chart(fig, "overview_scenario_lab", 300, legend=False)

# =============================================================================
# PAGE 2: COMMODITY BREAKDOWN
# =============================================================================
elif page == "Commodity breakdown":
    section("COMMODITY INTELLIGENCE", "Categorise every selected commodity group", "Each row combines the HS chapter, a readable commodity group, a higher-level segment, and recorded value for the selected year.")
    st.markdown(
        "<div class='info-panel'><b>What this page tells you:</b> compare the scale of each category, see which groups are strengthening or weakening year over year, and inspect the month-by-month pattern. These are broad HS chapter groups. The source does not provide product-level detail within a chapter.</div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.15, 1], gap="large")
    with left:
        commodity_bar = current.groupby(["Commodity", "Commodity Category", "Trade Flow"], as_index=False)["Value_USD_Bn"].sum()
        if len(known_flows) > 1:
            fig = px.bar(commodity_bar, x="Commodity", y="Value_USD_Bn", color="Trade Flow", barmode="group", color_discrete_sequence=PALETTE,
                         labels={"Value_USD_Bn": "Value (US$ billion)", "Commodity": "Commodity group"}, hover_data=["Commodity Category"])
        else:
            commodity_bar = current.groupby(["Commodity", "Commodity Category"], as_index=False)["Value_USD_Bn"].sum().sort_values("Value_USD_Bn")
            fig = px.bar(commodity_bar, x="Value_USD_Bn", y="Commodity", orientation="h", color="Value_USD_Bn", color_continuous_scale=["#F8D6CA", TEAL, NAVY],
                         labels={"Value_USD_Bn": "Value (US$ billion)", "Commodity": "Commodity group"}, hover_data=["Commodity Category"])
        fig.update_layout(coloraxis_showscale=False, xaxis_title="Value (US$ billion)", yaxis_title="" if len(known_flows) == 1 else "Commodity group")
        render_chart(fig, "commodity_current_value", 420, legend=len(known_flows) > 1)
    with right:
        if has_both_flows:
            both = current[current["Trade Flow"].isin(["Imports", "Exports"])].groupby(["Commodity", "Trade Flow"], as_index=False)["Value_USD_Bn"].sum()
            pivot = both.pivot(index="Commodity", columns="Trade Flow", values="Value_USD_Bn").fillna(0)
            pivot["Balance (Exports − Imports)"] = pivot.get("Exports", 0) - pivot.get("Imports", 0)
            bal = pivot.reset_index().sort_values("Balance (Exports − Imports)")
            fig = px.bar(bal, x="Balance (Exports − Imports)", y="Commodity", orientation="h", color="Balance (Exports − Imports)",
                         color_continuous_scale=[RED, "#24354B", GREEN], labels={"Balance (Exports − Imports)": "Net balance (US$ billion)"})
            fig.add_vline(x=0, line_dash="dash", line_color="#748394")
            fig.update_layout(coloraxis_showscale=False, xaxis_title="Exports minus imports (US$ billion)", yaxis_title="")
            render_chart(fig, "commodity_balance", 420, legend=False)
        else:
            segment = current.groupby("Commodity Category", as_index=False)["Value_USD_Bn"].sum().sort_values("Value_USD_Bn", ascending=False)
            fig = px.treemap(segment, path=["Commodity Category"], values="Value_USD_Bn", color="Value_USD_Bn",
                             color_continuous_scale=["#DDEFF0", "#6E9F93", TEAL, NAVY], labels={"Value_USD_Bn": "Value (US$ billion)"})
            fig.update_traces(texttemplate="%{label}<br>US$%{value:.2f}B", hovertemplate="%{label}<br>US$%{value:,.2f}B<extra></extra>")
            fig.update_layout(coloraxis_showscale=False)
            render_chart(fig, "commodity_segment_treemap", 420, legend=False)

    st.write("")
    section("MONTHLY PATTERN", "When does each commodity group run above its own average?", "Each row is indexed to that commodity's own monthly average in the selected year (=100), so the largest group does not dominate the colour scale.")
    heat = current.groupby(["Commodity", "MonthNum", "Month"], as_index=False)["Value_USD_Mn"].sum()
    if not heat.empty:
        pivot = heat.pivot(index="Commodity", columns="MonthNum", values="Value_USD_Mn").reindex(selected_commodities)
        pivot = pivot.reindex(columns=months_present)
        indexed = pivot.div(pivot.mean(axis=1).replace(0, np.nan), axis=0) * 100
        fig = go.Figure(data=go.Heatmap(
            z=indexed.values,
            x=[pd.Timestamp(year=2000, month=int(m), day=1).strftime("%b") for m in indexed.columns],
            y=indexed.index.tolist(),
            colorscale=[[0, "#14263C"], [.65, "#397F79"], [1, TEAL]],
            zmid=100,
            colorbar=dict(title="Index", thickness=13),
            hovertemplate="%{y}<br>%{x}<br>Index: %{z:.0f} (100 = category's own monthly average)<extra></extra>",
        ))
        fig.update_layout(xaxis_title="Month", yaxis_title="Commodity group")
        render_chart(fig, "commodity_monthly_heatmap", 330, legend=False)

    st.write("")
    section("COMMODITY LEDGER", "Annual imports, exports and trade balance by category", "Import/export columns are populated only for the flow-specific datasets you have loaded. Missing flows remain blank rather than being treated as zero.")
    ledger = build_commodity_ledger(current, prior, selected_commodities, known_flows)
    display_ledger = ledger.copy()
    for col in ["Recorded value (US$ B)", "Imports (US$ B)", "Exports (US$ B)", "Export − import (US$ B)"]:
        if col in display_ledger.columns:
            display_ledger[col] = display_ledger[col].map(lambda x: f"{x:,.2f}" if pd.notna(x) else "—")
    for col in ["YoY recorded change (%)", "Import YoY (%)", "Export YoY (%)"]:
        if col in display_ledger.columns:
            display_ledger[col] = display_ledger[col].map(fmt_pct)
    st.dataframe(display_ledger, use_container_width=True, hide_index=True, height=compact_height(len(display_ledger), max_height=360))
    st.download_button("Download commodity ledger", ledger.to_csv(index=False).encode("utf-8-sig"), file_name=f"petrotrade_commodity_ledger_{selected_year}.csv", mime="text/csv")

    # ============================================================
    # COMMIT 04: COMMODITY COMPARISON ANALYSIS
    # ============================================================

    st.write("")

    section(
        "COMMODITY COMPARISON",
        "Compare commodity performance side by side",
        "Select multiple commodity groups to compare recorded values, "
        "monthly movement and year-on-year performance."
    )

    comparison_options = list(selected_commodities)
    comparison_key = "commodity_comparison_selection"

    # Keep saved selections valid when global filters change.
    if comparison_key not in st.session_state:
        st.session_state[comparison_key] = comparison_options[:3]
    else:
        st.session_state[comparison_key] = [
            x for x in st.session_state[comparison_key]
            if x in comparison_options
        ]

    if not st.session_state[comparison_key] and comparison_options:
        st.session_state[comparison_key] = comparison_options[:2]

    comparison_selection = st.multiselect(
        "Select commodity groups to compare",
        options=comparison_options,
        key=comparison_key,
        help="Select at least two commodity groups."
    )

    # Let the user decide whether to compare all loaded flows
    # or a particular direction.
    comparison_flow_options = (
        ["All loaded flows"] + sorted(
            current["Trade Flow"].dropna().unique().tolist()
        )
    )

    if st.session_state.get("comparison_flow_key") not in comparison_flow_options:
        st.session_state["comparison_flow_key"] = "All loaded flows"

    comparison_flow = st.selectbox(
        "Trade flow for comparison",
        options=comparison_flow_options,
        key="comparison_flow_key"
    )

    if len(comparison_selection) < 2:

        empty_state(
            "Select at least two commodities",
            "Commodity comparison requires two or more selected HS chapters.",
            "Choose additional commodity groups using the selector above."
        )

    else:

        comparison_current = current[
            current["Commodity"].isin(comparison_selection)
        ].copy()

        comparison_prior = prior[
            prior["Commodity"].isin(comparison_selection)
        ].copy()

        if comparison_flow != "All loaded flows":
            comparison_current = comparison_current[
                comparison_current["Trade Flow"] == comparison_flow
            ].copy()

            comparison_prior = comparison_prior[
                comparison_prior["Trade Flow"] == comparison_flow
            ].copy()

        if comparison_current.empty:

            empty_state(
                "No comparison records available",
                "The selected commodities and trade flow have no records "
                "for the current reporting period.",
                "Try another flow or widen the selected reporting months."
            )

        else:

            # Aggregate current-period values.
            current_summary = (
                comparison_current
                .groupby("Commodity", as_index=False)["Value_USD_Mn"]
                .sum()
                .rename(columns={
                    "Value_USD_Mn": "Current_Mn"
                })
            )

            # Aggregate matching prior-year values.
            prior_summary = (
                comparison_prior
                .groupby("Commodity", as_index=False)["Value_USD_Mn"]
                .sum()
                .rename(columns={
                    "Value_USD_Mn": "Prior_Mn"
                })
            )

            # Preserve selected commodities even if a prior observation
            # is unavailable for one of them.
            comparison_summary = pd.DataFrame({
                "Commodity": comparison_selection
            })

            comparison_summary = comparison_summary.merge(
                current_summary,
                on="Commodity",
                how="left"
            )

            comparison_summary = comparison_summary.merge(
                prior_summary,
                on="Commodity",
                how="left"
            )

            comparison_summary["Current_Mn"] = (
                comparison_summary["Current_Mn"].fillna(0)
            )

            comparison_summary["Current value (US$ B)"] = (
                comparison_summary["Current_Mn"] / 1000
            )

            comparison_summary["Comparable prior value (US$ B)"] = (
                comparison_summary["Prior_Mn"] / 1000
            )

            # Calculate growth only where the previous-period
            # denominator is positive.
            comparison_summary["YoY change (%)"] = np.nan

            valid_growth = comparison_summary["Prior_Mn"] > 0

            comparison_summary.loc[
                valid_growth,
                "YoY change (%)"
            ] = (
                comparison_summary.loc[
                    valid_growth, "Current_Mn"
                ]
                / comparison_summary.loc[
                    valid_growth, "Prior_Mn"
                ] - 1
            ) * 100

            # Calculate portfolio contribution.
            total_comparison_value = (
                comparison_summary["Current_Mn"].sum()
            )

            comparison_summary["Contribution (%)"] = np.where(
                total_comparison_value > 0,
                comparison_summary["Current_Mn"]
                / total_comparison_value * 100,
                np.nan
            )

            # ----------------------------------------------------
            # Comparison KPI cards
            # ----------------------------------------------------

            
            # ----------------------------------------------------
            # COMMIT 06: FOUR-CARD COMPARISON KPI STRIP
            # ----------------------------------------------------

            k1, k2, k3, k4 = st.columns(4, gap="medium")

            largest = comparison_summary.loc[
                comparison_summary["Current_Mn"].idxmax()
            ]

            valid_growth_rows = comparison_summary.dropna(
                subset=["YoY change (%)"]
            )

            with k1:
                kpi_card(
                    "COMMODITIES COMPARED",
                    str(len(comparison_selection)),
                    "Selected HS commodity groups",
                    TEAL
                )

            with k2:
                kpi_card(
                    "COMBINED RECORDED VALUE",
                    fmt_money_mn(total_comparison_value),
                    "Across all selected commodity groups",
                    "#365B78"
                )

            with k3:
                kpi_card(
                    "LARGEST RECORDED VALUE",
                    largest["Commodity"],
                    fmt_money_bn(
                        largest["Current value (US$ B)"]
                    ),
                    "#E0B15A"
                )

            with k4:
                if not valid_growth_rows.empty:
                    fastest = valid_growth_rows.loc[
                        valid_growth_rows["YoY change (%)"].idxmax()
                    ]

                    kpi_card(
                        "FASTEST YoY GROWTH",
                        fastest["Commodity"],
                        fmt_pct(fastest["YoY change (%)"]),
                        GREEN
                    )
                else:
                    kpi_card(
                        "FASTEST YoY GROWTH",
                        "Unavailable",
                        "No positive comparable prior-year baseline",
                        RED
                    )

            # ----------------------------------------------------
            # Current versus previous period chart
            # ----------------------------------------------------

            chart_left, chart_right = st.columns(2, gap="large")

            with chart_left:

                st.markdown("**Current vs previous-period value**")

                comparison_long = comparison_summary.melt(
                    id_vars=["Commodity"],
                    value_vars=[
                        "Current value (US$ B)",
                        "Comparable prior value (US$ B)"
                    ],
                    var_name="Period",
                    value_name="Value_USD_Bn"
                ).dropna(subset=["Value_USD_Bn"])

                fig = px.bar(
                    comparison_long,
                    x="Commodity",
                    y="Value_USD_Bn",
                    color="Period",
                    barmode="group",
                    color_discrete_sequence=[
                        TEAL,
                        "#AAB7C4"
                    ],
                    labels={
                        "Commodity": "Commodity group",
                        "Value_USD_Bn": "Value (US$ billion)"
                    }
                )

                fig.update_layout(
                    xaxis_title="Commodity group",
                    yaxis_title="Value (US$ billion)",
                    legend_title=""
                )

                fig.update_traces(
                    hovertemplate=(
                        "%{x}<br>"
                        "%{fullData.name}: US$%{y:,.3f}B"
                        "<extra></extra>"
                    )
                )

                render_chart(
                    fig,
                    "comparison_current_prior",
                    400,
                    legend=True
                )

            # ----------------------------------------------------
            # Monthly trend comparison
            # ----------------------------------------------------

            with chart_right:

                st.markdown("**Monthly commodity movement**")

                monthly_comparison = (
                    comparison_current
                    .groupby(
                        ["MonthNum", "Month", "Commodity"],
                        as_index=False
                    )["Value_USD_Bn"]
                    .sum()
                    .sort_values("MonthNum")
                )

                if not monthly_comparison.empty:

                    fig = px.line(
                        monthly_comparison,
                        x="Month",
                        y="Value_USD_Bn",
                        color="Commodity",
                        markers=True,
                        category_orders={
                            "Month": month_labels
                        },
                        color_discrete_sequence=PALETTE,
                        labels={
                            "Month": "Month",
                            "Value_USD_Bn": "Value (US$ billion)"
                        }
                    )

                    fig.update_layout(
                        hovermode="x unified",
                        xaxis_title="Month",
                        yaxis_title="Value (US$ billion)",
                        legend_title="Commodity"
                    )

                    render_chart(
                        fig,
                        "comparison_monthly_trend",
                        400,
                        legend=True
                    )

            # ----------------------------------------------------
            # Detailed comparison table
            # ----------------------------------------------------

            st.write("")

            section(
                "COMPARISON SUMMARY",
                "Inspect the selected commodity groups",
                "Values use the same months in the current and previous reporting years."
            )

            display_comparison = comparison_summary[
                [
                    "Commodity",
                    "Current value (US$ B)",
                    "Comparable prior value (US$ B)",
                    "YoY change (%)",
                    "Contribution (%)"
                ]
            ].copy()

        
            # ====================================================
            # COMMIT 07: CUSTOM COMMODITY SORTING
            # ====================================================

            st.markdown("**Rank comparison results**")

            sort_col, order_col = st.columns([2, 1])

            with sort_col:
                sort_option = st.selectbox(
                    "Rank commodities by",
                    options=[
                        "Recorded value",
                        "YoY growth",
                        "Portfolio contribution"
                    ],
                    key="commodity_comparison_sort"
                )

            sort_mapping = {
                "Recorded value": "Current value (US$ B)",
                "YoY growth": "YoY change (%)",
                "Portfolio contribution": "Contribution (%)"
            }

            with order_col:
                descending = st.checkbox(
                    "Highest first",
                    value=True,
                    key="commodity_comparison_descending"
                )

            display_comparison = display_comparison.sort_values(
                by=sort_mapping[sort_option],
                ascending=not descending,
                na_position="last",
                kind="stable"
            ).reset_index(drop=True)

            # Add ranking numbers.
            display_comparison.insert(
                0,
                "Rank",
                range(1, len(display_comparison) + 1)
            )


            st.dataframe(
                display_comparison,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Current value (US$ B)":
                        st.column_config.NumberColumn(
                            format="$%.3fB"
                        ),
                    "Comparable prior value (US$ B)":
                        st.column_config.NumberColumn(
                            format="$%.3fB"
                        ),
                    "YoY change (%)":
                        st.column_config.NumberColumn(
                            format="%+.1f%%"
                        ),
                    "Contribution (%)":
                        st.column_config.NumberColumn(
                            format="%.1f%%"
                        )
                }
            )

            st.download_button(
                "Download commodity comparison as CSV",
                data=display_comparison.to_csv(
