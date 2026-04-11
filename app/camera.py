# app/camera.py
# 비동기 카메라 스트림
# 별도 스레드에서 지속적으로 프레임을 캡처하여 메인 루프의 I/O 블로킹을 제거

import cv2
import threading


class VideoStream:
    """V4L2 기반 비동기 카메라 스트림 클래스."""

    def __init__(self, src: int = 0) -> None:
        self.cap = cv2.VideoCapture(src, cv2.CAP_V4L2)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.ret, self.frame = self.cap.read()
        self.stopped = False

    def start(self) -> "VideoStream":
        """백그라운드 캡처 스레드를 시작하고 self를 반환합니다."""
        threading.Thread(target=self._update, daemon=True).start()
        return self

    def _update(self) -> None:
        """백그라운드에서 지속적으로 최신 프레임을 버퍼에 저장합니다."""
        while not self.stopped:
            self.ret, self.frame = self.cap.read()

    def read(self):
        """가장 최근 캡처 프레임을 반환합니다."""
        return self.frame

    def stop(self) -> None:
        """스트림 및 카메라 장치를 해제합니다."""
        self.stopped = True
        self.cap.release()
