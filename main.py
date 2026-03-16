import uvicorn
from loguru import logger
from app.config import ServerConfig
from app.core import create_app

logger.disable("gemini_webapi.utils.parsing")

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=ServerConfig.host,
        port=ServerConfig.port,
        reload=False,
    )
