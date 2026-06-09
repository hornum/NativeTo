import uvicorn
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.users import router as users_router
from app.config import settings

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL), format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")

app = FastAPI()

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(chat_router)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)



if __name__ == "__main__":
    uvicorn.run("app.main:app", port=8000, reload=True, reload_dirs=["app"])
