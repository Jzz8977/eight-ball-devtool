"""17-class detector contract shared by training and the desktop pipeline."""
from pathlib import Path

from ..config import PROJECT_ROOT
from ..models import Detection, Point

CLASS_NAMES = ('cue_ball', *(f'ball_{i}' for i in range(1, 16)), 'pocket')
DEFAULT_WEIGHTS = PROJECT_ROOT / 'yolo' / 'checkpoints' / 'yolo-eight-ball.pt'


def validate_names(names):
    if isinstance(names, dict):
        if set(names) != set(range(17)):
            raise ValueError('模型类别 ID 必须完整覆盖 0–16')
        names = [names[i] for i in range(17)]
    if not isinstance(names, (tuple, list)) or tuple(names) != CLASS_NAMES:
        raise ValueError('类别顺序必须为 cue_ball, ball_1 … ball_15, pocket；不能使用 COCO 或单类别台球模型')


class YOLODetector:
    display_name = 'YOLO 17 类检测'

    def __init__(self, weights=DEFAULT_WEIGHTS, confidence=.45, imgsz=1280, device=''):
        self.weights = Path(weights).resolve()
        if not self.weights.is_file():
            raise FileNotFoundError(f'未找到训练后的权重：{self.weights}')
        if not 0 < confidence <= 1 or imgsz < 32:
            raise ValueError('置信度需在 (0, 1]，imgsz 至少为 32')
        self.confidence, self.imgsz, self.device = confidence, imgsz, device
        self.model = None

    def detect(self, frame):
        if frame.source != 'image' or frame.rgb is None:
            raise ValueError('YOLO 需要真实 RGB 图片帧')
        if self.model is None:
            try:
                from ultralytics import YOLO
            except ImportError as error:
                raise RuntimeError('请先安装 requirements-yolo.txt') from error
            model = YOLO(str(self.weights), task='detect')
            if model.task != 'detect':
                raise ValueError('需要目标检测模型，不是分类或分割模型')
            validate_names(model.names)
            self.model = model
        import numpy as np
        rgb = np.frombuffer(frame.rgb, dtype=np.uint8).reshape(frame.height, frame.width, 3)
        # Ultralytics ndarray sources use BGR; acquisition frames use RGB.
        bgr = np.ascontiguousarray(rgb[:, :, ::-1])
        result = self.model.predict(source=bgr, conf=self.confidence, imgsz=self.imgsz, device=self.device, verbose=False)[0]
        detections = []
        if result.boxes is None:
            return ()
        for box in result.boxes:
            category = int(box.cls.item())
            if not 0 <= category < 17:
                raise ValueError('模型返回了超出 0–16 的类别')
            x1, y1, x2, y2 = map(float, box.xyxy[0].tolist())
            detections.append(Detection(category if category < 16 else None, Point((x1+x2)/2, (y1+y2)/2), min(x2-x1, y2-y1)/2, 'ball' if category < 16 else 'pocket', float(box.conf.item())))
        return tuple(detections)
