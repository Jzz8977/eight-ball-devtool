"""Reproducible versions of two upstream pooltool teaching experiments.

Adapted from pooltool 0.6 docs notebooks, Apache-2.0; attribution in
third_party/pooltool/NOTICE.md. Simulate with upstream code, not rewritten physics.
"""
from math import acos, degrees, hypot, isfinite, sqrt

from .aiming import ball_hit_fraction, natural_carom_angle
from .pooltool_runtime import load_pooltool


def thirty_degree_experiment(cuts=(14, 20, 30, 40, 49), speed=2.5):
    if not isfinite(speed) or not 1 <= speed <= 4:
        raise ValueError('实验杆速需在 1–4 m/s 之间')
    pt = load_pooltool()
    template = pt.System(table=pt.Table.from_table_specs(pt.objects.BilliardTableSpecs(l=10, w=10)), balls=(pt.Ball.create('cue', xy=(2.5, 1.5)), pt.Ball.create('obj', xy=(2.5, 3.0))), cue=pt.Cue(cue_ball_id='cue'))
    engine = pt.evolution.SimulationEngine()
    engine.resolver.ball_ball = pt.physics.ball_ball_models[pt.physics.BallBallModel.FRICTIONLESS_ELASTIC]()
    rows = []
    for cut in cuts:
        if not 2 <= cut <= 88:
            raise ValueError('实验切球角限定为 2–88 度，避免零速度端点')
        system = template.copy()
        system.cue.set_state(V0=speed, phi=pt.aim.at_ball(system, 'obj', cut=cut), a=0, b=.4, theta=0)
        pt.simulate(system, engine=engine, inplace=True)
        collision = next(event for event in system.events if event.event_type == pt.EventType.BALL_BALL)
        before = collision.get_ball('cue', initial=True)
        if before.state.s != pt.constants.rolling:
            raise ValueError('当前实验母球碰撞前不是纯滚动，不能套用自然角公式')
        transition = next(event for event in system.events if event.time > collision.time and 'cue' in event.ids and event.event_type == pt.EventType.SLIDING_ROLLING)
        initial = before.state.rvw[1, :2]
        final = transition.get_ball('cue', initial=False).state.rvw[1, :2]
        cosine = float(initial@final)/(hypot(*initial)*hypot(*final))
        measured = degrees(acos(max(-1, min(1, cosine))))
        rows.append({'cut_deg': float(cut), 'hit_fraction': ball_hit_fraction(cut), 'measured_carom_deg': measured, 'theory_carom_deg': natural_carom_angle(cut), 'cue_speed_m_s': speed})
    return rows


def create_straight_system(distance, separation):
    """D: cue-centre to pocket lip; d: distance between cue and object centres."""
    if not all(isfinite(v) for v in (distance, separation)) or not .3 <= distance <= 4 or not 2.001*.028575 <= separation < distance:
        raise ValueError('需满足 0.3≤D≤4 m 且 2.001R≤d<D')
    pt = load_pooltool()
    table = pt.Table.from_table_specs(pt.objects.PocketTableSpecs(l=10, w=10))
    pocket = table.pockets['lb']
    pocket_point = pocket.center[:2]+pocket.radius/sqrt(2)
    cue = pt.Ball.create('CB', xy=pocket_point+distance/sqrt(2))
    target = pt.Ball.create('OB', xy=cue.xyz[:2]-separation/sqrt(2))
    return pt.System(table=table, balls=(cue, target), cue=pt.Cue(cue_ball_id='CB'))


def straight_shot_experiment(distance=2.0, positions=12, trials=100, errors=(.15, .25, .5), seed=42):
    if type(positions) is not int or not 2 <= positions <= 100 or type(trials) is not int or not 1 <= trials <= 10000:
        raise ValueError('positions 需为 2–100，trials 需为 1–10000')
    if not errors or any(not isfinite(v) or not 0 <= v <= 5 for v in errors):
        raise ValueError('方向误差幅度需在 0–5 度之间')
    pt = load_pooltool()
    import numpy as np
    rng = np.random.default_rng(seed)
    separations = np.linspace(2.001*.028575, distance-.001, positions)
    rows = []
    for error in errors:
        for d in separations:
            template = create_straight_system(distance, float(d))
            pots, scratches, safe = 0, 0, 0
            for _ in range(trials):
                system = template.copy()
                system.cue.set_state(V0=1, phi=225+float(rng.uniform(-error, error)), a=0, b=.25, theta=0)
                pt.simulate(system, inplace=True)
                drops = {event.ids[0]: event.ids[1] for event in system.events if event.event_type == pt.EventType.BALL_POCKET}
                potted, scratch = drops.get('OB') == 'lb', 'CB' in drops
                pots += potted
                scratches += scratch
                safe += potted and not scratch
            rows.append({'D_m': distance, 'd_m': float(d), 'd_over_D': float(d)/distance, 'direction_error_deg': error, 'trials': trials, 'seed': seed, 'pot_rate': pots/trials, 'scratch_rate': scratches/trials, 'safe_pot_rate': safe/trials})
    return rows
