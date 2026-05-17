from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.analytics import ElevatorAnalyticsEngine


app = FastAPI(
    title="Video Analytics Elevator Demo",
    version="1.0.0",
    description="Public-safe portfolio demo for elevator dwell-time analytics.",
)


CAMERAS = [
    {
        "id": "cam-social-01",
        "name": "Elevator Social",
        "site": "Demo Tower",
        "vendor": "generic-vms",
        "threshold_s": 120.0,
        "cooldown_s": 60.0,
        "analysis_enabled": True,
    },
    {
        "id": "cam-service-01",
        "name": "Elevator Service",
        "site": "Demo Tower",
        "vendor": "generic-vms",
        "threshold_s": 120.0,
        "cooldown_s": 60.0,
        "analysis_enabled": True,
    },
]

engine = ElevatorAnalyticsEngine()
for camera in CAMERAS:
    engine.register_camera(camera["id"], camera["threshold_s"], camera["cooldown_s"])


class DetectionIn(BaseModel):
    track_id: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: list[float] = Field(min_length=4, max_length=4)
    observed_for_s: float = Field(ge=0.0)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """
    <main style="font-family:system-ui;max-width:880px;margin:40px auto;line-height:1.5">
      <h1>Video Analytics Elevator Demo</h1>
      <p>FastAPI demo for dwell-time analytics, alert thresholds, and health checks.</p>
      <ul>
        <li><a href="/api/system/health">System health</a></li>
        <li><a href="/api/cameras">Cameras</a></li>
        <li><a href="/api/alerts">Alerts</a></li>
      </ul>
    </main>
    """


@app.get("/api/cameras")
def list_cameras() -> list[dict]:
    return [
        {
            **camera,
            "runtime": engine.runtime_snapshot(camera["id"]),
        }
        for camera in CAMERAS
    ]


@app.get("/api/cameras/{camera_id}")
def get_camera(camera_id: str) -> dict:
    camera = _camera_by_id(camera_id)
    return {**camera, "runtime": engine.runtime_snapshot(camera_id)}


@app.post("/api/cameras/{camera_id}/detections")
def ingest_detection(camera_id: str, payload: DetectionIn) -> dict:
    _camera_by_id(camera_id)
    return engine.ingest_detection(
        camera_id=camera_id,
        track_id=payload.track_id,
        confidence=payload.confidence,
        bbox=payload.bbox,
        observed_for_s=payload.observed_for_s,
    )


@app.get("/api/alerts")
def list_alerts() -> list[dict]:
    return engine.list_alerts()


@app.get("/api/system/health")
def system_health() -> dict:
    return engine.system_health()


def _camera_by_id(camera_id: str) -> dict:
    for camera in CAMERAS:
        if camera["id"] == camera_id:
            return camera
    raise HTTPException(status_code=404, detail="Camera not found")

