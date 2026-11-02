"""Real image decoding and source-to-planner integration, without a GUI/model."""
from dataclasses import replace
from pathlib import Path
import importlib.util
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from eight_ball_devtool.acquisition import ImageSource
from eight_ball_devtool.application import Controller
from eight_ball_devtool.config import Config
from eight_ball_devtool.coordinates import map_detections
from eight_ball_devtool.models import Detection, Point
from eight_ball_devtool.perception.opencv import OpenCVCandidateDetector


def png_bytes(width=256, height=128, color=(20, 100, 60), circles=()):
    def chunk(tag, payload):
        return struct.pack('!I', len(payload))+tag+payload+struct.pack('!I', zlib.crc32(tag+payload)&0xffffffff)
    if circles:
        rows = b''.join(b'\0'+b''.join(bytes((245, 245, 245) if any((x-cx)**2+(y-cy)**2 <= r*r for cx, cy, r in circles) else color) for x in range(width)) for y in range(height))
    else:
        rows = (b'\0'+bytes(color)*width)*height
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('!IIBBBBB', width, height, 8, 2, 0, 0, 0))+chunk(b'IDAT', zlib.compress(rows))+chunk(b'IEND', b'')


class RecordingDetector:
    def __init__(self, known=False):
        self.frames = []
        self.known = known

    def detect(self, frame):
        self.frames.append(frame)
        assert frame.rgb is not None
        assert len(frame.rgb) == frame.width*frame.height*3
        return (
            Detection(0 if self.known else None, Point(frame.width*500/2540, frame.height*700/1270), 5),
            Detection(1 if self.known else None, Point(frame.width*1500/2540, frame.height*400/1270), 5),
        )


@unittest.skipUnless(importlib.util.find_spec('PIL') or importlib.util.find_spec('cv2'), 'Install requirements.txt for image decoding')
class ImageAcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root/'上传图片.png'
        self.path.write_bytes(png_bytes())
        self.detector = RecordingDetector()
        self.controller = Controller(self.root/'config.json', image_detector=self.detector)

    def calibrate(self):
        self.controller.set_calibration([[0, 0], [1, 0], [1, 1], [0, 1]])
        return self.controller.run()

    def test_image_source_decodes_rgb_and_keeps_snapshot_after_file_changes(self):
        source = ImageSource(self.path)
        frame = source.capture()
        self.assertEqual((frame.width, frame.height), (256, 128))
        self.assertEqual(frame.rgb[:3], bytes((20, 100, 60)))
        self.assertEqual(len(frame.rgb), 256*128*3)
        self.path.write_bytes(png_bytes(color=(200, 0, 0)))
        self.assertIs(source.capture(), frame)
        self.assertNotEqual(ImageSource(self.path).capture().image_id, frame.image_id)

    def test_real_frame_reaches_detector_without_demo_or_stale_routes(self):
        self.assertTrue(self.controller.run().shots)
        with patch.object(self.controller.detector, 'detect', side_effect=AssertionError('Demo detector must not run')):
            result = self.controller.load_image(self.path)
            self.assertEqual(result.status, 'needs_calibration')
            self.assertEqual(result.balls, ())
            self.assertEqual(result.shots, ())
            self.assertEqual(len(result.detections), 2)
            self.assertEqual(self.detector.frames[0].rgb[:3], bytes((20, 100, 60)))
            self.controller.run()
            self.assertEqual(len(self.detector.frames), 1)

    def test_calibration_mapping_and_manual_id_reach_planner(self):
        self.controller.load_image(self.path)
        result = self.calibrate()
        self.assertEqual(result.status, 'ready')
        self.assertAlmostEqual(result.balls[0].center.x, 500)
        self.assertAlmostEqual(result.balls[0].center.y, 700)
        self.assertTrue(all(b.number is None for b in result.balls))
        self.assertEqual(result.shots, ())
        self.controller.label_image_ball(0, 0)
        self.controller.label_image_ball(1, 1)
        result = self.controller.run()
        self.assertTrue(result.shots)
        self.assertTrue(all(shot.target.number == 1 for shot in result.shots))
        self.controller.config.mode = '3d'
        self.assertEqual(len(self.controller.run().world_points), 2)

    def test_new_image_invalidates_calibration_and_legacy_unbound_points(self):
        self.controller.config.calibration = [[0, 0], [1, 0], [1, 1], [0, 1]]
        self.controller.load_image(self.path)
        self.assertEqual(self.controller.config.calibration, [])
        self.calibrate()
        self.controller.load_image(self.path)
        self.assertEqual(self.controller.run().status, 'ready')
        self.path.write_bytes(png_bytes(color=(30, 110, 70)))
        result = self.controller.load_image(self.path)
        self.assertEqual(result.status, 'needs_calibration')
        self.assertFalse(result.fused)
        self.assertFalse(result.balls)

    def test_bad_image_does_not_replace_valid_source_or_result(self):
        self.controller.load_image(self.path)
        before_source = self.controller.source
        before_result = self.controller.result
        bad = self.root/'bad.png'
        bad.write_bytes(b'not an image')
        with self.assertRaises((ValueError, OSError)):
            self.controller.load_image(bad)
        self.assertIs(self.controller.source, before_source)
        self.assertIs(self.controller.result, before_result)

    def test_manual_add_remove_and_identity_uniqueness(self):
        self.controller.load_image(self.path)
        self.calibrate()
        self.controller.label_image_ball(0, 0)
        self.controller.label_image_ball(1, 0)
        self.assertEqual([b.number for b in self.controller.run().balls], [None, 0])
        self.controller.add_image_ball(Point(200, 80), 1)
        self.assertEqual(len(self.controller.run().balls), 3)
        self.controller.remove_image_ball(0)
        self.assertEqual(len(self.controller.run().balls), 2)
        with self.assertRaises(ValueError):
            self.controller.add_image_ball(Point(-1, 10), 2)

    def test_outside_table_candidates_are_not_physics_obstacles(self):
        source = ImageSource(self.path)
        config = Config(calibration=[[.2, .2], [.8, .2], [.8, .8], [.2, .8]])
        detections = (Detection(None, Point(5, 5), 4), Detection(None, Point(128, 64), 4))
        balls = map_detections(detections, source.capture(), config)
        self.assertEqual(len(balls), 1)
        self.assertAlmostEqual(balls[0].center.x, 1270)

    def test_saved_calibration_restores_for_same_image_and_demo_can_resume(self):
        self.controller.load_image(self.path)
        self.calibrate()
        restored = Controller(self.root/'config.json', image_detector=self.detector)
        self.assertEqual(restored.load_image(self.path).status, 'ready')
        restored.use_demo()
        self.assertEqual(restored.run().frame.source, 'demo')
        self.assertTrue(restored.run().shots)

    @unittest.skipUnless(importlib.util.find_spec('cv2'), 'OpenCV is optional')
    def test_opencv_candidates_use_real_pixels_and_never_assign_numbers(self):
        self.path.write_bytes(png_bytes(640, 320, circles=((200, 150, 10), (400, 180, 10))))
        detections = OpenCVCandidateDetector().detect(ImageSource(self.path).capture())
        self.assertTrue(detections)
        self.assertTrue(all(d.number is None for d in detections))
        self.assertTrue(any(d.center.distance(Point(200, 150)) < 4 for d in detections))

    def test_missing_detector_still_allows_manual_image_pipeline(self):
        class UnavailableDetector:
            def detect(self, frame):
                raise RuntimeError('OpenCV unavailable')
        self.controller.image_detector = UnavailableDetector()
        self.controller.load_image(self.path)
        self.calibrate()
        self.controller.add_image_ball(Point(256*500/2540, 128*700/1270), 0)
        self.controller.add_image_ball(Point(256*1500/2540, 128*400/1270), 1)
        self.assertTrue(self.controller.run().shots)


if __name__ == '__main__':
    unittest.main()
