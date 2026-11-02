"""Decode a local image once into an immutable, UI-independent RGB frame."""
from hashlib import sha256
from pathlib import Path
import warnings

from ..models import Frame

MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_PIXELS = 40_000_000


class ImageSource:
    def __init__(self, path):
        path = Path(path).expanduser().resolve(strict=True)
        if not path.is_file():
            raise ValueError('请选择图片文件')
        if path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError('图片文件请控制在 50 MB 以内')
        data = path.read_bytes()
        if not data or len(data) > MAX_FILE_BYTES:
            raise ValueError('图片为空或超过 50 MB')
        try:
            from PIL import Image, ImageOps
        except ImportError:
            try:
                import cv2
                import numpy as np
            except ImportError as error:
                raise RuntimeError('图片采集需要 Pillow 或 OpenCV，请安装 requirements.txt') from error
            try:
                image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
            except cv2.error as error:
                raise ValueError('图片解码失败') from error
            if image is None:
                raise ValueError('无法解码图片，文件可能已损坏或格式不受支持')
            height, width = image.shape[:2]
            if width * height > MAX_PIXELS:
                raise ValueError('图片请控制在 4000 万像素以内')
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB).tobytes()
        else:
            from io import BytesIO
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                try:
                    with Image.open(BytesIO(data)) as image:
                        if image.width * image.height > MAX_PIXELS:
                            raise ValueError('图片请控制在 4000 万像素以内')
                        image = ImageOps.exif_transpose(image).convert('RGB')
                        width, height = image.size
                        rgb = image.tobytes()
                except (Image.DecompressionBombWarning, Image.DecompressionBombError) as error:
                    raise ValueError('图片分辨率过大') from error
        self.frame = Frame('image', width, height, str(path), rgb, sha256(data).hexdigest())

    def capture(self) -> Frame:
        return self.frame
