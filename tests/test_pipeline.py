from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from eight_ball_devtool.application import Controller
from eight_ball_devtool.config import Config
from eight_ball_devtool.coordinates import TableTransform, validate_quad
from eight_ball_devtool.models import Ball, Point, Frame
from eight_ball_devtool.computation import plan
from eight_ball_devtool.fusion import fuse
from eight_ball_devtool.perception import DemoDetector


class PipelineTests(unittest.TestCase):
    def test_homography_maps_perspective_corners_and_center(self):
        points = [[.2, .1], [.8, .1], [.95, .9], [.05, .9]]
        transform = TableTransform(points, 2540, 1270)
        for point, expected in zip(points, [(0, 0), (2540, 0), (2540, 1270), (0, 1270)]):
            actual = transform.project(Point(*point))
            self.assertAlmostEqual(actual.x, expected[0], places=6)
            self.assertAlmostEqual(actual.y, expected[1], places=6)
        self.assertAlmostEqual(transform.project(Point(.5, .5)).x, 1270)

    def test_degenerate_and_crossed_calibration_rejected(self):
        for points in [[[0, 0]]*4, [[0, 0], [1, 1], [1, 0], [0, 1]], [[0, 0], [1, 0], [.5, 0], [0, 1]]]:
            with self.assertRaises(ValueError):
                validate_quad(points)

    def test_2d_never_calls_fusion_and_3d_produces_world_coordinates(self):
        with tempfile.TemporaryDirectory() as temp:
            controller = Controller(Path(temp)/'config.json')
            with patch('eight_ball_devtool.application.pipeline.fuse', side_effect=AssertionError('2D must bypass fusion')):
                result = controller.run()
                self.assertFalse(result.fused)
                self.assertEqual(result.world_points, ())
                self.assertEqual(len(result.balls), 8)
                self.assertTrue(result.shots)
            controller.config.mode = '3d'
            result = controller.run()
            self.assertTrue(result.fused)
            self.assertEqual(len(result.world_points), 8)
            self.assertEqual(result.world_points[0], (result.balls[0].center.x, result.balls[0].center.y, 750))

    def test_fusion_guard_and_rotation(self):
        ball = Ball(0, Point(10, 0))
        with self.assertRaises(ValueError):
            fuse((ball,), Config())
        actual = fuse((ball,), Config(mode='3d', world_yaw=90, world_x=20, world_y=30))[0]
        self.assertAlmostEqual(actual[0], 20)
        self.assertAlmostEqual(actual[1], 40)

    def test_blocker_removes_specific_shot(self):
        config = Config(target_group='solid')
        cue = Ball(0, Point(500, 700))
        target = Ball(1, Point(1500, 400))
        shots = plan((cue, target), config)
        self.assertTrue(shots)
        shot = shots[0]
        blocker = Ball(None, Point((target.center.x+shot.pocket.x)/2, (target.center.y+shot.pocket.y)/2))
        blocked = plan((cue, target, blocker), config)
        self.assertNotIn(shot.pocket, [s.pocket for s in blocked])
        self.assertAlmostEqual(shot.ghost.distance(target.center), cue.radius+target.radius)

    def test_unknown_balls_and_ambiguous_cue_have_no_plan(self):
        config = Config(target_group='any')
        cue = Ball(0, Point(500, 700))
        self.assertEqual(plan((cue, Ball(None, Point(1000, 400))), config), ())
        self.assertEqual(plan((cue, cue, Ball(1, Point(1500, 400))), config), ())

    def test_real_image_never_uses_demo_detections(self):
        with self.assertRaises(NotImplementedError):
            DemoDetector().detect(Frame('image', 1920, 1080))

    def test_overall_dimensions_never_change_playfield_or_plane_height(self):
        with tempfile.TemporaryDirectory() as temp:
            controller = Controller(Path(temp)/'config.json')
            controller.config.mode = '3d'
            before = controller.run()
            controller.config.table_outer_length = 3000
            controller.config.table_outer_width = 1700
            controller.config.table_outer_height = 900
            after = controller.run()
            self.assertEqual(before.balls, after.balls)
            self.assertEqual(before.shots, after.shots)
            self.assertEqual(before.world_points, after.world_points)
            for name in ('table_outer_length', 'table_outer_width', 'table_outer_height'):
                with self.assertRaises(ValueError):
                    replace(controller.config, **{name: float('nan')}).validate()

    def test_chinese_table_profile_and_legacy_config_load(self):
        root = Path(__file__).resolve().parents[1]
        profile = Config.load(root/'configs/chinese-eight-ball.json')
        self.assertEqual((profile.table_width, profile.table_height), (2540, 1270))
        self.assertEqual((profile.table_outer_length, profile.table_outer_width, profile.table_outer_height), (2830, 1550, 840))
        self.assertNotEqual(profile.world_z, profile.table_outer_height)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'legacy.json'
            path.write_text(json.dumps({'table_width': 2400, 'table_height': 1200}), encoding='utf-8')
            self.assertEqual(Config.load(path).table_width, 2400)

    def test_config_roundtrip_and_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'nested/config.json'
            config = Config(mode='3d', show_paths=False)
            config.save(path)
            self.assertEqual(Config.load(path), config)
            for invalid in [replace(config, table_width=float('nan')), replace(config, mode='4d'), replace(config, show_paths='yes')]:
                with self.assertRaises(ValueError):
                    invalid.validate()
            path.write_text(json.dumps({'unexpected': True}), encoding='utf-8')
            with self.assertRaises(ValueError):
                Config.load(path)


if __name__ == '__main__':
    unittest.main()
