import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate

from fastapi.staticfiles import StaticFiles
import json
import logging
from app_webcam.webrtc import CameraStreamTrack, create_peer_connection

logger = logging.getLogger(__name__)

app = FastAPI()
app.mount("/static", StaticFiles(directory="app_webcam/static"), name="static")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    pc = create_peer_connection()
    camera_track = CameraStreamTrack()
    pc.addTrack(camera_track)

    try:
        async for message in websocket.iter_text():
            data = json.loads(message)

            if data["type"] == "offer":
                # Обработка offer от клиента
                offer = RTCSessionDescription(sdp=data["sdp"], type=data["type"])
                await pc.setRemoteDescription(offer)

                # Создаем и отправляем answer
                answer = await pc.createAnswer()
                await pc.setLocalDescription(answer)

                await websocket.send_text(json.dumps({
                    "sdp": pc.localDescription.sdp,
                    "type": pc.localDescription.type
                }))

            elif data.get("candidate"):
                # Обработка ICE кандидатов
                try:
                    await pc.addIceCandidate(data["candidate"])
                except Exception as e:
                    logger.error(f"ICE candidate error: {e}")

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        camera_track.release()
        await pc.close()
        logger.info("WebRTC connection closed")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)