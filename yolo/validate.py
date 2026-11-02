import argparse
from pathlib import Path
from common import DEFAULT_DATA, DEFAULT_WEIGHTS, ROOT, check_dataset, load_yolo, local_weight, validate_names, write_resolved_data


def main():
    parser = argparse.ArgumentParser(description='验证 / 测试训练后的 17 类模型')
    parser.add_argument('--weights', type=Path, default=DEFAULT_WEIGHTS)
    parser.add_argument('--data', type=Path, default=DEFAULT_DATA)
    parser.add_argument('--split', choices=['val', 'test'], default='val')
    parser.add_argument('--imgsz', type=int, default=1280)
    parser.add_argument('--batch', type=int, default=4)
    parser.add_argument('--device', default='')
    args = parser.parse_args()
    try:
        data, report = check_dataset(args.data, splits=(args.split,), require_all_classes=False)
        if report[args.split]['missing_classes']:
            print('该分集缺少这些类别，不能据此评估它们的表现：'+', '.join(report[args.split]['missing_classes']))
        YOLO = load_yolo()
        model = YOLO(str(local_weight(args.weights)), task='detect')
        validate_names(model.names)
        metrics = model.val(data=str(write_resolved_data(data)), split=args.split, imgsz=args.imgsz, batch=args.batch, device=args.device, workers=0, project=str(ROOT/'runs'), name='evaluate', plots=True)
        print(metrics.results_dict)
        print('逐类结果、混淆矩阵和验证可视化见本次 evaluate 输出目录。')
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f'验证失败：{error}\n')


if __name__ == '__main__':
    main()
