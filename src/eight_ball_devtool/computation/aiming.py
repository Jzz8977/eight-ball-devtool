"""Ideal rolling-cue-ball reference used by pooltool's 30-degree example.

Source: pooltool docs/examples/30_degree_rule.ipynb (Apache-2.0).
This is not a universal aiming rule or a replacement for spin-aware simulation.
"""
from math import atan2, cos, degrees, isfinite, radians, sin


def ball_hit_fraction(cut_angle):
    if not isfinite(cut_angle) or not 0 <= cut_angle <= 90:
        raise ValueError('切球角需在 0–90 度之间')
    return 1-sin(radians(cut_angle))


def natural_carom_angle(cut_angle):
    ball_hit_fraction(cut_angle)
    phi = radians(cut_angle)
    return degrees(atan2(sin(phi)*cos(phi), sin(phi)**2+2/5))
