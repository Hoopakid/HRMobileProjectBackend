from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from admin.apis import admin_router
from auth.auth import auth_router
from chat.chat import chat_router
from mobile.mobile import mobile_router

app = FastAPI(title="MobileProjectBackend", version="1.0.0")


app.include_router(auth_router, prefix="/auth")
app.include_router(chat_router, prefix="/chat")
app.include_router(admin_router, prefix="/admin")
app.include_router(mobile_router, prefix="/mobile")
app.mount("/static", StaticFiles(directory="chat/templates/static"), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
