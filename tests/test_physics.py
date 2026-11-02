from dataclasses import replace
from importlib.metadata import PackageNotFoundError, version
from math import isfinite
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from eight_ball_devtool.application import Controller
from eight_ball_devtool.computation.aiming import ball_hit_fraction, natural_carom_angle
from eight_ball_devtool.computation.collision import assess_events, extract_events
from eight_ball_devtool.computation.physics import PooltoolEngine
from eight_ball_devtool.computation.trajectory import from_pooltool, to_pooltool
from eight_ball_devtool.config import Config
from eight_ball_devtool.models import Ball, CollisionEvent, Point

try:
    HAS_POOLTOOL = version('pooltool-billiards') == '0.6.0'
except PackageNotFoundError:
    HAS_POOLTOOL = False


class PhysicsContractTests(unittest.TestCase):
    def test_coordinate_axes_and_units(self):
        self.assertEqual(to_pooltool(Point(1000, 270), 1270), (1, 1))
        self.assertEqual(to_pooltool(Point(2540, 1270), 1270), (0, 2.54))
        for point in (Point(0, 0), Point(430, 930), Point(2540, 1270)):
            self.assertEqual(from_pooltool(*to_pooltool(point, 1270), 1270), point)
        # A project +X shot rotates to pooltool +Y, preserving the cue frame.
        a, b = to_pooltool(Point(100, 200), 1270), to_pooltool(Point(200, 200), 1270)
        self.assertEqual(a[0], b[0])
        self.assertGreater(b[1], a[1])

    def test_invalid_scene_and_spin_rejected_before_loading_engine(self):
        cue = Ball(0, Point(500, 500))
        for balls in ((), (cue, cue), (cue, Ball(1, Point(501, 500))), (Ball(0, Point(1, 1)),)):
            with self.assertRaises(ValueError):
                PooltoolEngine.validate_scene(balls, Config())
        for update in ({'cue_side_spin': .8, 'cue_top_spin': .8}, {'cue_speed': float('nan')}, {'trajectory_dt': True}):
            with self.assertRaises(ValueError):
                replace(Config(), **update).validate()

    def test_natural_angle_is_not_a_constant(self):
        self.assertAlmostEqual(ball_hit_fraction(30), .5)
        self.assertAlmostEqual(natural_carom_angle(30), 33.6704965083151)
        self.assertLess(natural_carom_angle(14), 28)
        with self.assertRaises(ValueError):
            natural_carom_angle(91)

    def test_event_acceptance_rejects_scratch_wrong_contact_and_incomplete_run(self):
        events = (CollisionEvent(.1, 'ball_ball', ('cue', 'obj')),
                  CollisionEvent(.4, 'ball_pocket', ('obj', 'lb')))
        numbers = {'cue': 0, 'obj': 1, 'other': 8}
        def assess(sequence, complete=True):
            return assess_events(sequence, 'obj', 'lb', numbers, Config(), complete)[3]
        self.assertTrue(assess(events))
        self.assertFalse(assess(events, False))
        self.assertFalse(assess(events + (CollisionEvent(.5, 'ball_pocket', ('cue', 'lb')),)))
        self.assertFalse(assess(events + (CollisionEvent(.5, 'ball_pocket', ('other', 'rb')),)))
        self.assertFalse(assess((CollisionEvent(.05, 'ball_ball', ('cue', 'other')), *events)))

    def test_controller_drops_results_after_parameters_or_scene_change(self):
        with tempfile.TemporaryDirectory() as temp:
            controller = Controller(Path(temp)/'config.json')
            controller.run()
            request = controller.physics_request()
            marker = object()
            self.assertTrue(controller.accept_physics(request[0], marker))
            self.assertIs(controller.run().physics, marker)
            controller.config.cue_speed = 2
            self.assertFalse(controller.accept_physics(request[0], marker))
            self.assertIsNone(controller.run().physics)
            self.assertEqual(request[3].cue_speed, 1.5)  # Immutable request snapshot.
            current = controller.physics_request()
            controller.use_demo()  # Scene replacement invalidates pending results.
            self.assertFalse(controller.accept_physics(current[0], marker))


@unittest.skipUnless(HAS_POOLTOOL, '需要可选 pooltool-billiards 0.6.0')
class RealPooltoolTests(unittest.TestCase):
    def test_real_pipeline_generates_collisions_and_sampled_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            controller = Controller(Path(temp)/'config.json')
            controller.run()
            key, evaluation = controller.calculate_physics(controller.physics_request())
            self.assertTrue(controller.accept_physics(key, evaluation))
            selected = controller.run().physics.selected
            self.assertTrue(selected.completed)
            self.assertTrue(selected.accepted, selected.reason)
            self.assertIn('ball_ball', [event.kind for event in selected.events])
            self.assertIn('ball_pocket', [event.kind for event in selected.events])
            self.assertFalse(selected.cue_pocketed)
            for path in selected.trajectories:
                self.assertGreater(len(path.samples), 2)
                initial = next(b for b in controller.result.balls if b.number == path.number)
                self.assertAlmostEqual(path.samples[0].x, initial.center.x)
                self.assertAlmostEqual(path.samples[0].y, initial.center.y)
                self.assertTrue(all(isfinite(s.x+s.y+s.z+s.time) for s in path.samples))

    def test_cushion_response_uses_upstream_solver_and_local_config(self):
        from eight_ball_devtool.computation.pooltool_runtime import CONFIG_DIR
        engine = PooltoolEngine()
        system, _, _ = engine.build_system((Ball(0, Point(1000, 600)),), Config())
        pt = engine.backend()
        self.assertEqual(pt.config.paths.CONFIG_DIR, CONFIG_DIR)
        system.cue.set_state(V0=1.5, phi=0, theta=0, a=0, b=0)
        pt.simulate(system, inplace=True)
        self.assertTrue(any('cushion' in event.kind for event in extract_events(system)))

    def test_thirty_degree_simulation_matches_ideal_reference(self):
        from eight_ball_devtool.computation.experiments import thirty_degree_experiment
        rows = thirty_degree_experiment(cuts=(14, 30, 49))
        for row in rows:
            self.assertLess(abs(row['measured_carom_deg']-row['theory_carom_deg']), .02)

    def test_straight_shot_reproducibility_and_scratch_accounting(self):
        from eight_ball_devtool.computation.experiments import straight_shot_experiment
        kwargs = dict(positions=3, trials=4, errors=(.4,), seed=42)
        first = straight_shot_experiment(**kwargs)
        self.assertEqual(first, straight_shot_experiment(**kwargs))
        self.assertTrue(all(0 <= r['safe_pot_rate'] <= r['pot_rate'] <= 1 for r in first))
        self.assertGreater(first[-1]['scratch_rate'], 0)
        self.assertLess(first[-1]['safe_pot_rate'], first[-1]['pot_rate'])


if __name__ == '__main__':
    unittest.main()
