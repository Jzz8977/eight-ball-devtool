"""Adapter to pooltool-billiards 0.6; never opens the Panda3D game window."""
from math import isfinite

from ..models import CueAction, PhysicsEvaluation, SimulationResult
from .collision import assess_events, extract_events
from .trajectory import extract_trajectories, to_pooltool


class PooltoolEngine:
    def __init__(self):
        self._pt = None

    def backend(self):
        if self._pt is None:
            from .pooltool_runtime import load_pooltool
            self._pt = load_pooltool()
        return self._pt

    @staticmethod
    def validate_scene(balls, config):
        config.validate()
        if sum(ball.number == 0 for ball in balls) != 1:
            raise ValueError('物理仿真需要唯一母球')
        for i, ball in enumerate(balls):
            if not all(isfinite(v) for v in (ball.center.x, ball.center.y, ball.radius)) or ball.radius <= 0:
                raise ValueError('球位或半径无效')
            if not (ball.radius <= ball.center.x <= config.table_width-ball.radius and ball.radius <= ball.center.y <= config.table_height-ball.radius):
                raise ValueError('球心过于靠近库边或位于台面外，请检查标定/误检')
            for other in balls[:i]:
                if ball.center.distance(other.center) < ball.radius+other.radius-.1:
                    raise ValueError('检测球位重叠，请移除重复候选或修正球心后再仿真')

    def build_system(self, balls, config):
        self.validate_scene(balls, config)
        pt = self.backend()
        specs = pt.objects.PocketTableSpecs(l=config.table_width/1000, w=config.table_height/1000, corner_pocket_width=config.corner_pocket_width/1000, side_pocket_width=config.side_pocket_width/1000, cushion_height=1.28*config.ball_radius/1000)
        table = pt.Table.from_table_specs(specs)
        objects, numbers, ids = {}, {}, []
        for i, ball in enumerate(balls):
            bid = 'cue' if ball.number == 0 else f'ball_{i}'
            ids.append(bid)
            numbers[bid] = ball.number
            objects[bid] = pt.Ball.create(bid, xy=to_pooltool(ball.center, config.table_height), R=ball.radius/1000, u_s=config.sliding_friction, u_r=config.rolling_friction, e_b=config.ball_restitution, e_c=config.cushion_restitution)
        return pt.System(cue=pt.Cue(cue_ball_id='cue'), table=table, balls=objects), numbers, ids

    def simulate(self, balls, shot, config):
        system, numbers, ids = self.build_system(balls, config)
        target_index = next((i for i, ball in enumerate(balls) if ball == shot.target), None)
        if target_index is None or shot.target.number in (0, None):
            raise ValueError('目标球必须是场景中已确认球号的非母球')
        target_id = ids[target_index]
        pt = self.backend()
        px, py = to_pooltool(shot.pocket, config.table_height)
        pocket = min(system.table.pockets.values(), key=lambda p: (float(p.center[0])-px)**2+(float(p.center[1])-py)**2)
        # Reuse pooltool's pocket-jaw-aware aiming, rather than the ideal corner.
        phi = float(pt.pot.calc_potting_angle(system.balls['cue'], system.balls[target_id], system.table, pocket))
        action = CueAction((phi-90)%360, config.cue_speed, config.cue_side_spin, config.cue_top_spin)
        system.cue.set_state(V0=action.speed_m_s, phi=phi, theta=0, a=action.side_spin, b=action.top_spin)
        try:
            pt.simulate(system, inplace=True, continuous=True, dt=config.trajectory_dt, max_events=500, t_final=30)
        except Exception as error:
            raise RuntimeError(f'pooltool 仿真失败：{error}') from error
        events = extract_events(system)
        completed = float(system.t) < 30 and len(system.events) < 500
        first, target_in, scratch, accepted, reason = assess_events(events, target_id, pocket.id, numbers, config, completed)
        return SimulationResult(shot, action, extract_trajectories(system, numbers, config.table_height), events, float(system.t), target_in, scratch, first, accepted, reason, pocket.id, completed)

    def evaluate(self, balls, shots, config):
        if not shots:
            raise ValueError('当前没有可用于仿真的几何候选方案')
        simulations = tuple(self.simulate(balls, shot, config) for shot in shots[:3])
        # All candidates use the user's chosen speed/spin; this is not a global
        # optimization over all possible powers, spins, banks or game strategies.
        best = min(simulations, key=lambda s: (not s.accepted, s.cue_pocketed, not s.target_pocketed, s.shot.cut_angle, s.shot.distance))
        return PhysicsEvaluation(best, simulations)
