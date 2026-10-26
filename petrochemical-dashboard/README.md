# PetroTrade Intelligence — v2 dashboard upgrade

This version keeps the project in Streamlit/Pandas/Plotly and adds a clearer interface and additional analysis tabs.

## Included
- `app.py` — complete dashboard application
- `.streamlit/config.toml` — light theme with teal accent
- `requirements.txt` — Python dependencies

## Setup
Copy these files into your existing project folder and keep your existing `DGCIS_DATA.csv` beside `app.py`.

In PowerShell, from the active virtual environment:

```powershell
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

## Main dashboard sections
- Market overview: KPIs, comparable monthly trend, commodity composition, historical context, top markets
- Commodity intelligence: year-on-year change and monthly relative-performance heatmap
- Partner explorer: partner-level KPIs, trends and commodity breakdown
- Data & methodology: searchable filtered records, downloadable CSV and documented limitations

## Data notes
- Source monthly columns are USD million; charts use USD billion for readability.
- The selected period is compared with the same months from the prior year when possible.
- The CSV has no explicit import/export field; confirm the original DGCIS query direction before describing the values as imports or exports.
- HS chapters 27, 28, 29, 39 and 40 are broad categories, not an exclusively petrochemical product list.
