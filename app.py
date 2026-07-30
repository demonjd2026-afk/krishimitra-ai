"""
app.py
-------
KrishiMitra backend. Ek Flask app jo pura AI pipeline serve karta hai:
  ingestion (simulated satellite) -> feature extraction -> AI models
  (crop + stress) -> decision engine (irrigation advisory) -> dashboard.

Run: python3 app.py   (default: http://0.0.0.0:5000)
"""

import os
import sys
import io
import csv
import json
from datetime import date, datetime, timedelta

from flask import Flask, jsonify, request, render_template, Response

sys.path.append(os.path.join(os.path.dirname(__file__), "model"))
from satellite_sim import simulate_field, CROP_CALENDAR
from decision_engine import compute_advisory
from weather import get_weather, get_forecast
from location_search import search_location
import history as history_db

import joblib
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(__file__)
MODEL_DIR = os.path.join(BASE, "model")
FEATURES = ["NDVI", "NDWI", "MSI", "VV_dB", "VH_dB", "VV_VH_ratio", "growth_fraction"]

# /api/trend: how many days of history a caller may ask for, and the maximum
# number of points we ever return (longer windows are sub-sampled, so a 180-day
# request stays as cheap to compute and as readable on a chart as a 30-day one).
TREND_MIN_DAYS = 7
TREND_MAX_DAYS = 180
TREND_MAX_POINTS = 45

app = Flask(__name__)

app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
app.config["TEMPLATES_AUTO_RELOAD"] = True

history_db.init_db()

_crop_model = None
_stress_model = None


def get_models():
    global _crop_model, _stress_model
    if _crop_model is None:
        crop_path = os.path.join(MODEL_DIR, "crop_model.pkl")
        stress_path = os.path.join(MODEL_DIR, "stress_model.pkl")
        if not (os.path.exists(crop_path) and os.path.exists(stress_path)):
            raise RuntimeError(
                "Models not found. Run: python3 model/generate_training_data.py "
                "&& python3 model/train_model.py"
            )
        _crop_model = joblib.load(crop_path)
        _stress_model = joblib.load(stress_path)
    return _crop_model, _stress_model


# ---- demo fields shown on the dashboard by default (matches the mock UI) ----
DEMO_FIELDS = [
    {
        "id": "F-21",
        "name": "Sunny Kumar",
        "district": "Bakhtiyarpur",
        "state": "Bihar",
        "lat": 25.46,
        "lon": 85.53,
        "crop_hint": "Rice"
    },
    {
        "id": "F-14",
        "name": "Tanya Garg",
        "district": "Meerut",
        "state": "Uttar Pradesh",
        "lat": 28.98,
        "lon": 77.70,
        "crop_hint": "Wheat"
    },
    {
        "id": "F-08",
        "name": "Adarsh Kushwaha",
        "district": "Faridabad",
        "state": "Haryana",
        "lat": 28.41,
        "lon": 77.31,
        "crop_hint": "Mustard"
    },
    {
        "id": "F-33",
        "name": "Siddharth",
        "district": "Lucknow",
        "state": "Uttar Pradesh",
        "lat": 26.85,
        "lon": 80.95,
        "crop_hint": "Maize"
    },
     {
    "id": "F-05",
    "name": "Kajal Kumari",
    "district": "Begusarai",
    "state": "Bihar",
    "lat": 25.4182,
    "lon": 86.1272,
    "crop_hint": "Rice"
},
{
    "id": "F-19",
    "name": "Team SpaceHack",
    "district": "Gurugram",
    "state": "Haryana",
    "lat": 28.46,
    "lon": 77.03,
    "crop_hint": "Sugarcane"
},
]


def run_pipeline(lat, lon, crop_hint=None, when=None, deficit=None):
    """Full pipeline: ingestion -> features -> AI models -> decision engine."""
    rec = simulate_field(lat, lon, crop_hint=crop_hint, when=when, irrigation_deficit_pct=deficit)

    crop_model, stress_model = get_models()
    feat = pd.DataFrame([{
        "NDVI": rec["optical"]["NDVI"], "NDWI": rec["optical"]["NDWI"], "MSI": rec["optical"]["MSI"],
        "VV_dB": rec["sar"]["VV_dB"], "VH_dB": rec["sar"]["VH_dB"],
        "VV_VH_ratio": rec["sar"]["VV_VH_ratio"], "growth_fraction": rec["growth_fraction"],
    }])[FEATURES]

    if crop_hint:
        predicted_crop = crop_hint
        crop_proba = 1.0
    else:
        predicted_crop = crop_model.predict(feat)[0]
        crop_proba = max(crop_model.predict_proba(feat)[0])
    predicted_stress = stress_model.predict(feat)[0]
    stress_proba = max(stress_model.predict_proba(feat)[0])

    advisory = compute_advisory(rec, predicted_stress)

    return {
        "field": {"lat": lat, "lon": lon, "date": rec["date"]},
        "satellite_features": rec,
        "ai_prediction": {
            "predicted_crop": predicted_crop,
            "crop_confidence": round(float(crop_proba), 3),
            "predicted_stress": predicted_stress,
            "stress_confidence": round(float(stress_proba), 3),
        },
        "advisory": advisory,
    }


@app.route("/")
def dashboard():
    return render_template("index.html")


@app.route("/api/fields")
def api_fields():
    """Runs the full pipeline for all demo fields in parallel."""

    def process(f):
        try:
            out = run_pipeline(
                f["lat"],
                f["lon"],
                crop_hint=f["crop_hint"]
            )

            out["field"].update({
                "id": f["id"],
                "name": f["name"],
                "district": f["district"],
                "state": f["state"]
            })

            return out

        except Exception as e:
            return {
                "error": str(e),
                "field": f
            }

    with ThreadPoolExecutor(max_workers=min(6, len(DEMO_FIELDS))) as executor:
        results = list(executor.map(process, DEMO_FIELDS))

    return jsonify(results)


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    """Ad-hoc analysis for a user-supplied lat/lon (+ optional crop hint / date)."""
    data = request.get_json(force=True) or {}
    try:
        lat = float(data["lat"])
        lon = float(data["lon"])
    except (KeyError, ValueError, TypeError):
        return jsonify({"error": "lat aur lon (numbers) required hain"}), 400

    crop_hint = data.get("crop") or None
    if crop_hint not in (None, *CROP_CALENDAR.keys()):
        crop_hint = None

    when = None
    if data.get("date"):
        try:
            when = datetime.strptime(data["date"], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "date format YYYY-MM-DD hona chahiye"}), 400

    deficit = data.get("deficit_pct")
    if deficit is not None:
        try:
            deficit = float(deficit)
        except ValueError:
            return jsonify({"error": "deficit_pct number hona chahiye"}), 400

    result = run_pipeline(lat, lon, crop_hint=crop_hint, when=when, deficit=deficit)
    try:
        history_db.log_analysis(result)
    except Exception as e:
        print(f"[app.py] History log failed (non-fatal): {e}")
    return jsonify(result)


@app.route("/api/model-metrics")
def api_metrics():
    metrics_path = os.path.join(MODEL_DIR, "metrics.json")
    if not os.path.exists(metrics_path):
        return jsonify({"error": "metrics.json missing, train model first"}), 404
    with open(metrics_path) as f:
        return jsonify(json.load(f))


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})


@app.route("/api/weather")
def api_weather():
    """Rain/humidity/temp/wind for a lat/lon -- live OpenWeatherMap if OPENWEATHER_API_KEY
    is set, otherwise a deterministic simulated forecast (never errors out)."""
    try:
        lat = float(request.args.get("lat"))
        lon = float(request.args.get("lon"))
    except (TypeError, ValueError):
        return jsonify({"error": "lat aur lon query params (numbers) required hain"}), 400
    return jsonify(get_weather(lat, lon))


@app.route("/api/forecast")
def api_forecast():
    """7-day weather forecast (current + daily) for a lat/lon via the free
    Open-Meteo API. Falls back to a deterministic simulated forecast if the API
    can't be reached, so it never errors out."""
    try:
        lat = float(request.args.get("lat"))
        lon = float(request.args.get("lon"))
    except (TypeError, ValueError):
        return jsonify({"error": "lat aur lon query params (numbers) required hain"}), 400
    return jsonify(get_forecast(lat, lon))


@app.route("/api/search-location")
def api_search_location():
    """Village/district/state autocomplete via Nominatim. Always returns 200 --
    an empty results list (with a note) if the lookup can't complete."""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"results": [], "note": "q query param required hai"}), 400
    return jsonify(search_location(query))


def _trend_dates(days, step, end=None):
    """Ascending list of dates covering the last `days` days (inclusive of today),
    sampled every `step` days. The most recent day is always the last point."""
    end = end or date.today()
    offsets = list(range(days - 1, -1, -step))
    if offsets[-1] != 0:
        offsets.append(0)
    return [end - timedelta(days=o) for o in offsets]


@app.route("/api/trend")
def api_trend():
    """Time-series of vegetation indices, SAR backscatter and irrigation demand
    for one field -- the data behind the Analytics charts.

    Query params: lat, lon (required), crop (optional hint), days (7-180,
    default 30). Runs the same ingestion -> features -> AI -> decision-engine
    pipeline as /api/analyze, once per sampled date, with a single batched model
    call. Read-only: nothing is written to the history DB."""
    try:
        lat = float(request.args.get("lat"))
        lon = float(request.args.get("lon"))
    except (TypeError, ValueError):
        return jsonify({"error": "lat aur lon query params (numbers) required hain"}), 400

    try:
        days = int(request.args.get("days", 30))
    except ValueError:
        return jsonify({"error": "days number hona chahiye"}), 400
    days = max(TREND_MIN_DAYS, min(days, TREND_MAX_DAYS))

    crop_hint = request.args.get("crop") or None
    if crop_hint not in (None, *CROP_CALENDAR.keys()):
        crop_hint = None

    step = max(1, -(-days // TREND_MAX_POINTS))  # ceil division
    dates = _trend_dates(days, step)

    try:
        records = [simulate_field(lat, lon, crop_hint=crop_hint, when=d) for d in dates]

        crop_model, stress_model = get_models()
        feats = pd.DataFrame([{
            "NDVI": r["optical"]["NDVI"], "NDWI": r["optical"]["NDWI"], "MSI": r["optical"]["MSI"],
            "VV_dB": r["sar"]["VV_dB"], "VH_dB": r["sar"]["VH_dB"],
            "VV_VH_ratio": r["sar"]["VV_VH_ratio"], "growth_fraction": r["growth_fraction"],
        } for r in records])[FEATURES]

        # One batched predict for the whole window instead of N single-row calls.
        stress_preds = stress_model.predict(feats)
        stress_probas = stress_model.predict_proba(feats)
        crop_preds = [crop_hint] * len(records) if crop_hint else list(crop_model.predict(feats))
    except Exception as e:
        return jsonify({"error": f"Trend computation failed: {e}"}), 500

    series = []
    stress_counts, urgency_counts = {}, {}
    for i, rec in enumerate(records):
        stress = str(stress_preds[i])
        advisory = compute_advisory(rec, stress)
        stress_counts[stress] = stress_counts.get(stress, 0) + 1
        urgency_counts[advisory["urgency"]] = urgency_counts.get(advisory["urgency"], 0) + 1
        series.append({
            "date": rec["date"],
            "crop": rec["crop"],
            "predicted_crop": str(crop_preds[i]),
            "growth_stage": rec["growth_stage"],
            "growth_fraction": rec["growth_fraction"],
            "NDVI": rec["optical"]["NDVI"],
            "NDWI": rec["optical"]["NDWI"],
            "MSI": rec["optical"]["MSI"],
            "VV_dB": rec["sar"]["VV_dB"],
            "VH_dB": rec["sar"]["VH_dB"],
            "VV_VH_ratio": rec["sar"]["VV_VH_ratio"],
            "moisture_deficit_pct": rec["simulated_deficit_pct"],
            "predicted_stress": stress,
            "stress_confidence": round(float(max(stress_probas[i])), 3),
            "urgency": advisory["urgency"],
            "recommended_water_mm": advisory["recommended_water_mm"],
            "crop_water_demand_mm_day": advisory["crop_water_demand_mm_day"],
        })

    ndvis = [p["NDVI"] for p in series]
    ndvi_change = round(series[-1]["NDVI"] - series[0]["NDVI"], 3)
    if ndvi_change > 0.05:
        trend = "improving"
    elif ndvi_change < -0.05:
        trend = "declining"
    else:
        trend = "stable"

    return jsonify({
        "field": {"lat": lat, "lon": lon, "crop_hint": crop_hint},
        "range": {
            "days": days,
            "step_days": step,
            "points": len(series),
            "from": series[0]["date"],
            "to": series[-1]["date"],
        },
        "series": series,
        "summary": {
            "avg_ndvi": round(sum(ndvis) / len(ndvis), 3),
            "min_ndvi": min(ndvis),
            "max_ndvi": max(ndvis),
            "avg_ndwi": round(sum(p["NDWI"] for p in series) / len(series), 3),
            "avg_msi": round(sum(p["MSI"] for p in series) / len(series), 3),
            "total_recommended_water_mm": round(sum(p["recommended_water_mm"] for p in series), 1),
            "ndvi_change": ndvi_change,
            "trend": trend,
            "stress_distribution": stress_counts,
            "urgency_distribution": urgency_counts,
            "latest": series[-1],
        },
        "source": records[-1]["source"],
    })


@app.route("/api/history")
def api_history():
    """Past analyses logged by /api/analyze. Supports ?crop=&urgency=&limit="""
    limit = request.args.get("limit", 50)
    try:
        limit = int(limit)
    except ValueError:
        limit = 50
    crop = request.args.get("crop") or None
    urgency = request.args.get("urgency") or None
    try:
        return jsonify(history_db.get_history(limit=limit, crop=crop, urgency=urgency))
    except Exception as e:
        return jsonify({"error": f"History fetch failed: {e}"}), 500


@app.route("/api/dashboard")
def api_dashboard():
    """Aggregate summary across the demo fields -- for a landing/overview widget."""
    try:
        def process_dashboard(f):
            try:
                return run_pipeline(
                    f["lat"],
                    f["lon"],
                    crop_hint=f["crop_hint"]
                )
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=min(6, len(DEMO_FIELDS))) as executor:
            results = [r for r in executor.map(process_dashboard, DEMO_FIELDS) if r is not None]

        total = len(results)
        crop_counts, stress_counts, urgency_counts = {}, {}, {}
        avg_ndvi = 0.0
        for r in results:
            crop_counts[r["ai_prediction"]["predicted_crop"]] = crop_counts.get(r["ai_prediction"]["predicted_crop"], 0) + 1
            stress_counts[r["ai_prediction"]["predicted_stress"]] = stress_counts.get(r["ai_prediction"]["predicted_stress"], 0) + 1
            urgency_counts[r["advisory"]["urgency"]] = urgency_counts.get(r["advisory"]["urgency"], 0) + 1
            avg_ndvi += r["satellite_features"]["optical"]["NDVI"]
        avg_ndvi = round(avg_ndvi / total, 3) if total else 0

        try:
            recent_history = history_db.get_history(limit=10)
        except Exception:
            recent_history = []

        return jsonify({
            "total_fields": total,
            "avg_ndvi": avg_ndvi,
            "crop_distribution": crop_counts,
            "stress_distribution": stress_counts,
            "urgency_distribution": urgency_counts,
            "recent_history": recent_history,
        })
    except Exception as e:
        return jsonify({"error": f"Dashboard aggregation failed: {e}"}), 500


@app.route("/api/export/csv")
def api_export_csv():
    """Exports the demo-field dashboard analysis as a downloadable CSV file.

    Reuses the same AI pipeline as /api/fields and adds the per-field weather
    context. Empty datasets are handled gracefully (headers-only CSV). The file
    is UTF-8 encoded (with BOM so Excel opens it correctly) and streamed as an
    attachment download."""

    def process(f):
        try:
            out = run_pipeline(f["lat"], f["lon"], crop_hint=f["crop_hint"])
            out["field"].update({
                "id": f["id"],
                "name": f["name"],
                "district": f["district"],
                "state": f["state"],
            })
            try:
                out["weather"] = get_weather(f["lat"], f["lon"])
            except Exception:
                out["weather"] = {}
            return out
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=min(6, len(DEMO_FIELDS))) as executor:
        results = [r for r in executor.map(process, DEMO_FIELDS) if r is not None]

    exported_at = datetime.now().isoformat(timespec="seconds")

    buf = io.StringIO()
    buf.write("﻿")  # UTF-8 BOM -> Excel opens special characters correctly
    writer = csv.writer(buf)

    writer.writerow([
        "Field ID", "Farmer", "District", "State", "Latitude", "Longitude",
        "Analysis Date", "Crop", "Crop Confidence", "Stress Level",
        "Stress Confidence", "NDVI", "NDWI", "MSI", "VV_dB", "VH_dB",
        "VV_VH_ratio", "Growth Stage", "Growth Fraction", "Urgency",
        "Recommended Water (mm)", "Crop Water Demand (mm/day)", "Advisory",
        "Reasoning", "Rain (mm)", "Humidity (%)", "Temp (C)", "Wind (kph)",
        "Exported At",
    ])

    for r in results:
        field = r.get("field", {})
        sat = r.get("satellite_features", {})
        optical = sat.get("optical", {})
        sar = sat.get("sar", {})
        ai = r.get("ai_prediction", {})
        adv = r.get("advisory", {})
        wx = r.get("weather", {})
        reasoning = adv.get("reasoning", "")
        if isinstance(reasoning, (list, tuple)):
            reasoning = "; ".join(str(x) for x in reasoning)
        writer.writerow([
            field.get("id", ""),
            field.get("name", ""),
            field.get("district", ""),
            field.get("state", ""),
            field.get("lat", ""),
            field.get("lon", ""),
            field.get("date", ""),
            ai.get("predicted_crop", ""),
            ai.get("crop_confidence", ""),
            ai.get("predicted_stress", ""),
            ai.get("stress_confidence", ""),
            optical.get("NDVI", ""),
            optical.get("NDWI", ""),
            optical.get("MSI", ""),
            sar.get("VV_dB", ""),
            sar.get("VH_dB", ""),
            sar.get("VV_VH_ratio", ""),
            sat.get("growth_stage", ""),
            sat.get("growth_fraction", ""),
            adv.get("urgency", ""),
            adv.get("recommended_water_mm", ""),
            adv.get("crop_water_demand_mm_day", ""),
            adv.get("action_hi", ""),
            reasoning,
            wx.get("rain_mm", ""),
            wx.get("humidity_pct", ""),
            wx.get("temp_c", ""),
            wx.get("wind_kph", ""),
            exported_at,
        ])

    filename = f"krishimitra_fields_{date.today().isoformat()}.csv"
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False
    )