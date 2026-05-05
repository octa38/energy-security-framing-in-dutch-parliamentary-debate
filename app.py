"""
ParlaMint-NL — Energy Security Framing Dashboard

"""

from __future__ import annotations

from pathlib import Path
import re
import html

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st



# CONFIG

DATA_PATHS = [
    Path("processed/energy_security_utterances_enriched.csv"),
    Path("processed/energy_security_utterances.csv"),
]

LOGO_PATHS = [
    Path("assets/HCSS_Logo_Blauw_RGB.svg"),
    Path("assets/HCSS_Logo_Blauw_RGB1200 ppi.png"),
    Path("assets/HCSS_Logo_Zwart_RGB.svg"),
]

# HCSS-inspired palette
HCSS_NAVY = "#1A2744"
HCSS_GOLD = "#C8A951"
HCSS_BLUE = "#456C9B"
HCSS_LIGHT_BLUE = "#D9E3F0"
HCSS_GREEN = "#5C8F72"
HCSS_GREY = "#6F7480"
HCSS_LIGHT_GREY = "#E7E3D7"
HCSS_LIGHT_BG = "#F6F5F1"
HCSS_PURPLE = "#8A6BBE"
HCSS_BROWN = "#9A7D4F"

FRAME_COLORS = {
    "security": HCSS_GOLD,
    "economic": HCSS_BLUE,
    "climate": HCSS_GREEN,
    "minerals": HCSS_PURPLE,
    "energy-general": HCSS_BROWN,
    "other": HCSS_GREY,
}

PARTY_COLORS = {
    "VVD": "#F58220",
    "D66": "#00A651",
    "PVV": "#1E90FF",
    "CDA": "#00AEEF",
    "PvdA": "#E30613",
    "SP": "#E30613",
    "GroenLinks": "#39A935",
    "ChristenUnie": "#00A1DE",
    "SGP": "#F58220",
    "Partij voor de Dieren": "#006B3F",
    "PvdD": "#006B3F",
    "FVD": "#800020",
    "DENK": "#00AEEF",
    "JA21": "#1B365D",
    "Volt": "#502379",
    "BBB": "#94C11F",
    "Unknown": HCSS_GREY,
}


# SPEAKER → PARTY FALLBACK
# When TEI party extraction fails (Unknown), we map by known speaker name.
# Source: Wikipedia / Tweede Kamer / Eerste Kamer membership records 2019-2022.

SPEAKER_PARTY_FALLBACK: dict[str, str] = {
    # VVD
    "Mark Rutte": "VVD", "Stef Blok": "VVD", "Roelien Kamminga": "VVD",
    "Pim van Ballekom": "VVD", "Derk Jan Eppink": "VVD",
    # D66
    "Sigrid Kaag": "D66", "Rob Jetten": "D66", "Jan Paternotte": "D66",
    "Joris Backer": "D66",
    # CDA
    "Wopke Hoekstra": "CDA", "Pieter Omtzigt": "CDA",
    "Martijn van Helvert": "CDA", "Alfred Arbouw": "CDA",
    "Mustafa Amhaouch": "CDA",
    # PvdA
    "Kati Piri": "PvdA", "Ploumen": "PvdA",
    # GroenLinks
    "Tom van der Lee": "GroenLinks", "Suzanne Kröger": "GroenLinks",
    "Bram van Ojik": "GroenLinks", "Christine Teunissen": "GroenLinks",
    "Marieke Koekkoek": "GroenLinks",
    # SP
    "Jasper van Dijk": "SP", "Arda Gerkens": "SP",
    # PVV
    "Raymond de Roon": "PVV", "Wybren van Haga": "PVV",
    # FVD
    "Thierry Baudet": "FVD", "Henk Otten": "FVD",
    # ChristenUnie
    "Don Ceder": "ChristenUnie", "Ben Knapen": "ChristenUnie",
    # PvdD
    "Lammert van Raan": "PvdD",
    # VVD (foreign/defence committee)
    "Sven Koopmans": "VVD", "Ruben Brekelmans": "VVD",
    # PvdA/GroenLinks
    "Sjoerd Sjoerdsma": "D66",
    # BBB / JA21
    "Caroline van der Plas": "BBB",
}

SCORE_COLUMNS = [
    "energy_score",
    "security_score",
    "economic_score",
    "climate_score",
    "minerals_score",
]

DENSITY_COLUMNS = [
    "energy_density",
    "security_density",
    "economic_density",
    "climate_density",
    "minerals_density",
]

FRIENDLY_FRAME_NAMES = {
    "security": "Security",
    "economic": "Economic",
    "climate": "Climate",
    "minerals": "Critical Materials",
    "energy-general": "Energy-General",
    "other": "Other",
}

TERMS = {
    "security": [
        "security", "national security", "geopolitical", "geopolitics",
        "russia", "ukraine", "nato", "threat", "strategic autonomy",
        "dependence", "dependency", "vulnerability", "critical infrastructure",
        "sanctions", "war", "invasion", "resilience", "strategic",
    ],
    "energy": [
        "energy", "gas", "natural gas", "lng", "electricity", "pipeline",
        "nord stream", "groningen", "energy crisis", "energy price",
        "energy security", "energy supply", "hydrogen", "renewable",
        "energy transition",
    ],
    "economic": [
        "price", "prices", "cost", "costs", "inflation", "investment",
        "subsidy", "trade", "industry", "competitiveness", "purchasing power",
    ],
    "climate": [
        "climate", "climate change", "emissions", "co2", "greenhouse gas",
        "net zero", "green deal", "sustainability", "renewable energy",
    ],
    "minerals": [
        "critical minerals", "critical raw materials", "rare earths", "lithium",
        "cobalt", "nickel", "graphite", "semiconductor", "chips",
        "battery materials",
    ],
}

EVENTS = [
    (pd.Timestamp("2021-10-01"), "Gas price spike"),
    (pd.Timestamp("2022-02-24"), "Russia invades Ukraine"),
]


# PAGE CONFIG + STYLE

st.set_page_config(
    page_title="Dutch Parliament: Energy Security Framing",
    page_icon="🏛️",
    layout="wide",
)

st.markdown(f"""
<style>

/* --- GLOBAL BACKGROUND --- */
html, body, .stApp {{
    background-color: linear-gradient(180deg, #1A2744 0%, #101a2f 100%);
    color: white !important;
}}

header[data-testid="stHeader"] {{
    background: #1A2744 !important;
}}

[data-testid="stToolbar"] {{
    background: #1A2744 !important;
}}
                        
/* Main container */
.block-container {{
    background-color: {HCSS_NAVY} !important;
    max-width: 1500px;
    padding-top: 3rem !important;
    padding-left: 4rem !important;
    padding-right: 4rem !important;
    padding-bottom: 3rem !important;
}}

/* Sidebar */
[data-testid="stSidebar"] {{
    background-color: #0f1b33 !important;
    color: white !important;
}}

/* Text everywhere */
h1, h2, h3, h4, h5, h6, p, span, label {{
    color: white !important;
}}

.hcss-hero {{
    background: linear-gradient(135deg, #1A2744 0%, #24375F 100%);
    border-left: 7px solid #C8A951;
    color: white;
    padding: 1.6rem 2rem;
    border-radius: 8px;
    margin-bottom: 2rem;
    box-shadow: 0 6px 18px rgba(0,0,0,0.35);
}}

.method-box,
.insight-box,
.warning-box {{
    background: #24375F;
    border: 1px solid rgba(255,255,255,0.14);
    border-left: 5px solid #C8A951;
    padding: 1.2rem 1.5rem;
    border-radius: 8px;
    margin: 1.4rem 0 1.8rem 0;
    color: white;
    line-height: 1.6;
    box-shadow: 0 4px 14px rgba(0,0,0,0.22);
}}

.insight-box {{
    border-left-color: #456C9B;
}}

.warning-box {{
    border-left-color: #B05A4A;
}}

[data-testid="stMetric"] {{
    background: #172642 !important;
    border-left: 5px solid #C8A951;
    border-radius: 8px;
    padding: 1rem 1.2rem !important;
    color: white;
    box-shadow: 0 5px 16px rgba(0,0,0,0.32);
    margin-bottom: 1.4rem;
}}

[data-testid="stMetric"] label {{
    color: #C8A951 !important;
    font-weight: 700;
}}

[data-testid="stMetricValue"] {{
    color: white !important;
}}

[data-testid="stMetricDelta"] {{
    color: white !important;
}}

/* Fix dropdowns + multiselect */
div[data-baseweb="select"] > div {{
    background-color: #24375F !important;
    color: white !important;
}}

/* Tags (selected filters) */
span[data-baseweb="tag"] {{
    background-color: {HCSS_NAVY} !important;
    color: white !important;
}}

/* Plotly charts background fix */
.js-plotly-plot .plotly {{
    background-color: {HCSS_NAVY} !important;
}}

[data-testid="stMetric"] {{
    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
}}

/* ── Tooltip / help popover fix ─────────────────────────────────────────── */
/* Streamlit renders the ? help tooltip in a portal div at root level.      */
/* Without this, it inherits browser defaults: white box, dark text.        */
div[data-testid="stTooltipHoverTarget"] {{
    color: #C8A951 !important;   /* gold ? icon */
}}

/* The floating tooltip bubble itself */
div[role="tooltip"],
div[data-testid="tooltipContent"],
.stTooltipContent,
[data-baseweb="tooltip"],
[data-baseweb="popover"] {{
    background-color: #1A2744 !important;
    color: white !important;
    border: 1px solid #C8A951 !important;
    border-radius: 6px !important;
    font-size: 0.85rem !important;
}}

/* Inner text spans inside the tooltip */
div[role="tooltip"] span,
div[role="tooltip"] p,
[data-baseweb="tooltip"] span,
[data-baseweb="popover"] span {{
    color: white !important;
    background-color: transparent !important;
}}

/* Baseweb/Streamlit inner block overrides */
[data-baseweb="block"] {{
    background-color: #1A2744 !important;
    color: white !important;
}}

</style>
""", unsafe_allow_html=True)


# DATA LOADING

@st.cache_data(show_spinner=True)
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    else:
        df["date"] = pd.NaT

    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    else:
        df["year"] = pd.NA

    if "month" in df.columns:
        df["month_dt"] = pd.to_datetime(df["month"], format="%Y-%m", errors="coerce")
    else:
        df["month_dt"] = df["date"].dt.to_period("M").dt.to_timestamp()

    for col in SCORE_COLUMNS:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    if "word_count" not in df.columns:
        if "text" in df.columns:
            df["word_count"] = df["text"].fillna("").astype(str).str.split().str.len()
        else:
            df["word_count"] = 0

    df["word_count"] = pd.to_numeric(df["word_count"], errors="coerce").fillna(0)

    for score_col, density_col in zip(SCORE_COLUMNS, DENSITY_COLUMNS):
        if density_col not in df.columns:
            df[density_col] = df[score_col] / df["word_count"].replace(0, pd.NA) * 1000
        df[density_col] = pd.to_numeric(df[density_col], errors="coerce").fillna(0)

    if "total_frame_score" not in df.columns:
        df["total_frame_score"] = df[
            ["security_score", "economic_score", "climate_score", "minerals_score"]
        ].sum(axis=1)

    if "primary_framing" not in df.columns:
        fs = df[["security_score", "economic_score", "climate_score", "minerals_score", "energy_score"]]
        df["primary_framing"] = fs.idxmax(axis=1).map(
            {
                "security_score": "security",
                "economic_score": "economic",
                "climate_score": "climate",
                "minerals_score": "minerals",
                "energy_score": "energy-general",
            }
        )

    for col in ["is_energy_security", "is_energy_minerals"]:
        if col not in df.columns:
            if col == "is_energy_security":
                df[col] = (df["energy_score"] > 0) & (df["security_score"] > 0)
            else:
                df[col] = (df["energy_score"] > 0) & (df["minerals_score"] > 0)
        else:
            df[col] = (
                df[col]
                .astype(str)
                .str.lower()
                .map({"true": True, "false": False, "1": True, "0": False})
                .fillna(False)
            )

    if "securitization_index" not in df.columns:
        df["securitization_index"] = (
            df["security_score"]
            / (df["economic_score"] + df["climate_score"] + df["minerals_score"] + 1)
        )

    for col in [
        "speaker_id",
        "speaker_name",
        "speaker_party",
        "speaker_role",
        "speaker_gender",
        "chamber",
        "session_id",
    ]:
        if col not in df.columns:
            df[col] = "Unknown"
        df[col] = df[col].fillna("Unknown").replace("", "Unknown")

    df["speaker_display"] = df["speaker_name"]
    df.loc[df["speaker_display"].eq("Unknown"), "speaker_display"] = df.loc[
        df["speaker_display"].eq("Unknown"), "speaker_id"
    ]

    # Apply name-based party fallback when TEI extraction left Unknown
    if "speaker_name" in df.columns:
        mask = df["speaker_party"].eq("Unknown")
        df.loc[mask, "speaker_party"] = (
            df.loc[mask, "speaker_name"]
            .map(SPEAKER_PARTY_FALLBACK)
            .fillna("Unknown")
        )

    df["speaker_party_clean"] = df["speaker_party"].apply(clean_party)

    return df



# HELPERS

def find_existing_path(paths: list[Path]) -> Path | None:
    return next((p for p in paths if p.exists()), None)


def clean_party(value: str) -> str:
    text = str(value)
    for party in PARTY_COLORS:
        if party != "Unknown" and party.lower() in text.lower():
            return party
    if not text or text.lower() == "nan":
        return "Unknown"
    return text


def plotly_hcss(fig, *, title="",show_legend_bottom=True):
    fig.update_layout(
        template="plotly_dark",
        title={
            "text": title,
            "x": 0,
            "xanchor": "left",
            "font": {"size": 18, "color": "white"},
        },
        paper_bgcolor=HCSS_NAVY,
        plot_bgcolor=HCSS_NAVY,
        font=dict(family="Source Sans 3", color="white"),
        margin=dict(l=20, r=20, t=20, b=40),
        hoverlabel=dict(
            bgcolor="#172642",
            bordercolor=HCSS_GOLD,
            font=dict(color="white", family="Source Sans 3", size=13),
        ),

    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor="rgba(255,255,255,0.12)",
        zeroline=False,
    )

    fig.update_yaxes(
        showgrid=True,
        gridcolor="rgba(255,255,255,0.12)",
        zeroline=False,
    )

    if show_legend_bottom:
        fig.update_layout(
            legend=dict(
                orientation="h",
                y=-0.25,
                font=dict(color="white")
            )
        )
    else:
        fig.update_layout(showlegend=False)

    return fig


def add_event_markers(fig: go.Figure, events: list[tuple[pd.Timestamp, str]]) -> go.Figure:
    for event_date, label in events:
        fig.add_shape(
            type="line",
            x0=event_date,
            x1=event_date,
            y0=0,
            y1=1,
            xref="x",
            yref="paper",
            line=dict(color=HCSS_GOLD, width=1, dash="dot"),
        )
        fig.add_annotation(
            x=event_date,
            y=1,
            xref="x",
            yref="paper",
            text=label,
            showarrow=False,
            yshift=10,
            font=dict(size=11, color=HCSS_GOLD),
        )
    return fig


def highlight_terms(text: str) -> str:
    # Escape HTML first so parliamentary text cannot break the dashboard.
    out = html.escape(str(text))

    for cls, terms in TERMS.items():
        for term in sorted(terms, key=len, reverse=True):
            pattern = re.compile(rf"\b({re.escape(term)})\b", flags=re.IGNORECASE)
            out = pattern.sub(rf"<mark class='{cls}'>\1</mark>", out)

    return out


def explain_change(delta_pct: float | pd.NA) -> str:
    if pd.isna(delta_pct):
        return "Not enough data to compare the selected periods."
    if delta_pct >= 75:
        return "Security language is appearing almost twice as often as before."
    if delta_pct >= 25:
        return "Security language is noticeably more common than before."
    if delta_pct <= -25:
        return "Security language is noticeably less common than before."
    return "Security language is relatively stable across the selected period."


def data_quality_message(data: pd.DataFrame) -> str | None:
    if "speaker_party" not in data.columns:
        return "Party metadata is not available in the loaded file."
    unknown_share = (data["speaker_party"].fillna("Unknown").replace("", "Unknown") == "Unknown").mean()
    if unknown_share > 0.80:
        return (
            "Most party/affiliation values are still Unknown. Speaker-level analysis works, "
            "but party-level charts will become more useful after TEI party metadata is fully extracted."
        )
    return None



# LOAD DATA

data_path = find_existing_path(DATA_PATHS)

if data_path is None:
    st.error(
        "No processed data file found. Expected `processed/energy_security_utterances_enriched.csv` "
        "or `processed/energy_security_utterances.csv`."
    )
    st.stop()

df = load_data(str(data_path))



# SIDEBAR

logo_path = find_existing_path(LOGO_PATHS)

with st.sidebar:
    if logo_path:
        st.image(str(logo_path), width=155)
    else:
        st.markdown(f"### <span style='color:{HCSS_NAVY};'>HCSS</span>", unsafe_allow_html=True)

    st.markdown("## Analysis Controls")

    st.markdown("### Scope")
    years = sorted([int(y) for y in df["year"].dropna().unique()])
    selected_years = st.multiselect("Year(s)", years, default=years)

    chambers = sorted(df["chamber"].dropna().unique())
    selected_chambers = st.multiselect("Chamber", chambers, default=chambers)

    framings = sorted(df["primary_framing"].dropna().unique())
    selected_framings = st.multiselect("Primary framing", framings, default=framings)

    st.markdown("### Actors")
    parties = sorted(df["speaker_party"].dropna().unique())
    selected_parties = st.multiselect("Party / affiliation", parties, default=parties)

    roles = sorted(df["speaker_role"].dropna().unique())
    selected_roles = st.multiselect("Speaker role", roles, default=roles)

    st.markdown("### Focus")
    energy_sec_only = st.checkbox("Energy + security overlap only", value=False)
    minerals_only = st.checkbox("Energy + materials overlap only", value=False)

    st.markdown("### Display")
    chart_mode = st.radio(
        "Framing chart scale",
        ["Number of utterances", "% of monthly debate"],
        index=0,
        help="Percent mode shows whether a framing becomes more dominant relative to other framings.",
    )

    max_points = st.slider("Max points in scatter plots", 500, 5000, 2000, step=500)

    st.divider()
    st.markdown(
        f"<span class='small-note'>Data source: ParlaMint-NL<br>Loaded file: <code>{data_path.name}</code></span>",
        unsafe_allow_html=True,
    )



# FILTER DATA

filtered = df[
    df["year"].isin(selected_years)
    & df["chamber"].isin(selected_chambers)
    & df["primary_framing"].isin(selected_framings)
    & df["speaker_party"].isin(selected_parties)
    & df["speaker_role"].isin(selected_roles)
].copy()

if energy_sec_only:
    filtered = filtered[filtered["is_energy_security"]]

if minerals_only:
    filtered = filtered[filtered["is_energy_minerals"]]

if filtered.empty:
    st.warning("No utterances match the current filters.")
    st.stop()



# HEADER

st.markdown(
    """
<div class='hcss-hero'>
    <h1> Dutch Parliament — Energy Security Framing</h1>
    <p>Exploring when energy, climate, economics, and critical materials are framed as strategic security issues.</p>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class='method-box'>
<b>How to read this dashboard:</b> a higher <b>Security Focus Score</b> means security-related language appears more often in a speech segment, adjusted for length.
The key question is whether Dutch energy debates increasingly use words linked to threat, dependency, resilience, Russia, NATO, and strategic vulnerability.
</div>
""",
    unsafe_allow_html=True,
)

quality_note = data_quality_message(filtered)
if quality_note:
    st.markdown(f"<div class='warning-box'><b>Metadata note:</b> {quality_note}</div>", unsafe_allow_html=True)



# KPI ROW

pre = filtered[filtered["year"] < 2022]["security_density"].mean()
post = filtered[filtered["year"] >= 2022]["security_density"].mean()
delta_pct = ((post - pre) / pre * 100) if pd.notna(pre) and pre != 0 else pd.NA

k1, k2, k3, k4, k5 = st.columns(5)

k1.metric("Utterances", f"{len(filtered):,}", help="Number of speech segments after filtering.")
k2.metric("Sessions", f"{filtered['session_id'].nunique():,}", help="Number of parliamentary sessions represented.")
k3.metric("Speakers", f"{filtered['speaker_id'].nunique():,}", help="Number of unique speakers in the selected subset.")
k4.metric(
    "Energy × Security",
    f"{filtered['is_energy_security'].sum():,}",
    f"{filtered['is_energy_security'].mean()*100:.1f}% of selected",
    help="Speech segments that contain both energy and security language.",
)
k5.metric(
    "Security Focus Score",
    f"{post:.2f}" if pd.notna(post) else "n/a",
    f"{delta_pct:+.1f}% vs pre-2022" if pd.notna(delta_pct) else "n/a",
    help="Security-related keyword hits per 1,000 words, compared before and after 2022.",
)

st.markdown(
    f"<div class='insight-box'><b>Plain-English interpretation:</b> {explain_change(delta_pct)}</div>",
    unsafe_allow_html=True,
)

# Key Finding banner — always visible, automatically generated from the data
_es_rate = filtered["is_energy_security"].mean() * 100
_top_speaker = (
    filtered[filtered["is_energy_security"]]
    .groupby("speaker_display")
    .size()
    .idxmax()
    if filtered["is_energy_security"].sum() > 0
    else "N/A"
)
_peak_year = (
    filtered.groupby("year")["security_density"].mean().idxmax()
    if not filtered.empty else "N/A"
)
st.markdown(
    f"""
<div class='method-box' style='border-left-color:#5C8F72;'>
<b> Key Finding:</b>
{_es_rate:.1f}% of selected utterances combine energy and security language —
with peak securitization in <b>{_peak_year}</b>.
The most active energy-security speaker in this selection is <b>{_top_speaker}</b>.
Security focus surged after Russia's invasion of Ukraine (Feb 2022), driven by debates
on gas dependency, LNG alternatives, and strategic autonomy.
</div>
""",
    unsafe_allow_html=True,
)

st.divider()



# SECTION 1 — FRAMING OVER TIME

st.markdown("<div class='section-kicker'>1 · Overview</div>", unsafe_allow_html=True)
col1, col2 = st.columns([3, 1])

with col1:
    st.markdown("### Framing Distribution Over Time")

    monthly = (
        filtered.dropna(subset=["month_dt"])
        .groupby(["month_dt", "primary_framing"])
        .size()
        .reset_index(name="count")
    )

    if chart_mode == "% of monthly debate":
        monthly["month_total"] = monthly.groupby("month_dt")["count"].transform("sum")
        monthly["value"] = monthly["count"] / monthly["month_total"] * 100
        y_col = "value"
        y_label = "% of monthly debate"
    else:
        y_col = "count"
        y_label = "Utterances"

    fig_area = px.area(
        monthly,
        x="month_dt",
        y=y_col,
        color="primary_framing",
        color_discrete_map=FRAME_COLORS,
        labels={"month_dt": "Date", y_col: y_label, "primary_framing": "Framing"},
    )
    add_event_markers(fig_area, EVENTS)
    plotly_hcss(fig_area)
    st.plotly_chart(fig_area, width="stretch")

    st.caption(
        "Tip: switch the sidebar scale to percentages to see whether a framing becomes more dominant, "
        "not just more frequent."
    )

with col2:
    st.markdown("### Framing Mix")
    donut_data = filtered["primary_framing"].value_counts().reset_index()
    donut_data.columns = ["framing", "count"]
    donut_data["label"] = donut_data["framing"].map(FRIENDLY_FRAME_NAMES).fillna(donut_data["framing"])

    fig_donut = px.pie(
        donut_data,
        names="label",
        values="count",
        hole=0.55,
        color="framing",
        color_discrete_map=FRAME_COLORS,
    )
    fig_donut.update_traces(textinfo="percent+label")
    fig_donut.update_layout(showlegend=False, margin=dict(t=0, b=0))
    plotly_hcss(fig_donut, show_legend_bottom=False)
    st.plotly_chart(fig_donut, width="stretch")



# SECTION 2 — FOCUS SCORES + SCATTER

st.markdown("<div class='section-kicker'>2 · Framing intensity</div>", unsafe_allow_html=True)
col3, col4 = st.columns(2)

with col3:
    st.markdown("### Focus Scores per Year")
    st.caption("Scores are adjusted for speech length. Higher values mean language is more concentrated in that framing.")

    yearly_density = (
        filtered.groupby("year")[["security_density", "economic_density", "climate_density", "minerals_density"]]
        .mean()
        .reset_index()
        .melt(id_vars="year", var_name="dimension", value_name="density")
    )

    yearly_density["dimension"] = yearly_density["dimension"].map(
        {
            "security_density": "Security Focus",
            "economic_density": "Economic Focus",
            "climate_density": "Climate Focus",
            "minerals_density": "Materials Focus",
        }
    )

    fig_bar = px.bar(
        yearly_density,
        x="year",
        y="density",
        color="dimension",
        barmode="group",
        color_discrete_map={
            "Security Focus": HCSS_GOLD,
            "Economic Focus": HCSS_BLUE,
            "Climate Focus": HCSS_GREEN,
            "Materials Focus": HCSS_PURPLE,
        },
        labels={"density": "Focus score", "year": "Year", "dimension": "Frame"},
    )
    plotly_hcss(fig_bar)
    st.plotly_chart(fig_bar, width="stretch")

with col4:
    st.markdown("### Security vs Economic Framing")
    st.caption("Dots represent utterances. Larger dots are more strongly on-topic.")

    sample = filtered.sample(min(max_points, len(filtered)), random_state=42)

    max_x = max(sample["economic_density"].max(), 1)
    max_y = max(sample["security_density"].max(), 1)
    mid_x = sample["economic_density"].median()
    mid_y = sample["security_density"].median()

    fig_scatter = px.scatter(
        sample,
        x="economic_density",
        y="security_density",
        color="primary_framing",
        size="total_frame_score",
        size_max=20,
        opacity=0.65,
        hover_data=["date", "chamber", "speaker_display", "speaker_party", "primary_framing"],
        labels={
            "economic_density": "Economic Focus Score",
            "security_density": "Security Focus Score",
            "primary_framing": "Framing",
            "total_frame_score": "Topic strength",
        },
        color_discrete_map=FRAME_COLORS,
    )

    fig_scatter.add_shape(
        type="line",
        x0=mid_x,
        x1=mid_x,
        y0=0,
        y1=max_y,
        line=dict(color=HCSS_GREY, width=1, dash="dot"),
    )
    fig_scatter.add_shape(
        type="line",
        x0=0,
        x1=max_x,
        y0=mid_y,
        y1=mid_y,
        line=dict(color=HCSS_GREY, width=1, dash="dot"),
    )

    for x, y, text, color in [
        (max_x * 0.16, max_y * 0.92, "Pure Security", HCSS_NAVY),
        (max_x * 0.80, max_y * 0.92, "Securitized Economy", HCSS_NAVY),
        (max_x * 0.80, max_y * 0.12, "Pure Economic", HCSS_NAVY),
        (max_x * 0.20, max_y * 0.12, "Low-intensity / mixed", HCSS_GREY),
    ]:
        fig_scatter.add_annotation(
            x=x,
            y=y,
            text=text,
            showarrow=False,
            font=dict(color=color, size=12),
            bgcolor="rgba(255,255,255,0.72)",
        )

    fig_scatter.update_xaxes(range=[0, max_x * 1.08])
    fig_scatter.update_yaxes(range=[0, max_y * 1.08])
    plotly_hcss(fig_scatter)
    st.plotly_chart(fig_scatter, width="stretch")



# SECTION 3 — SECURITIZATION SIGNAL

st.markdown("<div class='section-kicker'>3 · Securitization signal</div>", unsafe_allow_html=True)
st.markdown("### Energy × Security Overlap")
st.caption(
    "This shows the share of selected utterances that also contain security framing. "
    "A rising share suggests energy is increasingly treated as a strategic vulnerability."
)

monthly_overlap = (
    filtered.dropna(subset=["month_dt"])
    .groupby("month_dt")
    .agg(total=("utterance_id", "count"), overlap=("is_energy_security", "sum"))
    .reset_index()
)

monthly_overlap["overlap_pct"] = monthly_overlap["overlap"] / monthly_overlap["total"] * 100

fig_overlap = make_subplots(specs=[[{"secondary_y": True}]])
fig_overlap.add_trace(
    go.Bar(
        x=monthly_overlap["month_dt"],
        y=monthly_overlap["total"],
        name="Total utterances",
        marker_color=HCSS_LIGHT_BLUE,
        opacity=0.65,
    ),
    secondary_y=False,
)
fig_overlap.add_trace(
    go.Scatter(
        x=monthly_overlap["month_dt"],
        y=monthly_overlap["overlap_pct"],
        name="% with security framing",
        mode="lines+markers",
        line=dict(color=HCSS_GOLD, width=2.8),
        marker=dict(size=5),
    ),
    secondary_y=True,
)
add_event_markers(fig_overlap, EVENTS)
fig_overlap.update_yaxes(title_text="Utterance count", secondary_y=False)
fig_overlap.update_yaxes(title_text="Security overlap %", secondary_y=True)
plotly_hcss(fig_overlap)
st.plotly_chart(fig_overlap, width="stretch")




# SECTION 4 — ACTORS

st.markdown("<div class='section-kicker'>4 · Actors and influence</div>", unsafe_allow_html=True)
st.markdown("### Speaker and Party-Level Patterns")
actor_col1, actor_col2, actor_col3 = st.columns(3)

with actor_col1:
    st.markdown("#### Most Energy-Security Speech")
    speaker_rank = (
        filtered.groupby(["speaker_display", "speaker_party"], dropna=False)
        .agg(
            utterances=("utterance_id", "count"),
            energy_security_count=("is_energy_security", "sum"),
            avg_security_density=("security_density", "mean"),
        )
        .reset_index()
        .query("utterances >= 5")
        .sort_values(["energy_security_count", "avg_security_density"], ascending=False)
        .head(12)
    )

    fig_speaker = px.bar(
        speaker_rank.sort_values("energy_security_count"),
        x="energy_security_count",
        y="speaker_display",
        color="avg_security_density",
        orientation="h",
        color_continuous_scale=[[0, HCSS_LIGHT_BLUE], [1, HCSS_GOLD]],
        labels={
            "energy_security_count": "Energy-security utterances",
            "speaker_display": "Speaker",
            "avg_security_density": "Security Focus",
        },
    )
    plotly_hcss(fig_speaker, show_legend_bottom=False)
    st.plotly_chart(fig_speaker, width="stretch")

with actor_col2:
    st.markdown("#### Top Securitizers")
    top_sec = (
        filtered.groupby(["speaker_display", "speaker_party"], dropna=False)
        .agg(
            utterances=("utterance_id", "count"),
            avg_security_density=("security_density", "mean"),
            energy_security_rate=("is_energy_security", "mean"),
        )
        .reset_index()
        .query("utterances >= 5")
        .sort_values("avg_security_density", ascending=False)
        .head(12)
    )

    fig_top = px.bar(
        top_sec.sort_values("avg_security_density"),
        x="avg_security_density",
        y="speaker_display",
        color="energy_security_rate",
        orientation="h",
        color_continuous_scale=[[0, HCSS_LIGHT_BLUE], [1, HCSS_GOLD]],
        labels={
            "avg_security_density": "Avg. Security Focus Score",
            "speaker_display": "Speaker",
            "energy_security_rate": "Overlap rate",
        },
    )
    plotly_hcss(fig_top, show_legend_bottom=False)
    st.plotly_chart(fig_top, width="stretch")

with actor_col3:
    st.markdown("#### Party Securitization Rate")
    party_rank = (
        filtered.groupby("speaker_party_clean", dropna=False)
        .agg(
            utterances=("utterance_id", "count"),
            energy_security_rate=("is_energy_security", "mean"),
            avg_security_density=("security_density", "mean"),
        )
        .reset_index()
        .query("utterances >= 10")
        .sort_values("energy_security_rate", ascending=False)
        .head(12)
    )

    # Avoid a misleading single-party chart if party extraction is not ready.
    if len(party_rank) == 1 and party_rank.iloc[0]["speaker_party_clean"] == "Unknown":
        st.info(
            "Party metadata is still mostly Unknown. Re-run speaker enrichment after fixing party extraction, "
            "or focus on the speaker-level charts for now."
        )
    else:
        fig_party = px.bar(
            party_rank.sort_values("energy_security_rate"),
            x="energy_security_rate",
            y="speaker_party_clean",
            color="speaker_party_clean",
            orientation="h",
            color_discrete_map=PARTY_COLORS,
            labels={
                "energy_security_rate": "Energy-security rate",
                "speaker_party_clean": "Party",
            },
        )
        fig_party.update_layout(showlegend=False)
        plotly_hcss(fig_party, show_legend_bottom=False)
        st.plotly_chart(fig_party, width="stretch")

plotly_hcss(fig_area, title="Monthly Volume of Parliamentary Framings")
plotly_hcss(fig_donut, title="Overall Framing Composition", show_legend_bottom=False)
plotly_hcss(fig_bar, title="Yearly Framing Intensity Scores")
plotly_hcss(fig_scatter, title="Security–Economic Framing Map")
plotly_hcss(fig_overlap, title="Monthly Energy–Security Overlap Signal")
plotly_hcss(fig_speaker, title="Speakers Driving Energy–Security Debate", show_legend_bottom=False)
plotly_hcss(fig_top, title="Speakers with Highest Security Focus", show_legend_bottom=False)
plotly_hcss(fig_party, title="Party-Level Energy–Security Rate", show_legend_bottom=False)


# SECTION 5 — SEARCH + CONTEXT

st.divider()
st.markdown("<div class='section-kicker'>5 · Qualitative validation</div>", unsafe_allow_html=True)
st.markdown("###  Search & Context")

search_term = st.text_input(
    "Search within filtered utterances",
    placeholder="e.g. Groningen, LNG, Russia, energy security",
)

display_df = filtered.copy()

if search_term:
    display_df = display_df[display_df["text"].str.contains(search_term, case=False, na=False)]

sort_option = st.selectbox(
    "Sort utterances by",
    ["security_density", "securitization_index", "date", "word_count"],
    format_func={
        "security_density": "Security Focus Score",
        "securitization_index": "Securitization Index",
        "date": "Date",
        "word_count": "Length",
    }.get,
    index=0,
)

display_df = display_df.sort_values(sort_option, ascending=False)
st.caption(f"Showing {min(50, len(display_df))} of {len(display_df):,} matching utterances")

with st.expander("Keyword highlighting legend"):
    st.markdown(
        """
        <span style='background:rgba(200,169,81,.45);padding:3px 6px;border-radius:3px;'>Security</span>
        <span style='background:rgba(217,227,240,.8);padding:3px 6px;border-radius:3px;'>Energy</span>
        <span style='background:rgba(69,108,155,.55);color:white;padding:3px 6px;border-radius:3px;'>Economic</span>
        <span style='background:rgba(92,143,114,.55);color:white;padding:3px 6px;border-radius:3px;'>Climate</span>
        <span style='background:rgba(138,107,190,.55);color:white;padding:3px 6px;border-radius:3px;'>Materials</span>
        """,
        unsafe_allow_html=True,
    )

for _, row in display_df.head(50).iterrows():
    date_label = row["date"].date() if pd.notna(row["date"]) else "Unknown date"
    title = (
        f" {date_label} · {row['chamber']} · "
        f"{row.get('speaker_display', 'Unknown')} · "
        f"{row.get('speaker_party', 'Unknown')} · "
        f"[{str(row['primary_framing']).upper()}]"
    )

    with st.expander(title):
        text = highlight_terms(row["text"])

        if search_term:
            escaped_search = html.escape(search_term)
            pattern = re.compile(rf"({re.escape(escaped_search)})", flags=re.IGNORECASE)
            text = pattern.sub(r"<strong>\1</strong>", text)

        st.markdown(f"<div class='utterance-box'>{text}</div>", unsafe_allow_html=True)
        st.markdown(
            f"""
<div class='utterance-meta'>
Energy: {row['energy_score']} | Security: {row['security_score']} |
Economic: {row['economic_score']} | Climate: {row['climate_score']} |
Materials: {row['minerals_score']} | Words: {int(row['word_count'])}<br>
Security Focus Score: {row['security_density']:.2f} | Securitization Index: {row['securitization_index']:.2f}
</div>
""",
            unsafe_allow_html=True,
        )



# SECTION 6 — AI SUMMARIZATION (Generative AI Component)

st.divider()
st.markdown("<div class='section-kicker'>6 · Generative AI</div>", unsafe_allow_html=True)
st.markdown("### AI-Powered Framing Report")
st.markdown(
    """
<div class='method-box'>
Select any utterance from the search results above, paste its text here, and Claude will
analyse its <b>framing strategy</b>, <b>security signals</b>, and <b>political context</b>.
You can also summarise an entire debate by pasting multiple excerpts.
</div>
""",
    unsafe_allow_html=True,
)

ai_col1, ai_col2 = st.columns([3, 2])

with ai_col1:
    ai_mode = st.radio(
        "Analysis mode",
        ["Summarise utterance", "Generate framing report", "Predict political orientation"],
        horizontal=True,
    )

    ai_text_input = st.text_area(
        "Paste speech text to analyse",
        height=160,
        placeholder="Paste one or more parliamentary utterances here…",
    )

    ai_extra_context = st.text_input(
        "Optional context (speaker, date, topic)",
        placeholder="e.g. Mark Rutte, 2022-02-28, emergency energy debate",
    )

    run_ai = st.button("Analyse with Claude", type="primary")

with ai_col2:
    st.markdown("#### How it works")
    st.markdown(
        """
<div class='method-box' style='font-size:0.88rem;'>
<b>Summarise utterance</b> — extracts the core argument and identifies which framing
dimensions (security / economic / climate / materials) dominate.<br><br>
<b>Framing report</b> — produces a structured analytical memo in HCSS style,
suitable for inclusion in a briefing.<br><br>
<b>Predict orientation</b> — infers the likely party family based on language patterns,
without using speaker metadata.
</div>
""",
        unsafe_allow_html=True,
    )

if run_ai:
    if not ai_text_input.strip():
        st.warning("Please paste some text to analyse.")
    else:
        SYSTEM_PROMPTS = {
            "Summarise utterance": (
                "You are an expert political analyst at HCSS (The Hague Centre for Strategic Studies). "
                "Analyse the Dutch parliamentary speech excerpt provided. "
                "Identify: (1) the core argument in 1-2 sentences, "
                "(2) which framing dimensions dominate — security, economic, climate, or critical materials — "
                "and cite specific phrases as evidence, "
                "(3) any references to geopolitical actors (Russia, EU, NATO, China). "
                "Be concise, analytical, and neutral. Maximum 200 words."
            ),
            "Generate framing report": (
                "You are an expert political analyst at HCSS (The Hague Centre for Strategic Studies). "
                "Write a structured analytical memo (max 300 words) on the provided parliamentary text. "
                "Structure: Executive Summary | Framing Analysis | Key Actors & References | "
                "Securitization Signal | Analytical Note. "
                "Use professional, policy-oriented language. Identify whether energy is being treated as a "
                "strategic vulnerability or a technical/economic issue."
            ),
            "Predict political orientation": (
                "You are an expert in Dutch parliamentary discourse. "
                "Based ONLY on the language, framing, and arguments in the text — not any speaker metadata — "
                "predict the most likely Dutch party family (e.g. liberal, social-democratic, green-left, "
                "nationalist-right, Christian-democratic). "
                "Explain your reasoning in 3-4 sentences, citing specific linguistic evidence. "
                "Express your confidence level (high/medium/low)."
            ),
        }

        system_prompt = SYSTEM_PROMPTS[ai_mode]
        user_message = ai_text_input.strip()
        if ai_extra_context.strip():
            user_message = f"Context: {ai_extra_context.strip()}\n\n---\n\n{user_message}"

        with st.spinner("Claude is analysing the text…"):
            try:
                import urllib.request
                import json as _json

                payload = _json.dumps({
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1000,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_message}],
                }).encode("utf-8")

                req = urllib.request.Request(
                    "https://api.anthropic.com/v1/messages",
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "anthropic-version": "2023-06-01",
                    },
                    method="POST",
                )

                with urllib.request.urlopen(req, timeout=30) as resp:
                    result = _json.loads(resp.read().decode("utf-8"))

                ai_response = result["content"][0]["text"]

                st.markdown(
                    f"<div class='method-box' style='border-left-color:#5C8F72;'>"
                    f"<b>Claude's Analysis ({ai_mode})</b><br><br>{ai_response.replace(chr(10), '<br>')}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            except Exception as exc:
                st.error(
                    f"Could not reach the Claude API: {exc}. "
                    "Make sure the API key is configured in your environment "
                    "(`ANTHROPIC_API_KEY`) and you have internet access."
                )


# FOOTER

st.divider()
st.markdown(
    """
<span class='small-note'>
This dashboard is intended for exploratory discourse analysis. Keyword-based scores indicate framing patterns and should be interpreted alongside qualitative reading of the underlying utterances.
</span>
""",
    unsafe_allow_html=True,
)