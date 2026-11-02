"""Manual table-to-world rigid transform. Future SLAM adapters belong here."""
from math import cos, radians, sin


def fuse(balls, config):
    if config.mode != '3d':
        raise ValueError('空间融合只允许在 3D 模式执行')
    angle = radians(config.world_yaw)
    c, s = cos(angle), sin(angle)
    return tuple((config.world_x+c*b.center.x-s*b.center.y, config.world_y+s*b.center.x+c*b.center.y, config.world_z) for b in balls)
