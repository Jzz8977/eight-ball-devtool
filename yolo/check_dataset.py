import argparse
import json
from common import DEFAULT_DATA, check_dataset


def main():
    parser = argparse.ArgumentParser(description='检查 17 类台球 YOLO 数据集')
    parser.add_argument('--data', default=DEFAULT_DATA)
    parser.add_argument('--split', nargs='+', choices=['train', 'val', 'test'], default=['train', 'val'])
    parser.add_argument('--allow-missing-classes', action='store_true')
    args = parser.parse_args()
    try:
        _, report = check_dataset(args.data, args.split, not args.allow_missing_classes)
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f'数据检查失败：{error}\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
