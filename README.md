# Exchange Atlas

### Explore currencies. Understand global purchasing power.

**Exchange Atlas** is an interactive economic dashboard that allows users to explore nominal and real exchange rates between countries using monthly data from the International Monetary Fund (IMF).

Built with Python, Streamlit, pandas, and Plotly, the application transforms historical economic data into interactive visualizations.

## Features

**Country Comparison**

Select two countries or the Euro area to analyze their exchange rates over time.

**IMF Data Integration**

Retrieve monthly consumer price index (CPI) and exchange-rate data from the IMF SDMX API, beginning in January 1976 where available.

**Interactive Visualizations**

Switch between three chart views:

* Real Exchange Rate Index
* Nominal Exchange Rate
* Both (using separate vertical axes)

**Flexible Date Selection**

Choose a custom start and end month. The app automatically recalculates the sample-average real exchange rate and normalized index whenever the selected period changes.

**Data Export**

Download a CSV containing the underlying IMF observations and calculated exchange rates.

**Modern Dashboard**

A responsive interface featuring interactive charts, summary statistics, loading indicators, and a streamlined visual design.

---

## Economic Methodology

### 1. Nominal Exchange Rate

Let:

* E1 = Country 1 currency units per USD
* E2 = Country 2 currency units per USD

The nominal exchange rate is:

**S(t) = E2(t) / E1(t)**

This gives units of Country 2 currency per one unit of Country 1 currency.

For example, selecting the United Kingdom as Country 1 and the United States as Country 2 produces USD per GBP.

### 2. Real Exchange Rate

The real exchange rate is calculated as:

**RER(t) = S(t) × P1(t) / P2(t)**

Where:

* S(t) = nominal exchange rate
* P1(t) = Country 1 CPI
* P2(t) = Country 2 CPI

### 3. Real Exchange Rate Index

The sample-average real exchange rate is:

**RER* = Average of valid RER(t) observations**

The normalized index is:

**Real Index(t) = 100 × RER(t) / RER***

By construction, the average real index equals 100 across valid observations in the selected period, apart from numerical rounding.

Changing the sample dates changes RER* and therefore recalculates the index.

### Interpretation

* **Index = 100:** Real exchange rate equals its selected-period average.
* **Index > 100:** Country 1's goods are relatively more expensive than at the sample average, under the specified RER definition.
* **Index < 100:** Country 1's goods are relatively less expensive than at the sample average.

Because CPI values are index numbers, the raw RER level depends on their reference periods. The normalized index measures changes relative to the selected sample average.

---

## Data Sources

All downloaded economic observations come from the International Monetary Fund.

**IMF Data Portal:** https://data.imf.org

**IMF SDMX 3.0 API:** https://api.imf.org/external/sdmx/3.0

The application requests the following monthly series:

**Consumer Price Index:**

`{ISO3}.CPI._T.IX.M`

**Exchange Rate:**

`{ISO3}.XDC_USD.PA_RT.M`

The application requests the IMF CPI and ER dataflows and uses `G163` for the Euro area.

The IMF exchange-rate series represents local currency units per US dollar. The application converts these series into the required exchange-rate direction.

USD per USD is set to 1 by definition.

Data availability differs by country and time period. Missing observations are not interpolated or fabricated.

Historical currency changes may affect the interpretation of some country comparisons.

---

## Technology

The application uses:

* **Python 3.12** — Programming language
* **Streamlit** — Interactive web application
* **pandas** — Data processing and calculations
* **Plotly** — Interactive financial and economic charts
* **requests** — IMF API communication
* **pycountry and Babel** — Country and currency information
* **GitHub** — Code hosting
* **Streamlit Community Cloud** — Web deployment

---

## Running the Application

The application is designed for deployment on Streamlit Community Cloud.

1. Create a public GitHub repository.
2. Upload `app.py`, `requirements.txt`, and `README.md`.
3. Sign in to https://share.streamlit.io using GitHub.
4. Select the repository and the `main` branch.
5. Set the application entry point to `app.py`.
6. Select Python 3.12.
7. Deploy the application.

The application retrieves IMF observations when required and temporarily caches downloaded data.

An internet connection is required.

---

## Verification

The application should be tested using:

**Country 1:** United Kingdom
**Country 2:** United States

The nominal exchange rate must be expressed in USD per GBP.

The exported CSV should allow verification of:

1. Nominal exchange rate = FX_2_per_USD / FX_1_per_USD.
2. Real exchange rate = Nominal_S × CPI_1 / CPI_2.
3. Real Index = 100 × RER / selected-sample average RER.
4. The average real index equals approximately 100 across valid months.
5. Changing the date range recalculates the normalized real index.

Real, Nominal, and Both chart modes should also be tested.

---

## Project Structure

**app.py** — Application code, IMF data retrieval, calculations, and visualizations.

**requirements.txt** — Python dependencies.

**README.md** — Project documentation and methodology.

---

## Notes and Limitations

The application depends on the availability and structure of IMF API data.

Some countries may have incomplete CPI or exchange-rate histories. If necessary observations are unavailable, the application displays a message instead of generating artificial data.

The real exchange rate calculation follows the definition specified for this economics assignment.

**Exchange Atlas — An interactive exploration of currencies and international prices.**
