from pathlib import Path
from io import BytesIO
import html
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
PALETTE = ["#E46F4A", "#365B78", "#6E9F93", "#E0B15A", "#83919B", "#8E83B8"]
TEAL = "#E46F4A"
NAVY = "#172A3A"
SLATE = "#68727D"
GREEN = "#23745B"
RED = "#C84F4F"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');
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
.landing-hero {
  position: relative; overflow: hidden; display: grid;
  grid-template-columns: minmax(0, 1.38fr) minmax(270px, .62fr); gap: 2.1rem;
  padding: clamp(1.8rem, 4vw, 3.6rem); min-height: 380px;
  border-radius: 16px 30px 16px 30px;
  background: linear-gradient(118deg, #172A3A 0%, #243847 60%, #344E5B 100%);
  color: #F5F3EE; border-left: 6px solid #E46F4A;
  box-shadow: 0 18px 45px rgba(23,42,58,.14); animation: fadeSlideIn .65s ease both;
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
  box-shadow: 0 14px 32px rgba(23,42,58,.12); animation: fadeSlideIn .55s ease both;
}
.hero .hero-eyebrow { color: #F2A78E; font-size: .69rem; font-weight: 800; letter-spacing: .19em; text-transform: uppercase; margin-bottom: .6rem; }
.hero .hero-title { font-size: 2.45rem; font-weight: 750; line-height: 1.07; letter-spacing: -.055em; margin: 0 0 .55rem; }
.hero .hero-sub { max-width: 940px; color: #E0E7E9; font-size: .98rem; line-height: 1.65; }
.hero-meta { display: flex; gap: .55rem; flex-wrap: wrap; margin-top: 1.15rem; }
.hero-chip { display: inline-block; border: 1px solid rgba(255,255,255,.20); color: #F5F3EE; background: rgba(255,255,255,.075); padding: .35rem .68rem; border-radius: 6px; font-size: .73rem; }
/* Top navigation */
div[data-testid="stRadio"] { margin: .2rem 0 .9rem; }
div[data-testid="stRadio"] [role="radiogroup"] { display:flex; flex-direction:row; flex-wrap:wrap; gap:.5rem; padding:.35rem 0 .8rem; border-bottom:1px solid #DED9CF; }
div[data-testid="stRadio"] [role="radiogroup"] label { background:#FFFEFC; border:1px solid #DED9CF; border-radius:8px; padding:.54rem .9rem; margin:0; color:#53616D; font-weight:650; transition:transform .18s ease, border-color .18s ease, background .18s ease; }
div[data-testid="stRadio"] [role="radiogroup"] label:hover { transform:translateY(-2px); border-color:#E46F4A; }
div[data-testid="stRadio"] input[type="radio"] { accent-color:#E46F4A; }
div[data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) { background:#FBE8DF; border-color:#E46F4A; color:#A94328; }
/* Inputs and selections */
[data-baseweb="select"] > div { border-color:#DED9CF !important; border-radius:8px !important; }
[data-baseweb="tag"] { background:#E46F4A !important; border-radius:5px !important; }
[data-baseweb="tag"] span { color:#FFFFFF !important; }
button[kind="primary"] { background:#E46F4A !important; border-color:#E46F4A !important; }
button[kind="primary"]:hover { background:#C95C3B !important; border-color:#C95C3B !important; }
.section-kicker { font-size:.68rem; letter-spacing:.16em; text-transform:uppercase; font-weight:850; color:#C95C3B; margin:.25rem 0 .28rem; }
.section-title { font-size:1.4rem; letter-spacing:-.04em; font-weight:750; color:#172A3A; margin:0 0 .22rem; }
.section-note { font-size:.88rem; line-height:1.58; color:#68727D; margin:0 0 .9rem; }
.kpi-card { background:#FFFEFC; border:1px solid #E3DED4; border-top:3px solid #E46F4A; border-radius:10px 18px 10px 18px; padding:1.1rem 1.15rem 1rem; min-height:128px; box-shadow:0 4px 12px rgba(23,42,58,.035); animation:fadeSlideIn .5s ease both; transition:transform .2s ease,box-shadow .2s ease; }
.kpi-card:hover { transform:translateY(-3px); box-shadow:0 12px 25px rgba(23,42,58,.09); }
.kpi-label { color:#68727D; font-size:.75rem; font-weight:750; margin-bottom:.52rem; letter-spacing:.045em; }
.kpi-value { color:#172A3A; font-family:'Space Grotesk','DM Sans',sans-serif; font-size:1.82rem; line-height:1.1; letter-spacing:-.045em; font-weight:700; }
.kpi-foot { color:#737C84; font-size:.76rem; margin-top:.6rem; line-height:1.4; }
.insight-grid-card { background:#FFFEFC; border:1px solid #E3DED4; border-radius:10px 16px 10px 16px; padding:1rem; min-height:118px; box-shadow:0 2px 8px rgba(23,42,58,.025); animation:fadeSlideIn .55s ease both; transition:transform .18s ease,box-shadow .18s ease; }
.insight-grid-card:hover { transform:translateY(-3px); box-shadow:0 10px 20px rgba(23,42,58,.065); }
.insight-mark { display:inline-flex; align-items:center; justify-content:center; width:31px; height:31px; background:#FBE8DF; color:#C95C3B; border-radius:8px; font-size:.9rem; font-weight:850; margin-bottom:.62rem; }
.insight-label { color:#68727D; text-transform:uppercase; letter-spacing:.11em; font-size:.65rem; font-weight:850; margin-bottom:.35rem; }
.insight-text { color:#263844; font-size:.88rem; line-height:1.55; }
.callout { background:#FFF5E7; border:1px solid #E7C98C; color:#74532B; border-radius:8px; padding:.75rem .95rem; font-size:.83rem; line-height:1.55; margin:.4rem 0 .85rem; }
.info-panel { background:#F0EEE8; border:1px solid #E3DED4; border-left:3px solid #E46F4A; border-radius:8px 14px 8px 14px; padding:1rem 1.15rem; margin:.4rem 0 .95rem; color:#4B5D68; line-height:1.6; }
.info-panel b { color:#172A3A; }
.panel-note { color:#7A838B; font-size:.75rem; line-height:1.48; }
/* Chart cards */
div[data-testid="stPlotlyChart"] { background:#FFFEFC; border:1px solid #E3DED4; border-radius:10px 18px 10px 18px; padding:.38rem .42rem .08rem; box-shadow:0 3px 11px rgba(23,42,58,.025); animation:chartEnter .58s cubic-bezier(.2,.75,.3,1) both; transition:transform .2s ease,box-shadow .2s ease,border-color .2s ease; }
div[data-testid="stPlotlyChart"]:hover { transform:translateY(-2px); box-shadow:0 12px 25px rgba(23,42,58,.08); border-color:#E8B6A5; }
div[data-testid="stDataFrame"] { border:1px solid #E3DED4; border-radius:9px; overflow:hidden; }
.control-deck { background:linear-gradient(180deg,#FFFEFC 0%,#F8F6F1 100%); border:1px solid #E3DED4; border-radius:12px 20px 12px 20px; padding:1.1rem 1.2rem .5rem; margin:.7rem 0 1rem; box-shadow:0 6px 18px rgba(23,42,58,.04); }
.control-deck-title { color:#172A3A; font-size:1.08rem; font-weight:750; margin-bottom:.12rem; }
.control-deck-sub { color:#68727D; font-size:.82rem; margin-bottom:.8rem; line-height:1.5; }
.scope-strip { display:flex; align-items:center; flex-wrap:wrap; gap:.55rem; background:#F0EEE8; border:1px solid #E3DED4; color:#405461; border-radius:8px; padding:.62rem .85rem; margin:.65rem 0 .95rem; font-size:.79rem; }
.scope-pill { background:#FFFEFC; border:1px solid #DED9CF; border-radius:6px; padding:.27rem .58rem; color:#263844; font-weight:700; }
div[data-testid="stForm"] { background:#F8F6F1; border:1px solid #E3DED4; border-radius:10px; padding:.75rem; }
hr { border-color:#E3DED4; }
@keyframes fadeSlideIn { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
@keyframes chartEnter { from { opacity:.35; transform:translateY(8px) scale(.996); } to { opacity:1; transform:translateY(0) scale(1); } }
@media (prefers-reduced-motion:reduce) { *,*::before,*::after { animation-duration:.01ms !important; transition-duration:.01ms !important; } }
@media (max-width:900px) { .hero .hero-title { font-size:1.85rem; } .kpi-value { font-size:1.48rem; } }
</style>
""", unsafe_allow_html=True)


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
    st.markdown(
        f"<div class='kpi-card' style='border-top-color:{accent}'>"
        f"<div class='kpi-label'>{safe(label)}</div>"
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


def style_fig(fig, height=360, legend=True):
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=18, r=28, t=40, b=24),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        font=dict(family="DM Sans, Segoe UI, sans-serif", color="#53616D", size=12),
        hoverlabel=dict(bgcolor="#172A3A", font_color="#FFFFFF", bordercolor="#172A3A"),
        legend=dict(font=dict(color="#53616D", size=11), bgcolor="rgba(255,255,255,0)"),
        showlegend=legend,
        transition=dict(duration=450, easing="cubic-in-out"),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="#D8D2C7", ticks="outside")
    fig.update_yaxes(showgrid=True, gridcolor="#ECE8E0", zeroline=False, linecolor="#D8D2C7", ticks="outside")
    return fig


def render_chart(fig, key, height=360, legend=True):
    st.plotly_chart(
        style_fig(fig, height=height, legend=legend),
        use_container_width=True,
        key=key,
        config={
            "displayModeBar": "hover",
            "responsive": True,
            "scrollZoom": True,
            "displaylogo": False,
        },
    )


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
            preview = parse_trade_csv(DATA_FILE.read_bytes(), "Direction not verified")
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
        "<div class='landing-hero'>"
        "<div class='landing-main'>"
        "<div class='landing-kicker'>INDIA TRADE INTELLIGENCE · MARKET EXPLORATION</div>"
        "<div class='landing-title'>See the signal behind <span>commodity trade.</span></div>"
        "<div class='landing-copy'>PetroTrade Intelligence turns monthly trade records into a clear view of commodity performance, partner markets and trade patterns. Start with the market snapshot, then shape the analysis around the year, months, commodity groups and countries that matter to your question.</div>"
        f"<div class='landing-chips'><span class='landing-chip'>{safe(source_status)}</span>"
        f"<span class='landing-chip'>Reporting coverage · {safe(preview_range)}</span>"
        "<span class='landing-chip'>HS chapters 27 · 28 · 29 · 39 · 40</span></div>"
        "</div>"
        "<div class='landing-aside'>"
        "<div class='landing-aside-title'>From data to decision support</div>"
        "<div class='landing-route'><div class='landing-route-num'>01</div><div><div class='landing-route-title'>Shape your market view</div><div class='landing-route-copy'>Choose a reporting period, commodity families, HS chapters and partner markets.</div></div></div>"
        "<div class='landing-route'><div class='landing-route-num'>02</div><div><div class='landing-route-title'>Explore the signals</div><div class='landing-route-copy'>Compare recorded values, trends, category mix and market concentration.</div></div></div>"
        "<div class='landing-route'><div class='landing-route-num'>03</div><div><div class='landing-route-title'>Inspect the evidence</div><div class='landing-route-copy'>Drill into country records and export the filtered data for further analysis.</div></div></div>"
        "</div></div></div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)
    stat_cols = st.columns(4, gap="medium")
    stat_items = [
        ("LATEST PERIOD", preview_year_text, "The latest year and available monthly coverage"),
        ("RECORDED VALUE", preview_value_text, "Source value for the latest year; direction must be verified"),
        ("NAMED MARKETS", preview_partner_text, "Positive-value partner labels in the latest year"),
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

    st.markdown("<div class='landing-section-title'>One workspace, five analytical lenses</div>", unsafe_allow_html=True)
    st.markdown("<div class='landing-section-copy'>The preview introduces the areas available after you enter the dashboard. Every view is driven by the selected records, rather than static example numbers.</div>", unsafe_allow_html=True)
    feature_cols = st.columns(5, gap="small")
    feature_items = [
        ("◈", "Market overview", "Track recorded value, year-on-year movement, monthly peaks and commodity contribution."),
        ("▥", "Commodity intelligence", "Compare HS chapters and inspect monthly patterns across categories."),
        ("◎", "Partner markets", "Rank named partners and inspect country-level trends."),
        ("⌖", "Opportunity matrix", "Screen commodity groups or markets by recorded value and comparable-period growth."),
        ("⇄", "Trade-flow analysis", "Compare imports, exports and balance when both directions are verified."),
    ]
    for col, (icon, title, copy) in zip(feature_cols, feature_items):
        with col:
            st.markdown(
                f"<div class='landing-feature'><div class='landing-feature-icon'>{safe(icon)}</div>"
                f"<div class='landing-feature-title'>{safe(title)}</div>"
                f"<div class='landing-feature-copy'>{safe(copy)}</div></div>",
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:.9rem'></div>", unsafe_allow_html=True)
    action_cols = st.columns([1.25, 1.55, 3.2], gap="medium")
    with action_cols[0]:
        enter_clicked = st.button("Explore dashboard  →", type="primary", use_container_width=True, key="landing_enter_dashboard")
    with action_cols[1]:
        method_clicked = st.button("Read data methodology", use_container_width=True, key="landing_open_methodology")
    with action_cols[2]:
        st.caption("Built for exploratory analysis. The source file does not encode import/export direction; verify the DGCIS download settings before interpreting values as imports or exports.")

    with st.expander("How to use PetroTrade", expanded=False):
        st.markdown(
            "1. Enter the workspace to choose a reporting year and month window.\n"
            "2. Select the commodity families and HS chapters relevant to your question.\n"
            "3. Explore the overview, commodity breakdown and partner-market pages.\n"
            "4. Export filtered records from Data & methodology for independent validation.\n\n"
            "**Important:** year-on-year comparisons use the same months in the previous year. A partial year is not comparable to a complete annual total."
        )

    if enter_clicked or method_clicked:
        st.session_state["petrotrade_workspace_entered"] = True
        st.session_state["main_navigation"] = "Data & methodology" if method_clicked else "Overview"
        st.rerun()

    if preview_error:
        st.caption(f"Preview metrics could not be calculated from the source file: {preview_error}")
    st.stop()

# Small return path so users can revisit the landing / preview page.
back_col, _ = st.columns([1.4, 8], gap="small")
with back_col:
    if st.button("← Welcome / preview", key="petrotrade_back_to_landing"):
        st.session_state["petrotrade_workspace_entered"] = False
        st.rerun()

# =============================================================================
# Main-canvas intro + data-source setup
# =============================================================================
st.markdown(
    "<div class='hero'><div class='hero-eyebrow'>INDIA TRADE INTELLIGENCE · MARKET WORKSPACE</div>"
    "<div class='hero-title'>PetroTrade Intelligence</div>"
    "<div class='hero-sub'>Explore petroleum-related and downstream material trade through live filters, commodity comparisons, partner-market rankings, and year-on-year analysis. Select the slice of the market you want to understand; the headline metrics and charts recalculate from the underlying DGCIS records.</div>"
    "<div class='hero-meta'><span class='hero-chip'>Interactive analysis workspace</span><span class='hero-chip'>HS chapters 27 · 28 · 29 · 39 · 40</span><span class='hero-chip'>Monthly trade records</span></div></div>",
    unsafe_allow_html=True,
)

with st.expander("Data connections · label the primary file and add import/export datasets", expanded=False):
    source_left, source_right = st.columns([1, 1.35], gap="large")
    with source_left:
        if DATA_FILE.exists():
            base_bytes = DATA_FILE.read_bytes()
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
    # Use the local primary CSV when it exists; otherwise retain the upload bytes
    # collected in the Data connections expander.
    if DATA_FILE.exists():
        base_bytes = DATA_FILE.read_bytes()
    frames = []
    # Explicit flow uploads take precedence over the base file for that flow.
    if imports_upload is not None:
        frames.append(parse_trade_csv(imports_upload.getvalue(), "Imports"))
    elif base_flow == "Imports":
        frames.append(parse_trade_csv(base_bytes, "Imports"))

    if exports_upload is not None:
        frames.append(parse_trade_csv(exports_upload.getvalue(), "Exports"))
    elif base_flow == "Exports":
        frames.append(parse_trade_csv(base_bytes, "Exports"))

    if not frames:
        frames.append(parse_trade_csv(base_bytes, "Direction not verified"))

    data = pd.concat(frames, ignore_index=True).sort_values("Date").reset_index(drop=True)
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

section("LIVE ANALYSIS CONTROLS", "Build your market view", "These are live inputs, not decoration. Changing the reporting period, commodity scope, partner market, or chart style recalculates the dashboard from the selected records.")
with st.container(border=True):
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
    st.caption("Changes apply to every page immediately. Use the top navigation below to switch between the overview, commodity breakdown, market opportunity matrix, concentration and risk analysis, trade flows, partner markets, and data explorer.")

if not selected_categories:
    st.warning("Select at least one commodity family in the live controls to continue.")
    st.stop()
if not selected_commodities:
    st.warning("Select at least one HS commodity chapter in the live controls to continue.")
    st.stop()
if not selected_month_labels:
    st.warning("Select at least one month in the live controls to continue.")
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
    st.warning("No records match this combination of period, commodity and partner filters. Widen the live controls above and try again.")
    st.stop()
partial = len(months_present) < 12
period_start = pd.Timestamp(year=2000, month=min(months_present), day=1).strftime("%b")
period_end = pd.Timestamp(year=2000, month=max(months_present), day=1).strftime("%b")
period_label = f"{period_start}–{period_end} {selected_year}" if partial else f"Jan–Dec {selected_year}"
month_labels = [pd.Timestamp(year=2000, month=m, day=1).strftime("%b") for m in months_present]

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
month_window_label = ", ".join(month_labels)
st.markdown(
    "<div class='scope-strip'><b>LIVE VIEW</b>"
    f"<span class='scope-pill'>{safe(period_label)}</span>"
    f"<span class='scope-pill'>{len(selected_commodities)} HS chapters</span>"
    f"<span class='scope-pill'>{safe(market_label)}</span>"
    f"<span class='scope-pill'>{safe(month_window_label)}</span>"
    f"<span class='scope-pill'>{len(known_flows)} flow(s) loaded</span></div>",
    unsafe_allow_html=True,
)

pages = ["Overview", "Commodity breakdown", "Market opportunity matrix", "Concentration & risk", "Imports vs exports", "Partner markets", "Data & methodology"]
page = st.radio(
    "Main navigation",
    pages,
    horizontal=True,
    label_visibility="collapsed",
    key="main_navigation",
)

if not has_both_flows:
    st.markdown(
        "<div class='callout'><b>Data-flow note:</b> This workspace currently has "
        + safe(", ".join(available_flows))
        + ". Import/export comparisons and trade balance are only calculated after both flow-specific datasets are loaded. The app does not guess direction from values.</div>",
        unsafe_allow_html=True,
    )
if partial:
    st.markdown(
        f"<div class='callout'><b>Comparable-period rule:</b> {selected_year} contains {len(months_present)} comparable months in the selected flow data. Year-on-year figures use the same months of {prior_year}.</div>",
        unsafe_allow_html=True,
    )

# =============================================================================
# PAGE 1: OVERVIEW
# =============================================================================
if page == "Overview":
    section("WELCOME / START HERE", "From raw trade records to market signals", "Use the live controls above to change the year, months, commodity families, HS chapters, partner market, chart style and market-ranking depth. This page recalculates headline KPIs and the scenario lab from your selected data.")
    st.markdown(
        "<div class='info-panel'><b>How to use PetroTrade:</b><br>"
        "<b>1. Use the live controls above</b> to choose year, months, commodity families, HS chapters, and partner market. All metrics and charts respond to these inputs.<br>"
        "<b>2. Read the signals</b> to see the largest commodity group, the leading named partner, and the strongest month in the selected period.<br>"
        "<b>3. Explore a question</b> using Commodity breakdown, Imports vs exports, or Partner markets in the top navigation.<br>"
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
                chart_colors = ["#B7C1CA", TEAL]

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
                color_discrete_sequence=["#B7C1CA", TEAL], text="Value (US$ billion)",
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
                         color_continuous_scale=[RED, "#E8E4DB", GREEN], labels={"Balance (Exports − Imports)": "Net balance (US$ billion)"})
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
            colorscale=[[0, "#F1EDE5"], [.65, "#6E9F93"], [1, TEAL]],
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
    st.download_button("Download commodity ledger", ledger.to_csv(index=False).encode("utf-8"), file_name=f"petrotrade_commodity_ledger_{selected_year}.csv", mime="text/csv")

    with st.expander("Commodity categories explained"):
        explanations = []
        for code, info in COMMODITY_INFO.items():
            if info["commodity"] in selected_commodities:
                explanations.append({"HS chapter": code, "Commodity group": info["commodity"], "Analytical category": info["category"], "Scope note": info["description"]})
        st.dataframe(pd.DataFrame(explanations), use_container_width=True, hide_index=True)

# =============================================================================
# PAGE 3: MARKET OPPORTUNITY MATRIX
# =============================================================================
elif page == "Market opportunity matrix":
    section(
        "MARKET OPPORTUNITY MATRIX",
        "Where should an analyst look first?",
        "Compare current recorded value with year-on-year change to screen commodity groups or partner markets for further investigation."
    )
    st.markdown(
        "<div class='info-panel'><b>How to read the matrix:</b> each point is a commodity group or a named partner. The horizontal position shows current-period recorded value; the vertical position shows change against the same months in the previous year. The vertical divider is the median value in this selection, and the horizontal divider is your chosen growth threshold. Quadrants are relative screening labels, not investment recommendations or forecasts.</div>",
        unsafe_allow_html=True,
    )

    lens_col, flow_col, growth_col = st.columns([1.15, 1.0, 1.2], gap="medium")
    with lens_col:
        matrix_lens = st.radio(
            "Analyze",
            ["Commodity groups", "Partner markets"],
            horizontal=True,
            key="opportunity_matrix_lens",
            help="Choose whether each point represents an HS commodity group or a named trading partner.",
        )
    matrix_flow_options = []
    if has_both_flows:
        matrix_flow_options.append("Combined flows")
    matrix_flow_options.extend(available_flows)
    if not matrix_flow_options:
        matrix_flow_options = ["Direction not verified"]
    with flow_col:
        matrix_flow = st.selectbox(
            "Trade flow to analyze",
            matrix_flow_options,
            index=0,
            key="opportunity_matrix_flow",
            help="When both Imports and Exports are loaded, inspect them separately or choose Combined flows. Unknown direction is never inferred.",
        )
    with growth_col:
        growth_threshold = st.slider(
            "Growth threshold (%)",
            min_value=-50,
            max_value=200,
            value=0,
            step=5,
            key="opportunity_growth_threshold",
            help="The horizontal divider. Above-threshold means growth is at or above this selected percentage.",
        )

    coverage = "All named markets"
    if matrix_lens == "Partner markets":
        cov_col, label_col = st.columns([1.2, 1], gap="medium")
        with cov_col:
            coverage = st.selectbox(
                "Partner coverage",
                ["All named markets", f"Top {top_partner_count} by current value"],
                index=0,
                key="opportunity_partner_coverage",
                help="All named markets helps reveal smaller but fast-growing markets. Top N simplifies the display to the largest current values.",
            )
        with label_col:
            label_points = st.checkbox(
                "Label points on chart",
                value=False,
                key="opportunity_label_points",
                help="For partner markets, labels are limited to a small set to avoid chart clutter. Hover over any point for the full details.",
            )
    else:
        label_points = st.checkbox(
            "Label points on chart",
            value=True,
            key="opportunity_label_points_commodities",
            help="Commodity labels are short enough to show directly on the chart.",
        )

    matrix_current = current.copy()
    matrix_prior = prior.copy()
    if matrix_flow != "Combined flows":
        matrix_current = matrix_current[matrix_current["Trade Flow"] == matrix_flow].copy()
        matrix_prior = matrix_prior[matrix_prior["Trade Flow"] == matrix_flow].copy()

    if matrix_lens == "Commodity groups":
        cur_entities = (
            matrix_current.groupby(["Commodity", "Commodity Category"], as_index=False)["Value_USD_Mn"]
            .sum()
            .rename(columns={"Commodity": "Entity", "Value_USD_Mn": "Current_Mn"})
        )
        prior_entities = (
            matrix_prior.groupby(["Commodity"], as_index=False)["Value_USD_Mn"]
            .sum()
            .rename(columns={"Commodity": "Entity", "Value_USD_Mn": "Prior_Mn"})
        )
        entity_type_label = "commodity groups"
    else:
        cur_named = named_rows(matrix_current)
        prior_named = named_rows(matrix_prior)
        cur_entities = (
            cur_named.groupby("DisplayCountry", as_index=False)["Value_USD_Mn"]
            .sum()
            .rename(columns={"DisplayCountry": "Entity", "Value_USD_Mn": "Current_Mn"})
        )
        prior_entities = (
            prior_named.groupby("DisplayCountry", as_index=False)["Value_USD_Mn"]
            .sum()
            .rename(columns={"DisplayCountry": "Entity", "Value_USD_Mn": "Prior_Mn"})
        )
        entity_type_label = "named partner markets"

    matrix_df = cur_entities.merge(prior_entities, on="Entity", how="left")
    if "Prior_Mn" not in matrix_df.columns:
        matrix_df["Prior_Mn"] = np.nan
    matrix_df["Prior_Mn"] = pd.to_numeric(matrix_df["Prior_Mn"], errors="coerce")
    matrix_df["Current_Mn"] = pd.to_numeric(matrix_df["Current_Mn"], errors="coerce").fillna(0)
    matrix_df["Current_USD_Bn"] = matrix_df["Current_Mn"] / 1000
    matrix_df["Prior_USD_Bn"] = matrix_df["Prior_Mn"] / 1000
    matrix_df["YoY change (%)"] = np.where(
        matrix_df["Prior_Mn"] > 0,
        (matrix_df["Current_Mn"] / matrix_df["Prior_Mn"] - 1) * 100,
        np.nan,
    )

    # Optional top-N view is applied after the partner aggregates are created.
    if matrix_lens == "Partner markets" and coverage.startswith("Top "):
        matrix_limit = int(re.search(r"Top (\d+)", coverage).group(1))
        matrix_df = matrix_df.nlargest(matrix_limit, "Current_Mn").copy()

    # Growth is not meaningful when the comparable prior-period denominator is zero or missing.
    assessed = matrix_df[matrix_df["Prior_Mn"].gt(0) & matrix_df["YoY change (%)"].notna()].copy()
    unassessed_count = int(len(matrix_df) - len(assessed))

    if assessed.empty:
        st.warning(
            f"There is no positive comparable prior-year baseline for these {entity_type_label} in {selected_year}. "
            "Choose a year with prior-year data or broaden the current filters to build the opportunity matrix."
        )
        current_rank = matrix_df.sort_values("Current_Mn", ascending=False).head(15).copy()
        if not current_rank.empty:
            current_rank["Recorded value (US$ B)"] = current_rank["Current_USD_Bn"]
            st.dataframe(
                current_rank[["Entity", "Recorded value (US$ B)"]],
                use_container_width=True,
                hide_index=True,
                column_config={"Recorded value (US$ B)": st.column_config.NumberColumn(format="$%.3fB")},
            )
    else:
        value_threshold = float(assessed["Current_USD_Bn"].median())
        assessed["Value segment"] = np.where(
            assessed["Current_USD_Bn"] >= value_threshold,
            "Higher value",
            "Lower value",
        )
        assessed["Growth segment"] = np.where(
            assessed["YoY change (%)"] >= growth_threshold,
            "Above threshold",
            "Below threshold",
        )
        assessed["Quadrant"] = assessed.apply(
            lambda row: f"{row['Value segment']} · {row['Growth segment']}", axis=1
        )
        quadrant_colors = {
            "Higher value · Above threshold": "#23745B",
            "Higher value · Below threshold": "#365B78",
            "Lower value · Above threshold": "#E46F4A",
            "Lower value · Below threshold": "#83919B",
        }

        priority_entities = assessed[
            (assessed["Current_USD_Bn"] >= value_threshold)
            & (assessed["YoY change (%)"] >= growth_threshold)
        ].copy()
        value_leader = assessed.loc[assessed["Current_USD_Bn"].idxmax()]
        growth_leader = assessed.loc[assessed["YoY change (%)"].idxmax()]

        k1, k2, k3, k4 = st.columns(4, gap="medium")
        with k1:
            kpi_card("ENTITIES ASSESSED", f"{len(assessed):,}", f"Comparable {selected_year} vs {prior_year}", TEAL)
        with k2:
            kpi_card("HIGHER VALUE + ABOVE THRESHOLD", f"{len(priority_entities):,}", f"Growth ≥ {growth_threshold:.0f}% and value ≥ median", GREEN)
        with k3:
            kpi_card("VALUE LEADER", str(value_leader["Entity"]), fmt_money_mn(value_leader["Current_Mn"]), "#365B78")
        with k4:
            kpi_card("FASTEST COMPARABLE GROWTH", fmt_pct(growth_leader["YoY change (%)"]), str(growth_leader["Entity"]), "#E0B15A")

        st.write("")
        chart_left, chart_right = st.columns([1.55, 1], gap="large")
        with chart_left:
            section(
                "OPPORTUNITY SCATTER",
                "Value versus year-on-year change",
                f"Vertical line = median value ({fmt_money_bn(value_threshold)}); horizontal line = selected growth threshold ({growth_threshold:.0f}%). Bubble size reflects current-period recorded value."
            )
            plot_df = assessed.copy()
            # Keep this column present for Plotly's hover schema even when labels are off.
            plot_df["Plot label"] = ""
            # To keep the partner view readable, label only the 12 largest entities if requested.
            if label_points and matrix_lens == "Partner markets":
                label_entities = set(plot_df.nlargest(12, "Current_Mn")["Entity"].tolist())
                plot_df["Plot label"] = plot_df["Entity"].where(plot_df["Entity"].isin(label_entities), "")
                text_arg = "Plot label"
            elif label_points:
                plot_df["Plot label"] = plot_df["Entity"]
                text_arg = "Plot label"
            else:
                text_arg = None

            fig = px.scatter(
                plot_df,
                x="Current_USD_Bn",
                y="YoY change (%)",
                size="Current_USD_Bn",
                color="Quadrant",
                text=text_arg,
                hover_name="Entity",
                hover_data={
                    "Current_USD_Bn": ":.3f",
                    "Prior_USD_Bn": ":.3f",
                    "YoY change (%)": ":+.1f",
                    "Quadrant": True,
                    "Current_Mn": False,
                    "Prior_Mn": False,
                    "Value segment": False,
                    "Growth segment": False,
                    "Plot label": False,
                },
                size_max=32 if matrix_lens == "Partner markets" else 48,
                color_discrete_map=quadrant_colors,
                labels={
                    "Current_USD_Bn": "Current value (US$ billion)",
                    "YoY change (%)": "YoY change (%)",
                    "Quadrant": "Relative segment",
                    "Prior_USD_Bn": "Comparable prior value (US$ billion)",
                },
            )
            fig.add_vline(x=value_threshold, line_dash="dash", line_color="#68727D", line_width=1.5)
            fig.add_hline(y=growth_threshold, line_dash="dash", line_color="#68727D", line_width=1.5)
            fig.update_traces(marker=dict(opacity=0.83, line=dict(width=1, color="#FFFEFC")))
            if text_arg:
                fig.update_traces(textposition="top center", textfont=dict(size=10, color=NAVY))
            fig.update_layout(
                xaxis_title="Current-period value (US$ billion)",
                yaxis_title="Year-on-year change (%)",
                legend_title_text="Relative segment",
                hovermode="closest",
            )
            fig.update_yaxes(ticksuffix="%", zeroline=True, zerolinecolor="#BFC8CE")
            render_chart(fig, "market_opportunity_matrix_scatter", 500)

        with chart_right:
            section(
                "HOW TO INTERPRET",
                "Read the four quadrants",
                "Quadrants are calculated relative to the selected entities, months, commodities and flow."
            )
            insight_card("01", "HIGHER VALUE · ABOVE THRESHOLD", "Large recorded value with growth at or above the selected threshold. These entities are worth prioritising for deeper review.")
            st.write("")
            insight_card("02", "HIGHER VALUE · BELOW THRESHOLD", "Large recorded value but growth below the selected threshold. Established markets may warrant monitoring.")
            st.write("")
            insight_card("03", "LOWER VALUE · ABOVE THRESHOLD", "Smaller recorded value with growth at or above the threshold. These can be emerging signals, but check the baseline and value size.")
            st.write("")
            insight_card("04", "LOWER VALUE · BELOW THRESHOLD", "Smaller value and growth below the threshold. Review selectively in light of the project or business context.")

        st.write("")
        high_growth_count = int((assessed["YoY change (%)"] >= growth_threshold).sum())
        st.markdown(
            f"<div class='callout'><b>Selected-scope readout:</b> {len(priority_entities)} of {len(assessed)} assessed {entity_type_label} sit in the higher-value / above-threshold quadrant. {high_growth_count} entities are at or above the {growth_threshold:.0f}% growth threshold. These are screening signals only; they do not establish causes or predict future results.</div>",
            unsafe_allow_html=True,
        )
        if unassessed_count > 0:
            st.caption(
                f"{unassessed_count} additional entities were not plotted because the comparable prior-period value was zero or missing. Growth percentages are not defined for those records."
            )

        section(
            "OPPORTUNITY TABLE",
            "Inspect and export every point",
            "Sort by current value or growth to investigate the strongest signals."
        )
        display_matrix = assessed.copy()
        display_matrix = display_matrix.rename(columns={
            "Entity": "Commodity / market",
            "Current_USD_Bn": "Current value (US$ B)",
            "Prior_USD_Bn": "Comparable prior value (US$ B)",
        })
        display_matrix = display_matrix[[
            "Commodity / market", "Current value (US$ B)", "Comparable prior value (US$ B)",
            "YoY change (%)", "Quadrant"
        ]].sort_values(["Quadrant", "Current value (US$ B)"], ascending=[True, False])
        st.dataframe(
            display_matrix,
            use_container_width=True,
            hide_index=True,
            height=compact_height(len(display_matrix), max_height=520),
            column_config={
                "Current value (US$ B)": st.column_config.NumberColumn(format="$%.3fB"),
                "Comparable prior value (US$ B)": st.column_config.NumberColumn(format="$%.3fB"),
                "YoY change (%)": st.column_config.NumberColumn(format="%+.1f%%"),
            },
        )
        st.download_button(
            "Download opportunity matrix as CSV",
            data=display_matrix.to_csv(index=False).encode("utf-8"),
            file_name=f"petrotrade_opportunity_matrix_{selected_year}.csv",
            mime="text/csv",
            type="primary",
        )

# =============================================================================
# PAGE 4: MARKET CONCENTRATION & RISK ANALYSIS
# =============================================================================
elif page == "Concentration & risk":
    section(
        "MARKET CONCENTRATION & RISK",
        "How dependent is each commodity on a small set of markets?",
        "Measure how recorded values are distributed across named partner markets, compare concentration with the comparable period, and flag commodity groups for further review."
    )
    st.markdown(
        "<div class='info-panel'><b>What this analysis measures:</b> concentration of recorded value across named country labels. Top-3 and top-5 shares show how much value sits with the largest markets; HHI is the sum of squared market shares (shares expressed as percentages), on a 0–10,000 scale. These are screening indicators, not predictions or formal legal risk assessments.</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='callout'><b>Scope note:</b> concentration must be calculated across all named markets. This page intentionally ignores the single <i>Partner market</i> choice in the global controls, otherwise a one-country filter would make that country appear to represent 100% of the market. Commodity, category, year and month selections still apply.</div>",
        unsafe_allow_html=True,
    )

    risk_flow_options = []
    if has_both_flows:
        risk_flow_options.append("Combined flows")
    risk_flow_options.extend(available_flows)
    if not risk_flow_options:
        risk_flow_options = ["Direction not verified"]
    if "Imports" in risk_flow_options:
        default_risk_flow = "Imports"
    elif "Direction not verified" in risk_flow_options:
        default_risk_flow = "Direction not verified"
    else:
        default_risk_flow = risk_flow_options[0]

    risk_ctrl1, risk_ctrl2, risk_ctrl3 = st.columns([1.2, 1, 1], gap="medium")
    with risk_ctrl1:
        risk_flow = st.selectbox(
            "Trade flow for concentration analysis",
            risk_flow_options,
            index=risk_flow_options.index(default_risk_flow),
            key="risk_analysis_flow",
            help="Imports can indicate supplier exposure; exports can indicate destination exposure. If direction is unverified, results are only described as recorded-value concentration.",
        )
    with risk_ctrl2:
        top5_flag_threshold = st.slider(
            "Flag top-5 share at or above (%)",
            min_value=30,
            max_value=95,
            value=45,
            step=5,
            key="risk_top5_threshold",
            help="A user-defined screening threshold, not an official risk or regulatory cutoff.",
        )
    with risk_ctrl3:
        hhi_flag_threshold = st.slider(
            "Flag HHI at or above",
            min_value=500,
            max_value=8000,
            value=600,
            step=100,
            key="risk_hhi_threshold",
            help="A user-defined screening threshold on the 0–10,000 HHI scale.",
        )

    # Build the risk scope independently of the global partner-market filter.
    risk_scope = data[
        data["Commodity"].isin(selected_commodities)
        & data["Commodity Category"].isin(selected_categories)
        & data["MonthNum"].isin(months_present)
    ].copy()
    risk_current = risk_scope[risk_scope["Year"] == selected_year].copy()
    risk_prior = risk_scope[risk_scope["Year"] == prior_year].copy()
    if risk_flow != "Combined flows":
        risk_current = risk_current[risk_current["Trade Flow"] == risk_flow].copy()
        risk_prior = risk_prior[risk_prior["Trade Flow"] == risk_flow].copy()

    risk_current_named = named_rows(risk_current)
    risk_prior_named = named_rows(risk_prior)

    def concentration_stats(country_values):
        """Compute concentration measures from positive named-market values."""
        clean = country_values.copy()
        if clean.empty:
            return {
                "Total_Mn": np.nan, "Named markets": 0, "Largest market": "—",
                "Top-1 share (%)": np.nan, "Top-3 share (%)": np.nan,
                "Top-5 share (%)": np.nan, "HHI": np.nan,
            }
        clean = clean.groupby("DisplayCountry", as_index=False)["Value_USD_Mn"].sum()
        clean = clean[clean["Value_USD_Mn"] > 0].sort_values("Value_USD_Mn", ascending=False)
        total = float(clean["Value_USD_Mn"].sum())
        if total <= 0 or clean.empty:
            return {
                "Total_Mn": total, "Named markets": 0, "Largest market": "—",
                "Top-1 share (%)": np.nan, "Top-3 share (%)": np.nan,
                "Top-5 share (%)": np.nan, "HHI": np.nan,
            }
        shares = clean["Value_USD_Mn"] / total * 100
        return {
            "Total_Mn": total,
            "Named markets": int(clean["DisplayCountry"].nunique()),
            "Largest market": str(clean.iloc[0]["DisplayCountry"]),
            "Top-1 share (%)": float(shares.head(1).sum()),
            "Top-3 share (%)": float(shares.head(3).sum()),
            "Top-5 share (%)": float(shares.head(5).sum()),
            "HHI": float((shares ** 2).sum()),
        }

    def summarize_by_commodity(frame):
        if frame.empty:
            return pd.DataFrame(columns=[
                "Commodity", "Total_Mn", "Named markets", "Largest market",
                "Top-1 share (%)", "Top-3 share (%)", "Top-5 share (%)", "HHI"
            ])
        rows = []
        for commodity_name, group in frame.groupby("Commodity"):
            stats = concentration_stats(group)
            stats["Commodity"] = commodity_name
            rows.append(stats)
        return pd.DataFrame(rows)

    if risk_current_named.empty:
        st.warning("No named partner-market records are available for this flow and selection. Widen the commodity or period filters, or verify the dataset direction.")
    else:
        risk_now_summary = summarize_by_commodity(risk_current_named)
        risk_prev_summary = summarize_by_commodity(risk_prior_named)
        if risk_prev_summary.empty:
            risk_prev_summary = pd.DataFrame(columns=["Commodity", "Top-5 share (%)", "HHI"])
        risk_prev_summary = risk_prev_summary.rename(columns={
            "Top-5 share (%)": "Prior top-5 share (%)",
            "HHI": "Prior HHI",
        })
        risk_summary = risk_now_summary.merge(
            risk_prev_summary[[c for c in ["Commodity", "Prior top-5 share (%)", "Prior HHI"] if c in risk_prev_summary.columns]],
            on="Commodity", how="left"
        )
        risk_summary["Top-5 share change (pp)"] = risk_summary["Top-5 share (%)"] - risk_summary["Prior top-5 share (%)"]
        risk_summary["HHI change"] = risk_summary["HHI"] - risk_summary["Prior HHI"]

        def risk_flag(row):
            high_top5 = pd.notna(row["Top-5 share (%)"]) and row["Top-5 share (%)"] >= top5_flag_threshold
            high_hhi = pd.notna(row["HHI"]) and row["HHI"] >= hhi_flag_threshold
            if high_top5 and high_hhi:
                return "Flagged on both measures"
            if high_top5:
                return "Flagged: top-5 share"
            if high_hhi:
                return "Flagged: HHI"
            return "Below selected thresholds"

        def concentration_movement(row):
            hhi_delta = row.get("HHI change", np.nan)
            top5_delta = row.get("Top-5 share change (pp)", np.nan)
            if pd.isna(hhi_delta) and pd.isna(top5_delta):
                return "No comparable baseline"
            if pd.notna(hhi_delta) and hhi_delta >= 100:
                return "Concentration rising"
            if pd.notna(hhi_delta) and hhi_delta <= -100:
                return "Concentration easing"
            if pd.notna(top5_delta) and top5_delta >= 3:
                return "Top-5 share rising"
            if pd.notna(top5_delta) and top5_delta <= -3:
                return "Top-5 share easing"
            return "Broadly stable"

        risk_summary["Screening signal"] = risk_summary.apply(risk_flag, axis=1)
        risk_summary["YoY concentration movement"] = risk_summary.apply(concentration_movement, axis=1)
        risk_summary["Total value (US$ B) in scope"] = risk_summary["Total_Mn"] / 1000

        portfolio_now = concentration_stats(risk_current_named)
        portfolio_prev = concentration_stats(risk_prior_named)
        portfolio_top5_change = (
            portfolio_now["Top-5 share (%)"] - portfolio_prev["Top-5 share (%)"]
            if pd.notna(portfolio_now["Top-5 share (%)"]) and pd.notna(portfolio_prev["Top-5 share (%)"])
            else np.nan
        )
        portfolio_hhi_change = (
            portfolio_now["HHI"] - portfolio_prev["HHI"]
            if pd.notna(portfolio_now["HHI"]) and pd.notna(portfolio_prev["HHI"])
            else np.nan
        )

        flagged_count = int(risk_summary["Screening signal"].str.startswith("Flagged").sum())
        metric_cols = st.columns(4, gap="medium")
        with metric_cols[0]:
            kpi_card("TOP-5 MARKET SHARE", f"{portfolio_now['Top-5 share (%)']:.1f}%" if pd.notna(portfolio_now["Top-5 share (%)"]) else "—", "Across named partner values", TEAL)
        with metric_cols[1]:
            kpi_card("PORTFOLIO HHI", f"{portfolio_now['HHI']:,.0f}" if pd.notna(portfolio_now["HHI"]) else "—", "0–10,000 index; descriptive", "#365B78")
        with metric_cols[2]:
            kpi_card("COMMODITIES FLAGGED", f"{flagged_count} / {len(risk_summary)}", f"Top-5 ≥ {top5_flag_threshold}% or HHI ≥ {hhi_flag_threshold:,}", RED if flagged_count else GREEN)
        with metric_cols[3]:
            kpi_card("TOP-5 SHARE CHANGE", f"{portfolio_top5_change:+.1f} pp" if pd.notna(portfolio_top5_change) else "—", f"Vs. comparable months in {prior_year}", RED if pd.notna(portfolio_top5_change) and portfolio_top5_change > 0 else GREEN)

        st.write("")
        section(
            "CONCENTRATION PROFILE",
            "Which commodity groups rely on the fewest partner markets?",
            "Top-5 share and HHI summarize the partner-value distribution within each commodity. The thresholds below are editable screening settings, not official classifications."
        )
        chart_left, chart_right = st.columns([1.1, 1], gap="large")
        with chart_left:
            top5_plot = risk_summary.sort_values("Top-5 share (%)", ascending=True).copy()
            top5_plot["Threshold status"] = np.where(top5_plot["Top-5 share (%)"] >= top5_flag_threshold, "At / above threshold", "Below threshold")
            fig = px.bar(
                top5_plot, x="Top-5 share (%)", y="Commodity", orientation="h",
                color="Threshold status",
                color_discrete_map={"At / above threshold": RED, "Below threshold": "#6E9F93"},
                text="Top-5 share (%)",
                labels={"Top-5 share (%)": "Top-5 share (%)", "Commodity": "Commodity group"},
            )
            fig.add_vline(x=top5_flag_threshold, line_dash="dash", line_color=NAVY, line_width=1.4)
            fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside", cliponaxis=False, hovertemplate="%{y}<br>Top-5 share: %{x:.1f}%<extra></extra>")
            fig.update_layout(xaxis_range=[0, min(110, max(100, float(top5_plot["Top-5 share (%)"].max()) + 12))], xaxis_title="Top-5 named-market share", yaxis_title="", legend_title_text="")
            render_chart(fig, "risk_top5_share_by_commodity", 380)
        with chart_right:
            hhi_plot = risk_summary.sort_values("HHI", ascending=True).copy()
            hhi_plot["Threshold status"] = np.where(hhi_plot["HHI"] >= hhi_flag_threshold, "At / above threshold", "Below threshold")
            fig = px.bar(
                hhi_plot, x="HHI", y="Commodity", orientation="h",
                color="Threshold status",
                color_discrete_map={"At / above threshold": RED, "Below threshold": "#365B78"},
                text="HHI",
                labels={"HHI": "HHI (0–10,000)", "Commodity": "Commodity group"},
            )
            fig.add_vline(x=hhi_flag_threshold, line_dash="dash", line_color=NAVY, line_width=1.4)
            fig.update_traces(texttemplate="%{text:.0f}", textposition="outside", cliponaxis=False, hovertemplate="%{y}<br>HHI: %{x:.0f}<extra></extra>")
            hhi_max_value = float(hhi_plot["HHI"].max()) if hhi_plot["HHI"].notna().any() else float(hhi_flag_threshold)
            hhi_axis_max = min(10000, max(1000, max(hhi_max_value, float(hhi_flag_threshold)) * 1.15))
            fig.update_layout(xaxis_range=[0, hhi_axis_max], xaxis_title="HHI (squared percentage shares)", yaxis_title="", legend_title_text="")
            render_chart(fig, "risk_hhi_by_commodity", 380)

        st.write("")
        section(
            "PARTNER DEPENDENCY MAP",
            "Which named markets contribute to each commodity?",
            "Each horizontal bar totals 100%. The five largest named markets across the selected scope are shown separately; the remaining named markets are combined as Other."
        )
        partner_commodity = (
            risk_current_named.groupby(["Commodity", "DisplayCountry"], as_index=False)["Value_USD_Mn"]
            .sum()
        )
        partner_commodity = partner_commodity[partner_commodity["Value_USD_Mn"] > 0].copy()
        if not partner_commodity.empty:
            top_global_markets = (
                partner_commodity.groupby("DisplayCountry")["Value_USD_Mn"].sum()
                .nlargest(5).index.tolist()
            )
            mix_rows = []
            for commodity_name, group in partner_commodity.groupby("Commodity"):
                total = float(group["Value_USD_Mn"].sum())
                if total <= 0:
                    continue
                values = group.set_index("DisplayCountry")["Value_USD_Mn"]
                assigned = 0.0
                for market_name in top_global_markets:
                    value = float(values.get(market_name, 0.0))
                    assigned += value
                    mix_rows.append({"Commodity": commodity_name, "Market segment": market_name, "Share (%)": value / total * 100})
                other_value = max(0.0, total - assigned)
                mix_rows.append({"Commodity": commodity_name, "Market segment": "Other named markets", "Share (%)": other_value / total * 100})
            mix_df = pd.DataFrame(mix_rows)
            mix_colors = {market: PALETTE[i % len(PALETTE)] for i, market in enumerate(top_global_markets)}
            mix_colors["Other named markets"] = "#C8C9C3"
            fig = px.bar(
                mix_df, x="Share (%)", y="Commodity", color="Market segment", orientation="h", barmode="stack",
                color_discrete_map=mix_colors,
                category_orders={"Market segment": top_global_markets + ["Other named markets"]},
                labels={"Commodity": "Commodity group", "Share (%)": "Share of commodity value (%)"},
            )
            fig.update_layout(xaxis_range=[0, 100], xaxis_ticksuffix="%", xaxis_title="Share of commodity value", yaxis_title="", legend_title_text="Named market")
            fig.update_traces(hovertemplate="%{y}<br>%{fullData.name}: %{x:.1f}%<extra></extra>")
            render_chart(fig, "risk_partner_mix_by_commodity", 410)
        else:
            st.info("Partner contribution chart is unavailable because no positive named-market values exist for the selected scope.")

        st.write("")
        section(
            "RISK REGISTER",
            "Inspect and export concentration signals",
            "Top-1/3/5 shares are calculated from positive values for named markets only. HHI = sum of each market's percentage share squared."
        )
        show_risk = risk_summary.sort_values(["Screening signal", "HHI"], ascending=[True, False]).copy()
        risk_display = show_risk[[
            "Commodity", "Total value (US$ B) in scope", "Named markets", "Largest market",
            "Top-1 share (%)", "Top-3 share (%)", "Top-5 share (%)", "HHI",
            "HHI change", "Top-5 share change (pp)", "YoY concentration movement", "Screening signal"
        ]].rename(columns={
            "Total value (US$ B) in scope": "Recorded value (US$ B)",
            "HHI change": "HHI change vs prior",
            "Top-5 share change (pp)": "Top-5 change (pp)",
        })
        st.dataframe(
            risk_display,
            use_container_width=True,
            hide_index=True,
            height=compact_height(len(risk_display), max_height=460),
            column_config={
                "Recorded value (US$ B)": st.column_config.NumberColumn(format="$%.3fB"),
                "Top-1 share (%)": st.column_config.NumberColumn(format="%.1f%%"),
                "Top-3 share (%)": st.column_config.NumberColumn(format="%.1f%%"),
                "Top-5 share (%)": st.column_config.NumberColumn(format="%.1f%%"),
                "HHI": st.column_config.NumberColumn(format="%.0f"),
                "HHI change vs prior": st.column_config.NumberColumn(format="%+.0f"),
                "Top-5 change (pp)": st.column_config.NumberColumn(format="%+.1f"),
            },
        )
        st.download_button(
            "Download concentration & risk register as CSV",
            data=risk_display.to_csv(index=False).encode("utf-8"),
            file_name=f"petrotrade_concentration_risk_{selected_year}.csv",
            mime="text/csv",
            type="primary",
        )
        if risk_flow == "Imports":
            flow_interpretation = "Because the selected flow is Imports, concentration can be interpreted as a descriptive signal of supplier-market exposure in this dataset. It does not by itself measure disruption probability or supplier substitutability."
        elif risk_flow == "Exports":
            flow_interpretation = "Because the selected flow is Exports, concentration can be interpreted as a descriptive signal of destination-market exposure in this dataset. It does not by itself establish demand risk."
        elif risk_flow == "Combined flows":
            flow_interpretation = "The selected view combines imports and exports. Treat this as overall recorded-value concentration, not supplier dependency or export-destination dependency."
        else:
            flow_interpretation = "The direction of the selected flow is unverified. Results describe named-market concentration in recorded values only and should not be described as supplier or destination dependency."
        st.markdown(
            f"<div class='callout'><b>Interpretation guardrail:</b> {safe(flow_interpretation)} The top-5 and HHI thresholds are analyst-defined screening settings. They flag records for investigation; they do not prove that a commodity is risky.</div>",
            unsafe_allow_html=True,
        )

# =============================================================================
# PAGE 5: IMPORTS VS EXPORTS
# =============================================================================
elif page == "Imports vs exports":
    section("TRADE-FLOW COMPARISON", "See imports, exports and net trade position", "This page requires flow-specific datasets. The app does not infer import/export direction from the value columns.")
    st.markdown(
        "<div class='info-panel'><b>Definitions:</b> Imports are goods brought into the country; exports are goods sent out of the country. For this dashboard, <b>trade balance = exports − imports</b>. A positive balance means exports exceed imports for the selected commodity group and period; a negative balance means imports exceed exports.</div>",
        unsafe_allow_html=True,
    )

    if has_both_flows:
        imports_mn = current.loc[current["Trade Flow"] == "Imports", "Value_USD_Mn"].sum()
        exports_mn = current.loc[current["Trade Flow"] == "Exports", "Value_USD_Mn"].sum()
        balance_mn = exports_mn - imports_mn
        import_share = imports_mn / (imports_mn + exports_mn) * 100 if (imports_mn + exports_mn) > 0 else np.nan
        a, b, c, d = st.columns(4, gap="medium")
        with a:
            kpi_card("IMPORTS", fmt_money_mn(imports_mn), period_label, "#365B78")
        with b:
            kpi_card("EXPORTS", fmt_money_mn(exports_mn), period_label, TEAL)
        with c:
            kpi_card("TRADE BALANCE", fmt_money_mn(balance_mn), "Exports − imports", GREEN if balance_mn >= 0 else RED)
        with d:
            kpi_card("IMPORT SHARE", f"{import_share:.1f}%" if pd.notna(import_share) else "—", "Of combined import + export value", "#E0B15A")

        st.write("")
        flow_by_commodity = current[current["Trade Flow"].isin(["Imports", "Exports"])].groupby(["Commodity", "Trade Flow"], as_index=False)["Value_USD_Bn"].sum()
        left, right = st.columns([1.15, 1], gap="large")
        with left:
            fig = px.bar(flow_by_commodity, x="Commodity", y="Value_USD_Bn", color="Trade Flow", barmode="group", color_discrete_map={"Imports": "#365B78", "Exports": TEAL},
                         labels={"Value_USD_Bn": "Value (US$ billion)", "Commodity": "Commodity group"})
            fig.update_layout(xaxis_title="Commodity group", yaxis_title="Value (US$ billion)")
            render_chart(fig, "flow_import_export_commodity", 420)
        with right:
            balances = flow_by_commodity.pivot(index="Commodity", columns="Trade Flow", values="Value_USD_Bn").fillna(0)
            balances["Balance"] = balances.get("Exports", 0) - balances.get("Imports", 0)
            balances = balances.reset_index().sort_values("Balance")
            fig = px.bar(balances, x="Balance", y="Commodity", orientation="h", color="Balance", color_continuous_scale=[RED, "#ECE8E0", GREEN],
                         labels={"Balance": "Net balance (US$ billion)", "Commodity": "Commodity group"})
            fig.add_vline(x=0, line_dash="dash", line_color="#68727D")
            fig.update_layout(coloraxis_showscale=False, xaxis_title="Exports minus imports (US$ billion)", yaxis_title="")
            render_chart(fig, "flow_trade_balance", 420, legend=False)

        st.write("")
        section("MONTHLY FLOW MOVEMENT", "Do imports and exports follow the same monthly pattern?", "Use the legend to focus on a flow. Hover over a point to inspect the month's value.")
        monthly_flow = current.groupby(["MonthNum", "Month", "Trade Flow"], as_index=False)["Value_USD_Bn"].sum()
        fig = px.line(monthly_flow, x="Month", y="Value_USD_Bn", color="Trade Flow", markers=True,
                      category_orders={"Month": month_labels}, color_discrete_map={"Imports": "#365B78", "Exports": TEAL},
                      labels={"Value_USD_Bn": "Value (US$ billion)", "Month": "Month"})
        fig.update_traces(line_width=3, marker_size=8)
        fig.update_layout(hovermode="x unified", legend_title_text="")
        render_chart(fig, "flow_monthly_trend", 380)
    else:
        st.warning("Both flow-specific datasets are needed to calculate imports, exports and trade balance. The current values are not automatically labelled as imports or exports.")
        st.markdown("""
        **How to enable this page**

        1. Confirm the direction used for your existing `DGCIS_DATA.csv` download.
        2. In the left sidebar, choose **Imports** or **Exports** for that file.
        3. Download the opposite flow from DGCIS using matching HS chapters and the same period, then upload it in the corresponding **Import dataset CSV** or **Export dataset CSV** field.
        4. Keep the same HS chapters (27, 28, 29, 39 and 40) and compare like-for-like months.

        Once both are available, this page displays imports, exports, net trade balance, commodity comparisons and monthly trends.
        """)
        available_summary = current.groupby(["Commodity", "Trade Flow"], as_index=False)["Value_USD_Bn"].sum().sort_values("Value_USD_Bn", ascending=False)
        if not available_summary.empty:
            fig = px.bar(available_summary, x="Value_USD_Bn", y="Commodity", color="Trade Flow", orientation="h", color_discrete_sequence=PALETTE,
                         labels={"Value_USD_Bn": "Recorded value (US$ billion)", "Commodity": "Commodity group"})
            fig.update_layout(xaxis_title="Recorded value (US$ billion)", yaxis_title="")
            render_chart(fig, "flow_available_only", 350)

# =============================================================================
# PAGE 5: PARTNER MARKETS
# =============================================================================
elif page == "Partner markets":
    section("PARTNER EXPLORER", "Understand which markets drive recorded value", "Choose a partner to inspect its monthly trajectory, commodity mix, and year-on-year movement.")
    partner_options_df = partner_totals.copy()
    if partner_options_df.empty:
        st.info("No named positive-value partner markets are available for this selection.")
    else:
        option_rows = partner_options_df["Country Name"].tolist()
        display_by_country = dict(zip(partner_options_df["Country Name"], partner_options_df["DisplayCountry"]))
        selected_partner = st.selectbox("Choose a partner market", option_rows, index=0, format_func=lambda c: display_by_country.get(c, c))
        market_current = named_current[named_current["Country Name"] == selected_partner].copy()
        market_prior = named_prior[named_prior["Country Name"] == selected_partner].copy()
        market_value = market_current["Value_USD_Mn"].sum()
        market_prev_value = market_prior["Value_USD_Mn"].sum()
        market_yoy = (market_value / market_prev_value - 1) * 100 if market_prev_value > 0 else np.nan
        market_share = market_value / partner_sum * 100 if partner_sum > 0 else np.nan
        mc1, mc2, mc3, mc4 = st.columns(4, gap="medium")
        with mc1:
            kpi_card("PARTNER VALUE", fmt_money_mn(market_value), period_label, TEAL)
        with mc2:
            kpi_card("YEAR-ON-YEAR", fmt_pct(market_yoy), f"Comparable months in {prior_year}", GREEN if pd.notna(market_yoy) and market_yoy >= 0 else RED)
        with mc3:
            kpi_card("SHARE OF NAMED MARKETS", f"{market_share:.1f}%" if pd.notna(market_share) else "—", "Within current filters", "#365B78")
        with mc4:
            market_commodity = market_current.groupby("Commodity")["Value_USD_Mn"].sum().sort_values(ascending=False)
            kpi_card("TOP COMMODITY", market_commodity.index[0] if not market_commodity.empty else "—", fmt_money_mn(market_commodity.iloc[0]) if not market_commodity.empty else "No value", "#E0B15A")

        left, right = st.columns([1.15, 1], gap="large")
        with left:
            market_monthly = []
            for frame, name in [(market_prior, f"{prior_year} · comparable"), (market_current, f"{selected_year}{' · YTD' if partial else ''}")]:
                if not frame.empty:
                    mm = frame.groupby(["MonthNum", "Month"], as_index=False)["Value_USD_Bn"].sum()
                    mm["Period"] = name
                    market_monthly.append(mm)
            if market_monthly:
                trend = pd.concat(market_monthly, ignore_index=True)
                fig = px.line(trend, x="Month", y="Value_USD_Bn", color="Period", markers=True,
                              category_orders={"Month": month_labels}, color_discrete_sequence=["#B7C1CA", TEAL],
                              labels={"Value_USD_Bn": "Value (US$ billion)", "Month": "Month"})
                fig.update_traces(line_width=3, marker_size=7)
                fig.update_layout(hovermode="x unified", legend_title_text="")
                render_chart(fig, "partner_monthly_trend", 370)
        with right:
            market_commodity = market_current.groupby("Commodity", as_index=False)["Value_USD_Bn"].sum().sort_values("Value_USD_Bn")
            if not market_commodity.empty:
                fig = px.bar(market_commodity, x="Value_USD_Bn", y="Commodity", orientation="h", color="Commodity", color_discrete_sequence=PALETTE,
                             labels={"Value_USD_Bn": "Value (US$ billion)", "Commodity": "Commodity group"})
                fig.update_layout(showlegend=False, xaxis_title="Value (US$ billion)", yaxis_title="")
                render_chart(fig, "partner_commodity_mix", 370, legend=False)

        st.write("")
        section("MARKET RANKING", "Compare the largest named partner markets", "The table and chart exclude aggregate or unspecified country labels.")
        top = partner_totals.head(15).sort_values("Value_USD_Mn")
        top["Value_USD_Bn"] = top["Value_USD_Mn"] / 1000
        fig = px.bar(top, x="Value_USD_Bn", y="DisplayCountry", orientation="h", color="Value_USD_Bn", color_continuous_scale=["#F8D6CA", TEAL, NAVY],
                     labels={"Value_USD_Bn": "Value (US$ billion)", "DisplayCountry": "Partner market"})
        fig.update_layout(coloraxis_showscale=False, yaxis_title="", xaxis_title="Value (US$ billion)")
        render_chart(fig, "partner_ranking", 470, legend=False)

        compare_rows = []
        for commodity in selected_commodities:
            cv = market_current.loc[market_current["Commodity"] == commodity, "Value_USD_Mn"].sum()
            pv = market_prior.loc[market_prior["Commodity"] == commodity, "Value_USD_Mn"].sum()
            compare_rows.append({"Commodity": commodity, "Selected period (US$ B)": cv / 1000, "Comparable prior (US$ B)": pv / 1000, "YoY change (%)": (cv / pv - 1) * 100 if pv > 0 else np.nan})
        compare = pd.DataFrame(compare_rows)
        st.dataframe(compare, use_container_width=True, hide_index=True, height=compact_height(len(compare), max_height=320),
                     column_config={"Selected period (US$ B)": st.column_config.NumberColumn(format="$%.2fB"), "Comparable prior (US$ B)": st.column_config.NumberColumn(format="$%.2fB"), "YoY change (%)": st.column_config.NumberColumn(format="%.1f%%")})

# =============================================================================
# PAGE 6: DATA & METHODOLOGY
# =============================================================================
else:
    section("DATA & METHODOLOGY", "Inspect, validate and export the underlying records", "Use this page to check the data behind the visuals and download a filtered extract for further analysis.")
    st.markdown(
        "<div class='info-panel'><b>How the dashboard calculates values:</b> each monthly USD million column is reshaped into one row per HS chapter, partner, month, and flow. The app removes aggregate TOTAL country rows, maps the five selected HS chapters to readable commodity labels, and converts USD million to USD billion for selected charts. Year-on-year comparisons use matching months.</div>",
        unsafe_allow_html=True,
    )
    search = st.text_input("Search country, commodity, category or HS code", placeholder="e.g. United States, plastics, chemical intermediates, 39")
    table = current[["Date", "Year", "Trade Flow", "Country Name", "HS Code", "HS Description", "Commodity", "Commodity Category", "Value_USD_Mn"]].copy()
    table = table.rename(columns={"Value_USD_Mn": "Value (US$ million)"})
    if search.strip():
        query = search.strip().casefold()
        searchable = ["Country Name", "HS Description", "Commodity", "Commodity Category", "HS Code", "Trade Flow"]
        mask = pd.Series(False, index=table.index)
        for col in searchable:
            mask = mask | table[col].astype(str).str.casefold().str.contains(query, na=False)
        table = table[mask]
    table = table.sort_values("Value (US$ million)", ascending=False)

    a, b, c = st.columns(3, gap="medium")
    with a:
        kpi_card("ROWS IN CURRENT VIEW", f"{len(table):,}", "After year, commodity and search filters", TEAL)
    with b:
        kpi_card("SOURCE YEARS", f"{min(years)}–{max(years)}", "Available reporting years", "#365B78")
    with c:
        latest_date = data["Date"].max()
        kpi_card("LATEST SOURCE MONTH", latest_date.strftime("%b %Y"), "Latest date present in loaded data", "#E0B15A")

    st.write("")
    with st.expander("Commodity taxonomy and scope", expanded=True):
        tax_rows = []
        for code, info in COMMODITY_INFO.items():
            if info["commodity"] in selected_commodities:
                tax_rows.append({"HS chapter": code, "Commodity group": info["commodity"], "Analytical category": info["category"], "Description / limitation": info["description"]})
        st.dataframe(pd.DataFrame(tax_rows), use_container_width=True, hide_index=True)

    st.markdown("**Definitions and limitations**")
    st.markdown("""
- **HS chapters:** 27 mineral fuels and oils; 28 inorganic chemicals; 29 organic chemicals; 39 plastics and articles; 40 rubber and articles.
- **Analytical category:** a human-readable grouping added by this app to help organize the broad HS chapters; it is not a separate official DGCIS field.
- **Units:** source values are in US$ million; some charts divide by 1,000 and show US$ billion.
- **Import/export direction:** the CSV itself does not identify direction. Only a dataset you explicitly classify as Imports or Exports appears in that flow. Unknown direction is retained as “Direction not verified”.
- **Trade balance:** calculated as exports minus imports only when both datasets are loaded. Missing direction is never silently treated as zero.
- **Partial year:** year-on-year comparison uses the months common to all loaded flows in the selected year and the same months from the prior year.
- **Scope limitation:** these are broad HS chapters related to petroleum, chemicals, plastics and rubber. They are not an exact list of every petrochemical product.
- **Market Opportunity Matrix:** current value is compared with same-month prior-year value. Entities with a positive prior-period denominator receive a year-on-year rate. The horizontal divider is user-selected; the vertical divider is the median current value within the assessed selection. Quadrants are relative screening labels, not recommendations.
- **Interpretation:** trends and concentration measures describe this dataset; they do not establish the causes behind a change or forecast future values.
    """)

    st.write("")
    section("FILTERED RECORDS", "Browse the source observations", f"Showing {len(table):,} filtered rows for the selected period and commodity groups.")
    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        height=480,
        column_config={
            "Date": st.column_config.DateColumn("Month", format="MMM YYYY"),
            "Value (US$ million)": st.column_config.NumberColumn("Value (US$ million)", format="%.3f"),
        },
    )
    st.download_button(
        "Download filtered data as CSV",
        data=table.to_csv(index=False).encode("utf-8"),
        file_name=f"petrotrade_{selected_year}_filtered.csv",
        mime="text/csv",
        type="primary",
    )

st.divider()
st.markdown(
    "<div class='panel-note'>PetroTrade Intelligence · DGCIS CSV supplied for this project. Commodity groups are derived from HS chapters. The app preserves the distinction between imported, exported, and unverified trade-flow data. Use the visible live controls to update the whole workspace. Hover over charts for values; use each chart's modebar to zoom, pan, or download the image.</div>",
    unsafe_allow_html=True,
)
