"""Application orchestration and persistence; no UI dependencies."""
from time import perf_counter
from dataclasses import replace
from ..acquisition import DemoSource, ImageSource
from ..config import Config, DEFAULT_CONFIG
from ..coordinates import map_detections
from ..perception import DemoDetector
from ..perception.opencv import OpenCVCandidateDetector
from ..computation import plan
from ..fusion import fuse
from ..models import Detection, Result

LAYERS = (
    ('采集层', 'ACQUISITION', '平面图 / 3D 图'),
    ('感知层', 'PERCEPTION', 'YOLO / 球号分类 / OpenCV 标定'),
    ('坐标层', 'COORDINATES', '球桌坐标对齐与转换'),
    ('计算层', 'COMPUTATION', '瞄准 / 路径 / 碰撞预测'),
    ('融合层', 'SPATIAL FUSION', '空间定位与坐标融合 · 仅 3D'),
    ('渲染层', 'RENDERING', '2D 数字桌球 / 3D 叠加'),
    ('应用层', 'APPLICATION', '电脑 / 手机 / 眼镜'),
)


class Controller:
    def __init__(self, path=None, image_detector=None):
        self.path = path or DEFAULT_CONFIG
        self.startup_warning = ''
        try:
            self.config = Config.load(self.path) if self.path.exists() else Config()
        except (OSError, ValueError, TypeError) as error:
            self.config = Config()
            self.startup_warning = f'配置加载失败，已使用默认配置：{error}'
        self.source = DemoSource()
        self.detector = DemoDetector()
        self.image_detector = image_detector if image_detector is not None else OpenCVCandidateDetector()
        self._image_detections = None
        self._detector_message = ''
        self.result = None

    def prepare_image(self, path):
        """Decode and detect off the UI thread without changing the live session."""
        source = ImageSource(path)
        try:
            return source, tuple(self.image_detector.detect(source.capture())), ''
        except RuntimeError as error:
            return source, (), str(error)

    def use_image(self, source, detections=None, detector_message=''):
        """Commit a fully decoded source; failed loading never replaces a session."""
        frame = source.capture()
        if frame.source != 'image' or frame.rgb is None:
            raise ValueError('需要有效的 RGB 图片源')
        if self.config.calibration_image_id != frame.image_id:
            self.config = replace(self.config, calibration=[], calibration_image_id='')
        self.source = source
        self._image_detections = detections
        self._detector_message = detector_message
        self.result = None

    def load_image(self, path):
        self.use_image(*self.prepare_image(path))
        return self.run()

    def use_demo(self):
        self.source = DemoSource()
        self.result = None

    def set_calibration(self, points):
        frame = self.source.capture()
        if frame.source != 'image':
            raise ValueError('请先导入图片')
        updated = replace(self.config, calibration=[list(p) for p in points], calibration_image_id=frame.image_id)
        updated.validate()
        updated.save(self.path)
        self.config = updated

    def _detect_image(self, frame):
        if self._image_detections is None:
            try:
                self._image_detections = tuple(self.image_detector.detect(frame))
            except RuntimeError as error:
                self._image_detections = ()
                self._detector_message = str(error)
        return self._image_detections

    def label_image_ball(self, index, number):
        frame = self.source.capture()
        if frame.source != 'image':
            raise ValueError('仅可确认图片球位')
        if number is not None and (type(number) is not int or not 0 <= number <= 15):
            raise ValueError('球号范围为 0–15，未知为 None')
        detections = list(self._detect_image(frame))
        if not 0 <= index < len(detections):
            raise ValueError('候选球不存在')
        if detections[index].kind != 'ball':
            raise ValueError('球洞不能标为台球')
        # A confirmed identity can belong to only one candidate.
        if number is not None:
            detections = [replace(d, number=None) if d.number == number else d for d in detections]
        detections[index] = replace(detections[index], number=number)
        self._image_detections = tuple(detections)

    def add_image_ball(self, point, number=None):
        frame = self.source.capture()
        if frame.source != 'image' or not (0 <= point.x < frame.width and 0 <= point.y < frame.height):
            raise ValueError('请在图片范围内添加球位')
        detections = self._detect_image(frame)
        self._image_detections = (*detections, Detection(None, point, max(3, min(frame.width, frame.height)*.015)))
        self.label_image_ball(len(detections), number)

    def remove_image_ball(self, index):
        frame = self.source.capture()
        if frame.source != 'image':
            raise ValueError('仅可移除图片候选')
        detections = list(self._detect_image(frame))
        if not 0 <= index < len(detections):
            raise ValueError('候选球不存在')
        del detections[index]
        self._image_detections = tuple(detections)

    def run(self):
        self.result = None
        self.config.validate()
        start = perf_counter()
        frame = self.source.capture()
        detections = self.detector.detect(frame) if frame.source == 'demo' else self._detect_image(frame)
        if frame.source == 'image' and (not self.config.calibration or self.config.calibration_image_id != frame.image_id):
            self.result = Result(frame, (), (), False, (perf_counter()-start)*1000, detections=detections, status='needs_calibration', message='请完成四点标定，再转换球桌坐标；右键可确认或添加球位。')
            return self.result
        balls = map_detections(detections, frame, self.config)
        shots = plan(balls, self.config)
        # Hard guard at orchestration and implementation, not only a UI switch.
        world = fuse(balls, self.config) if self.config.mode == '3d' else ()
        message = self._detector_message if frame.source == 'image' else ''
        if frame.source == 'image' and not shots:
            message = message or ('未找到候选球，可在采集画面右键手动添加。' if not balls else '候选球号待确认；右键确认母球和目标球后生成可行路线。')
            if any(b.number == 0 for b in balls) and any(b.number not in (None, 0) for b in balls):
                message = '当前确认球位与配置下没有可行直线路线。'
        self.result = Result(frame, balls, shots, self.config.mode == '3d', (perf_counter()-start)*1000, world, detections, message=message)
        return self.result

    def save(self):
        self.config.save(self.path)
