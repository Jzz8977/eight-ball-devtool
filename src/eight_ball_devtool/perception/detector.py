"""Perception contracts for YOLO detection, ball classification and calibration.

The bundled detector ONLY accepts demo frames. Real images are never passed off
as recognized scenes. Implement Detector.detect for YOLO/OpenCV integration.
"""
from typing import Protocol
from ..models import Detection, Frame, Point


class Detector(Protocol):
    def detect(self, frame: Frame) -> tuple[Detection, ...]: ...


class DemoDetector:
    def detect(self, frame: Frame) -> tuple[Detection, ...]:
        if frame.source != 'demo':
            raise NotImplementedError('图片仅支持预览与标定；尚未接入 YOLO / 球号分类')
        positions = [(0, .23, .68), (1, .65, .29), (3, .36, .23), (5, .74, .76), (8, .53, .60), (10, .83, .45), (12, .40, .84), (14, .14, .38)]
        return tuple(Detection(n, Point(x * frame.width, y * frame.height), 18) for n, x, y in positions)
