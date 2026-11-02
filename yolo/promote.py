"""Publish a validated local checkpoint under the stable application filename."""
import argparse
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import shutil
from common import CLASS_NAMES, DEFAULT_WEIGHTS, load_yolo, local_weight, validate_names


def promote(weights, model_factory=None, target=DEFAULT_WEIGHTS):
    source, target = local_weight(weights), Path(target).resolve()
    YOLO = model_factory or load_yolo()
    model = YOLO(str(source), task='detect')
    if model.task != 'detect':
        raise ValueError('只能发布目标检测模型')
    validate_names(model.names)
    if source == target:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        archive = target.parent/'archive'
        archive.mkdir(exist_ok=True)
        shutil.copy2(target, archive/f'{target.stem}-{datetime.now():%Y%m%d-%H%M%S-%f}.pt')
    temp = target.with_suffix('.pt.tmp')
    shutil.copy2(source, temp)
    temp.replace(target)
    metadata = {'source': str(source), 'sha256': sha256(target.read_bytes()).hexdigest(), 'names': list(CLASS_NAMES), 'published_at': datetime.now().astimezone().isoformat()}
    target.with_suffix('.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    return target


def main():
    parser = argparse.ArgumentParser(description='发布权重到 yolo/checkpoints/yolo-eight-ball.pt')
    parser.add_argument('--weights', type=Path, required=True)
    args = parser.parse_args()
    try:
        print(promote(args.weights))
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f'权重未发布：{error}\n')


if __name__ == '__main__':
    main()
