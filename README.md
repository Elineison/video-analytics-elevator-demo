# Elevator Dwell Analytics

Public case study of an elevator video-analytics service for security operations.

This repository is a sanitized, portfolio-safe version of work I built around VMS camera streams, person detection, dwell-time rules, alert cooldowns, and operator health checks. It is not a dump of production code. The purpose is to show the engineering decisions without exposing customers, camera endpoints, recordings, SDK files, credentials, or private integrations.

## Operational Problem

In monitored residential environments, an elevator camera can stay visually normal while the operational signal is abnormal: a person remains inside the cabin, the stream freezes, an alert endpoint stops receiving events, or the same event repeats too often. The system needs to detect dwell time, keep enough runtime context for support, and produce a payload that downstream monitoring tools can understand.

## What This Demonstrates

- FastAPI service design for video analytics workers.
- Per-camera runtime state with ROI, threshold, cooldown, last frame age, and tracks.
- Synthetic person-track ingestion that creates an event only after the configured dwell threshold.
- Health endpoint that separates camera runtime issues from business events.
- Public-safe integration payload shape for alert forwarding.

## Architecture

```text
VMS stream worker -> detection payload -> dwell-time engine -> event payload
                                      -> runtime snapshot -> health endpoint
```

The real production-style system would receive frames from a VMS/SDK worker and run detection/tracking before calling the analytics layer. This public version starts at the detection payload boundary so the repository can be tested anywhere.

## Run Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8011
```

Open:

- `http://127.0.0.1:8011/`
- `http://127.0.0.1:8011/api/cameras`
- `http://127.0.0.1:8011/api/system/health`

Create a synthetic dwell event:

```bash
curl -X POST http://127.0.0.1:8011/api/demo/elevator-dwell
curl http://127.0.0.1:8011/api/events
```

## Why This Is Public-Safe

The repository uses synthetic sites, camera IDs, bounding boxes, and event payloads. It does not include real IP addresses, customer names, recordings, vendor SDK binaries, alert URLs, or credentials.

## Skills Represented

Python, FastAPI, video analytics architecture, runtime health checks, event modeling, VMS operations, API design, and production-minded sanitization.
