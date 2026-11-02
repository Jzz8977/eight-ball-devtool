"""Explicit download step; training itself only opens local model files."""
import argparse
from common import DEFAULT_BASE


def main():
    parser = argparse.ArgumentParser(description='下载官方 YOLO11 初始化权重至固定目录')
    parser.add_argument('--size', choices=['n', 's', 'm', 'l', 'x'], default='n')
    args = parser.parse_args()
    path = DEFAULT_BASE.parent/f'yolo11{args.size}.pt'
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from ultralytics.utils.downloads import attempt_download_asset
        result = attempt_download_asset(str(path))
        if not path.is_file():
            raise RuntimeError(f'下载未生成目标权重；返回路径：{result}')
    except (ImportError, OSError, RuntimeError) as error:
        parser.exit(1, f'下载失败，请安装 requirements-yolo.txt 或手动放置官方权重：{error}\n')
    print(path)


if __name__ == '__main__':
    main()
