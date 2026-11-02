"""Shared contracts; layer implementations must not depend on Tkinter."""
from dataclasses import dataclass
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


@dataclass(frozen=True)
class Detection:
    number: int | None
    center: Point
    radius: float


@dataclass(frozen=True)
class Shot:
    target: Ball
    pocket: Point
    ghost: Point
    cut_angle: float
    distance: float


@dataclass(frozen=True)
class Result:
    frame: Frame
    balls: tuple[Ball, ...]
    shots: tuple[Shot, ...]
    fused: bool
    elapsed_ms: float
    # Manual table-to-world registration, not a SLAM estimate.
    world_points: tuple[tuple[float, float, float], ...] = ()
