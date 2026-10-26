"""Real Exchange Rates — an IMF-powered Streamlit dashboard."""

import io
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import pycountry
import requests
import streamlit as st
from babel.numbers import get_territory_currencies
from plotly.subplots import make_subplots

st.set_page_config(page_title="Real Exchange Rates", page_icon="💱", layout="wide")
API_ROOT = "https://api.imf.org/external/sdmx/3.0"
BLUE, MINT = "#8FAAFF", "#62D7BA"

# IMF member countries and the Euro area (G163). Some series are unavailable.
COUNTRIES = """
AFG ALB DZA AND AGO ATG ARG ARM AUS AUT AZE BHS BHR BGD BRB BLR BEL
BLZ BEN BTN BOL BIH BWA BRA BRN BGR BFA BDI CPV KHM CMR CAN CAF
TCD CHL CHN COL COM COD COG CRI CIV HRV CYP CZE DNK DJI DMA DOM ECU
EGY SLV GNQ ERI EST SWZ ETH FJI FIN FRA GAB GMB GEO DEU GHA GRC
GRD GTM GIN GNB GUY HTI HND HUN ISL IND IDN IRN IRQ IRL ISR ITA
JAM JPN JOR KAZ KEN KIR KOR XKX KWT KGZ LAO LVA LBN LSO LBR LBY
LIE LTU LUX MDG MWI MYS MDV MLI MLT MHL MRT MUS MEX FSM MDA MNG
MNE MAR MOZ MMR NAM NRU NPL NLD NZL NIC NER NGA MKD NOR OMN PAK
PLW PAN PNG PRY PER PHL POL PRT QAT ROU RUS RWA KNA LCA VCT WSM
SMR STP SAU SEN SRB SYC SLE SGP SVK SVN SLB SOM ZAF SSD ESP LKA
SDN SUR SWE CHE SYR TJK TZA THA TLS TGO TON TTO TUN TUR TKM TUV
UGA UKR ARE GBR USA URY UZB VUT VEN VNM YEM ZMB ZWE G163
""".split()


def country_name(code):
    if code == "G163":
        return "Euro area"
    if code == "XKX":
        return "Kosovo"
    record = pycountry.countries.get(alpha_3=code)
    return record.name if record else code


def currency_code(code):
    if code in {"G163", "XKX"}:
        return "EUR"
    record = pycountry.countries.get(alpha_3=code)
    if record:
        try:
            codes = get_territory_currencies(record.alpha_2, tender=True)
            if codes:
                return codes[0]
        except (ValueError, LookupError, AttributeError):
            pass
    return code


NAMES = {code: country_name(code) for code in COUNTRIES}
OPTIONS = sorted(COUNTRIES, key=lambda c: NAMES[c].casefold())

st.markdown("""
<style>
.stApp {
  background: radial-gradient(ellipse at 88% -12%, #1A2B46, transparent 43%), #0A111F;
  color: #EDF2FB;
}
.block-container {max-width: 1210px; padding-top: 6rem !important; padding-bottom: 4rem;}
h1, h2, h3 {letter-spacing: -.035em !important;}
h1 {font-weight: 750 !important;}
[data-testid="stMetric"] {
  border-radius: 14px; border: 1px solid #2B3A53;
  padding: 18px; background: #142034;
}
.stButton button, .stDownloadButton button {
  border-radius: 11px !important; min-height: 43px;
  transition: transform .15s ease, box-shadow .2s ease, border-color .2s ease;
}
.stButton button:hover, .stDownloadButton button:hover {
  transform: translateY(-2px); border-color: #8FAAFF !important;
  box-shadow: 0 8px 22px rgba(143,170,255,.14);
}
.stButton button:active, .stDownloadButton button:active {transform: scale(.97);}
[data-testid="stPlotlyChart"] {animation: appear .38s ease-out;}
@keyframes appear {from {opacity:.3; transform:translateY(8px)} to {opacity:1; transform:none}}
@media (prefers-reduced-motion:reduce) {
  *, *::before, *::after {animation:none !important; transition:none !important;}
}
@media (max-width:700px) {.block-container {padding-top:5.5rem !important;}}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def imf_monthly(country, dataset):
    """Fetch CPI or local-currency-per-USD monthly IMF observations."""
    if dataset == "ER" and country == "USA":
        # USD per USD = 1 by definition; this is not an IMF observation.
        months = pd.date_range("1976-01-01", date.today(), freq="MS")
        return pd.Series(1.0, index=months)

    if dataset == "CPI":
        key = f"{country}.CPI._T.IX.M"
    elif dataset == "ER":
        key = f"{country}.XDC_USD.PA_RT.M"
    else:
        raise ValueError("Unknown IMF dataset.")

    url = f"{API_ROOT}/data/dataflow/IMF.STA/{dataset}/~/{key}"
    response = requests.get(
        url, params={"c[TIME_PERIOD]": "ge:1976-M01"},
        headers={"Accept": "text/csv"}, timeout=50,
    )
    response.raise_for_status()
    try:
        frame = pd.read_csv(io.StringIO(response.text), low_memory=False)
    except pd.errors.EmptyDataError as exc:
        raise ValueError(f"No data returned for {key}.") from exc

    frame.columns = [str(c).upper().strip() for c in frame.columns]
    if not {"TIME_PERIOD", "OBS_VALUE"}.issubset(frame.columns):
        raise ValueError(f"Unexpected IMF response for {key}: {list(frame.columns)}")
    if "FREQUENCY" in frame:
        frame = frame[frame["FREQUENCY"].astype(str).str.upper() == "M"]

    times = frame["TIME_PERIOD"].astype(str).str.replace(
        r"^(\d{4})-M(\d{2})$", r"\1-\2", regex=True
    )
    month = pd.to_datetime(times, errors="coerce").dt.to_period("M").dt.to_timestamp()
    values = pd.to_numeric(frame["OBS_VALUE"], errors="coerce")
    if "SCALE" in frame:
        scale = pd.to_numeric(frame["SCALE"], errors="coerce").fillna(0)
        values = values * (10.0 ** scale)

    tidy = pd.DataFrame({"Month": month.to_numpy(), "Value": values.to_numpy()})
    tidy = tidy.dropna().query("Value > 0")
    tidy = tidy[tidy["Month"] >= pd.Timestamp("1976-01-01")]
    tidy = tidy.sort_values("Month").drop_duplicates("Month", keep="last")
    if tidy.empty:
        raise ValueError(f"No usable monthly observations for {key}.")
    return tidy.set_index("Month")["Value"]


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def country_pair(code1, code2):
    return (
        imf_monthly(code1, "CPI"), imf_monthly(code2, "CPI"),
        imf_monthly(code1, "ER"), imf_monthly(code2, "ER"),
    )


def calculate(cpi1, cpi2, fx1, fx2, start, end):
    """Preserve missing rows; normalize from valid months in this date range."""
    result = pd.DataFrame(index=pd.date_range(start, end, freq="MS"))
    result.index.name = "Month"
    for label, series in (
        ("CPI_1", cpi1), ("CPI_2", cpi2),
        ("FX_1_per_USD", fx1), ("FX_2_per_USD", fx2),
    ):
        result[label] = series
        result.loc[result[label] <= 0, label] = float("nan")
    result["Nominal_S"] = result["FX_2_per_USD"] / result["FX_1_per_USD"]
    result["RER"] = result["Nominal_S"] * result["CPI_1"] / result["CPI_2"]
    avg = result["RER"].mean(skipna=True)
    result["Real_Index"] = 100 * result["RER"] / avg if pd.notna(avg) else float("nan")
    return result, avg


def chart(data, view, c1, c2):
    dual = view == "Both"
    fig = make_subplots(specs=[[{"secondary_y": True}]]) if dual else go.Figure()
    real = go.Scatter(
        x=data.index, y=data["Real_Index"], name="Real index", mode="lines",
        line=dict(color=BLUE, width=3), connectgaps=False,
        hovertemplate="%{x|%b %Y}<br>Real index: %{y:.2f}<extra></extra>",
    )
    nominal = go.Scatter(
        x=data.index, y=data["Nominal_S"], name="Nominal exchange rate",
        mode="lines", line=dict(color=MINT, width=2.6), connectgaps=False,
        hovertemplate=f"%{{x|%b %Y}}<br>{c2} per {c1}: %{{y:.5f}}<extra></extra>",
    )
    if dual:
        fig.add_trace(real, secondary_y=False)
        fig.add_trace(nominal, secondary_y=True)
        fig.update_yaxes(title_text="Real index", secondary_y=False)
        fig.update_yaxes(title_text=f"{c2} per {c1}", secondary_y=True, showgrid=False)
    elif view == "Real":
        fig.add_trace(real)
        fig.update_yaxes(title_text="Real index")
    else:
        fig.add_trace(nominal)
        fig.update_yaxes(title_text=f"{c2} per {c1}")
    if view in ("Real", "Both"):
        fig.add_hline(y=100, line_color="#65758D", line_dash="dot", opacity=.6)
    fig.update_layout(
        height=470, template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#EDF2FB"), hovermode="x unified",
        margin=dict(l=20, r=28, t=40, b=20),
        legend=dict(orientation="h", x=0, y=1.13),
        transition=dict(duration=350, easing="cubic-in-out"),
        xaxis=dict(showgrid=True, gridcolor="#28364B"),
        yaxis=dict(gridcolor="#28364B"),
    )
    return fig


def flip_countries():
    st.session_state.country1, st.session_state.country2 = (
        st.session_state.country2, st.session_state.country1
    )


st.session_state.setdefault("country1", "GBR")
st.session_state.setdefault("country2", "USA")

st.title("Real Exchange Rates")
st.write(
    "Compare two countries' currencies over time, before and after adjusting "
    "for consumer prices. Explore IMF data, interactive charts, and calculations."
)
st.divider()
st.subheader("Choose your comparison")

left, middle, right = st.columns([1, .15, 1], vertical_alignment="bottom")
with left:
    st.selectbox("Country 1 · Base", OPTIONS, key="country1",
                 format_func=lambda x: f"{NAMES[x]} ({currency_code(x)})")
with middle:
    st.button("⇄", on_click=flip_countries, use_container_width=True,
              help="Swap Country 1 and Country 2")
with right:
    st.selectbox("Country 2 · Quote", OPTIONS, key="country2",
                 format_func=lambda x: f"{NAMES[x]} ({currency_code(x)})")

code1, code2 = st.session_state.country1, st.session_state.country2
cur1, cur2 = currency_code(code1), currency_code(code2)
months = pd.period_range("1976-01", date.today().strftime("%Y-%m"), freq="M").astype(str).tolist()
start_col, end_col, view_col = st.columns([1, 1, 1.25])
with start_col:
    start = st.selectbox("Start month", months, index=months.index("2015-01"))
with end_col:
    end = st.selectbox("End month", months, index=len(months) - 1)
with view_col:
    view = st.segmented_control("Chart view", ["Real", "Nominal", "Both"], default="Both") or "Both"

st.info(
    f"**How to read this pair:** The nominal rate shows how many **{cur2}** "
    f"one **{cur1}** buys. The real index adjusts for CPI differences, "
    "and averages **100** during the selected period."
)

if code1 == code2:
    st.warning("Select two different countries.")
    st.stop()
if start > end:
    st.warning("Start month must be on or before end month.")
    st.stop()
if st.button("↻ Refresh IMF data"):
    imf_monthly.clear()
    country_pair.clear()
    st.toast("Retrieving fresh IMF observations")

try:
    with st.spinner("Loading IMF observations and updating your chart..."):
        cpi1, cpi2, fx1, fx2 = country_pair(code1, code2)
        data, average = calculate(cpi1, cpi2, fx1, fx2, start, end)
except (requests.RequestException, ValueError) as exc:
    st.error("The IMF data could not be loaded for this comparison.")
    st.caption("Some countries lack monthly series; the IMF service may also be temporarily unavailable.")
    with st.expander("Technical details"):
        st.code(str(exc))
    st.stop()

valid = data.dropna(subset=["RER", "Real_Index"])
if valid.empty:
    st.warning("No complete CPI and exchange-rate observations for these months. Try another period or country pair.")
    st.stop()

st.divider()
st.subheader("At a glance")
latest = valid.iloc[-1]
a, b, c, d = st.columns(4)
a.metric("Latest real index", f"{latest['Real_Index']:.2f}",
         delta=f"{latest['Real_Index']-100:+.2f} vs average")
b.metric(f"Nominal · {cur2}/{cur1}", f"{latest['Nominal_S']:.4f}")
c.metric("Sample mean RER", f"{average:.5f}")
d.metric("Valid months", f"{len(valid):,} of {len(data):,}")
st.caption(f"Latest complete month: {valid.index[-1]:%B %Y}")

st.divider()
st.subheader("Exchange rate over time")
st.caption(
    "Real: CPI-adjusted index relative to this period's average of 100. "
    f"Nominal: actual {cur2} per {cur1}, without normalization. "
    "With Both, each measure uses its own vertical axis."
)
st.plotly_chart(chart(data, view, cur1, cur2), width="stretch",
                config={"displaylogo": False, "scrollZoom": False})

st.divider()
st.subheader("Download the data")
st.caption("All months in your sample are included. Missing observations remain blank; they are excluded from the real-index average.")
export = data.reset_index()
export["Month"] = export["Month"].dt.strftime("%Y-%m")
export = export[["Month", "CPI_1", "CPI_2", "FX_1_per_USD",
                 "FX_2_per_USD", "Nominal_S", "RER", "Real_Index"]]
st.download_button(
    "↓ Download CSV", export.to_csv(index=False, float_format="%.12g").encode("utf-8"),
    file_name=f"real_exchange_rates_{code1}_{code2}_{start}_{end}.csv",
    mime="text/csv", type="primary",
)
with st.expander("Preview monthly calculations"):
    st.dataframe(export, hide_index=True, use_container_width=True)

with st.expander("Methodology and data sources"):
    st.markdown(r"""
    **Nominal exchange rate.** If the IMF reports local-currency units per USD
    as \(E_1\) and \(E_2\), then \(S_t = E_{2,t}/E_{1,t}\).
    This is **Country 2 currency per Country 1 currency**.

    **Real exchange rate:** \(RER_t = S_t \times P_{1,t}/P_{2,t}\),
    where \(P_1\) and \(P_2\) are the monthly CPI indexes.

    **Sample mean:** \(RER^* = \mathrm{mean}(RER_t)\) over complete months in
    the selected date range.

    **Real index:** \(100 \times RER_t/RER^*\), averaging 100 over valid months.
    The reference average is recalculated when the selected dates change.

    Missing data are never interpolated. The index is relative to the selected
    period, not a direct currency-misvaluation or purchasing-power-parity measure.
    Historical currency changes can affect interpretation.
    """)
    st.code(
        f"CPI 1: {code1}.CPI._T.IX.M\nCPI 2: {code2}.CPI._T.IX.M\n"
        f"FX 1: {code1}.XDC_USD.PA_RT.M\nFX 2: {code2}.XDC_USD.PA_RT.M"
    )
    st.caption("IMF CPI and ER dataflows · January 1976 onward where available · Euro area = G163 · USD/USD = 1 by definition")
    st.markdown("[IMF data portal](https://data.imf.org) · [IMF SDMX API](https://api.imf.org/external/sdmx/3.0)")

st.divider()
st.caption("Real Exchange Rates · Monthly IMF data · Educational analysis")
