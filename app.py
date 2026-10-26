
import io

import pandas as pd
import plotly.graph_objects as go
import pycountry
import requests
import streamlit as st
from babel.numbers import get_territory_currencies
from plotly.subplots import make_subplots

# ------------------------------------------------------------
# PAGE CONFIGURATION
# ------------------------------------------------------------

st.set_page_config(
    page_title="Exchange Atlas | Real Exchange Rates",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

API_BASE = "https://api.imf.org/external/sdmx/3.0"
FIRST_MONTH = "1976-01"

COLORS = {
    "background": "#080F1F",
    "card": "#111C30",
    "primary": "#68A7FF",
    "secondary": "#62DECA",
    "text": "#E9F0FC",
    "muted": "#95A7C2",
    "grid": "#27354D",
}

# ISO3 country codes for IMF member economies.
# G163 is the IMF's Euro area aggregate.
MEMBER_CODES = """
AFG ALB DZA AND AGO ATG ARG ARM AUS AUT AZE BHS BHR BGD
BRB BLR BEL BLZ BEN BTN BOL BIH BWA BRA BRN BGR BFA
BDI CPV KHM CMR CAN CAF TCD CHL CHN COL COM COD COG
CRI CIV HRV CYP CZE DNK DJI DMA DOM ECU EGY SLV GNQ
ERI EST SWZ ETH FJI FIN FRA GAB GMB GEO DEU GHA GRC
GRD GTM GIN GNB GUY HTI HND HUN ISL IND IDN IRN IRQ
IRL ISR ITA JAM JPN JOR KAZ KEN KIR KOR XKX KWT KGZ
LAO LVA LBN LSO LBR LBY LIE LTU LUX MDG MWI MYS MDV
MLI MLT MHL MRT MUS MEX FSM MDA MNG MNE MAR MOZ MMR
NAM NRU NPL NLD NZL NIC NER NGA MKD NOR OMN PAK PLW
PAN PNG PRY PER PHL POL PRT QAT ROU RUS RWA KNA LCA
VCT WSM SMR STP SAU SEN SRB SYC SLE SGP SVK SVN SLB
SOM ZAF SSD ESP LKA SDN SUR SWE CHE SYR TJK TZA THA
TLS TGO TON TTO TUN TUR TKM TUV UGA UKR ARE GBR USA
URY UZB VUT VEN VNM YEM ZMB ZWE
""".split()

# ------------------------------------------------------------
# VISUAL STYLING
# ------------------------------------------------------------

st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(
                ellipse at 85% 0%,
                rgba(45, 94, 165, 0.13),
                transparent 38%
            ),
            #080F1F;
        color: #E9F0FC;
    }

    .block-container {
        max-width: 1250px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    h1, h2, h3 {
        letter-spacing: -0.035em;
    }

    h1 {
        font-weight: 750;
    }

    [data-testid="stMetric"] {
        background: rgba(20, 34, 55, 0.88);
        padding: 19px;
        border: 1px solid #293954;
        border-radius: 16px;
    }

    [data-testid="stMetricValue"] {
        color: #E9F0FC;
    }

    div.stButton > button,
    div.stDownloadButton > button {
        border-radius: 11px;
        transition:
            transform 0.16s ease,
            box-shadow 0.16s ease,
            background-color 0.16s ease;
    }

    div.stButton > button:hover,
    div.stDownloadButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 7px 22px rgba(75, 140, 230, 0.18);
    }

    div.stButton > button:active,
    div.stDownloadButton > button:active {
        transform: scale(0.97);
    }

    @keyframes fadeUp {
        from {
            opacity: 0;
            transform: translateY(9px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    [data-testid="stPlotlyChart"] {
        animation: fadeUp 0.42s ease-out;
    }

    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
    }

    .eyebrow {
        text-transform: uppercase;
        letter-spacing: 0.20em;
        font-size: 0.75rem;
        font-weight: 700;
        color: #62DECA;
        margin-bottom: 0.6rem;
    }

    .hero-subtitle {
        color: #95A7C2;
        font-size: 1.05rem;
        max-width: 760px;
        line-height: 1.7;
        margin-bottom: 1.3rem;
    }

    .small-note {
        color: #95A7C2;
        font-size: 0.85rem;
    }

    a {
        color: #82B9FF !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# COUNTRY NAMES AND CURRENCIES
# ------------------------------------------------------------

def country_name(code):
    if code == "G163":
        return "Euro area"
    if code == "XKX":
        return "Kosovo"

    country = pycountry.countries.get(alpha_3=code)
    return country.name if country else code

def currency_code(code):
    if code == "G163":
        return "EUR"
    if code == "XKX":
        return "EUR"

    country = pycountry.countries.get(alpha_3=code)
    if country is None:
        return code

    try:
        currencies = get_territory_currencies(
            country.alpha_2,
            tender=True,
        )
        if currencies:
            return currencies[0]
    except (LookupError, ValueError, AttributeError):
        pass

    return code

COUNTRY_OPTIONS = {
    code: country_name(code)
    for code in MEMBER_CODES + ["G163"]
}

COUNTRY_CODES = sorted(
    COUNTRY_OPTIONS,
    key=lambda code: COUNTRY_OPTIONS[code].lower(),
)

# ------------------------------------------------------------
# IMF DATA RETRIEVAL
# ------------------------------------------------------------

@st.cache_data(ttl=21600, show_spinner=False)
def fetch_imf_series(country, dataset, indicator):
    """
    Download a single monthly IMF SDMX series.

    CPI series:
        COUNTRY.CPI._T.IX.M

    Exchange rate series:
        COUNTRY.XDC_USD.PA_RT.M

    The exchange-rate series represents units of local
    currency per one US dollar.
    """

    # USD per USD is exactly 1 by definition.
    # No IMF observation is invented or substituted.
    if dataset == "ER" and country == "USA":
        months = pd.date_range(
            FIRST_MONTH,
            pd.Timestamp.today().strftime("%Y-%m"),
            freq="MS",
        )
        return pd.Series(1.0, index=months, dtype=float)

    if dataset == "CPI":
        key = f"{country}.CPI._T.IX.M"
    elif dataset == "ER":
        key = f"{country}.XDC_USD.PA_RT.M"
    else:
        raise ValueError("Unsupported IMF dataset.")

    url = (
        f"{API_BASE}/data/dataflow/"
        f"IMF.STA/{dataset}/~/{key}"
    )

    response = requests.get(
        url,
        params={"c[TIME_PERIOD]": "ge:1976-M01"},
        headers={
            "Accept": "text/csv",
            "User-Agent": "ExchangeAtlas/1.0",
        },
        timeout=45,
    )

    response.raise_for_status()

    if not response.content.strip():
        raise ValueError(f"No IMF response for {key}.")

    try:
        df = pd.read_csv(
            io.StringIO(response.text),
            low_memory=False,
        )
    except pd.errors.EmptyDataError as exc:
        raise ValueError(
            f"IMF returned no observations for {key}."
        ) from exc

    df.columns = [
        str(column).strip().upper()
        for column in df.columns
    ]

    if not {"TIME_PERIOD", "OBS_VALUE"}.issubset(df.columns):
        raise ValueError(
            f"Unexpected IMF response format for {key}. "
            f"Columns received: {list(df.columns)}"
        )

    if "FREQUENCY" in df.columns:
        df = df[df["FREQUENCY"].astype(str) == "M"]

    # IMF monthly periods can be written as 2024-M01.
    periods = (
        df["TIME_PERIOD"]
        .astype(str)
        .str.replace(
            r"^(\d{4})-M(\d{2})$",
            r"\1-\2",
            regex=True,
        )
    )

    dates = pd.to_datetime(periods, errors="coerce")
    values = pd.to_numeric(
        df["OBS_VALUE"],
        errors="coerce",
    )

    # Apply any numeric IMF scale multiplier when present.
    if "SCALE" in df.columns:
        scales = pd.to_numeric(
            df["SCALE"],
            errors="coerce",
        ).fillna(0)

        values = values * (10.0 ** scales)

    clean = pd.DataFrame({
        "month": dates.to_numpy(),
        "value": values.to_numpy(),
    })

    clean = clean.dropna()
    clean = clean[clean["value"] > 0]
    clean = clean[
        clean["month"] >= pd.Timestamp(FIRST_MONTH)
    ]

    clean = (
        clean.drop_duplicates("month", keep="last")
        .sort_values("month")
    )

    if clean.empty:
        raise ValueError(
            f"No valid monthly IMF observations found for {key}."
        )

    series = clean.set_index("month")["value"]
    series.index.name = "Month"

    return series

@st.cache_data(ttl=21600, show_spinner=False)
def load_country_data(code):
    cpi = fetch_imf_series(code, "CPI", "CPI")
    fx = fetch_imf_series(code, "ER", "XDC_USD")
    return cpi, fx

# ------------------------------------------------------------
# ECONOMIC CALCULATIONS
# ------------------------------------------------------------

def calculate_exchange_rates(
    cpi1,
    cpi2,
    fx1,
    fx2,
    start_month,
    end_month,
):
    months = pd.date_range(
        start=start_month,
        end=end_month,
        freq="MS",
    )

    result = pd.DataFrame(index=months)
    result.index.name = "Month"

    result["CPI_1"] = cpi1
    result["CPI_2"] = cpi2
    result["FX_1_per_USD"] = fx1
    result["FX_2_per_USD"] = fx2

    # All four inputs must be positive and available.
    inputs = [
        "CPI_1",
        "CPI_2",
        "FX_1_per_USD",
        "FX_2_per_USD",
    ]

    for column in inputs:
        result.loc[
            result[column] <= 0, column
        ] = float("nan")

    # S = Country 2 currency / Country 1 currency.
    result["Nominal_S"] = (
        result["FX_2_per_USD"]
        / result["FX_1_per_USD"]
    )

    # RER = S * P1 / P2.
    result["RER"] = (
        result["Nominal_S"]
        * result["CPI_1"]
        / result["CPI_2"]
    )

    valid_rer = result["RER"].dropna()

    if valid_rer.empty:
        result["Real_Index"] = float("nan")
        return result, None

    # Sample-specific arithmetic mean.
    rer_star = valid_rer.mean()

    # The mean index of valid months equals 100.
    result["Real_Index"] = (
        100.0 * result["RER"] / rer_star
    )

    return result, rer_star

# ------------------------------------------------------------
# CHART GENERATION
# ------------------------------------------------------------

def create_chart(data, chart_type, currency1, currency2):
    plot_data = data.dropna(
        subset=["Nominal_S", "Real_Index"]
    )

    both = chart_type == "Both"

    if both:
        fig = make_subplots(
            specs=[[{"secondary_y": True}]]
        )
    else:
        fig = go.Figure()

    real_trace = go.Scatter(
        x=plot_data.index,
        y=plot_data["Real_Index"],
        mode="lines",
        name="Real exchange rate",
        line=dict(
            color=COLORS["primary"],
            width=3,
            shape="spline",
            smoothing=0.35,
        ),
        hovertemplate="%{y:.2f}<extra></extra>",
    )

    nominal_trace = go.Scatter(
        x=plot_data.index,
        y=plot_data["Nominal_S"],
        mode="lines",
        name="Nominal exchange rate",
        line=dict(
            color=COLORS["secondary"],
            width=2.5,
            shape="spline",
            smoothing=0.35,
        ),
        hovertemplate="%{y:.5f}<extra></extra>",
    )

    if chart_type == "Real":
        fig.add_trace(real_trace)
        fig.add_hline(
            y=100,
            line_dash="dot",
            line_color=COLORS["muted"],
            opacity=0.6,
        )
        fig.update_yaxes(
            title_text="Real exchange rate index"
        )

    elif chart_type == "Nominal":
        fig.add_trace(nominal_trace)
        fig.update_yaxes(
            title_text=f"{currency2} per {currency1}"
        )

    else:
        fig.add_trace(
            real_trace,
            secondary_y=False,
        )
        fig.add_trace(
            nominal_trace,
            secondary_y=True,
        )
        fig.update_yaxes(
            title_text="Real index",
            secondary_y=False,
        )
        fig.update_yaxes(
            title_text=f"{currency2} per {currency1}",
            secondary_y=True,
        )

    fig.update_layout(
        template="plotly_dark",
        height=470,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="Arial, sans-serif",
            color=COLORS["text"],
        ),
        margin=dict(l=30, r=35, t=35, b=35),
        hovermode="x unified",
        transition=dict(
            duration=450,
            easing="cubic-in-out",
        ),
        legend=dict(
            orientation="h",
            y=1.12,
            x=0,
        ),
        xaxis=dict(
            title="Month",
            gridcolor=COLORS["grid"],
            showline=False,
            rangeslider=dict(visible=False),
        ),
        yaxis=dict(
            gridcolor=COLORS["grid"],
            zeroline=False,
        ),
    )

    return fig

# ------------------------------------------------------------
# DASHBOARD HEADER
# ------------------------------------------------------------

st.markdown(
    '<div class="eyebrow">GLOBAL ECONOMIC INTELLIGENCE</div>',
    unsafe_allow_html=True,
)

st.title("Exchange Atlas")

st.markdown(
    """
    <div class="hero-subtitle">
        Explore how currencies move across economies.
        Compare nominal and inflation-adjusted exchange
        rates using monthly data from the International
        Monetary Fund.
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

# ------------------------------------------------------------
# USER CONTROLS
# ------------------------------------------------------------

st.subheader("Build your comparison")

col1, col2 = st.columns(2)

with col1:
    country1 = st.selectbox(
        "Country 1 · Base currency",
        COUNTRY_CODES,
        index=COUNTRY_CODES.index("GBR"),
        format_func=lambda c: (
            f"{COUNTRY_OPTIONS[c]} ({c})"
        ),
    )

with col2:
    country2 = st.selectbox(
        "Country 2 · Quote currency",
        COUNTRY_CODES,
        index=COUNTRY_CODES.index("USA"),
        format_func=lambda c: (
            f"{COUNTRY_OPTIONS[c]} ({c})"
        ),
    )

available_months = (
    pd.period_range(
        FIRST_MONTH,
        pd.Timestamp.today().strftime("%Y-%m"),
        freq="M",
    )
    .astype(str)
    .tolist()
)

start_col, end_col, view_col = st.columns(
    [1, 1, 1.2]
)

with start_col:
    start_month = st.selectbox(
        "Start month",
        available_months,
        index=available_months.index("2015-01"),
    )

with end_col:
    end_month = st.selectbox(
        "End month",
        available_months,
        index=len(available_months) - 1,
    )

with view_col:
    chart_type = st.segmented_control(
        "Chart view",
        ["Real", "Nominal", "Both"],
        default="Both",
    )

if chart_type is None:
    chart_type = "Both"

if country1 == country2:
    st.warning(
        "Choose two different countries to compare."
    )
    st.stop()

if start_month > end_month:
    st.error(
        "The start month must be before or equal "
        "to the end month."
    )
    st.stop()

currency1 = currency_code(country1)
currency2 = currency_code(country2)

st.caption(
    f"Exchange-rate direction: **{currency2} per "
    f"{currency1}** · Monthly period-average rates"
)

refresh_col, info_col = st.columns([1, 4])

with refresh_col:
    refresh = st.button(
        "↻ Refresh IMF data",
        use_container_width=True,
    )

if refresh:
    fetch_imf_series.clear()
    load_country_data.clear()
    st.toast("IMF cache cleared. Reloading data.")

# ------------------------------------------------------------
# LOAD THE DATA
# ------------------------------------------------------------

try:
    with st.spinner(
        "Connecting to IMF and preparing your analysis..."
    ):
        cpi1, fx1 = load_country_data(country1)
        cpi2, fx2 = load_country_data(country2)

        result, rer_star = calculate_exchange_rates(
            cpi1=cpi1,
            cpi2=cpi2,
            fx1=fx1,
            fx2=fx2,
            start_month=start_month,
            end_month=end_month,
        )

except (requests.RequestException, ValueError) as error:
    st.error("Unable to retrieve the required IMF data.")
    st.warning(
        "A series may be unavailable or the IMF API "
        "may be temporarily unreachable."
    )
    st.code(str(error))
    st.info(
        "Try another country pair, refresh the data, "
        "or check the IMF API availability."
    )
    st.stop()

valid_data = result.dropna(
    subset=["Nominal_S", "RER", "Real_Index"]
)

if valid_data.empty or rer_star is None:
    st.warning(
        "There are no complete monthly observations "
        "for these countries in the selected period. "
        "Try a wider or more recent date range."
    )
    st.stop()

# ------------------------------------------------------------
# SUMMARY METRICS
# ------------------------------------------------------------

st.divider()
st.subheader("Market snapshot")

latest = valid_data.iloc[-1]
latest_date = valid_data.index[-1]

metric1, metric2, metric3, metric4 = st.columns(4)

with metric1:
    st.metric(
        "Latest real index",
        f"{latest['Real_Index']:.2f}",
        delta=f"{latest['Real_Index'] - 100:+.2f} vs mean",
    )

with metric2:
    st.metric(
        f"Nominal · {currency2}/{currency1}",
        f"{latest['Nominal_S']:.4f}",
    )

with metric3:
    st.metric(
        "Sample mean RER",
        f"{rer_star:.5f}",
    )

with metric4:
    st.metric(
        "Valid observations",
        f"{len(valid_data):,}",
    )

st.caption(
    f"Latest complete observation: "
    f"{latest_date.strftime('%B %Y')} · "
    f"Sample: {start_month} through {end_month}"
)

# ------------------------------------------------------------
# INTERACTIVE VISUALIZATION
# ------------------------------------------------------------

st.divider()
st.subheader("Exchange rate trends")

st.caption(
    "Hover to inspect monthly values. "
    "Zoom and pan to explore the historical series."
)

fig = create_chart(
    result,
    chart_type,
    currency1,
    currency2,
)

st.plotly_chart(
    fig,
    use_container_width=True,
    theme=None,
    config={
        "displayModeBar": True,
        "displaylogo": False,
        "scrollZoom": False,
        "responsive": True,
    },
)

st.caption(
    "Real index = 100 × RER / sample mean RER. "
    "Nominal rates remain in actual currency units."
)

# ------------------------------------------------------------
# DATA EXPORT
# ------------------------------------------------------------

st.divider()
st.subheader("Explore the underlying data")

st.markdown(
    """
    Review the IMF inputs, nominal exchange rates,
    real exchange rates, and normalized index.
    Missing observations are preserved as blank cells
    in the exported dataset.
    """
)

export_data = result.reset_index()
export_data["Month"] = (
    export_data["Month"].dt.strftime("%Y-%m")
)

export_data = export_data[
    [
        "Month",
        "CPI_1",
        "CPI_2",
        "FX_1_per_USD",
        "FX_2_per_USD",
        "Nominal_S",
        "RER",
        "Real_Index",
    ]
]

with st.expander("View monthly data", expanded=False):
    st.dataframe(
        export_data,
        use_container_width=True,
        hide_index=True,
    )

csv_data = export_data.to_csv(
    index=False,
    float_format="%.12g",
).encode("utf-8")

st.download_button(
    label="↓ Download complete CSV",
    data=csv_data,
    file_name=(
        f"exchange_atlas_{country1}_{country2}_"
        f"{start_month}_{end_month}.csv"
    ),
    mime="text/csv",
    use_container_width=True,
)

missing_count = len(result) - len(valid_data)

st.caption(
    f"{missing_count} month(s) have incomplete inputs "
    "and are excluded from the RER average."
)

# ------------------------------------------------------------
# METHODOLOGY AND SOURCES
# ------------------------------------------------------------

st.divider()

with st.expander("Methodology and IMF data sources"):
    st.markdown(
        r"""
        ### Nominal exchange rate

        Let E1 and E2 be the countries' local
        currency units per US dollar.

        \[
        S_t=\frac{E_{2,t}}{E_{1,t}}
        \]

        S measures Country 2 currency per unit
        of Country 1 currency.

        ### Real exchange rate

        \[
        RER_t=S_t\frac{P_{1,t}}{P_{2,t}}
        \]

        P1 and P2 are monthly CPI indexes.

        ### Sample normalization

        \[
        RER^*=\frac{1}{N}\sum_{t=1}^{N}RER_t
        \]

        \[
        RealIndex_t=100\frac{RER_t}{RER^*}
        \]

        N counts months with complete, valid inputs.
        Changing the dates changes the sample mean.

        The real index averages 100 across valid
        observations, apart from rounding.

        ### Data treatment

        - Data source: International Monetary Fund.
        - Frequency: monthly.
        - CPI: headline index.
        - FX: period-average national currency per USD.
        - USD per USD is 1 by definition.
        - Missing data are not interpolated.
        - Calculations use overlapping valid months.
        - Available history begins January 1976.
        - Euro area uses IMF code G163.
        - Currency labels use current ISO currencies;
          historical currency changes may require care.
        """
    )

    st.markdown("### Requested IMF series")

    st.code(
        f"CPI 1: {country1}.CPI._T.IX.M\n"
        f"CPI 2: {country2}.CPI._T.IX.M\n"
        f"FX 1:  {country1}.XDC_USD.PA_RT.M\n"
        f"FX 2:  {country2}.XDC_USD.PA_RT.M"
    )

    st.markdown(
        "[IMF Data Portal](https://data.imf.org) · "
        "[IMF SDMX API](https://api.imf.org/external/sdmx/3.0)"
    )

# ------------------------------------------------------------
# FOOTER
# ------------------------------------------------------------

st.divider()

st.markdown(
    """
    <div class="small-note">
        EXCHANGE ATLAS · Built with Python, Streamlit,
        Plotly, and International Monetary Fund data.
        <br>
        Educational economic analysis dashboard.
    </div>
    """,
    unsafe_allow_html=True,
)
