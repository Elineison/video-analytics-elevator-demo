from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Dict, List


@dataclass
class TrackState:
    track_id: str
    first_seen: float
    last_seen: float
    observed_for_s: float
    confidence: float
    bbox: List[float]
    alert_sent: bool = False


@dataclass
class CameraRuntime:
    camera_id: str
    threshold_s: float
    cooldown_s: float
    last_frame_at: float = field(default_factory=time)
    last_alert_at: float = 0.0
    tracks: Dict[str, TrackState] = field(default_factory=dict)


class ElevatorAnalyticsEngine:
    def __init__(self) -> None:
        self._runtimes: Dict[str, CameraRuntime] = {}
        self._alerts: List[dict] = []

    def register_camera(self, camera_id: str, threshold_s: float, cooldown_s: float) -> None:
        self._runtimes[camera_id] = CameraRuntime(
            camera_id=camera_id,
            threshold_s=threshold_s,
            cooldown_s=cooldown_s,
        )

    def ingest_detection(
        self,
        camera_id: str,
        track_id: str,
        confidence: float,
        bbox: List[float],
        observed_for_s: float,
    ) -> dict:
        runtime = self._runtimes[camera_id]
        now = time()
        runtime.last_frame_at = now
        track = runtime.tracks.get(track_id)
        if track is None:
            track = TrackState(
                track_id=track_id,
                first_seen=now - observed_for_s,
                last_seen=now,
                observed_for_s=observed_for_s,
                confidence=confidence,
                bbox=bbox,
            )
            runtime.tracks[track_id] = track
        else:
            track.last_seen = now
            track.observed_for_s = max(track.observed_for_s, observed_for_s)
            track.confidence = confidence
            track.bbox = bbox

        alert = self._maybe_alert(runtime, track)
        return {"track": self._track_payload(track), "alert": alert}

    def list_alerts(self) -> List[dict]:
        return list(self._alerts)

    def runtime_snapshot(self, camera_id: str) -> dict:
        runtime = self._runtimes[camera_id]
        now = time()
        return {
            "camera_id": runtime.camera_id,
            "state": "RUNNING",
            "last_frame_age_s": round(now - runtime.last_frame_at, 3),
            "threshold_s": runtime.threshold_s,
            "cooldown_s": runtime.cooldown_s,
            "tracks": [self._track_payload(track) for track in runtime.tracks.values()],
        }

    def system_health(self) -> dict:
        snapshots = [self.runtime_snapshot(camera_id) for camera_id in self._runtimes]
        stale = [
            item["camera_id"]
            for item in snapshots
            if item["last_frame_age_s"] > 30
        ]
        return {
            "service": "video-analytics-elevator-demo",
            "state": "HEALTHY" if not stale else "DEGRADED",
            "cameras_total": len(snapshots),
            "cameras_running": len(snapshots) - len(stale),
            "active_alerts": len(self._alerts),
            "issues": [
                {"camera_id": camera_id, "reason": "no_recent_frames"}
                for camera_id in stale
            ],
        }

    def _maybe_alert(self, runtime: CameraRuntime, track: TrackState) -> dict | None:
        now = time()
        cooldown_ok = now - runtime.last_alert_at >= runtime.cooldown_s
        if track.observed_for_s < runtime.threshold_s or track.alert_sent or not cooldown_ok:
            return None

        track.alert_sent = True
        runtime.last_alert_at = now
        alert = {
            "id": f"alert-{len(self._alerts) + 1:04d}",
            "type": "elevator_dwell_time",
            "camera_id": runtime.camera_id,
            "track_id": track.track_id,
            "duration_s": round(track.observed_for_s, 1),
            "confidence": round(track.confidence, 3),
            "created_at": now,
            "status": "active",
        }
        self._alerts.append(alert)
        return alert

    @staticmethod
    def _track_payload(track: TrackState) -> dict:
        return {
            "track_id": track.track_id,
            "observed_for_s": round(track.observed_for_s, 1),
            "confidence": round(track.confidence, 3),
            "bbox": track.bbox,
            "alert_sent": track.alert_sent,
        }

