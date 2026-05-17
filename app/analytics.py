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
    counter_paused: bool = False
    alert_sent: bool = False


@dataclass
class CameraRuntime:
    camera_id: str
    camera_name: str
    site: str
    threshold_s: float
    cooldown_s: float
    roi: List[dict]
    forbidden_zone: List[dict]
    last_frame_at: float = field(default_factory=time)
    last_alert_at: float = 0.0
    tracks: Dict[str, TrackState] = field(default_factory=dict)


class ElevatorAnalyticsEngine:
    def __init__(self) -> None:
        self._runtimes: Dict[str, CameraRuntime] = {}
        self._events: List[dict] = []

    def register_camera(self, camera: dict) -> None:
        self._runtimes[camera['id']] = CameraRuntime(
            camera_id=camera['id'],
            camera_name=camera['name'],
            site=camera['site'],
            threshold_s=float(camera['threshold_s']),
            cooldown_s=float(camera['cooldown_s']),
            roi=list(camera.get('roi', [])),
            forbidden_zone=list(camera.get('forbidden_zone', [])),
        )

    def ingest_detection(
        self,
        camera_id: str,
        track_id: str,
        confidence: float,
        bbox: List[float],
        observed_for_s: float,
        counter_paused: bool = False,
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
                counter_paused=counter_paused,
            )
            runtime.tracks[track_id] = track
        else:
            track.last_seen = now
            track.observed_for_s = max(track.observed_for_s, observed_for_s)
            track.confidence = confidence
            track.bbox = bbox
            track.counter_paused = counter_paused

        event = self._maybe_create_event(runtime, track)
        return {'track': self._track_payload(track), 'event': event}

    def list_events(self) -> List[dict]:
        return list(self._events)

    def runtime_snapshot(self, camera_id: str) -> dict:
        runtime = self._runtimes[camera_id]
        now = time()
        return {
            'camera_id': runtime.camera_id,
            'camera_name': runtime.camera_name,
            'site': runtime.site,
            'state': 'RUNNING',
            'last_frame_age_s': round(now - runtime.last_frame_at, 3),
            'threshold_s': runtime.threshold_s,
            'cooldown_s': runtime.cooldown_s,
            'roi': runtime.roi,
            'forbidden_zone': runtime.forbidden_zone,
            'tracks': [self._track_payload(track) for track in runtime.tracks.values()],
        }

    def system_health(self) -> dict:
        snapshots = [self.runtime_snapshot(camera_id) for camera_id in self._runtimes]
        stale = [item['camera_id'] for item in snapshots if item['last_frame_age_s'] > 30]
        open_events = [event for event in self._events if event['status'] == 'open']
        return {
            'service': 'elevator-dwell-analytics',
            'state': 'HEALTHY' if not stale else 'DEGRADED',
            'cameras_total': len(snapshots),
            'cameras_running': len(snapshots) - len(stale),
            'open_events': len(open_events),
            'issues': [
                {'camera_id': camera_id, 'reason': 'no_recent_frames'}
                for camera_id in stale
            ],
        }

    def _maybe_create_event(self, runtime: CameraRuntime, track: TrackState) -> dict | None:
        now = time()
        cooldown_ok = now - runtime.last_alert_at >= runtime.cooldown_s
        if (
            track.observed_for_s < runtime.threshold_s
            or track.alert_sent
            or not cooldown_ok
            or track.counter_paused
        ):
            return None

        track.alert_sent = True
        runtime.last_alert_at = now
        event = {
            'id': f"evt-elev-{len(self._events) + 1:04d}",
            'type': 'elevator_dwell_time',
            'severity': 'warning',
            'camera_id': runtime.camera_id,
            'camera_name': runtime.camera_name,
            'site': runtime.site,
            'track_id': track.track_id,
            'duration_s': round(track.observed_for_s, 1),
            'confidence': round(track.confidence, 3),
            'operator_note': 'Person remained in elevator area above configured threshold.',
            'integration_payload': self._integration_payload(runtime, track, now),
            'created_at': now,
            'status': 'open',
        }
        self._events.append(event)
        return event

    @staticmethod
    def _track_payload(track: TrackState) -> dict:
        return {
            'track_id': track.track_id,
            'observed_for_s': round(track.observed_for_s, 1),
            'confidence': round(track.confidence, 3),
            'bbox': track.bbox,
            'counter_paused': track.counter_paused,
            'alert_sent': track.alert_sent,
        }

    @staticmethod
    def _integration_payload(runtime: CameraRuntime, track: TrackState, created_at: float) -> dict:
        return {
            'camera_reference': runtime.camera_id,
            'event_type': 'EXCESS_TIME_ELEVATOR',
            'duration_seconds': round(track.observed_for_s, 1),
            'received_at_epoch': round(created_at, 3),
            'evidence': {
                'track_id': track.track_id,
                'bbox': track.bbox,
                'confidence': round(track.confidence, 3),
            },
        }
