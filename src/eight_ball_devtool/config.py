from dataclasses import asdict, dataclass, field
import json
import math
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / 'runtime' / 'config.json'


@dataclass
class Config:
    mode: str = '2d'
    table_width: float = 2540
    table_height: float = 1270
    # Overall table dimensions are metadata, never the homography bounds.
    table_outer_length: float = 2830
    table_outer_width: float = 1550
    table_outer_height: float = 840
    ball_radius: float = 28.575
    max_cut_angle: float = 75
    target_group: str = 'solid'
    show_grid: bool = True
    show_paths: bool = True
    show_numbers: bool = True
    blue_cloth: bool = False
    device: str = '电脑'
    world_x: float = 0
    world_y: float = 0
    world_z: float = 750  # Demo registration only; not inferred from overall height.
    world_yaw: float = 0
    calibration: list[list[float]] = field(default_factory=list)
    calibration_image_id: str = ''

    def validate(self):
        if not isinstance(self.calibration_image_id, str):
            raise ValueError('calibration_image_id 必须为字符串')
        if self.mode not in ('2d', '3d'):
            raise ValueError('模式只能为 2d 或 3d')
        if self.target_group not in ('solid', 'stripe', 'eight', 'any'):
            raise ValueError('无效的目标球组')
        if self.device not in ('电脑', '手机', '眼镜'):
            raise ValueError('无效的输出终端')
        for name, low, high in [('table_width', 1000, 4000), ('table_height', 500, 2000), ('table_outer_length', 1000, 6000), ('table_outer_width', 500, 3500), ('table_outer_height', 100, 2000), ('ball_radius', 10, 50), ('max_cut_angle', 1, 89), ('world_x', -100000, 100000), ('world_y', -100000, 100000), ('world_z', -100000, 100000), ('world_yaw', -360, 360)]:
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
                raise ValueError(f'{name} 需要在 {low}–{high} 范围内')
        for name in ('show_grid', 'show_paths', 'show_numbers', 'blue_cloth'):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f'{name} 必须为布尔值')
        if self.calibration:
            from .coordinates import validate_quad
            validate_quad(self.calibration)

    def save(self, path: Path):
        self.validate()
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding='utf-8')
        temp.replace(path)

    @classmethod
    def load(cls, path: Path):
        raw = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(raw, dict):
            raise ValueError('配置必须是 JSON 对象')
        unknown = set(raw) - cls.__dataclass_fields__.keys()
        if unknown:
            raise ValueError(f'未知配置项: {", ".join(sorted(unknown))}')
        config = cls(**raw)
        config.validate()
        return config
