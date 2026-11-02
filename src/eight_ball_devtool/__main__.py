import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='Eight Ball 原生 Python 开发工作台')
    parser.add_argument('--check', action='store_true', help='运行无界面的流水线检查')
    parser.add_argument('--config', type=Path, help='指定配置 JSON 文件')
    parser.add_argument('--image', type=Path, help='以本地图片替代示例采集源')
    parser.add_argument('--detector', choices=['opencv', 'yolo'], default='opencv', help='图片检测器')
    parser.add_argument('--weights', type=Path, help='YOLO 权重，默认 yolo/checkpoints/yolo-eight-ball.pt')
    args = parser.parse_args()
    from .application import Controller
    controller = Controller(args.config)
    if args.detector == 'yolo':
        from .perception.yolo import DEFAULT_WEIGHTS, YOLODetector
        try:
            controller.image_detector = YOLODetector(args.weights or DEFAULT_WEIGHTS)
        except (OSError, ValueError) as error:
            parser.error(str(error))
    elif args.weights:
        parser.error('--weights 需要与 --detector yolo 一起使用')
    if args.image:
        try:
            controller.load_image(args.image)
        except (OSError, ValueError, RuntimeError) as error:
            parser.error(str(error))
    if args.check:
        result = controller.run()
        print(f'Python pipeline OK: source={result.frame.source}, mode={controller.config.mode}, balls={len(result.balls)}, shots={len(result.shots)}, fusion={result.fused}, status={result.status}')
        return
    from .ui import Workbench
    Workbench(controller).mainloop()


if __name__ == '__main__':
    main()
