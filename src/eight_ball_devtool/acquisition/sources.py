"""Acquisition: demo frames and image metadata. Add camera/depth adapters here."""
from ..models import Frame


class DemoSource:
    def capture(self) -> Frame:
        return Frame('demo', 1920, 1080)


class ImageSource:
    def __init__(self, path: str, width: int, height: int):
        self.frame = Frame('image', width, height, path)

    def capture(self) -> Frame:
        return self.frame
