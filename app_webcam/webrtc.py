import logging
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaBlackhole, MediaRecorder, MediaRelay
from av import VideoFrame
import cv2

logger = logging.getLogger(__name__)
relay = MediaRelay()


class CameraStreamTrack(VideoStreamTrack):
    """
    Трек для трансляции видео с веб-камеры (Linux-совместимый)
    """

    def __init__(self):
        super().__init__()
        self.cap = cv2.VideoCapture(self._get_camera_index())
        if not self.cap.isOpened():
            raise RuntimeError("Could not open video device")

        # Настройки камеры для Linux
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

    def _get_camera_index(self):
        """Определяет индекс камеры для Linux"""
        # Пробуем разные варианты
        for index in [0, 1, 2, "/dev/video0", "/dev/video2"]:
            print("!!!__", index)
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                cap.release()
                return index
        return 0  # По умолчанию пробуем 0

    async def recv(self):
        pts, time_base = await self.next_timestamp()

        ret, frame = self.cap.read()
        if not ret:
            logger.error("Camera read failed, trying to restart...")
            self.cap.release()
            self.cap = cv2.VideoCapture(self._get_camera_index())
            raise RuntimeError("Failed to read camera frame")

        # Конвертация цветового пространства
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        video_frame = VideoFrame.from_ndarray(frame, format='rgb24')
        video_frame.pts = pts
        video_frame.time_base = time_base

        return video_frame

    def release(self):
        if self.cap and self.cap.isOpened():
            self.cap.release()


def create_peer_connection():
    pc = RTCPeerConnection()

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info(f"Connection state: {pc.connectionState}")
        if pc.connectionState == "failed":
            await pc.close()

    @pc.on("iceconnectionstatechange")
    async def on_iceconnectionstatechange():
        logger.info(f"ICE connection state: {pc.iceConnectionState}")
        if pc.iceConnectionState == "failed":
            await pc.close()

    return pc
