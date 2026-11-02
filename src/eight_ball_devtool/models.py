"""Shared contracts; layer implementations must not depend on Tkinter."""
from dataclasses import dataclass, field
from math import hypot


@dataclass(frozen=True)
class Point:
    x: float
    y: float

    def distance(self, other: 'Point') -> float:
        return hypot(self.x - other.x, self.y - other.y)


@dataclass(frozen=True)
class Ball:
    number: int | None
    center: Point
    radius: float = 28.575
    # None is deliberately retained for unknown identities from future detectors.


@dataclass(frozen=True)
class Frame:
    source: str
    width: int
    height: int
    path: str | None = None
    rgb: bytes | None = field(default=None, repr=False)
    image_id: str = ''


@dataclass(frozen=True)
class Detection:
    number: int | None
    center: Point
    radius: float
    kind: str = 'ball'
    confidence: float = 1.0


@dataclass(frozen=True)
class Shot:
    target: Ball
    pocket: Point
    ghost: Point
    cut_angle: float
    distance: float


@dataclass(frozen=True)
class CueAction:
    direction_deg: float
    speed_m_s: float
    side_spin: float = 0
    top_spin: float = 0


@dataclass(frozen=True)
class TrajectorySample:
    time: float
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class BallTrajectory:
    ball_id: str
    number: int | None
    samples: tuple[TrajectorySample, ...]
    pocketed: bool


@dataclass(frozen=True)
class CollisionEvent:
    time: float
    kind: str
    agents: tuple[str, ...]


@dataclass(frozen=True)
class SimulationResult:
    shot: Shot
    action: CueAction
    trajectories: tuple[BallTrajectory, ...]
    events: tuple[CollisionEvent, ...]
    duration: float
    target_pocketed: bool
    cue_pocketed: bool
    first_contact: str | None
    accepted: bool
    reason: str
    pocket_id: str
    completed: bool


@dataclass(frozen=True)
class PhysicsEvaluation:
    selected: SimulationResult
    candidates: tuple[SimulationResult, ...]


@dataclass(frozen=True)
class Result:
    frame: Frame
    balls: tuple[Ball, ...]
    shots: tuple[Shot, ...]
    fused: bool
    elapsed_ms: float
    # Manual table-to-world registration, not a SLAM estimate.
    world_points: tuple[tuple[float, float, float], ...] = ()
    detections: tuple[Detection, ...] = ()
    status: str = 'ready'
    message: str = ''
    physics: PhysicsEvaluation | None = None
