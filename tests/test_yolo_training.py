"""No real model download, GPU or training required for these contract tests."""
from contextlib import redirect_stdout
import importlib.util
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
sys.path.insert(0, str(ROOT/'yolo'))
from eight_ball_devtool.perception.yolo import CLASS_NAMES, YOLODetector, validate_names
from eight_ball_devtool.models import Detection, Frame, Point
from eight_ball_devtool.config import Config
from eight_ball_devtool.coordinates import map_detections
from eight_ball_devtool.application import Controller
import common
import promote
import train


class TemporaryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()


@unittest.skipUnless(importlib.util.find_spec('yaml'), 'PyYAML is part of requirements-yolo.txt')
class DatasetTests(TemporaryTest):
    def setUp(self):
        super().setUp()
        self.data = self.root/'dataset.yaml'
        self.data.write_text(json.dumps({'path': 'data', 'train': 'images/train', 'val': 'images/val', 'names': list(CLASS_NAMES)}), encoding='utf-8')
        # The checker intentionally validates layout/labels, not pixel decoding.
        for split in ('train', 'val'):
            image = self.root/f'data/images/{split}/scene.png'
            label = self.root/f'data/labels/{split}/scene.txt'
            image.parent.mkdir(parents=True)
            label.parent.mkdir(parents=True)
            image.write_bytes(f'{split} image contents'.encode())
            label.write_text('\n'.join(f'{i} 0.5 0.5 0.1 0.1' for i in range(17)), encoding='utf-8')

    def test_class_order_and_yaml_root_are_fixed(self):
        data, report = common.check_dataset(self.data)
        self.assertEqual(data['path'], str(self.root/'data'))
        self.assertEqual(report['train']['objects'], 17)
        self.assertEqual(report['train']['missing_classes'], [])
        raw = json.loads(self.data.read_text())
        raw['names'][0], raw['names'][1] = raw['names'][1], raw['names'][0]
        self.data.write_text(json.dumps(raw))
        with self.assertRaises(ValueError):
            common.check_dataset(self.data)

    def test_label_errors_identify_line_and_image_leakage_is_rejected(self):
        label = self.root/'data/labels/train/scene.txt'
        for invalid in ['17 0.5 0.5 0.1 0.1', '1 nan 0.5 0.1 0.1', '1 0.01 0.5 0.5 0.1', '1 0.5 0.5 0.1']:
            label.write_text(invalid)
            with self.assertRaisesRegex(ValueError, 'scene.txt:1:'):
                common.check_dataset(self.data)
        label.write_text('\n'.join(f'{i} 0.5 0.5 0.1 0.1' for i in range(17)))
        (self.root/'data/images/val/scene.png').write_bytes((self.root/'data/images/train/scene.png').read_bytes())
        with self.assertRaisesRegex(ValueError, '数据泄漏'):
            common.check_dataset(self.data)

    def test_missing_labels_classes_and_empty_dataset_fail(self):
        label = self.root/'data/labels/train/scene.txt'
        moved = label.with_suffix('.missing')
        label.rename(moved)
        with self.assertRaisesRegex(ValueError, '缺少标注'):
            common.check_dataset(self.data)
        moved.rename(label)
        label.write_text('')
        with self.assertRaisesRegex(ValueError, '缺少类别'):
            common.check_dataset(self.data)
        _, report = common.check_dataset(self.data, require_all_classes=False)
        self.assertEqual(report['train']['backgrounds'], 1)
        # A different configured root gives a clear error instead of auto-download.
        self.data.write_text(json.dumps({'path': 'empty', 'train': 'images/train', 'val': 'images/val', 'names': list(CLASS_NAMES)}))
        with self.assertRaisesRegex(ValueError, '没有图片'):
            common.check_dataset(self.data)

    def test_check_only_never_imports_model_or_writes_run(self):
        with patch.object(sys, 'argv', ['train.py', '--data', str(self.data), '--check-only']), patch.object(train, 'load_yolo', side_effect=AssertionError('No model import')), patch.object(train, 'write_resolved_data', side_effect=AssertionError('No run writes')), redirect_stdout(StringIO()):
            train.main()

    def test_training_forwards_absolute_dataset_and_config(self):
        base = self.root/'base.pt'
        base.write_bytes(b'test checkpoint')
        model = SimpleNamespace(task='detect', trainer=SimpleNamespace(save_dir=self.root/'run', best=self.root/'run/best.pt'))
        calls = []
        model.train = lambda **kwargs: calls.append(kwargs)
        with patch.object(sys, 'argv', ['train.py', '--data', str(self.data), '--base', str(base), '--epochs', '2', '--device', 'cpu']), patch.object(train, 'load_yolo', return_value=lambda *a, **k: model), patch.object(train, 'write_resolved_data', return_value=self.root/'resolved.yaml'), patch.object(train, 'ROOT', self.root), redirect_stdout(StringIO()):
            train.main()
        self.assertEqual(calls[0]['data'], str(self.root/'resolved.yaml'))
        self.assertEqual(calls[0]['epochs'], 2)
        self.assertEqual(calls[0]['fliplr'], 0)
        self.assertEqual(calls[0]['workers'], 0)
        self.assertFalse(calls[0]['exist_ok'])

    def test_resume_keeps_checkpoint_settings_and_rejects_new_epoch_count(self):
        checkpoint = self.root/'last.pt'
        checkpoint.write_bytes(b'test checkpoint')
        calls = []
        model = SimpleNamespace(task='detect', names=list(CLASS_NAMES), trainer=SimpleNamespace(save_dir=self.root/'run', best=self.root/'run/best.pt'), train=lambda **kwargs: calls.append(kwargs))
        argv = ['train.py', '--data', str(self.data), '--resume', str(checkpoint), '--device', 'cpu']
        with patch.object(sys, 'argv', argv), patch.object(train, 'load_yolo', return_value=lambda *a, **k: model), patch.object(train, 'write_resolved_data', return_value=self.root/'resolved.yaml'), redirect_stdout(StringIO()):
            train.main()
        self.assertTrue(calls[0]['resume'])
        self.assertNotIn('epochs', calls[0])
        self.assertEqual(calls[0]['device'], 'cpu')
        with patch.object(sys, 'argv', [*argv, '--epochs', '200']), patch('sys.stderr', new_callable=StringIO), self.assertRaises(SystemExit) as caught:
            train.main()
        self.assertEqual(caught.exception.code, 1)


class ModelContractTests(TemporaryTest):
    def test_classes_template_and_pockets_are_not_balls(self):
        validate_names(dict(enumerate(CLASS_NAMES)))
        self.assertEqual((ROOT/'yolo/configs/classes.txt').read_text().splitlines(), list(CLASS_NAMES))
        with self.assertRaises(ValueError):
            validate_names({0: 'ball'})
        detections = (Detection(0, Point(50, 50), 3), Detection(None, Point(10, 10), 7, kind='pocket'))
        config = Config(calibration=[[0, 0], [1, 0], [1, 1], [0, 1]])
        balls = map_detections(detections, Frame('image', 100, 100), config)
        self.assertEqual(len(balls), 1)
        controller = Controller(self.root/'config.json')
        source = SimpleNamespace(capture=lambda: Frame('image', 100, 100, rgb=b'\0'*30000, image_id='test'))
        controller.use_image(source, detections)
        with self.assertRaisesRegex(ValueError, '球洞'):
            controller.label_image_ball(1, 0)

    def test_promote_validates_names_and_backs_up_existing_weights(self):
        source, target = self.root/'best.pt', self.root/'checkpoints/yolo-eight-ball.pt'
        source.write_bytes(b'new checkpoint')
        target.parent.mkdir()
        target.write_bytes(b'old checkpoint')
        factory = lambda *a, **k: SimpleNamespace(task='detect', names=list(CLASS_NAMES))
        self.assertEqual(promote.promote(source, factory, target), target)
        self.assertEqual(target.read_bytes(), b'new checkpoint')
        self.assertEqual(next((target.parent/'archive').glob('*.pt')).read_bytes(), b'old checkpoint')
        self.assertEqual(json.loads(target.with_suffix('.json').read_text())['names'], list(CLASS_NAMES))
        with self.assertRaises(ValueError):
            promote.promote(source, lambda *a, **k: SimpleNamespace(task='detect', names=['ball']), target)
        self.assertEqual(target.read_bytes(), b'new checkpoint')

    @unittest.skipUnless(importlib.util.find_spec('numpy'), 'NumPy required for inference adapter')
    def test_adapter_preserves_ball_id_pocket_type_confidence_and_bgr(self):
        weights = self.root/'test.pt'
        weights.write_bytes(b'test checkpoint')
        def box(category):
            return SimpleNamespace(cls=SimpleNamespace(item=lambda: category), conf=SimpleNamespace(item=lambda: .87), xyxy=[SimpleNamespace(tolist=lambda: [0, 0, 2, 2])])
        sources = []
        def predict(**kwargs):
            sources.append(kwargs['source'])
            return [SimpleNamespace(boxes=[box(15), box(16)])]
        fake_model = SimpleNamespace(task='detect', names=list(CLASS_NAMES), predict=predict)
        fake_module = SimpleNamespace(YOLO=lambda *a, **k: fake_model)
        with patch.dict(sys.modules, {'ultralytics': fake_module}):
            detections = YOLODetector(weights).detect(Frame('image', 2, 2, rgb=bytes((10, 20, 30))*4))
        self.assertEqual(sources[0][0, 0].tolist(), [30, 20, 10])
        self.assertEqual(detections[0].number, 15)
        self.assertEqual(detections[1].kind, 'pocket')
        self.assertIsNone(detections[1].number)
        self.assertEqual(detections[0].confidence, .87)


if __name__ == '__main__':
    unittest.main()
