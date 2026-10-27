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
    initial_sidebar_state="expanded",
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
PALETTE = ["#087E8B", "#315B75", "#6DA9BC", "#D39B49", "#8A9BA8", "#8E79B7"]
TEAL = "#087E8B"
NAVY = "#142B3B"
SLATE = "#667085"
GREEN = "#16794B"
RED = "#C2414B"

st.markdown("""
<style>
:root { color-scheme: light; }
.block-container { padding-top: 1.1rem; padding-bottom: 2.8rem; max-width: 1600px; }
[data-testid="stSidebar"] { background: #F1F5F8; border-right: 1px solid #DCE4EB; }
[data-testid="stSidebar"] > div { padding-top: 1.15rem; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #526579; }
/* Hide Streamlit's toolbar in the local app; config.toml also sets minimal toolbar mode. */
[data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
.eyebrow { font-size: .70rem; letter-spacing: .17em; font-weight: 800; color: #0C8995; text-transform: uppercase; }
.hero { background: linear-gradient(120deg, #102A3A 0%, #183C50 58%, #17616A 100%); color: white; padding: 1.75rem 1.9rem; border-radius: 18px; margin: .1rem 0 1.0rem 0; box-shadow: 0 10px 28px rgba(20,43,59,.10); animation: fadeSlideIn .65s ease both; }
.hero .hero-eyebrow { color: #7BD0D0; font-size: .70rem; font-weight: 800; letter-spacing: .18em; text-transform: uppercase; margin-bottom: .55rem; }
.hero .hero-title { font-size: 2.35rem; font-weight: 850; line-height: 1.08; letter-spacing: -.045em; margin: 0 0 .55rem; }
.hero .hero-sub { max-width: 920px; color: #D4E2EA; font-size: .98rem; line-height: 1.6; }
.hero-meta { display: flex; gap: .55rem; flex-wrap: wrap; margin-top: 1.1rem; }
.hero-chip { display: inline-block; border: 1px solid rgba(255,255,255,.23); color: #E9F5F6; background: rgba(255,255,255,.08); padding: .35rem .65rem; border-radius: 999px; font-size: .73rem; }
/* Radio navigation is used as a compact top navigation bar. */
div[data-testid="stRadio"] { margin: .2rem 0 .85rem; }
div[data-testid="stRadio"] [role="radiogroup"] { display: flex; flex-direction: row; flex-wrap: wrap; gap: .45rem; padding: .35rem 0 .75rem; border-bottom: 1px solid #DDE5EC; }
div[data-testid="stRadio"] [role="radiogroup"] label { background: #FFFFFF; border: 1px solid #DDE5EC; border-radius: 10px; padding: .5rem .85rem; margin: 0; color: #526579; font-weight: 680; transition: transform .2s ease, border-color .2s ease, background .2s ease; }
div[data-testid="stRadio"] [role="radiogroup"] label:hover { transform: translateY(-2px); border-color: #087E8B; }
div[data-testid="stRadio"] input[type="radio"] { accent-color: #087E8B; }
div[data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) { background: #E5F4F4; border-color: #087E8B; color: #087E8B; }
.section-kicker { font-size: .70rem; letter-spacing: .14em; text-transform: uppercase; font-weight: 800; color: #087E8B; margin: .25rem 0 .23rem; }
.section-title { font-size: 1.35rem; letter-spacing: -.025em; font-weight: 790; color: #142B3B; margin: 0 0 .2rem; }
.section-note { font-size: .87rem; line-height: 1.55; color: #667085; margin: 0 0 .85rem; }
.kpi-card { background: #FFFFFF; border: 1px solid #DDE5EC; border-top: 3px solid #087E8B; border-radius: 14px; padding: 1.05rem 1.1rem .95rem; min-height: 126px; box-shadow: 0 3px 10px rgba(16,42,58,.035); animation: fadeSlideIn .55s ease both; transition: transform .22s ease, box-shadow .22s ease; }
.kpi-card:hover { transform: translateY(-4px); box-shadow: 0 12px 25px rgba(16,42,58,.10); }
.kpi-label { color: #667085; font-size: .77rem; font-weight: 720; margin-bottom: .50rem; letter-spacing: .025em; }
.kpi-value { color: #142B3B; font-size: 1.78rem; line-height: 1.1; letter-spacing: -.035em; font-weight: 840; }
.kpi-foot { color: #748394; font-size: .76rem; margin-top: .55rem; line-height: 1.35; }
.insight-grid-card { background: white; border: 1px solid #DFE6EC; border-radius: 12px; padding: .95rem; min-height: 116px; box-shadow: 0 2px 8px rgba(16,42,58,.025); animation: fadeSlideIn .6s ease both; transition: transform .2s ease, box-shadow .2s ease; }
.insight-grid-card:hover { transform: translateY(-3px); box-shadow: 0 10px 20px rgba(16,42,58,.07); }
.insight-mark { display: inline-flex; align-items:center; justify-content:center; width: 30px; height: 30px; background:#E5F4F4; color:#087E8B; border-radius:9px; font-size:.9rem; font-weight:850; margin-bottom:.6rem; }
.insight-label { color: #667085; text-transform: uppercase; letter-spacing: .105em; font-size: .66rem; font-weight: 850; margin-bottom: .32rem; }
.insight-text { color: #263D4E; font-size: .88rem; line-height: 1.52; }
.callout { background: #FFF8E8; border: 1px solid #F0D89E; color: #6E531F; border-radius: 10px; padding: .7rem .9rem; font-size: .82rem; line-height: 1.5; margin: .4rem 0 .8rem; }
.info-panel { background: #F3F8FA; border: 1px solid #D8E7ED; border-radius: 13px; padding: 1rem 1.1rem; margin: .4rem 0 .9rem; color: #365164; line-height: 1.55; }
.info-panel b { color: #142B3B; }
.panel-note { color: #7A8794; font-size: .75rem; line-height: 1.45; }
/* Charts animate into view and gently lift on hover. Plotly itself supplies hover/zoom/legend interactions. */
div[data-testid="stPlotlyChart"] { background: #FFFFFF; border: 1px solid #DDE5EC; border-radius: 14px; padding: .35rem .4rem .08rem; box-shadow: 0 3px 10px rgba(16,42,58,.025); animation: chartEnter .72s cubic-bezier(.2,.75,.3,1) both; transition: transform .24s ease, box-shadow .24s ease, border-color .24s ease; }
div[data-testid="stPlotlyChart"]:hover { transform: translateY(-3px); box-shadow: 0 12px 28px rgba(16,42,58,.085); border-color: #B8D6DD; }
div[data-testid="stDataFrame"] { border: 1px solid #DDE5EC; border-radius: 10px; overflow: hidden; }
hr { border-color: #DDE5EC; }
@keyframes fadeSlideIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
@keyframes chartEnter { from { opacity: .25; transform: translateY(12px) scale(.992); } to { opacity: 1; transform: translateY(0) scale(1); } }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: .01ms !important; transition-duration: .01ms !important; } }
@media (max-width: 900px) { .hero .hero-title { font-size: 1.8rem; } .kpi-value { font-size: 1.45rem; } }
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
        font=dict(family="Inter, Segoe UI, Arial, sans-serif", color="#526579", size=12),
        hoverlabel=dict(bgcolor="#142B3B", font_color="#FFFFFF", bordercolor="#142B3B"),
        legend=dict(font=dict(color="#526579", size=11), bgcolor="rgba(255,255,255,0)"),
        showlegend=legend,
        transition=dict(duration=450, easing="cubic-in-out"),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="#D6DEE6", ticks="outside")
    fig.update_yaxes(showgrid=True, gridcolor="#EDF1F5", zeroline=False, linecolor="#D6DEE6", ticks="outside")
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
# Sidebar: data direction and file loading
# =============================================================================
if not DATA_FILE.exists():
    st.error("DGCIS_DATA.csv was not found. Place it in the same folder as app.py.")
    st.stop()

st.sidebar.markdown("<div class='eyebrow'>WORKSPACE</div>", unsafe_allow_html=True)
st.sidebar.title("PetroTrade controls")
st.sidebar.caption("Choose your time window, commodity groups, and data flows. Charts and tables update automatically.")

base_flow = st.sidebar.selectbox(
    "DGCIS_DATA.csv represents",
    ["Direction not verified", "Imports", "Exports"],
    index=0,
    help="Only select Imports or Exports after confirming the DGCIS query settings used to download this CSV.",
)
st.sidebar.markdown("**Optional: add separate trade-flow files**")
imports_upload = st.sidebar.file_uploader("Import dataset CSV", type=["csv"], key="imports_csv")
exports_upload = st.sidebar.file_uploader("Export dataset CSV", type=["csv"], key="exports_csv")
st.sidebar.caption("For a real import/export comparison, supply one Imports CSV and one Exports CSV with matching HS chapters and periods.")

try:
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

selected_year = st.sidebar.selectbox("Analysis year", years, index=years.index(latest_year), format_func=year_label)
commodity_options = sorted(data["Commodity"].dropna().unique().tolist(), key=lambda c: next((k for k, v in COMMODITY_INFO.items() if v["commodity"] == c), 999))
selected_commodities = st.sidebar.multiselect("Commodity groups", commodity_options, default=commodity_options)
if not selected_commodities:
    st.warning("Select at least one commodity group in the sidebar to continue.")
    st.stop()

available_flows = sorted(data["Trade Flow"].dropna().unique().tolist())
months_present = select_months_for_flows(data, selected_year)
if not months_present:
    st.error("No months are available for the selected year.")
    st.stop()

# Apply the same months to all flows for fair import/export and YoY comparisons.
base_filtered = data[data["Commodity"].isin(selected_commodities)].copy()
current = base_filtered[(base_filtered["Year"] == selected_year) & base_filtered["MonthNum"].isin(months_present)].copy()
prior_year = selected_year - 1
prior = base_filtered[(base_filtered["Year"] == prior_year) & base_filtered["MonthNum"].isin(months_present)].copy()
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
# Global hero and top navigation
# =============================================================================
st.markdown(
    f"<div class='hero'><div class='hero-eyebrow'>INDIA TRADE INTELLIGENCE · {safe(year_label(selected_year))}</div>"
    f"<div class='hero-title'>PetroTrade Intelligence</div>"
    f"<div class='hero-sub'>A market intelligence workspace for petroleum-related and downstream material trade. Explore commodity categories, compare yearly import/export values when both flows are supplied, and uncover which partner markets account for recorded value.</div>"
    f"<div class='hero-meta'><span class='hero-chip'>DGCIS source extract</span><span class='hero-chip'>{safe(period_label)}</span>"
    f"<span class='hero-chip'>{len(selected_commodities)} commodity groups selected</span><span class='hero-chip'>{len(known_flows)} data flow(s) loaded</span></div></div>",
    unsafe_allow_html=True,
)

pages = ["Overview", "Commodity breakdown", "Imports vs exports", "Partner markets", "Data & methodology"]
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
    section("WELCOME / START HERE", "From raw trade records to market signals", "Use this page for a quick executive view. Move to the other pages for commodity-level breakdowns, import/export comparison, partner-market exploration, and downloadable records.")
    st.markdown(
        "<div class='info-panel'><b>How to use PetroTrade:</b><br>"
        "<b>1. Choose the year and commodity groups</b> from the left panel. All metrics and charts respond to these filters.<br>"
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
        kpi_card("LEADING COMMODITY SHARE", f"{leader_share:.1f}%" if pd.notna(leader_share) else "—", f"{leader['Commodity']} · {fmt_money_mn(leader['Value_USD_Mn'])}" if leader is not None else "No value available", "#315B75")
    with c4:
        kpi_card("NAMED PARTNER MARKETS", f"{active_markets:,}", "Positive-value named markets", "#D39B49")

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
                fig = px.line(line_data, x="Month", y="Value_USD_Bn", color="Series", markers=True,
                              category_orders={"Month": month_labels}, color_discrete_sequence=PALETTE,
                              labels={"Value_USD_Bn": "Value (US$ billion)", "Month": "Month"})
            else:
                fig = px.line(line_data, x="Month", y="Value_USD_Bn", color="Trade Flow", markers=True,
                              category_orders={"Month": month_labels}, color_discrete_sequence=["#A3B3C2", TEAL],
                              labels={"Value_USD_Bn": "Value (US$ billion)", "Month": "Month", "Trade Flow": "Period"})
            fig.update_traces(line_width=3, marker_size=7, hovertemplate="%{x}<br>US$%{y:,.2f}B<extra>%{fullData.name}</extra>")
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
    annual = base_filtered.groupby(["Year", "Trade Flow"], as_index=False)["Value_USD_Bn"].sum()
    annual_months = base_filtered.groupby(["Year", "Trade Flow"])["MonthNum"].nunique().reset_index(name="Months")
    annual = annual.merge(annual_months, on=["Year", "Trade Flow"], how="left")
    annual["Period"] = annual.apply(lambda r: f"{int(r['Year'])} · YTD" if int(r["Months"]) < 12 else str(int(r["Year"])), axis=1)
    if len(known_flows) > 1:
        fig = px.bar(annual, x="Period", y="Value_USD_Bn", color="Trade Flow", barmode="group", color_discrete_sequence=PALETTE,
                     labels={"Value_USD_Bn": "Recorded value (US$ billion)", "Period": "Reporting period"})
    else:
        annual_sum = base_filtered.groupby("Year", as_index=False)["Value_USD_Bn"].sum()
        annual_sum["Period"] = annual_sum["Year"].astype(str)
        annual_sum.loc[annual_sum["Year"] == latest_year, "Period"] = f"{latest_year} · YTD" if base_filtered.loc[base_filtered["Year"] == latest_year, "MonthNum"].nunique() < 12 else str(latest_year)
        fig = px.bar(annual_sum, x="Period", y="Value_USD_Bn", color="Period", color_discrete_sequence=[TEAL, "#315B75", "#6DA9BC", "#D39B49", "#8A9BA8"],
                     labels={"Value_USD_Bn": "Recorded value (US$ billion)", "Period": "Reporting period"})
    fig.update_traces(texttemplate="US$%{y:.1f}B", textposition="outside", cliponaxis=False, hovertemplate="%{x}<br>US$%{y:,.2f}B<extra></extra>")
    fig.update_layout(showlegend=len(known_flows) > 1, yaxis_title="Value (US$ billion)", xaxis_title="Reporting period")
    render_chart(fig, "overview_annual_context", 360, legend=len(known_flows) > 1)

    st.write("")
    section("03 / LEADING MARKETS", "Which named markets have the largest recorded values?", "Aggregate labels are excluded from the ranking so they do not appear as real trading partners.")
    top_markets = partner_totals.head(10).sort_values("Value_USD_Mn")
    if not top_markets.empty:
        top_markets["Value_USD_Bn"] = top_markets["Value_USD_Mn"] / 1000
        fig = px.bar(top_markets, x="Value_USD_Bn", y="DisplayCountry", orientation="h", text="Value_USD_Bn",
                     color="Value_USD_Bn", color_continuous_scale=["#BFE5E5", TEAL, NAVY],
                     labels={"Value_USD_Bn": "Value (US$ billion)", "DisplayCountry": "Partner market"})
        fig.update_traces(texttemplate="US$%{x:.2f}B", textposition="outside", cliponaxis=False,
                          hovertemplate="%{y}<br>US$%{x:,.2f}B<extra></extra>")
        fig.update_layout(coloraxis_showscale=False, yaxis_title="", xaxis_title="Value (US$ billion)")
        render_chart(fig, "overview_top_markets", 400, legend=False)

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
            fig = px.bar(commodity_bar, x="Value_USD_Bn", y="Commodity", orientation="h", color="Value_USD_Bn", color_continuous_scale=["#BFE5E5", TEAL, NAVY],
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
                         color_continuous_scale=[RED, "#E9EDF1", GREEN], labels={"Balance (Exports − Imports)": "Net balance (US$ billion)"})
            fig.add_vline(x=0, line_dash="dash", line_color="#748394")
            fig.update_layout(coloraxis_showscale=False, xaxis_title="Exports minus imports (US$ billion)", yaxis_title="")
            render_chart(fig, "commodity_balance", 420, legend=False)
        else:
            segment = current.groupby("Commodity Category", as_index=False)["Value_USD_Bn"].sum().sort_values("Value_USD_Bn", ascending=False)
            fig = px.treemap(segment, path=["Commodity Category"], values="Value_USD_Bn", color="Value_USD_Bn",
                             color_continuous_scale=["#DDEFF0", "#6DA9BC", TEAL, NAVY], labels={"Value_USD_Bn": "Value (US$ billion)"})
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
            colorscale=[[0, "#F1F5F9"], [.65, "#A6DAD9"], [1, TEAL]],
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
# PAGE 3: IMPORTS VS EXPORTS
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
            kpi_card("IMPORTS", fmt_money_mn(imports_mn), period_label, "#315B75")
        with b:
            kpi_card("EXPORTS", fmt_money_mn(exports_mn), period_label, TEAL)
        with c:
            kpi_card("TRADE BALANCE", fmt_money_mn(balance_mn), "Exports − imports", GREEN if balance_mn >= 0 else RED)
        with d:
            kpi_card("IMPORT SHARE", f"{import_share:.1f}%" if pd.notna(import_share) else "—", "Of combined import + export value", "#D39B49")

        st.write("")
        flow_by_commodity = current[current["Trade Flow"].isin(["Imports", "Exports"])].groupby(["Commodity", "Trade Flow"], as_index=False)["Value_USD_Bn"].sum()
        left, right = st.columns([1.15, 1], gap="large")
        with left:
            fig = px.bar(flow_by_commodity, x="Commodity", y="Value_USD_Bn", color="Trade Flow", barmode="group", color_discrete_map={"Imports": "#315B75", "Exports": TEAL},
                         labels={"Value_USD_Bn": "Value (US$ billion)", "Commodity": "Commodity group"})
            fig.update_layout(xaxis_title="Commodity group", yaxis_title="Value (US$ billion)")
            render_chart(fig, "flow_import_export_commodity", 420)
        with right:
            balances = flow_by_commodity.pivot(index="Commodity", columns="Trade Flow", values="Value_USD_Bn").fillna(0)
            balances["Balance"] = balances.get("Exports", 0) - balances.get("Imports", 0)
            balances = balances.reset_index().sort_values("Balance")
            fig = px.bar(balances, x="Balance", y="Commodity", orientation="h", color="Balance", color_continuous_scale=[RED, "#F0F3F6", GREEN],
                         labels={"Balance": "Net balance (US$ billion)", "Commodity": "Commodity group"})
            fig.add_vline(x=0, line_dash="dash", line_color="#667085")
            fig.update_layout(coloraxis_showscale=False, xaxis_title="Exports minus imports (US$ billion)", yaxis_title="")
            render_chart(fig, "flow_trade_balance", 420, legend=False)

        st.write("")
        section("MONTHLY FLOW MOVEMENT", "Do imports and exports follow the same monthly pattern?", "Use the legend to focus on a flow. Hover over a point to inspect the month's value.")
        monthly_flow = current.groupby(["MonthNum", "Month", "Trade Flow"], as_index=False)["Value_USD_Bn"].sum()
        fig = px.line(monthly_flow, x="Month", y="Value_USD_Bn", color="Trade Flow", markers=True,
                      category_orders={"Month": month_labels}, color_discrete_map={"Imports": "#315B75", "Exports": TEAL},
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
# PAGE 4: PARTNER MARKETS
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
            kpi_card("SHARE OF NAMED MARKETS", f"{market_share:.1f}%" if pd.notna(market_share) else "—", "Within current filters", "#315B75")
        with mc4:
            market_commodity = market_current.groupby("Commodity")["Value_USD_Mn"].sum().sort_values(ascending=False)
            kpi_card("TOP COMMODITY", market_commodity.index[0] if not market_commodity.empty else "—", fmt_money_mn(market_commodity.iloc[0]) if not market_commodity.empty else "No value", "#D39B49")

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
                              category_orders={"Month": month_labels}, color_discrete_sequence=["#A3B3C2", TEAL],
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
        fig = px.bar(top, x="Value_USD_Bn", y="DisplayCountry", orientation="h", color="Value_USD_Bn", color_continuous_scale=["#BFE5E5", TEAL, NAVY],
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
# PAGE 5: DATA & METHODOLOGY
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
        kpi_card("SOURCE YEARS", f"{min(years)}–{max(years)}", "Available reporting years", "#315B75")
    with c:
        latest_date = data["Date"].max()
        kpi_card("LATEST SOURCE MONTH", latest_date.strftime("%b %Y"), "Latest date present in loaded data", "#D39B49")

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
    "<div class='panel-note'>PetroTrade Intelligence · DGCIS CSV supplied for this project. Commodity groups are derived from HS chapters. The app preserves the distinction between imported, exported, and unverified trade-flow data. Hover over charts for values; use each chart's modebar to zoom, pan, or download the image.</div>",
    unsafe_allow_html=True,
)
