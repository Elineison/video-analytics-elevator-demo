# Video Analytics Elevator Demo

Public portfolio demo of an elevator dwell-time analytics service.

This project presents a professional, sanitized version of a real-world video analytics workflow: cameras send person detections, the service maintains tracks, applies dwell-time thresholds, emits alerts, and exposes health/runtime data for operators.

## What This Demonstrates

- Python backend design with FastAPI
- stateful video analytics workflow modeling
- configurable alert thresholds and cooldowns
- operational health endpoints for support teams
- clean separation between camera catalog, analytics logic, and API layer
- privacy-first demo design with synthetic data only

## Why It Exists

Elevator video analytics is useful when security teams need to detect unusual permanence, possible user distress, maintenance events, or operational anomalies. This demo focuses on the software architecture behind that flow, not on private production footage or proprietary SDK integrations.

## Run Locally

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/api/system/health`
- `http://127.0.0.1:8000/api/cameras`

## Demo Flow

Create synthetic detections:

```bash
curl -X POST "http://127.0.0.1:8000/api/cameras/cam-social-01/detections" \
  -H "Content-Type: application/json" \
  -d '{"track_id":"person-001","confidence":0.91,"bbox":[0.32,0.12,0.58,0.91],"observed_for_s":130}'
```

Then check alerts:

```bash
curl http://127.0.0.1:8000/api/alerts
```

## Portfolio Note

This repository is not a copy of any private production system. It is an original, public-safe demonstration inspired by hands-on work with video monitoring, AI analytics, and operational support.

