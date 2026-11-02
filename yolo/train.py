"""Train a 17-class detector. Does not run until this script is invoked."""
import argparse
import json
from pathlib import Path
from common import DEFAULT_BASE, DEFAULT_DATA, DEFAULT_TRAIN, ROOT, check_dataset, load_yolo, local_weight, read_yaml, write_resolved_data


def main():
    parser = argparse.ArgumentParser(description='训练母球、1–15 号球和球洞的 YOLO 检测模型')
    parser.add_argument('--data', type=Path, default=DEFAULT_DATA)
    parser.add_argument('--config', type=Path, default=DEFAULT_TRAIN)
    parser.add_argument('--base', type=Path, default=DEFAULT_BASE)
    parser.add_argument('--resume', type=Path, help='从训练中断时的 last.pt 恢复，不是增加训练轮次')
    parser.add_argument('--name', default='eight-ball')
    parser.add_argument('--epochs', type=int)
    parser.add_argument('--imgsz', type=int)
    parser.add_argument('--batch', type=int)
    parser.add_argument('--device')
    parser.add_argument('--workers', type=int)
    parser.add_argument('--check-only', action='store_true', help='检查数据并打印计划，不导入 Torch / 不训练')
    args = parser.parse_args()
    try:
        if Path(args.name).name != args.name or args.name in ('', '.', '..'):
            raise ValueError('name 必须是单个目录名')
        if args.resume and any(getattr(args, key) is not None for key in ('epochs', 'imgsz', 'batch')):
            raise ValueError('resume 恢复原训练轮次和参数；改变 epochs/imgsz/batch 请用 --base last.pt 开始新训练')
        data, report = check_dataset(args.data)
        settings = read_yaml(args.config)
        allowed = {'epochs', 'imgsz', 'batch', 'workers', 'device', 'seed', 'deterministic', 'patience', 'save', 'plots', 'fliplr', 'flipud', 'hsv_h', 'hsv_s', 'hsv_v', 'degrees', 'translate', 'scale', 'mosaic', 'mixup'}
        if set(settings)-allowed:
            raise ValueError('训练配置有不支持的参数：'+', '.join(sorted(set(settings)-allowed)))
        settings.update({key: getattr(args, key) for key in ('epochs', 'imgsz', 'batch', 'device', 'workers') if getattr(args, key) is not None})
        for key in ('epochs', 'imgsz', 'batch'):
            if type(settings.get(key)) is not int or settings[key] < 1:
                raise ValueError(f'{key} 必须为正整数')
        if type(settings.get('workers')) is not int or settings['workers'] < 0:
            raise ValueError('workers 必须为非负整数')
        print(json.dumps({'dataset': report, 'settings': settings, 'base': str(args.resume or args.base), 'output': str(ROOT/'runs'/args.name)}, ensure_ascii=False, indent=2))
        if args.check_only:
            return
        checkpoint = local_weight(args.resume or args.base)
        YOLO = load_yolo()
        model = YOLO(str(checkpoint), task='detect')
        if model.task != 'detect':
            raise ValueError('需要目标检测初始化权重')
        resolved = write_resolved_data(data)
        if args.resume:
            from common import validate_names
            validate_names(model.names)
            overrides = {key: getattr(args, key) for key in ('device', 'workers') if getattr(args, key) is not None}
            model.train(resume=True, data=str(resolved), **overrides)
        else:
            model.train(data=str(resolved), project=str(ROOT/'runs'), name=args.name, exist_ok=False, **settings)
        print(f'训练输出：{model.trainer.save_dir}')
        print(f'最佳权重：{model.trainer.best}')
        print('验证后运行 yolo/promote.py，将选定权重发布为固定的 yolo-eight-ball.pt。')
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f'训练未完成：{error}\n')


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support()
    main()
