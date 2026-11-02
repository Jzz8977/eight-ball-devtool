"""Geometric direct-pot planner with ghost-ball aim and obstruction checks.

This is not a full physics simulator: no cushions, spin, speed or pocket jaws.
"""
from math import acos, degrees, hypot
from ..models import Point, Shot


def segment_distance(p, a, b):
    dx, dy = b.x-a.x, b.y-a.y
    length2 = dx*dx + dy*dy
    t = max(0, min(1, ((p.x-a.x)*dx+(p.y-a.y)*dy)/length2)) if length2 else 0
    return hypot(p.x-a.x-t*dx, p.y-a.y-t*dy)


def pockets(width, height):
    return tuple(Point(x, y) for y in (0, height) for x in (0, width/2, width))


def plan(balls, config):
    cues = [b for b in balls if b.number == 0]
    if len(cues) != 1:
        return ()
    cue = cues[0]
    allowed = {'solid': range(1, 8), 'stripe': range(9, 16), 'eight': [8], 'any': range(1, 16)}[config.target_group]
    shots = []
    for target in balls:
        if target.number not in allowed:
            continue
        others = [b for b in balls if b is not cue and b is not target]
        for pocket in pockets(config.table_width, config.table_height):
            distance = target.center.distance(pocket)
            if distance < 1e-9:
                continue
            ux, uy = (pocket.x-target.center.x)/distance, (pocket.y-target.center.y)/distance
            ghost = Point(target.center.x-ux*(cue.radius+target.radius), target.center.y-uy*(cue.radius+target.radius))
            r = cue.radius
            if not (r <= ghost.x <= config.table_width-r and r <= ghost.y <= config.table_height-r):
                continue
            travel = cue.center.distance(ghost)
            if travel < 1e-9:
                continue
            vx, vy = (ghost.x-cue.center.x)/travel, (ghost.y-cue.center.y)/travel
            angle = degrees(acos(max(-1, min(1, vx*ux+vy*uy))))
            if angle > config.max_cut_angle:
                continue
            # The cue must first reach the ghost point without crossing the target.
            if segment_distance(target.center, cue.center, ghost) < cue.radius+target.radius-1e-6:
                continue
            if any(segment_distance(b.center, cue.center, ghost) < b.radius+cue.radius or segment_distance(b.center, target.center, pocket) < b.radius+target.radius for b in others):
                continue
            # After contact the cue also blocks a target moving back through it.
            if segment_distance(cue.center, target.center, pocket) < cue.radius+target.radius:
                continue
            shots.append(Shot(target, pocket, ghost, angle, travel+distance))
    return tuple(sorted(shots, key=lambda s: (s.cut_angle/90+s.distance/6000, s.target.number))[:3])
