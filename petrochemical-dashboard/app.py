from pathlib import Path
import html
import re

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# -----------------------------------------------------------------------------
# PetroTrade Intelligence | Market intelligence dashboard
# Data source: user-downloaded DGCIS CSV. Values in source are USD million.
# The source file does not include an explicit import/export field.
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="PetroTrade Intelligence",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_FILE = Path(__file__).parent / "DGCIS_DATA.csv"
MONTH_RE = re.compile(r"^[A-Za-z]+-\d{4}_USD_Mn$")
COMMODITIES = {
    27: "Mineral fuels & oils",
    28: "Inorganic chemicals",
    29: "Organic chemicals",
    39: "Plastics & articles",
    40: "Rubber & articles",
}
MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
PALETTE = ["#087E8B", "#315B75", "#6DA9BC", "#8A9BA8", "#D39B49", "#9B7EBD"]
TEAL = "#087E8B"
NAVY = "#142B3B"
SLATE = "#667085"
GREEN = "#16794B"
RED = "#C2414B"

COUNTRY_ALIASES = {
    "U S A": "United States",
    "USA": "United States",
    "U ARAB EMTS": "United Arab Emirates",
    "NETHERLAND": "Netherlands",
    "SAUDI ARAB": "Saudi Arabia",
    "SRI LANKA DSR": "Sri Lanka",
    "YEMEN REPUBLC": "Yemen",
    "KYRGHYZSTAN": "Kyrgyzstan",
    "C AFRI REP": "Central African Republic",
    "BOSNIA-HRZGOVIN": "Bosnia and Herzegovina",
    "MACEDONIA": "North Macedonia",
}
EXCLUDED_MARKETS = {"TOTAL", "ALL COUNTRIES", "WORLD TOTAL", "UNSPECIFIED", "NOT SPECIFIED", "OTHERS", "OTHER", ""}

st.markdown("""
<style>
:root { color-scheme: light; }
.block-container { padding-top: 1.2rem; padding-bottom: 2.8rem; max-width: 1580px; }
[data-testid="stSidebar"] { background: #F0F4F7; border-right: 1px solid #DCE4EB; }
[data-testid="stSidebar"] > div { padding-top: 1.5rem; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #526579; }
.eyebrow { font-size: .70rem; letter-spacing: .17em; font-weight: 800; color: #0C8995; text-transform: uppercase; }
.hero { background: linear-gradient(120deg, #102A3A 0%, #183C50 58%, #17616A 100%); color: white; padding: 1.65rem 1.85rem; border-radius: 18px; margin: .1rem 0 1.05rem 0; box-shadow: 0 10px 28px rgba(20,43,59,.10); }
.hero .hero-eyebrow { color: #7BD0D0; font-size: .70rem; font-weight: 800; letter-spacing: .18em; text-transform: uppercase; margin-bottom: .55rem; }
.hero .hero-title { font-size: 2.3rem; font-weight: 800; line-height: 1.08; letter-spacing: -.045em; margin: 0 0 .55rem; }
.hero .hero-sub { max-width: 880px; color: #D4E2EA; font-size: .98rem; line-height: 1.55; }
.hero-meta { display: flex; gap: .55rem; flex-wrap: wrap; margin-top: 1.1rem; }
.hero-chip { display: inline-block; border: 1px solid rgba(255,255,255,.23); color: #E9F5F6; background: rgba(255,255,255,.08); padding: .35rem .65rem; border-radius: 999px; font-size: .73rem; }
.section-kicker { font-size: .70rem; letter-spacing: .14em; text-transform: uppercase; font-weight: 800; color: #087E8B; margin: .15rem 0 .23rem; }
.section-title { font-size: 1.35rem; letter-spacing: -.025em; font-weight: 770; color: #142B3B; margin: 0 0 .2rem; }
.section-note { font-size: .87rem; line-height: 1.5; color: #667085; margin: 0 0 .85rem; }
.kpi-card { background: #FFFFFF; border: 1px solid #DDE5EC; border-top: 3px solid #087E8B; border-radius: 14px; padding: 1.05rem 1.1rem .95rem; min-height: 126px; box-shadow: 0 3px 10px rgba(16,42,58,.035); }
.kpi-label { color: #667085; font-size: .79rem; font-weight: 650; margin-bottom: .50rem; }
.kpi-value { color: #142B3B; font-size: 1.78rem; line-height: 1.1; letter-spacing: -.035em; font-weight: 820; }
.kpi-foot { color: #748394; font-size: .76rem; margin-top: .55rem; line-height: 1.35; }
.insight-card { display: flex; gap: .75rem; align-items: flex-start; background: white; border: 1px solid #DFE6EC; border-radius: 12px; padding: .9rem .95rem; min-height: 116px; }
.insight-mark { flex-shrink: 0; width: 30px; height: 30px; display:flex; align-items:center; justify-content:center; background:#E5F4F4; color:#087E8B; border-radius:9px; font-size:.96rem; font-weight:800; }
.insight-label { color: #667085; text-transform: uppercase; letter-spacing: .105em; font-size: .66rem; font-weight: 800; margin-bottom: .32rem; }
.insight-text { color: #263D4E; font-size: .88rem; line-height: 1.5; }
.callout { background: #FFF8E8; border: 1px solid #F0D89E; color: #6E531F; border-radius: 10px; padding: .7rem .9rem; font-size: .82rem; line-height: 1.45; margin: .4rem 0 .8rem; }
.panel-note { color: #7A8794; font-size: .75rem; line-height: 1.45; }
div[data-testid="stPlotlyChart"] { background: #FFFFFF; border: 1px solid #DDE5EC; border-radius: 14px; padding: .38rem .45rem .1rem; box-shadow: 0 3px 10px rgba(16,42,58,.025); }
div[data-testid="stDataFrame"] { border: 1px solid #DDE5EC; border-radius: 10px; overflow: hidden; }
/* Streamlit toolbar fallback */
[data-testid="stToolbar"],
[data-testid="stDecoration"] {
    display: none !important;
}

/* Top navigation */
div[data-testid="stRadio"] {
    margin-bottom: 1rem;
}

div[data-testid="stRadio"] [role="radiogroup"] {
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
    gap: 0.5rem;
    padding: 0.5rem 0 0.8rem;
    border-bottom: 1px solid #DDE5EC;
}

div[data-testid="stRadio"] [role="radiogroup"] label {
    background: #FFFFFF;
    border: 1px solid #DDE5EC;
    border-radius: 10px;
    padding: 0.55rem 0.9rem;
    margin: 0;
    color: #526579;
    font-weight: 650;
}

div[data-testid="stRadio"] input[type="radio"] {
    accent-color: #087E8B;
}

div[data-testid="stRadio"] [role="radiogroup"]
label:has(input:checked) {
    background: #E5F4F4;
    border-color: #087E8B;
    color: #087E8B;
}

/* Chart cards */
div[data-testid="stPlotlyChart"] {
    overflow: hidden;
    border: 1px solid #DDE5EC;
    border-radius: 14px;
    background: #FFFFFF;
    padding: 0.3rem;
    box-shadow: 0 3px 10px rgba(16, 42, 58, 0.025);
}
hr { border-color: #DDE5EC; }
@media (max-width: 900px) { .hero .hero-title { font-size: 1.8rem; } .kpi-value { font-size: 1.45rem; } }
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner="Preparing DGCIS trade records…")
def load_data(path: str) -> pd.DataFrame:
    raw = pd.read_csv(path, low_memory=False)
    raw.columns = raw.columns.astype(str).str.strip()
    required = ["HS Code", "HS Description", "Country Name"]
    missing = [c for c in required if c not in raw.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))

    month_cols = [c for c in raw.columns if MONTH_RE.match(c)]
    if not month_cols:
        raise ValueError("No monthly USD_Mn columns found. Expected names like January-2025_USD_Mn.")

    raw["HS Code"] = pd.to_numeric(raw["HS Code"], errors="coerce")
    raw["Country Name"] = raw["Country Name"].fillna("").astype(str).str.strip()
    raw["HS Description"] = raw["HS Description"].fillna("").astype(str).str.strip()
    # Drop the source's overall TOTAL row (it has no HS code) to prevent double counting.
    raw = raw.dropna(subset=["HS Code"])

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
    long_df["Commodity"] = long_df["HS Code"].map(COMMODITIES).fillna(long_df["HS Description"])
    long_df["CountryKey"] = long_df["Country Name"].str.upper().str.strip()
    long_df["DisplayCountry"] = long_df["CountryKey"].map(COUNTRY_ALIASES).fillna(long_df["Country Name"])
    long_df = long_df[~long_df["CountryKey"].isin({"TOTAL", "ALL COUNTRIES", "WORLD TOTAL"})]
    return long_df.sort_values("Date").reset_index(drop=True)


def money(value, decimals=1):
    if pd.isna(value):
        return "—"
    value = float(value)
    if abs(value) >= 1000:
        return f"US${value / 1000:,.{decimals}f}B"
    return f"US${value:,.{decimals}f}M"


def money_bn(value, decimals=1):
    if pd.isna(value):
        return "—"
    return f"US${float(value):,.{decimals}f}B"


def pct(value, decimals=1):
    return "—" if pd.isna(value) else f"{float(value):+,.{decimals}f}%"


def safe_html(value):
    return html.escape(str(value))


def section(kicker, title, note=""):
    st.markdown(f"<div class='section-kicker'>{safe_html(kicker)}</div><div class='section-title'>{safe_html(title)}</div>", unsafe_allow_html=True)
    if note:
        st.markdown(f"<div class='section-note'>{safe_html(note)}</div>", unsafe_allow_html=True)


def kpi_card(label, value, foot, accent=TEAL):
    st.markdown(
        f"<div class='kpi-card' style='border-top-color:{accent}'>"
        f"<div class='kpi-label'>{safe_html(label)}</div>"
        f"<div class='kpi-value'>{safe_html(value)}</div>"
        f"<div class='kpi-foot'>{safe_html(foot)}</div></div>",
        unsafe_allow_html=True,
    )


def insight_card(mark, label, text):
    st.markdown(
        f"<div class='insight-card'><div class='insight-mark'>{safe_html(mark)}</div>"
        f"<div><div class='insight-label'>{safe_html(label)}</div>"
        f"<div class='insight-text'>{safe_html(text)}</div></div></div>",
        unsafe_allow_html=True,
    )


def style_fig(fig, height=370, showlegend=None, horizontal=False):
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=18, r=145 if any(getattr(trace, "type", "") == "pie" for trace in fig.data) else 26, t=30, b=22),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        font=dict(family="Inter, Segoe UI, Arial, sans-serif", color="#526579", size=12),
        hoverlabel=dict(bgcolor="#142B3B", font_color="#FFFFFF", bordercolor="#142B3B"),
        legend=dict(font=dict(color="#526579", size=11), bgcolor="rgba(255,255,255,0)"),
    )
    if showlegend is not None:
        fig.update_layout(showlegend=showlegend)
    if horizontal:
        fig.update_xaxes(showgrid=True, gridcolor="#EDF1F5", zeroline=False, linecolor="#D6DEE6", tickfont=dict(color="#667085"))
        fig.update_yaxes(showgrid=False, zeroline=False, linecolor="#D6DEE6", tickfont=dict(color="#667085"))
    else:
        fig.update_xaxes(showgrid=False, linecolor="#D6DEE6", tickfont=dict(color="#667085"))
        fig.update_yaxes(showgrid=True, gridcolor="#EDF1F5", zeroline=False, tickfont=dict(color="#667085"))
    return fig


def clean_chart_axis(fig, x_title=None, y_title=None):
    if x_title is not None:
        fig.update_xaxes(title=x_title)
    if y_title is not None:
        fig.update_yaxes(title=y_title)
    return fig


def named_rows(frame):
    return frame[~frame["CountryKey"].isin(EXCLUDED_MARKETS) & (frame["Value_USD_Mn"] > 0)].copy()


def compact_table_height(n_rows, min_height=120, max_height=420):
    return min(max_height, max(min_height, 43 + n_rows * 36))


# Load and validate source
if not DATA_FILE.exists():
    st.error("DGCIS_DATA.csv was not found. Keep the downloaded CSV in the same folder as app.py.")
    st.stop()
try:
    data = load_data(str(DATA_FILE))
except Exception as exc:
    st.error(f"Could not load the dataset: {exc}")
    st.stop()
if data.empty:
    st.error("No valid trade records were found in this CSV.")
    st.stop()

# Sidebar controls
years = sorted(data["Year"].dropna().unique().tolist())
latest_year = max(years)
latest_months = sorted(data.loc[data["Year"] == latest_year, "MonthNum"].unique().tolist())
latest_partial = len(latest_months) < 12
st.sidebar.markdown("---")

st.sidebar.markdown("**Data source**")

st.sidebar.caption(
    "DGCIS monthly trade records · USD million"
)

st.sidebar.caption(
    "HS chapters 27, 28, 29, 39 and 40"
)

st.sidebar.caption(
    "Verify import/export direction in the source query."
)

def year_label(y):
    n = data.loc[data["Year"] == y, "MonthNum"].nunique()
    return f"{y} · YTD ({n} months)" if n < 12 else str(y)

year = st.sidebar.selectbox("Analysis year", years, index=years.index(latest_year), format_func=year_label)
commodity_options = [COMMODITIES[k] for k in [27, 28, 29, 39, 40] if COMMODITIES[k] in set(data["Commodity"].dropna())]
selected_commodities = st.sidebar.multiselect("Commodity groups", commodity_options, default=commodity_options)
if not selected_commodities:
    st.warning("Select at least one commodity group in the sidebar to continue.")
    st.stop()

st.sidebar.markdown("---")
st.sidebar.markdown("**Current scope**")
st.sidebar.caption("Trade value in US dollars. The downloaded file does not encode import/export direction, so confirm the query settings in DGCIS before presenting the figures as imports or exports.")

# Base filters and comparable period
filtered = data[data["Commodity"].isin(selected_commodities)].copy()
current = filtered[filtered["Year"] == year].copy()
months_present = sorted(current["MonthNum"].unique().tolist())
period_month_order = [pd.Timestamp(year=2000, month=int(m), day=1).strftime("%b") for m in months_present]
prior_year = year - 1
prior = filtered[(filtered["Year"] == prior_year) & filtered["MonthNum"].isin(months_present)].copy()
partial = len(months_present) < 12
if months_present:
    start_month = pd.Timestamp(year=2000, month=min(months_present), day=1).strftime("%b")
    end_month = pd.Timestamp(year=2000, month=max(months_present), day=1).strftime("%b")
    period_label = f"{start_month}–{end_month} {year}" if len(months_present) < 12 else f"Jan–Dec {year}"
else:
    period_label = str(year)

current_total_mn = current["Value_USD_Mn"].sum()
prior_total_mn = prior["Value_USD_Mn"].sum()
yoy_total = (current_total_mn / prior_total_mn - 1) * 100 if prior_total_mn > 0 else float("nan")
commodity_totals = (current.groupby("Commodity", as_index=False)["Value_USD_Mn"].sum()
                    .sort_values("Value_USD_Mn", ascending=False))
if not commodity_totals.empty and current_total_mn > 0:
    leader = commodity_totals.iloc[0]
    leader_share = leader["Value_USD_Mn"] / current_total_mn * 100
else:
    leader = None
    leader_share = 0
named_current = named_rows(current)
named_prior = named_rows(prior)
partner_totals = (named_current.groupby(["Country Name", "DisplayCountry"], as_index=False)["Value_USD_Mn"].sum()
                  .sort_values("Value_USD_Mn", ascending=False))
partner_total = partner_totals["Value_USD_Mn"].sum()
active_markets = int(partner_totals["Country Name"].nunique())
top_partner = partner_totals.iloc[0] if not partner_totals.empty else None
top5_share = partner_totals.head(5)["Value_USD_Mn"].sum() / partner_total * 100 if partner_total > 0 else float("nan")
monthly_current = (current.groupby(["MonthNum", "Month"], as_index=False)["Value_USD_Mn"].sum().sort_values("MonthNum"))
monthly_prior = (prior.groupby(["MonthNum", "Month"], as_index=False)["Value_USD_Mn"].sum().sort_values("MonthNum"))
peak = monthly_current.loc[monthly_current["Value_USD_Mn"].idxmax()] if not monthly_current.empty else None

# Hero header
st.markdown(
    f"<div class='hero'><div class='hero-eyebrow'>India trade intelligence / {safe_html(year_label(year))}</div>"
    f"<div class='hero-title'>PetroTrade Intelligence</div>"
    f"<div class='hero-sub'>From trade records to market signals. Track commodity performance, measure year-on-year movement, and identify which partner markets account for the most recorded value.</div>"
    f"<div class='hero-meta'><span class='hero-chip'>DGCIS source extract</span><span class='hero-chip'>{safe_html(period_label)}</span>"
    f"<span class='hero-chip'>{len(selected_commodities)} commodity groups</span><span class='hero-chip'>USD value · Millions converted to billions for charts</span></div></div>",
    unsafe_allow_html=True,
)

# KPI strip
k1, k2, k3, k4 = st.columns(4, gap="medium")
with k1:
    kpi_card("RECORDED TRADE VALUE", money(current_total_mn), f"{period_label} · selected commodity groups", TEAL)
with k2:
    yoy_value = pct(yoy_total) if not pd.isna(yoy_total) else "No baseline"
    delta_caption = f"vs. same {len(months_present)} month(s) in {prior_year}" if prior_total_mn > 0 else "Comparable prior-year data unavailable"
    kpi_card("YEAR-ON-YEAR CHANGE", yoy_value, delta_caption, GREEN if (not pd.isna(yoy_total) and yoy_total >= 0) else RED)
with k3:
    leader_label = f"{leader_share:.1f}%" if leader is not None else "—"
    leader_foot = f"{leader['Commodity']} · {money(leader['Value_USD_Mn'])}" if leader is not None else "No commodity values available"
    kpi_card("LEADING COMMODITY SHARE", leader_label, leader_foot, "#315B75")
with k4:
    kpi_card("NAMED PARTNER MARKETS", f"{active_markets:,}", "Positive-value named partners in selected period", "#D39B49")

if partial:
    st.markdown(f"<div class='callout'><b>Period note:</b> {safe_html(year)} currently contains {len(months_present)} months in this dataset. Year-on-year change compares only {len(months_present)} comparable month(s) from {prior_year}, rather than comparing a partial year with a full year.</div>", unsafe_allow_html=True)

# Executive readout
st.write("")
section("Executive readout", "Signals worth noticing", "These observations describe patterns in the selected data; they do not establish the causes behind those patterns.")
i1, i2, i3 = st.columns(3, gap="medium")
with i1:
    if leader is not None:
        insight_card("01", "Commodity mix", f"{leader['Commodity']} is the largest selected group at {leader_share:.1f}% of recorded value ({money(leader['Value_USD_Mn'])}).")
    else:
        insight_card("01", "Commodity mix", "No commodity leader can be calculated for the current selection.")
with i2:
    if top_partner is not None:
        insight_card("02", "Largest named partner", f"{top_partner['DisplayCountry']} leads named markets at {money(top_partner['Value_USD_Mn'])}. The top five markets account for {top5_share:.1f}% of named-partner value.")
    else:
        insight_card("02", "Partner markets", "No named partner markets are available for this selection.")
with i3:
    if peak is not None:
        insight_card("03", "Monthly high", f"{peak['Month']} is the strongest month in {year} at {money(peak['Value_USD_Mn'])}. This is a descriptive peak, not a forecast.")
    else:
        insight_card("03", "Monthly high", "No monthly peak is available for the current selection.")

st.write("")
# Main navigation: each tab has a distinct analytical job.
# Main navigation
selected_page = st.radio(
    "Main navigation",
    [
        "Market overview",
        "Commodity intelligence",
        "Partner explorer",
        "Data & methodology",
    ],
    horizontal=True,
    label_visibility="collapsed",
    key="main_navigation",
)

# -----------------------------------------------------------------------------
# Overview tab
# -----------------------------------------------------------------------------
if selected_page == "Market overview":
    st.write("")
    section("01 / Time series", "Is recorded value moving up or down?", "Compare each month with the same month in the prior year. This makes partial-year comparisons more meaningful.")
    trend_left, trend_right = st.columns([1.45, 1], gap="large")
    with trend_left:
        frames = []
        if not monthly_prior.empty:
            p = monthly_prior.copy()
            p["Period"] = f"{prior_year} · comparable"
            p["Value_USD_Bn"] = p["Value_USD_Mn"] / 1000
            frames.append(p)
        if not monthly_current.empty:
            c = monthly_current.copy()
            c["Period"] = f"{year}{' · YTD' if partial else ''}"
            c["Value_USD_Bn"] = c["Value_USD_Mn"] / 1000
            frames.append(c)
        if frames:
            trend = pd.concat(frames, ignore_index=True)
            color_map = {f"{prior_year} · comparable": "#A3B3C2", f"{year}{' · YTD' if partial else ''}": TEAL}
            fig = px.line(
                trend, x="Month", y="Value_USD_Bn", color="Period", markers=True,
                category_orders={"Month": period_month_order}, color_discrete_map=color_map,
                labels={"Month": "Month", "Value_USD_Bn": "Recorded value (US$ billion)"},
            )
            fig.update_traces(line_width=3, marker_size=7, hovertemplate="%{x}<br>US$%{y:,.2f}B<extra>%{fullData.name}</extra>")
            fig.update_layout(hovermode="x unified", legend_title_text="", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0))
            fig.update_yaxes(tickprefix="$", ticksuffix="B", title="Value (US$ billion)")
            st.plotly_chart(style_fig(fig, 390), use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No monthly values available for this selection.")
    with trend_right:
        if not commodity_totals.empty:
            mix = commodity_totals.copy()
            mix["Value_USD_Bn"] = mix["Value_USD_Mn"] / 1000
            fig = px.pie(
                mix, names="Commodity", values="Value_USD_Bn", hole=.66,
                color_discrete_sequence=PALETTE,
                labels={"Commodity": "Commodity group", "Value_USD_Bn": "Value (US$ billion)"},
            )
            fig.update_traces(
                textposition="inside", textinfo="percent", textfont=dict(size=12, color="white"),
                hovertemplate="%{label}<br>US$%{value:,.2f}B<br>%{percent}<extra></extra>",
                marker=dict(line=dict(color="#FFFFFF", width=2)),
            )
            fig.add_annotation(x=.5, y=.5, text=f"<b>{money_bn(current_total_mn / 1000)}</b><br><span style='font-size:11px'>total value</span>",
                               showarrow=False, font=dict(size=16, color=NAVY))
            fig.update_layout(legend=dict(orientation="v", x=1.02, y=.5, yanchor="middle"), margin=dict(l=8, r=120, t=20, b=12))
            st.plotly_chart(style_fig(fig, 390), use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No commodity values available.")

    st.write("")
    section("02 / Historical context", "How does this period compare with the wider series?", "Annual totals are shown for context. The latest partial year is explicitly marked YTD.")
    annual = (filtered.groupby("Year", as_index=False)["Value_USD_Mn"].sum().sort_values("Year"))
    annual_month_count = filtered.groupby("Year")["MonthNum"].nunique().to_dict()
    annual["Period"] = annual["Year"].apply(lambda y: f"{y} · YTD" if annual_month_count.get(y, 0) < 12 else str(y))
    annual["Value_USD_Bn"] = annual["Value_USD_Mn"] / 1000
    annual["Label"] = annual["Value_USD_Bn"].map(lambda v: f"${v:,.1f}B")
    fig = px.bar(annual, x="Period", y="Value_USD_Bn", text="Label",
                 labels={"Period": "Reporting period", "Value_USD_Bn": "Recorded value (US$ billion)"})
    fig.update_traces(marker_color=["#AAB7C4" if "YTD" in p else TEAL for p in annual["Period"]],
                      textposition="outside", cliponaxis=False, hovertemplate="%{x}<br>US$%{y:,.2f}B<extra></extra>")
    fig.update_layout(showlegend=False, yaxis_title="Value (US$ billion)")
    fig.update_yaxes(range=[0, float(annual["Value_USD_Bn"].max()) * 1.18])
    st.plotly_chart(style_fig(fig, 330), use_container_width=True, config={"displayModeBar": False})

    st.write("")
    section("03 / Leading markets", "Which named markets have the largest recorded values?", "Aggregate labels are excluded from the ranking. Select a market in the Partner explorer tab for a country-level drill-down.")
    if partner_totals.empty:
        st.info("No named partner markets available.")
    else:
        top = partner_totals.head(10).sort_values("Value_USD_Mn", ascending=True).copy()
        top["Value_USD_Bn"] = top["Value_USD_Mn"] / 1000
        fig = px.bar(top, x="Value_USD_Bn", y="DisplayCountry", orientation="h", text="Value_USD_Bn",
                     labels={"Value_USD_Bn": "Recorded value (US$ billion)", "DisplayCountry": "Partner market"})
        fig.update_traces(marker_color="#315B75", texttemplate="$%{x:,.2f}B", textposition="outside", cliponaxis=False,
                          hovertemplate="%{y}<br>US$%{x:,.2f}B<extra></extra>")
        fig.update_layout(showlegend=False, xaxis_title="Value (US$ billion)", yaxis_title="")
        fig.update_xaxes(range=[0, float(top["Value_USD_Bn"].max()) * 1.22])
        st.plotly_chart(style_fig(fig, 400, horizontal=True), use_container_width=True, config={"displayModeBar": False})
        st.write("")

    section(
        "04 / Partner momentum",
        "Which major markets are growing or declining?",
        "Bubble size represents current-period value. Colour represents "
        "year-on-year growth against comparable months."
    )

    partner_now = (
        named_current.groupby(
            ["Country Name", "DisplayCountry"],
            as_index=False
        )["Value_USD_Mn"]
        .sum()
        .rename(columns={"Value_USD_Mn": "Current_Mn"})
    )

    partner_prev = (
        named_prior.groupby(
            "Country Name",
            as_index=False
        )["Value_USD_Mn"]
        .sum()
        .rename(columns={"Value_USD_Mn": "Prior_Mn"})
    )

    momentum = partner_now.merge(
        partner_prev,
        on="Country Name",
        how="left",
    )

    momentum["Prior_Mn"] = momentum["Prior_Mn"].fillna(0)

    # Growth needs a positive, comparable prior-year baseline.
    momentum = momentum[momentum["Prior_Mn"] > 0].copy()

    if not momentum.empty:
        momentum["YoY change (%)"] = (
            momentum["Current_Mn"] / momentum["Prior_Mn"] - 1
        ) * 100

        momentum["Current_USD_Bn"] = momentum["Current_Mn"] / 1000

        # Focus the view on the 25 largest current-period markets.
        momentum = momentum.nlargest(25, "Current_Mn")

        fig = px.scatter(
            momentum,
            x="Current_USD_Bn",
            y="YoY change (%)",
            size="Current_USD_Bn",
            color="YoY change (%)",
            hover_name="DisplayCountry",
            size_max=38,
            color_continuous_scale=[
                "#C2414B",
                "#E8EDF2",
                "#087E8B",
            ],
            labels={
                "Current_USD_Bn": "Recorded value (US$ billion)",
                "YoY change (%)": "YoY change (%)",
            },
            hover_data={
                "Current_USD_Bn": ":.2f",
                "YoY change (%)": ":.1f",
                "Prior_Mn": False,
            },
        )

        fig.add_hline(
            y=0,
            line_dash="dash",
            line_color="#98A6B5",
        )

        fig.update_layout(
            coloraxis_colorbar_title="YoY %",
            xaxis_title="Current-period value (US$ billion)",
            yaxis_title="YoY change (%)",
        )

        st.plotly_chart(
            style_fig(fig, 420),
            use_container_width=True,
            config={"displayModeBar": False, "responsive": True},
        )

    else:
        st.info(
            "Comparable positive prior-year values are unavailable "
            "for the selected filters."
        )
# -----------------------------------------------------------------------------
# Commodity intelligence tab
# -----------------------------------------------------------------------------
if selected_page == "Commodity intelligence":
    st.write("")
    section("04 / Commodity performance", "Which commodity groups are gaining or losing ground?", "Year-on-year values compare the selected year with the same months in the previous year. Percentages are not calculated where no positive baseline exists.")

    change_rows = []
    for commodity in selected_commodities:
        cur_val = current.loc[current["Commodity"] == commodity, "Value_USD_Mn"].sum()
        prev_val = prior.loc[prior["Commodity"] == commodity, "Value_USD_Mn"].sum()
        change_val = cur_val - prev_val
        change_pct = (cur_val / prev_val - 1) * 100 if prev_val > 0 else float("nan")
        change_rows.append({
            "Commodity": commodity,
            "Selected value (US$ B)": cur_val / 1000,
            "Comparable prior (US$ B)": prev_val / 1000,
            "Change (US$ B)": change_val / 1000,
            "YoY change (%)": change_pct,
        })
    changes = pd.DataFrame(change_rows)
    change_left, change_right = st.columns([1.1, 1], gap="large")
    with change_left:
        plot_changes = changes.dropna(subset=["YoY change (%)"]).sort_values("YoY change (%)", ascending=True)
        if not plot_changes.empty:
            fig = go.Figure(go.Bar(
                x=plot_changes["YoY change (%)"], y=plot_changes["Commodity"], orientation="h",
                marker_color=[GREEN if x >= 0 else RED for x in plot_changes["YoY change (%)"]],
                text=[f"{x:+.1f}%" for x in plot_changes["YoY change (%)"]], textposition="outside",
                hovertemplate="%{y}<br>YoY change: %{x:+.1f}%<extra></extra>",
            ))
            fig.add_vline(x=0, line_width=1, line_color="#98A6B5")
            fig.update_layout(showlegend=False, xaxis_title="Year-on-year change (%)", yaxis_title="")
            xmin = min(0.0, float(plot_changes["YoY change (%)"].min()))
            xmax = max(0.0, float(plot_changes["YoY change (%)"].max()))
            span = max(10.0, xmax - xmin)
            fig.update_xaxes(range=[xmin - span * 0.12, xmax + span * 0.25])
            st.plotly_chart(style_fig(fig, 340, horizontal=True), use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("A positive prior-year baseline is unavailable for this year.")
    with change_right:
        shown = changes.copy()
        shown["Selected value (US$ B)"] = shown["Selected value (US$ B)"].map(lambda x: f"${x:,.2f}B")
        shown["Comparable prior (US$ B)"] = shown["Comparable prior (US$ B)"].map(lambda x: f"${x:,.2f}B")
        shown["Change (US$ B)"] = shown["Change (US$ B)"].map(lambda x: f"{'+' if x >= 0 else '−'}${abs(x):,.2f}B")
        shown["YoY change (%)"] = shown["YoY change (%)"].map(pct)
        st.dataframe(shown, use_container_width=True, hide_index=True, height=compact_table_height(len(shown), max_height=330))

    st.write("")
    section("05 / Monthly pattern", "When is each commodity group relatively stronger?", "Heatmap values are indexed to each commodity's own average month in the selected year (= 100). This reveals relative monthly pattern without letting the largest commodity dominate the colour scale.")
    heat = current.groupby(["Commodity", "MonthNum", "Month"], as_index=False)["Value_USD_Mn"].sum()
    if not heat.empty:
        pivot = heat.pivot(index="Commodity", columns="MonthNum", values="Value_USD_Mn").reindex(selected_commodities)
        pivot = pivot.reindex(columns=months_present)
        indexed = pivot.div(pivot.mean(axis=1).replace(0, pd.NA), axis=0) * 100
        labels = [pd.Timestamp(year=2000, month=int(m), day=1).strftime("%b") for m in indexed.columns]
        fig = go.Figure(data=go.Heatmap(
            z=indexed.values, x=labels, y=indexed.index.tolist(),
            colorscale=[[0, "#F1F5F9"], [.65, "#A6DAD9"], [1, "#087E8B"]],
            zmid=100, colorbar=dict(title="Index", ticksuffix="", thickness=14),
            hovertemplate="%{y}<br>%{x}<br>Index: %{z:.0f}<extra></extra>",
        ))
        fig.update_layout(xaxis_title="Month", yaxis_title="Commodity group")
        st.plotly_chart(style_fig(fig, 300), use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Monthly values are not available for the current selection.")
    st.write("")

    section(
        "06 / Commodity composition",
        "Where is recorded value concentrated?",
        "Tile area represents each commodity group's recorded value "
        "during the selected period."
    )

    treemap_data = (
        current.groupby("Commodity", as_index=False)["Value_USD_Bn"]
        .sum()
        .sort_values("Value_USD_Bn", ascending=False)
    )

    if not treemap_data.empty:
        fig = px.treemap(
            treemap_data,
            path=["Commodity"],
            values="Value_USD_Bn",
            color="Value_USD_Bn",
            color_continuous_scale=[
                "#DDEFF0",
                "#6DA9BC",
                "#087E8B",
                "#142B3B",
            ],
            labels={
                "Commodity": "Commodity group",
                "Value_USD_Bn": "Value (US$ billion)",
            },
        )

        fig.update_traces(
            texttemplate="%{label}<br>US$%{value:.2f}B",
            hovertemplate=(
                "<b>%{label}</b><br>"
                "Recorded value: US$%{value:.2f}B"
                "<extra></extra>"
            ),
        )

        fig.update_layout(
            coloraxis_showscale=False,
            margin=dict(l=10, r=10, t=15, b=10),
        )

        st.plotly_chart(
            style_fig(fig, 370),
            use_container_width=True,
            config={"displayModeBar": False, "responsive": True},
        )
    

# -----------------------------------------------------------------------------
# Partner explorer tab
# -----------------------------------------------------------------------------
if selected_page == "Partner explorer":
    st.write("")
    section("06 / Partner-market drill-down", "Explore one trading partner in detail", "Choose a named market to compare its selected-period value, comparable prior-year value and commodity mix.")
    partner_options_df = partner_totals.copy()
    if partner_options_df.empty:
        st.info("No named positive-value partner markets found for the selected filters.")
    else:
        # Rank options by selected-period value; the first option is the largest market.
        option_rows = partner_options_df["Country Name"].tolist()
        display_by_country = dict(zip(partner_options_df["Country Name"], partner_options_df["DisplayCountry"]))
        default_partner = option_rows[0]
        selected_partner = st.selectbox(
            "Choose partner market",
            option_rows,
            index=0,
            format_func=lambda c: display_by_country.get(c, c),
        )
        market_current = named_current[named_current["Country Name"] == selected_partner].copy()
        market_prior = named_prior[named_prior["Country Name"] == selected_partner].copy()
        market_value = market_current["Value_USD_Mn"].sum()
        market_prev_value = market_prior["Value_USD_Mn"].sum()
        market_yoy = (market_value / market_prev_value - 1) * 100 if market_prev_value > 0 else float("nan")
        market_share = market_value / partner_total * 100 if partner_total > 0 else float("nan")
        mc1, mc2, mc3, mc4 = st.columns(4, gap="medium")
        with mc1:
            kpi_card("PARTNER VALUE", money(market_value), period_label, TEAL)
        with mc2:
            kpi_card("YEAR-ON-YEAR", pct(market_yoy) if not pd.isna(market_yoy) else "No baseline", f"Compared with same months in {prior_year}", GREEN if not pd.isna(market_yoy) and market_yoy >= 0 else RED)
        with mc3:
            kpi_card("SHARE OF NAMED MARKETS", f"{market_share:.1f}%" if not pd.isna(market_share) else "—", "Share within the selected filters", "#315B75")
        with mc4:
            market_leader = market_current.groupby("Commodity")["Value_USD_Mn"].sum().sort_values(ascending=False)
            main_market_commodity = market_leader.index[0] if not market_leader.empty else "—"
            kpi_card("TOP COMMODITY", main_market_commodity, money(market_leader.iloc[0]) if not market_leader.empty else "No value", "#D39B49")

        chart_left, chart_right = st.columns([1.3, 1], gap="large")
        with chart_left:
            market_frames = []
            for market_df, label in [(market_prior, f"{prior_year} · comparable"), (market_current, f"{year}{' · YTD' if partial else ''}")]:
                if market_df.empty:
                    continue
                mm = market_df.groupby(["MonthNum", "Month"], as_index=False)["Value_USD_Mn"].sum()
                mm["Value_USD_Bn"] = mm["Value_USD_Mn"] / 1000
                mm["Period"] = label
                market_frames.append(mm)
            if market_frames:
                mtrend = pd.concat(market_frames, ignore_index=True)
                fig = px.line(mtrend, x="Month", y="Value_USD_Bn", color="Period", markers=True,
                              category_orders={"Month": period_month_order},
                              color_discrete_map={f"{prior_year} · comparable": "#A3B3C2", f"{year}{' · YTD' if partial else ''}": TEAL},
                              labels={"Month": "Month", "Value_USD_Bn": "Value (US$ billion)"})
                fig.update_traces(line_width=3, marker_size=6, hovertemplate="%{x}<br>US$%{y:,.2f}B<extra>%{fullData.name}</extra>")
                fig.update_layout(hovermode="x unified", legend_title_text="", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0))
                st.plotly_chart(style_fig(fig, 370), use_container_width=True, config={"displayModeBar": False})
        with chart_right:
            cmix = market_current.groupby("Commodity", as_index=False)["Value_USD_Mn"].sum().sort_values("Value_USD_Mn", ascending=False)
            cmix["Value_USD_Bn"] = cmix["Value_USD_Mn"] / 1000
            if not cmix.empty:
                fig = px.bar(cmix.sort_values("Value_USD_Bn"), x="Value_USD_Bn", y="Commodity", orientation="h",
                             text="Value_USD_Bn", labels={"Value_USD_Bn": "Value (US$ billion)", "Commodity": "Commodity"})
                fig.update_traces(marker_color=TEAL, text=[money_bn(v) if v >= 1 else money(v * 1000) for v in cmix.sort_values("Value_USD_Bn")["Value_USD_Bn"]], textposition="outside", cliponaxis=False,
                                  hovertemplate="%{y}<br>US$%{x:,.3f}B<extra></extra>")
                fig.update_layout(showlegend=False, yaxis_title="", xaxis_title="Value (US$ billion)")
                fig.update_xaxes(range=[0, float(cmix["Value_USD_Bn"].max()) * 1.28])
                st.plotly_chart(style_fig(fig, 370, horizontal=True), use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("No commodity breakdown available for this market.")

        market_compare = []
        for commodity in selected_commodities:
            cv = market_current.loc[market_current["Commodity"] == commodity, "Value_USD_Mn"].sum()
            pv = market_prior.loc[market_prior["Commodity"] == commodity, "Value_USD_Mn"].sum()
            market_compare.append({"Commodity": commodity, "Selected period (US$ B)": cv / 1000,
                                   "Comparable prior (US$ B)": pv / 1000,
                                   "YoY change (%)": (cv / pv - 1) * 100 if pv > 0 else float("nan")})
        mtable = pd.DataFrame(market_compare)
        mtable["Selected period (US$ B)"] = mtable["Selected period (US$ B)"].map(lambda v: f"${v:,.2f}B")
        mtable["Comparable prior (US$ B)"] = mtable["Comparable prior (US$ B)"].map(lambda v: f"${v:,.2f}B")
        mtable["YoY change (%)"] = mtable["YoY change (%)"].map(pct)
        st.dataframe(mtable, use_container_width=True, hide_index=True, height=compact_table_height(len(mtable), max_height=320))

# -----------------------------------------------------------------------------
# Data & methodology tab
# -----------------------------------------------------------------------------
elif selected_page == "Data & methodology":
    st.write("")
    section("07 / Data explorer", "Inspect and export the underlying records", "The table uses the selected analysis year and commodity filters. Values are presented in US dollars million, as supplied by the source CSV.")
    search = st.text_input("Search country or commodity", placeholder="e.g. United States, plastics, organic chemicals")
    table = current[["Date", "Year", "Country Name", "HS Code", "Commodity", "Value_USD_Mn"]].copy()
    table = table.rename(columns={"Value_USD_Mn": "Value (US$ million)"})
    if search.strip():
        q = search.strip().casefold()
        keep = table["Country Name"].astype(str).str.casefold().str.contains(q, na=False) | table["Commodity"].astype(str).str.casefold().str.contains(q, na=False) | table["HS Code"].astype(str).str.contains(q, na=False)
        table = table[keep]
    table = table.sort_values("Value (US$ million)", ascending=False)
    data_left, data_right = st.columns([1, 1], gap="large")
    with data_left:
        st.markdown("**Dataset snapshot**")
        snapshot = pd.DataFrame({
            "Field": ["Monthly observations (all years)", "Country × HS-code combinations", "Commodity groups in current view", "Country / partner labels", "Available years", "Latest available month"],
            "Value": [f"{len(data):,}", f"{data[['HS Code', 'Country Name']].drop_duplicates().shape[0]:,}", f"{len(selected_commodities)}", f"{data['Country Name'].nunique():,}", f"{min(years)}–{max(years)}", pd.Timestamp(year=latest_year, month=max(latest_months), day=1).strftime("%B %Y")],
        })
        st.dataframe(snapshot, use_container_width=True, hide_index=True, height=compact_table_height(len(snapshot), max_height=280))
    with data_right:
        st.markdown("**Definitions and limitations**")
        st.markdown("""
- **HS chapters included:** 27 mineral fuels and oils; 28 inorganic chemicals; 29 organic chemicals; 39 plastics; 40 rubber.
- **Units:** the source columns are in USD million. Charts convert values to USD billion for readability.
- **Year-on-year:** selected months are compared with the same months in the preceding year.
- **Partial year:** a year with fewer than 12 available months is labelled YTD.
- **Trade direction:** the CSV has no explicit import/export field. Verify the DGCIS query settings before claiming this is imports, exports, or total trade.
- **Category scope:** these are broad HS chapters, not a perfectly isolated petrochemical-only classification.
- **Interpretation:** observed growth and concentration are descriptive; this dashboard does not infer causes or forecast future values.
        """)
    st.write("")
    st.markdown(f"**Filtered records: {len(table):,}**")
    st.dataframe(table, use_container_width=True, hide_index=True, height=480,
                 column_config={"Date": st.column_config.DateColumn("Month", format="MMM YYYY"),
                                "Value (US$ million)": st.column_config.NumberColumn("Value (US$ million)", format="%.2f")})
    st.download_button(
        "Download filtered CSV",
        data=table.to_csv(index=False).encode("utf-8"),
        file_name=f"petrotrade_{year}_filtered.csv",
        mime="text/csv",
        type="primary",
    )

st.divider()
st.markdown(
    "<div class='panel-note'>Data source: DGCIS CSV supplied for this project. Country labels are lightly normalized for display only. The dataset does not identify the trade direction, and HS chapters are broad groups. Insights summarize recorded patterns and should not be interpreted as causal claims.</div>",
    unsafe_allow_html=True,
)
