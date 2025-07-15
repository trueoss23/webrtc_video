from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate
from aiortc.contrib.media import MediaPlayer, MediaRelay
import uvicorn
import json
import os
import logging

# Настройка логгирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Реле для трансляции медиа
relay = MediaRelay()


class VideoStreamTrack(MediaPlayer):
    """Кастомный трек для трансляции видео из файла"""

    def __init__(self, file_path):
        super().__init__(file_path)
        self.kind = "video"

    async def recv(self):
        frame = await super().video.recv()
        return frame


def create_local_tracks(file_path):
    """Создание медиа треков из файла"""
    player = MediaPlayer(file_path)
    return player.video, player.audio


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    pc = RTCPeerConnection()

    # Конфигурация для лучшей совместимости
    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info(f"Connection state is {pc.connectionState}")
        if pc.connectionState == "failed":
            await pc.close()

    @pc.on("iceconnectionstatechange")
    async def on_iceconnectionstatechange():
        logger.info(f"ICE connection state is {pc.iceConnectionState}")
        if pc.iceConnectionState == "failed":
            await pc.close()

    # Отключаем ограничение битрейта (для тестирования)
    @pc.on("track")
    def on_track(track):
        logger.info(f"Track {track.kind} received")

    try:
        # Добавляем видео трек
        video_file = "static/video.mp4"  # Убедитесь что файл существует
        if not os.path.exists(video_file):
            raise FileNotFoundError(f"Video file {video_file} not found")

        video_track, audio_track = create_local_tracks(video_file)
        pc.addTrack(video_track)
        pc.addTrack(audio_track)

        # Обработка сообщений от клиента
        async for message in websocket.iter_text():
            data = json.loads(message)

            if data["type"] == "offer":
                # Получаем offer от клиента
                offer = RTCSessionDescription(sdp=data["sdp"], type=data["type"])
                await pc.setRemoteDescription(offer)

                # Создаем и отправляем answer
                answer = await pc.createAnswer()
                await pc.setLocalDescription(answer)

                await websocket.send_text(json.dumps({
                    "sdp": pc.localDescription.sdp,
                    "type": pc.localDescription.type
                }))

            elif data["type"] == "candidate" and data["candidate"]:
                try:
                    candidate = RTCIceCandidate(
                        component=data["candidate"]["component"],
                        foundation=data["candidate"]["foundation"],
                        ip=data["candidate"]["ip"],
                        port=data["candidate"]["port"],
                        priority=data["candidate"]["priority"],
                        protocol=data["candidate"]["protocol"],
                        relatedAddress=data["candidate"]["relatedAddress"],
                        relatedPort=data["candidate"]["relatedPort"],
                        sdpMid=data["candidate"]["sdpMid"],
                        sdpMLineIndex=data["candidate"]["sdpMLineIndex"],
                        tcpType=data["candidate"]["tcpType"],
                        type=data["candidate"]["type"]
                    )
                    await pc.addIceCandidate(candidate)
                except Exception as e:
                    logger.error(f"Error adding ICE candidate: {e}")

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await pc.close()


if __name__ == "__main__":
    # Создаем папку для статики если ее нет
    os.makedirs("static", exist_ok=True)

    # Создаем простую HTML страницу для клиента
    with open("static/index.html", "w") as f:
        f.write("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Video Stream</title>
        </head>
        <body>
            <video id="video" autoplay playsinline controls></video>
            <script>
                const video = document.getElementById('video');
                const ws = new WebSocket('ws://' + window.location.host + '/ws');
                let pc;

                async function start() {
                    pc = new RTCPeerConnection({
                        iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
                    });

                    pc.ontrack = (event) => {
                        if (event.track.kind === 'video') {
                            video.srcObject = event.streams[0];
                        }
                    };

                    pc.onicecandidate = (event) => {
                        if (event.candidate) {
                            ws.send(JSON.stringify({
                                type: 'candidate',
                                candidate: event.candidate
                            }));
                        }
                    };

                    try {
                        const offer = await pc.createOffer({
                            offerToReceiveVideo: true,
                            offerToReceiveAudio: true
                        });
                        await pc.setLocalDescription(offer);

                        ws.send(JSON.stringify({
                            sdp: pc.localDescription.sdp,
                            type: pc.localDescription.type
                        }));
                    } catch (error) {
                        console.error('Error creating offer:', error);
                    }
                }

                ws.onopen = start;

                ws.onmessage = async (event) => {
                    const message = JSON.parse(event.data);
                    if (message.type === 'answer') {
                        await pc.setRemoteDescription(
                            new RTCSessionDescription(message)
                        );
                    } else if (message.candidate) {
                        try {
                            await pc.addIceCandidate(
                                new RTCIceCandidate(message.candidate)
                            );
                        } catch (error) {
                            console.error('Error adding ICE candidate:', error);
                        }
                    }
                };

                ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                };
            </script>
        </body>
        </html>
        """)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
