"""Acquisition: demo frames and image metadata. Add camera/depth adapters here."""
from ..models import Frame
from .image import ImageSource
from typing import Protocol


class FrameSource(Protocol):
    def capture(self) -> Frame: ...


class DemoSource:
    def capture(self) -> Frame:
        return Frame('demo', 1920, 1080)
