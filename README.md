# Real Exchange Rates

An interactive Streamlit app for comparing nominal and CPI-adjusted real exchange rates between two economies using monthly International Monetary Fund (IMF) data.

## What the app does

* Select **Country 1** (base) and **Country 2** (quote), including the Euro area (`G163`).
* Use the **swap button** to reverse the currency pair instantly.
* Choose any starting and ending month from January 1976 onward, subject to IMF coverage.
* Switch between **Real**, **Nominal**, and **Both** interactive charts. Both uses separate vertical axes.
* Examine summary statistics, preview observations, and download a **CSV** containing the underlying inputs and calculations. Missing months are included with blank values.

## Economic methodology

The app retrieves CPI and period-average exchange rates from the [IMF SDMX 3.0 API](https://api.imf.org/external/sdmx/3.0). Requested monthly series are:

* CPI (CPI dataflow): `{ISO3}.CPI._T.IX.M`
* Exchange rate (ER dataflow): `{ISO3}.XDC_USD.PA_RT.M`

Let `E1` and `E2` be the IMF exchange-rate inputs, measured in **local-currency units per US dollar**. The nominal exchange rate must be **Country 2 currency per one unit of Country 1 currency**:

```text
S(t) = E2(t) / E1(t)
```

If Country 1 is the United Kingdom and Country 2 is the United States, this produces **USD per GBP**. USD per USD is 1 by definition.

Let `P1` and `P2` be the monthly consumer price indexes for Countries 1 and 2. The assignment's real exchange rate is:

```text
RER(t) = S(t) × P1(t) / P2(t)
```

The app calculates `RER*`, the **arithmetic average of valid RER observations in the selected period**, and normalizes as follows:

```text
Real Index(t) = 100 × RER(t) / RER*
```

The real index averages **100** over months with complete data. Changing the start or end month recalculates `RER*`. The nominal rate remains in actual currency units and is **not** normalized.

### Interpretation

* **100**: The real exchange rate is at its selected-period average.
* **Above 100**: Country 1's CPI-adjusted relative price level is higher than at the selected-period average under this formula.
* **Below 100**: It is lower than at the selected-period average.

The CPI-based real index does **not** directly establish whether a currency is overvalued or undervalued. CPI base periods, historical changes in national currencies, and IMF data gaps can affect interpretation. Missing observations are not interpolated or fabricated.

## Run online

The repository contains these files at its top level:

* `app.py` — user interface, data retrieval, economic calculations, interactive charts, and downloads.
* `requirements.txt` — Python dependencies.
* `README.md` — instructions and economic methodology.

To deploy, sign into [Streamlit Community Cloud](https://share.streamlit.io), connect this repository, select the `main` branch and `app.py`, choose **Python 3.12**, and deploy. IMF downloads normally need no API key. Set the app to public if you want visitors to access it without signing in.

## Verification checklist

1. Select **United Kingdom** for Country 1 and **United States** for Country 2.
2. Confirm nominal `S` is expressed in **USD per GBP**.
3. Download the CSV for a period with complete observations.
4. Verify one row manually: `Nominal_S = FX_2_per_USD / FX_1_per_USD` and `RER = Nominal_S × CPI_1 / CPI_2`.
5. Check the average of nonblank `Real_Index` values is approximately **100**.
6. Change the dates and confirm the real index is recalculated; test Real, Nominal, Both, and the swap button.

## Technology and source

Python 3.12 · Streamlit · pandas · Plotly · requests · pycountry · Babel

**Source:** [International Monetary Fund Data Portal](https://data.imf.org). Coverage and live API availability vary by series and economy.
