"""Load pooltool with project-local config, preserving the user's older config.

pooltool 0.6 has no config-directory option. This narrow import hook replaces
only its paths module; physics, event detection and aiming code remain upstream.
"""
from importlib.abc import Loader, MetaPathFinder
from importlib.metadata import PackageNotFoundError, version
from importlib.util import spec_from_loader
from pathlib import Path
import sys
from threading import RLock

from ..config import PROJECT_ROOT

CONFIG_DIR = PROJECT_ROOT/'runtime/pooltool-config'
_lock = RLock()


class _PathsLoader(Loader):
    def create_module(self, spec):
        return None

    def exec_module(self, module):
        module.HOME = Path.home()
        module.CONFIG_DIR = CONFIG_DIR
        module.PHYSICS_DIR = CONFIG_DIR/'physics'
        module.GENERAL_CONFIG = CONFIG_DIR/'general.yaml'
        module.PHYSICS_DIR.mkdir(parents=True, exist_ok=True)


class _PathsFinder(MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'pooltool.config.paths':
            return spec_from_loader(fullname, _PathsLoader())
        return None


def load_pooltool():
    with _lock:
        try:
            installed = version('pooltool-billiards')
        except PackageNotFoundError as error:
            raise RuntimeError('当前环境缺少 pooltool；请使用已配置的 .venv 或安装 requirements-physics.txt') from error
        if installed != '0.6.0':
            raise RuntimeError(f'此适配器需要 pooltool 0.6.0，当前为 {installed}')
        if 'pooltool' in sys.modules:
            paths = sys.modules.get('pooltool.config.paths')
            if paths is None or paths.CONFIG_DIR != CONFIG_DIR:
                raise RuntimeError('pooltool 已使用其他配置初始化，请重启程序以启用本项目的隔离配置')
            return sys.modules['pooltool']
        finder = _PathsFinder()
        sys.meta_path.insert(0, finder)
        try:
            import pooltool
        except ImportError as error:
            raise RuntimeError(f'pooltool 依赖未完整安装：{error}') from error
        finally:
            sys.meta_path.remove(finder)
        return pooltool
