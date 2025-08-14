from pathlib import Path
from fastapi import FastAPI
from fastapi import Request, Response
from fastapi import Header
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware



app = FastAPI()
templates = Jinja2Templates(directory="templates")
CHUNK_SIZE = 1024*1024
video_path = Path("video/margo.mp4")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", context={"request": request})


@app.get("/video")
async def video_endpoint(range: str = Header(None)):
    if not video_path.exists():
        return Response(f"Video not found at {video_path}", status_code=404)
    
    file_size = video_path.stat().st_size
    
    # Если запрос без Range (первый запрос от плеера)
    if not range:
        headers = {
            'Accept-Ranges': 'bytes',
            'Content-Length': str(file_size),
            'Content-Type': 'video/mp4'
        }
        return Response(
            content=open(video_path, "rb").read(),
            status_code=200,
            headers=headers
        )
    
    # Обработка Range-запросов
    start, end = range.replace("bytes=", "").split("-")
    start = int(start)
    end = min(int(end) if end else start + CHUNK_SIZE, file_size - 1)
    
    with open(video_path, "rb") as video:
        video.seek(start)
        data = video.read(end - start + 1)
        headers = {
            'Content-Range': f'bytes {start}-{end}/{file_size}',
            'Accept-Ranges': 'bytes',
            'Content-Length': str(end - start + 1),
            'Content-Type': 'video/mp4'
        }
        return Response(
            content=data,
            status_code=206,
            headers=headers
        )