"""Lightweight circle candidates for image pipeline bring-up, not ball IDs/YOLO."""
from ..models import Detection, Point


class OpenCVCandidateDetector:
    display_name = 'OpenCV 圆形候选'

    def detect(self, frame):
        if frame.source != 'image' or frame.rgb is None:
            raise ValueError('图片检测器需要真实 RGB 图片帧')
        try:
            import cv2
            import numpy as np
        except ImportError as error:
            raise RuntimeError('未安装 OpenCV，可先手动添加球位，或安装 requirements.txt') from error
        image = np.frombuffer(frame.rgb, dtype=np.uint8).reshape(frame.height, frame.width, 3)
        scale = min(1, 1200/max(frame.width, frame.height))
        if scale < 1:
            image = cv2.resize(image, (max(1, round(frame.width*scale)), max(1, round(frame.height*scale))))
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 1)
        short = min(gray.shape)
        minimum = max(3, round(short*.007))
        maximum = max(minimum+1, round(short*.035))
        circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=1.2, minDist=minimum*2, param1=100, param2=18, minRadius=minimum, maxRadius=maximum)
        if circles is None:
            return ()
        # Every identity remains unknown until explicitly confirmed by the user.
        return tuple(Detection(None, Point(float(x)/scale, float(y)/scale), float(r)/scale) for x, y, r in sorted(circles[0], key=lambda p: (float(p[1]), float(p[0])))[:64])
