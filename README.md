# 🌾 KrishiMitra AI

> AI-powered Crop Type, Moisture Stress Detection & Smart Irrigation Advisory System

Built for **ISRO Bharatiya Antariksh Hackathon 2026** by **Team SpaceHack**

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Flask](https://img.shields.io/badge/Flask-Backend-black)
![Scikit Learn](https://img.shields.io/badge/Scikit--Learn-AI-orange)
![Leaflet](https://img.shields.io/badge/Leaflet-Maps-green)
![License](https://img.shields.io/badge/License-MIT-success)
[![CI](https://github.com/SunnyAgrwl05/krishimitra-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/SunnyAgrwl05/krishimitra-ai/actions/workflows/ci.yml)

---

## 📸 Dashboard Preview

![KrishiMitra Dashboard](https://raw.githubusercontent.com/SunnyAgrwl05/krishimitra-ai/main/docs/dashboard-preview.png)
---

## 📖 Overview

KrishiMitra AI is an intelligent agriculture platform that combines simulated satellite imagery, machine learning, weather analysis, and irrigation advisory into a single interactive dashboard.

The platform helps farmers monitor crop health, detect moisture stress, and receive smart irrigation recommendations using satellite-derived vegetation indices and AI models.

---

## ✨ Features

- 🛰️ Satellite-based Crop Monitoring
- 🌱 AI Crop Classification
- 💧 Smart Irrigation Recommendation
- 📍 Interactive GIS Dashboard
- 🌦️ Weather Integration
- 📅 7-Day Weather Forecast
- 📄 PDF Report Generation
- 📤 CSV Data Export
- 🔍 Location Search — autocomplete with recent-search history & keyboard navigation
- 📊 NDVI, NDWI & MSI Visualization
- 📈 Interactive Analytics Charts — NDVI/NDWI/MSI/SAR & irrigation trends with tooltips and PNG export
- 📱 Responsive UI
- 🌗 Dark / Light Theme Toggle — remembers your choice and follows your system preference

---

# 🏗 System Architecture

```text
Satellite Data
      │
      ▼
Preprocessing
      │
      ▼
Feature Extraction
      │
      ▼
AI Models
      │
      ▼
Decision Engine
      │
      ▼
Interactive Dashboard
```

---

# 🛠 Tech Stack

| Category | Technologies |
|----------|--------------|
| Frontend | HTML5, CSS3, JavaScript |
| Backend | Flask, Python |
| AI/ML | Scikit-learn, Pandas, Joblib |
| Mapping | Leaflet.js, OpenStreetMap |
| Satellite | Sentinel-2 (Simulated), Sentinel-1 SAR (Simulated) |
| Charts | Chart.js |
| Reports | jsPDF |
| Deployment | Docker |

---

# 📂 Project Structure

```text
krishimitra-ai/
│
├── app.py
├── model/
├── static/
├── templates/
├── docs/
├── tests/
├── requirements.txt
├── Dockerfile
└── README.md
```

---

# ⚙ Installation

```bash
git clone https://github.com/SunnyAgrwl05/krishimitra-ai.git

cd krishimitra-ai

python -m venv venv

source venv/bin/activate
# Windows:
# venv\Scripts\activate

pip install -r requirements.txt
```

---

# 🚀 Run the Project

Train the AI models

```bash
python model/generate_training_data.py
python model/train_model.py
```

Start the Flask server

```bash
python app.py
```

Open

```
http://localhost:5001
```

---

# 📡 REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/fields` | GET | Fetch all monitored fields |
| `/api/analyze` | POST | Analyze a custom location |
| `/api/weather` | GET | Weather information |
| `/api/forecast` | GET | 7-day weather forecast (Open-Meteo) |
| `/api/history` | GET | Analysis history |
| `/api/dashboard` | GET | Dashboard statistics |
| `/api/search-location?q=<query>` | GET | Location autocomplete — `<query>` is the place name to search (Photon/OpenStreetMap, India-focused) |
| `/api/trend?lat=&lon=&days=&crop=` | GET | Time-series of vegetation indices, SAR backscatter & irrigation demand (data behind the Analytics charts) |
| `/api/model-metrics` | GET | AI model performance |
| `/api/export/csv` | GET | Download dashboard field data as CSV |
| `/api/health` | GET | Health check |

---

# 📈 Interactive Analytics

The **Analytics** tab turns the raw index values into interactive
[Chart.js](https://www.chartjs.org) visualisations, so trends are visible at a
glance instead of having to compare numbers by hand.

<p align="center">
  <img src="docs/analytics-charts.png" width="100%" alt="Analytics tab — summary tiles with NDVI, NDWI and MSI trend charts (dark theme)">
</p>

<p align="center">
  <img src="docs/analytics-charts-light.png" width="100%" alt="Analytics tab — SAR backscatter, irrigation trend, crop health doughnut and field NDVI comparison (light theme)">
</p>

**Charts included**

| Chart | Type | Shows |
|---|---|---|
| NDVI Trend | Area line | Vegetation vigour over the selected window |
| NDWI Trend | Area line | Canopy water content |
| MSI (Moisture Stress) | Bar (colour-coded) | Moisture stress — bars warm up as MSI rises |
| SAR Backscatter | Multi-line | Sentinel-1 VV & VH in dB |
| Irrigation Trend | Bar + line | Recommended water (mm) against crop demand (mm/day) |
| Crop Health Summary | Doughnut | How many days fell in each stress class |
| Fields NDVI Comparison | Horizontal bar | All dashboard fields side by side |

**How to use it**

- Enter a latitude/longitude, or press 📍 **Selected Field** to chart the field
  currently selected on the Field Map.
- Optionally pin a **crop**, and pick a **range** — 7, 14, 30, 90 or 180 days.
  Changing crop or range refreshes the charts immediately.
- **Hover** any chart for exact values; click a legend entry to toggle a series.
- The **download icon** on each card saves that chart as a **PNG**.
- Summary tiles above the grid show average NDVI/NDWI/MSI, the NDVI change
  across the window (📈/📉), total recommended water and the latest stress class.

**Where the data comes from**

The charts are fed by `GET /api/trend`, which replays the same
ingestion → features → AI models → decision-engine pipeline as `/api/analyze`
once per sampled date, with a **single batched model call** for the whole
window. The endpoint is **read-only** — unlike `/api/analyze` it never writes to
the history database.

| Query param | Default | Notes |
|---|---|---|
| `lat`, `lon` | — | Required; non-numeric or missing → `400` |
| `days` | `30` | Clamped to **7–180** |
| `crop` | auto-detect | One of `Wheat`, `Rice`, `Maize`, `Pulses`, `Sugarcane`; anything else is ignored |

Long windows are **sub-sampled to at most ~45 points** (`step_days` in the
response says how coarse the sampling is), so a 180-day chart costs about the
same to compute — and stays as readable — as a 30-day one. The most recent point
is always today.

```bash
curl "http://localhost:5001/api/trend?lat=26.85&lon=80.95&days=30&crop=Rice"
```

```jsonc
{
  "field": { "lat": 26.85, "lon": 80.95, "crop_hint": "Rice" },
  "range": { "days": 30, "step_days": 1, "points": 30,
             "from": "2026-07-01", "to": "2026-07-30" },
  "series": [
    {
      "date": "2026-07-01",
      "crop": "Rice", "predicted_crop": "Rice",
      "growth_stage": "Vegetative", "growth_fraction": 0.183,
      "NDVI": 0.617, "NDWI": 0.215, "MSI": 1.391,
      "VV_dB": -19.43, "VH_dB": -13.63, "VV_VH_ratio": 1.426,
      "moisture_deficit_pct": 41.6,
      "predicted_stress": "Moderate Stress", "stress_confidence": 0.995,
      "urgency": "High",
      "recommended_water_mm": 4.6, "crop_water_demand_mm_day": 4.63
    }
    // … one entry per sampled date, oldest → newest
  ],
  "summary": {
    "avg_ndvi": 0.766, "min_ndvi": 0.617, "max_ndvi": 0.865,
    "avg_ndwi": 0.3, "avg_msi": 1.228,
    "total_recommended_water_mm": 111.9,
    "ndvi_change": 0.248, "trend": "improving",
    "stress_distribution":  { "Healthy": 8, "Mild Stress": 6,
                              "Moderate Stress": 13, "Severe Stress": 3 },
    "urgency_distribution": { "Low": 8, "Moderate": 6, "High": 13, "Critical": 3 },
    "latest": { "…": "the most recent series entry" }
  },
  "source": "Simulated Sentinel-2 + Sentinel-1 (schema-matched; swap-in ready for GEE)"
}
```

`trend` is derived from `ndvi_change` across the window: `improving` above
`+0.05`, `declining` below `-0.05`, otherwise `stable`.

**Behaviour & fallbacks**

- Charts follow the **dark/light theme** — canvas can't inherit CSS variables,
  so they repaint on toggle.
- The grid collapses to a **single column** on phones, and animations respect
  `prefers-reduced-motion`.
- If the **Chart.js CDN is unreachable** or the endpoint fails, the tab shows a
  short message and the rest of the dashboard is unaffected.
- Invalid coordinates surface an inline error instead of an empty chart.

---

# 🔍 Location Search

The **Analyze → Step 1 (Location)** panel includes a smart location search so
you can find a farm by name instead of typing raw coordinates.

- **Autocomplete suggestions** as you type (from 3 characters), matching even
  partial words — e.g. `luckno` → *Lucknow*.
- **Auto-fills** Latitude/Longitude and Village/District/State on selection.
- **Recent search history** (kept in the browser's Local Storage) with a
  one-click **Clear** — no duplicate entries.
- **Keyboard navigation** — `↓`/`↑` to move, `Enter` to select, `Esc` to close.
- **Match highlighting**, a **loading indicator**, and graceful **error
  handling** with a **Retry** button on network failure.
- Debounced input + in-memory caching for **faster, lighter** lookups.

Suggestions are served by the app's own `GET /api/search-location?q=<query>`
endpoint, which proxies [Photon](https://photon.komoot.io) — an
OpenStreetMap-based geocoder designed for type-ahead search. Results are
focused on India using a geographic bounding box. The endpoint always responds
gracefully — an empty list with a note — if the upstream geocoder is
unreachable. Manual latitude/longitude entry and the 📍 *Auto-fill Coordinates*
(device geolocation) button continue to work as before.

### Why Photon and not Nominatim?

Both are **free, no-API-key geocoders built on the same OpenStreetMap data**,
but they are built for different jobs, and the choice matters for a
search-as-you-type box:

| Aspect | Nominatim | **Photon (chosen)** |
|---|---|---|
| Designed for | Full-address & reverse geocoding | **Autocomplete / type-ahead** |
| Partial words | ❌ needs complete words | ✅ matches prefixes (`luckno` → *Lucknow*) |
| Typo tolerance | Minimal | Some built in |
| Public-API policy | Discourages autocomplete use; ~1 req/sec | Meant for many small type-ahead requests |

The deciding factor: Nominatim's `/search` only matches **complete words**, so
typing `luckno` returns **nothing** — unusable for an autocomplete box (and
Nominatim's own docs advise against using its public API this way). Photon was
built specifically as the autocomplete companion to Nominatim and matches
partial input instantly, which is exactly what this feature needs.

> **Note:** Nominatim is still the better tool for one-shot *full-address*
> geocoding and *reverse* geocoding (coordinates → address). Photon is chosen
> here only because this is a live autocomplete experience. The India focus uses
> a bounding box (Photon's free tier has no country-code filter), so it may
> include small border areas of neighbouring countries. Both public instances
> are free/shared and fine for this project; heavy production traffic would call
> for a self-hosted or paid geocoder.

---

# 🧠 AI Pipeline

- Satellite Image Simulation
- Feature Extraction
- Crop Classification
- Moisture Stress Detection
- Decision Engine
- Smart Irrigation Advisory
- Dashboard Visualization

---

# 📊 Satellite Features

The AI model uses the following satellite-derived parameters:

- NDVI
- NDWI
- MSI
- VV Backscatter
- VH Backscatter
- VV/VH Ratio
- Growth Fraction

---

# 👥 Team SpaceHack

- 👩 Tanya Garg (Team Leader)
- 👨 Sunny Kumar
- 👨 Adarsh Kushwaha
- 👨 Siddharth

---

# 🔮 Future Improvements

- Google Earth Engine Integration
- Live Sentinel Data
- Mobile Application
- Multi-language Support
- Farmer Authentication
- Yield Prediction
- Disease Detection
- SMS & WhatsApp Alerts

---

# 📜 License

This project is developed for the **ISRO Bharatiya Antariksh Hackathon 2026** by **Team SpaceHack**.

For learning, research, and demonstration purposes.

---

# 🤝 Contributing

Contributions are always welcome!

If you'd like to improve KrishiMitra AI:

1. Fork this repository
2. Create a feature branch

```bash
git checkout -b feature/amazing-feature
```

3. Commit your changes

```bash
git commit -m "feat: add amazing feature"
```

4. Push your branch

```bash
git push origin feature/amazing-feature
```

5. Open a Pull Request

---

# 🌱 Contributors

KrishiMitra AI is built and improved by our open-source community. A live
**Contributors** tab is available in the dashboard top navigation — it fetches
the latest contributors straight from the GitHub API and shows their avatars,
usernames, contribution counts, and profile links.

<a href="https://github.com/SunnyAgrwl05/krishimitra-ai/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=SunnyAgrwl05/krishimitra-ai" alt="Contributors" />
</a>

Thank you to everyone who has contributed! ❤️

---

# 🖼️ Additional Screenshots

## 📍 Field Monitoring Dashboard

<p align="center">
  <img src="docs/dashboard-preview.png" width="100%" alt="Dashboard">
</p>

## 📈 Interactive Analytics — Trend Charts (Dark Theme)

NDVI, NDWI and MSI trends for the selected field, with the summary tiles
(average indices, NDVI change, water demand, latest stress) above them.

<p align="center">
  <img src="docs/analytics-charts.png" width="100%" alt="Analytics tab — summary tiles with NDVI, NDWI and MSI trend charts (dark theme)">
</p>

## 🌗 Interactive Analytics — SAR, Irrigation & Comparison (Light Theme)

SAR VV/VH backscatter, the irrigation trend (recommended water vs crop demand),
the crop-health doughnut and the cross-field NDVI comparison — shown in the
light theme, since the charts repaint when the theme is toggled.

<p align="center">
  <img src="docs/analytics-charts-light.png" width="100%" alt="Analytics tab — SAR backscatter, irrigation trend, crop health doughnut and field NDVI comparison (light theme)">
</p>

---

# 🧪 Testing & Continuous Integration

Every push and pull request to `main` is automatically validated by a
[GitHub Actions CI pipeline](.github/workflows/ci.yml) that runs across
Python 3.11, 3.12 and 3.13:

- ✅ **Tests** — full `pytest` suite executed with coverage reporting
- 🔍 **Linting** — `flake8` (build fails on syntax errors / undefined names; style issues are reported as advisory)
- 🎨 **Formatting** — `black` and `isort` checks (advisory)
- ⚡ **Caching** — pip dependencies cached for faster runs

### Run the checks locally

```bash
# Install dev/CI tooling (in addition to requirements.txt)
pip install -r requirements-dev.txt

# Run the test suite with coverage
coverage run -m pytest -q && coverage report -m

# Lint & formatting checks
flake8 .
black --check .
isort --check-only .
```

---

# 📈 Project Highlights

- 🚀 End-to-End AI Agriculture Pipeline
- 🛰️ Satellite-based Crop Monitoring
- 🌱 AI Crop Type Prediction
- 💧 Smart Irrigation Advisory
- 📊 NDVI, NDWI & SAR Analytics
- 🌦️ Weather Information Integration
- 📄 Professional PDF Report Generation
- 🗺️ Interactive GIS Dashboard
- ⚡ Fast REST APIs
- 📱 Responsive Modern UI

---

# 🌍 Real-World Applications

- Smart Farming
- Precision Agriculture
- Irrigation Planning
- Crop Health Monitoring
- Agricultural Decision Support
- Government Agriculture Programs
- Satellite Data Analytics
- Remote Sensing Research

---

# 🙏 Acknowledgements

Special thanks to:

- 🇮🇳 ISRO – Bharatiya Antariksh Hackathon 2026
- Sentinel-1 & Sentinel-2 Mission
- OpenStreetMap
- Leaflet.js
- Flask
- Scikit-learn
- Python Community

---

# 📬 Contact

**Sunny Kumar**

- GitHub: https://github.com/SunnyAgrwl05
- LinkedIn: https://linkedin.com/in/sunny-kumar-a06484297

For collaboration, feedback, or project discussions, feel free to connect.

---

<p align="center">

### ⭐ If you found this project useful, please consider giving it a Star!

Made with ❤️ by **Team SpaceHack**

</p>







