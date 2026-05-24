import asyncio
import json
import uuid
import logging
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from room_manager import RoomManager
from stt_service import STTService
from translation_service import TranslationService
from tts_service import TTSService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(title="Live Translation Platform", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Services (loaded once at startup) ─────────────────────────────────────────
room_manager = RoomManager()
stt_service: STTService = None
translation_service: TranslationService = None
tts_service: TTSService = None
room_audio_queues: dict[str, asyncio.Queue] = {}
room_audio_workers: dict[str, asyncio.Task] = {}


@app.on_event("startup")
async def startup():
    global stt_service, translation_service, tts_service
    load_dotenv(Path(__file__).with_name(".env"))
    logger.info("Loading AI models ... (this may take a minute on first run)")
    loop = asyncio.get_event_loop()

    # Load heavy models in thread pool so startup doesn't block event loop
    stt_service = await loop.run_in_executor(None, STTService)
    translation_service = await loop.run_in_executor(None, TranslationService)
    tts_service = TTSService()          # lightweight – just reads env var
    logger.info("All models ready. Server is live.")


# ── Static frontend ────────────────────────────────────────────────────────────
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
async def root():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/speaker")
async def speaker_page():
    return FileResponse(str(FRONTEND_DIR / "speaker.html"))


@app.get("/listener")
async def listener_page():
    return FileResponse(str(FRONTEND_DIR / "listener.html"))


# ── REST API ───────────────────────────────────────────────────────────────────
@app.get("/api/create-room")
async def create_room():
    room_id = str(uuid.uuid4())[:6].upper()
    room_manager.create_room(room_id)
    logger.info(f"Room created: {room_id}")
    return {"room_id": room_id}


@app.get("/api/room/{room_id}/info")
async def room_info(room_id: str):
    if not room_manager.room_exists(room_id):
        raise HTTPException(status_code=404, detail="Room not found")
    return room_manager.get_room_info(room_id)


@app.get("/api/languages")
async def get_languages():
    return {
        "languages": [
            {"code": "hi-IN", "name": "Hindi", "native": "हिंदी"},
            {"code": "en-IN", "name": "English", "native": "English"},
            {"code": "ta-IN", "name": "Tamil", "native": "தமிழ்"},
            {"code": "te-IN", "name": "Telugu", "native": "తెలుగు"},
            {"code": "kn-IN", "name": "Kannada", "native": "ಕನ್ನಡ"},
            {"code": "bn-IN", "name": "Bengali", "native": "বাংলা"},
            {"code": "mr-IN", "name": "Marathi", "native": "मराठी"},
            {"code": "gu-IN", "name": "Gujarati", "native": "ગુજરાતી"},
        ]
    }


# ── WebSocket: Speaker ─────────────────────────────────────────────────────────
@app.websocket("/ws/speaker/{room_id}")
async def speaker_websocket(websocket: WebSocket, room_id: str):
    await websocket.accept()

    if not room_manager.room_exists(room_id):
        await websocket.close(code=4004, reason="Room not found")
        return

    # First message from speaker: { "language": "hi-IN" }
    try:
        config_raw = await asyncio.wait_for(websocket.receive_text(), timeout=10)
        config = json.loads(config_raw)
    except Exception:
        await websocket.close(code=4000, reason="Invalid config")
        return

    source_lang = config.get("language", "hi-IN")
    room_manager.set_speaker(room_id, websocket)
    queue = asyncio.Queue(maxsize=4)
    room_audio_queues[room_id] = queue
    room_audio_workers[room_id] = asyncio.create_task(
        _audio_worker(room_id, source_lang, queue)
    )

    await websocket.send_json({"type": "ready", "message": "You're live!"})
    logger.info(f"Speaker connected → room={room_id}  lang={source_lang}")

    webm_header = None

    try:
        while True:
            message = await websocket.receive()

            if message["type"] == "websocket.disconnect":
                break

            if "bytes" in message and message["bytes"]:
                raw = bytes(message["bytes"])

                # Save the very first chunk — it contains the WebM/EBML header
                if webm_header is None:
                    webm_header = raw

                chunk = raw if raw.startswith(webm_header) else (webm_header + raw)
                await _enqueue_audio_chunk(room_id, chunk)

            elif "text" in message:
                ctrl = json.loads(message["text"])
                if ctrl.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        await _shutdown_audio_worker(room_id)
        room_manager.remove_speaker(room_id)
        logger.info(f"Speaker disconnected ← room={room_id}")


async def _enqueue_audio_chunk(room_id: str, chunk: bytes):
    queue = room_audio_queues.get(room_id)
    if queue is None:
        return

    if queue.full():
        try:
            queue.get_nowait()
            queue.task_done()
            logger.warning(f"[{room_id}] Dropped stale audio chunk to keep latency bounded")
        except asyncio.QueueEmpty:
            pass

    await queue.put(chunk)


async def _shutdown_audio_worker(room_id: str):
    queue = room_audio_queues.pop(room_id, None)
    worker = room_audio_workers.pop(room_id, None)

    if queue is not None:
        await queue.put(None)
    if worker is not None:
        await worker


async def _audio_worker(room_id: str, source_lang: str, queue: asyncio.Queue):
    while True:
        audio_bytes = await queue.get()
        try:
            if audio_bytes is None:
                return
            await _process_audio_chunk(room_id, audio_bytes, source_lang)
        finally:
            queue.task_done()


async def _process_audio_chunk(room_id: str, audio_bytes: bytes, source_lang: str):
    try:
        # 1. Speech-to-Text
        transcript = await stt_service.transcribe(audio_bytes, source_lang)
        if not transcript or len(transcript.strip()) < 3:
            return

        logger.info(f"[{room_id}] 🎙  {transcript}")

        listeners = room_manager.get_listeners(room_id)
        if not listeners:
            return

        # 2. Translate + TTS for every listener in parallel
        tasks = [
            _translate_and_send(ws, transcript, source_lang, tgt_lang)
            for _, ws, tgt_lang in listeners
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    except Exception as e:
        logger.error(f"Error processing audio chunk: {e}")


async def _translate_and_send(
    listener_ws: WebSocket,
    transcript: str,
    source_lang: str,
    target_lang: str,
):
    try:
        # Step 1: Translate
        translated = await translation_service.translate(
            transcript, source_lang, target_lang
        )

        # Step 2: Send text IMMEDIATELY — listener sees bubble right away
        await listener_ws.send_json(
            {
                "type": "translation",
                "original": transcript,
                "translated": translated,
                "audio": "",           # no audio yet
                "source_lang": source_lang,
                "target_lang": target_lang,
            }
        )

        # Step 3: TTS in background — send audio separately when ready
        audio_b64 = await tts_service.synthesize(translated, target_lang)
        if audio_b64:
            await listener_ws.send_json(
                {
                    "type": "audio",
                    "audio": audio_b64,
                }
            )

    except Exception as e:
        logger.error(f"translate_and_send error: {e}")


# ── WebSocket: Listener ────────────────────────────────────────────────────────
@app.websocket("/ws/listener/{room_id}/{listener_id}")
async def listener_websocket(websocket: WebSocket, room_id: str, listener_id: str):
    await websocket.accept()

    if not room_manager.room_exists(room_id):
        await websocket.close(code=4004, reason="Room not found")
        return

    # First message: { "language": "ta-IN" }
    try:
        config_raw = await asyncio.wait_for(websocket.receive_text(), timeout=10)
        config = json.loads(config_raw)
    except Exception:
        await websocket.close(code=4000, reason="Invalid config")
        return

    target_lang = config.get("language", "hi-IN")
    room_manager.add_listener(room_id, listener_id, websocket, target_lang)

    await websocket.send_json(
        {
            "type": "connected",
            "message": f"Joined room {room_id}",
            "language": target_lang,
        }
    )
    logger.info(f"Listener connected → room={room_id}  lid={listener_id}  lang={target_lang}")

    try:
        while True:
            msg_raw = await websocket.receive_text()
            ctrl = json.loads(msg_raw)

            if ctrl.get("type") == "change_language":
                new_lang = ctrl.get("language", target_lang)
                target_lang = new_lang
                room_manager.update_listener_language(room_id, listener_id, new_lang)
                await websocket.send_json(
                    {"type": "language_changed", "language": new_lang}
                )
                logger.info(f"Listener {listener_id} changed lang → {new_lang}")

            elif ctrl.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        room_manager.remove_listener(room_id, listener_id)
        logger.info(f"Listener disconnected ← room={room_id}  lid={listener_id}")
