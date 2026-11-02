"""Training paths and strict dataset validation. No Torch import here."""
from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent/'src'))
from eight_ball_devtool.perception.yolo import CLASS_NAMES, DEFAULT_WEIGHTS, validate_names

DEFAULT_DATA = ROOT/'configs/dataset.yaml'
DEFAULT_TRAIN = ROOT/'configs/train.yaml'
DEFAULT_BASE = ROOT/'checkpoints/pretrained/yolo11n.pt'
IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tif', '.tiff'}


def read_yaml(path):
    try:
        import yaml
    except ImportError as error:
        raise RuntimeError('请先安装 requirements-yolo.txt（需要 PyYAML）') from error
    data = yaml.safe_load(Path(path).read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict):
        raise ValueError(f'{path} 必须包含 YAML 对象')
    return data


def dataset_config(path):
    path = Path(path).resolve()
    data = read_yaml(path)
    validate_names(data.get('names'))
    root = (path.parent/str(data.get('path', '.'))).resolve()
    # Always persist an absolute dataset root so Ultralytics never redirects it
    # through a machine-specific datasets_dir setting.
    return {**data, 'path': str(root), 'names': list(CLASS_NAMES)}


def parse_label(path):
    counts = Counter()
    for line_no, line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split()
        try:
            if len(parts) != 5:
                raise ValueError('每行必须有 class_id x_center y_center width height 五列')
            category = int(parts[0])
            x, y, w, h = map(float, parts[1:])
            if not 0 <= category < 17 or not all(math.isfinite(v) for v in (x, y, w, h)):
                raise ValueError('类别必须为 0–16，坐标必须为有限数值')
            if not (0 <= x <= 1 and 0 <= y <= 1 and 0 < w <= 1 and 0 < h <= 1):
                raise ValueError('坐标需归一化到 0–1，宽高必须大于零')
            if min(x-w/2, y-h/2) < -1e-6 or max(x+w/2, y+h/2) > 1+1e-6:
                raise ValueError('标注框超出了图像范围')
        except ValueError as error:
            raise ValueError(f'{path}:{line_no}: {error}') from error
        counts[category] += 1
    return counts


def check_dataset(data_path=DEFAULT_DATA, splits=('train', 'val'), require_all_classes=True):
    data = dataset_config(data_path)
    root = Path(data['path'])
    report, seen = {}, {}
    for split in splits:
        relative = data.get(split)
        if not isinstance(relative, str):
            raise ValueError(f'{split} 必须指向 images/{split} 目录')
        image_dir = (root/relative).resolve()
        if image_dir != root/'images'/split:
            raise ValueError('当前训练工具使用固定布局 images/{train,val,test} 与 labels/{train,val,test}')
        label_dir = root/'labels'/split
        images = sorted(p for p in image_dir.rglob('*') if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES) if image_dir.is_dir() else []
        if not images:
            raise ValueError(f'{split} 集没有图片：{image_dir}')
        counts, negatives, labels = Counter(), 0, set()
        for image in images:
            label = label_dir/image.relative_to(image_dir).with_suffix('.txt')
            if label in labels:
                raise ValueError(f'同名不同格式图片共用了一个标注：{label}')
            labels.add(label)
            if not label.is_file():
                raise ValueError(f'缺少标注：{label}；负样本也请提供空 txt')
            objects = parse_label(label)
            counts.update(objects)
            negatives += not bool(objects)
            with image.open('rb') as file:
                digest = sha256()
                for block in iter(lambda: file.read(1024*1024), b''):
                    digest.update(block)
            key = digest.hexdigest()
            if key in seen and seen[key][0] != split:
                raise ValueError(f'数据泄漏：{image} 与 {seen[key][1]} 内容相同')
            seen[key] = (split, image)
        orphans = set(label_dir.rglob('*.txt'))-labels
        if orphans:
            raise ValueError(f'存在没有对应图片的标注：{sorted(orphans)[0]}')
        missing = [name for i, name in enumerate(CLASS_NAMES) if counts[i] == 0]
        if split == 'train' and require_all_classes and missing:
            raise ValueError('训练集缺少类别：'+', '.join(missing))
        report[split] = {'images': len(images), 'backgrounds': negatives, 'objects': sum(counts.values()), 'classes': {name: counts[i] for i, name in enumerate(CLASS_NAMES)}, 'missing_classes': missing}
    return data, report


def write_resolved_data(data):
    content = json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2)
    path = ROOT/'runs/configs'/f'dataset-{sha256(content.encode()).hexdigest()[:12]}.yaml'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')  # JSON is also valid YAML.
    return path


def load_yolo():
    try:
        from ultralytics import YOLO
    except ImportError as error:
        raise RuntimeError('请先运行 python -m pip install -r requirements-yolo.txt') from error
    return YOLO


def local_weight(path):
    path = Path(path).resolve()
    if not path.is_file() or path.suffix.lower() != '.pt':
        raise ValueError(f'缺少本地 .pt 权重：{path}')
    return path
