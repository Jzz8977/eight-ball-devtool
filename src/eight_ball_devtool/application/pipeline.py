"""Application orchestration and persistence; no UI dependencies."""
from time import perf_counter
from ..acquisition import DemoSource
from ..config import Config, DEFAULT_CONFIG
from ..coordinates import map_detections
from ..perception import DemoDetector
from ..computation import plan
from ..fusion import fuse
from ..models import Result

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
    def __init__(self, path=None):
        self.path = path or DEFAULT_CONFIG
        self.startup_warning = ''
        try:
            self.config = Config.load(self.path) if self.path.exists() else Config()
        except (OSError, ValueError, TypeError) as error:
            self.config = Config()
            self.startup_warning = f'配置加载失败，已使用默认配置：{error}'
        self.source = DemoSource()
        self.detector = DemoDetector()
        self.result = None

    def run(self):
        self.config.validate()
        start = perf_counter()
        frame = self.source.capture()
        detections = self.detector.detect(frame)
        balls = map_detections(detections, frame, self.config)
        shots = plan(balls, self.config)
        # Hard guard at orchestration and implementation, not only a UI switch.
        world = fuse(balls, self.config) if self.config.mode == '3d' else ()
        self.result = Result(frame, balls, shots, self.config.mode == '3d', (perf_counter()-start)*1000, world)
        return self.result

    def save(self):
        self.config.save(self.path)
