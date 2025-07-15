import uvicorn
from app_webcam.show_webcam import app
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Создаем SSL контекст для HTTPS
    ssl_keyfile = "./key.pem"
    ssl_certfile = "./cert.pem"

    if not os.path.exists(ssl_keyfile) or not os.path.exists(ssl_certfile):
        logger.warning("SSL certificates not found, generating self-signed...")
        os.system(f"openssl req -x509 -newkey rsa:4096 -keyout {ssl_keyfile} -out {ssl_certfile} -days 365 -nodes -subj '/CN=localhost'")

    uvicorn.run(
        "app_webcam.show_webcam:app",
        host="0.0.0.0",
        port=8443,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile,
        reload=True
    )
