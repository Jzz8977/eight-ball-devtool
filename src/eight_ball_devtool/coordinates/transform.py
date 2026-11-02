"""Pure Python planar homography. Image points are normalized before fitting."""
import math
from ..models import Ball, Point


def validate_quad(points):
    if not isinstance(points, (list, tuple)) or len(points) != 4:
        raise ValueError('标定需要四个点：左上、右上、右下、左下')
    for p in points:
        if not isinstance(p, (list, tuple)) or len(p) != 2 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1 for v in p):
            raise ValueError('标定点必须为 0–1 之间的归一化坐标')
    crosses = []
    for i, a in enumerate(points):
        b, c = points[(i + 1) % 4], points[(i + 2) % 4]
        crosses.append((b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0]))
    if min(crosses) < 1e-6:
        raise ValueError('四点需按左上、右上、右下、左下形成非退化凸四边形')


def solve(matrix, rhs):
    rows = [list(a) + [b] for a, b in zip(matrix, rhs)]
    size = len(rhs)
    for c in range(size):
        pivot = max(range(c, size), key=lambda r: abs(rows[r][c]))
        if abs(rows[pivot][c]) < 1e-12:
            raise ValueError('标定矩阵退化，请重新选点')
        rows[c], rows[pivot] = rows[pivot], rows[c]
        factor = rows[c][c]
        rows[c] = [x / factor for x in rows[c]]
        for r in range(size):
            if r != c:
                factor = rows[r][c]
                rows[r] = [x - factor*y for x, y in zip(rows[r], rows[c])]
    return tuple(row[-1] for row in rows)


class TableTransform:
    def __init__(self, points, width, height):
        validate_quad(points)
        matrix, rhs = [], []
        for (x, y), (u, v) in zip(points, [(0, 0), (width, 0), (width, height), (0, height)]):
            matrix += [[x, y, 1, 0, 0, 0, -u*x, -u*y], [0, 0, 0, x, y, 1, -v*x, -v*y]]
            rhs += [u, v]
        self.h = solve(matrix, rhs)

    def project(self, p: Point) -> Point:
        a, b, c, d, e, f, g, h = self.h
        scale = g*p.x + h*p.y + 1
        if abs(scale) < 1e-12:
            raise ValueError('点位投影到无穷远')
        return Point((a*p.x+b*p.y+c)/scale, (d*p.x+e*p.y+f)/scale)


def map_detections(detections, frame, config):
    # Demo frame covers the table exactly. Real images need explicit calibration.
    points = [[0, 0], [1, 0], [1, 1], [0, 1]] if frame.source == 'demo' else config.calibration
    transform = TableTransform(points, config.table_width, config.table_height)
    return tuple(Ball(d.number, transform.project(Point(d.center.x/frame.width, d.center.y/frame.height)), config.ball_radius) for d in detections)
