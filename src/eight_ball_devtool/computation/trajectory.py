"""Project millimetres / pooltool metres, with a 90-degree axis rotation."""
from ..models import BallTrajectory, Point, TrajectorySample


def to_pooltool(point, table_height):
    return (table_height-point.y)/1000, point.x/1000


def from_pooltool(x, y, table_height):
    return Point(y*1000, table_height-x*1000)


def extract_trajectories(system, numbers, table_height):
    paths = []
    for ball_id, ball in system.balls.items():
        samples = []
        for state in ball.history_cts:
            x, y, z = state.rvw[0]
            point = from_pooltool(float(x), float(y), table_height)
            samples.append(TrajectorySample(float(state.t), point.x, point.y, float(z)*1000))
        paths.append(BallTrajectory(ball_id, numbers[ball_id], tuple(samples), ball.state.s == 4))
    return tuple(paths)
