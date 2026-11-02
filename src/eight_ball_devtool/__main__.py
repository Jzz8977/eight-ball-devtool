import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='Eight Ball 原生 Python 开发工作台')
    parser.add_argument('--check', action='store_true', help='运行无界面的流水线检查')
    parser.add_argument('--config', type=Path, help='指定配置 JSON 文件')
    args = parser.parse_args()
    from .application import Controller
    controller = Controller(args.config)
    if args.check:
        result = controller.run()
        print(f'Python pipeline OK: mode={controller.config.mode}, balls={len(result.balls)}, shots={len(result.shots)}, fusion={result.fused}')
        return
    from .ui import Workbench
    Workbench(controller).mainloop()


if __name__ == '__main__':
    main()
