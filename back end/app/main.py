from __future__ import annotations

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.live_bridge import LiveBridge
from app.logging_config import configure_logging


settings = get_settings()
configure_logging(settings.log_level)
app = FastAPI(title="Raksha Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

bridge = LiveBridge(
    app_name=settings.app_name,
    model=settings.gemini_model,
    gemini_api_key=settings.gemini_api_key,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket) -> None:
    user_id = websocket.query_params.get("user_id", "raksha-user")
    await bridge.run_websocket(websocket, user_id=user_id)
