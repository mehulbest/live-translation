from typing import Dict, List, Tuple, Optional
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)


class RoomManager:
    def __init__(self):
        # room_id -> { speaker: WebSocket|None, listeners: {lid: (WebSocket, lang)} }
        self.rooms: Dict[str, dict] = {}

    def create_room(self, room_id: str):
        self.rooms[room_id] = {"speaker": None, "listeners": {}}
        logger.info(f"Room created: {room_id}")

    def room_exists(self, room_id: str) -> bool:
        return room_id in self.rooms

    def set_speaker(self, room_id: str, websocket: WebSocket):
        if room_id not in self.rooms:
            self.rooms[room_id] = {"speaker": None, "listeners": {}}
        self.rooms[room_id]["speaker"] = websocket

    def remove_speaker(self, room_id: str):
        if room_id in self.rooms:
            self.rooms[room_id]["speaker"] = None

    def add_listener(self, room_id: str, listener_id: str, websocket: WebSocket, language: str):
        if room_id not in self.rooms:
            self.rooms[room_id] = {"speaker": None, "listeners": {}}
        self.rooms[room_id]["listeners"][listener_id] = (websocket, language)

    def remove_listener(self, room_id: str, listener_id: str):
        if room_id in self.rooms:
            self.rooms[room_id]["listeners"].pop(listener_id, None)

    def get_listeners(self, room_id: str) -> List[Tuple[str, WebSocket, str]]:
        if room_id not in self.rooms:
            return []
        return [
            (lid, ws, lang)
            for lid, (ws, lang) in self.rooms[room_id]["listeners"].items()
        ]

    def get_room_info(self, room_id: str) -> dict:
        if room_id not in self.rooms:
            return {}
        room = self.rooms[room_id]
        return {
            "has_speaker": room["speaker"] is not None,
            "listener_count": len(room["listeners"]),
            "listener_languages": [
                lang for _, lang in room["listeners"].values()
            ],
        }

    def update_listener_language(self, room_id: str, listener_id: str, new_lang: str):
        if room_id in self.rooms and listener_id in self.rooms[room_id]["listeners"]:
            ws, _ = self.rooms[room_id]["listeners"][listener_id]
            self.rooms[room_id]["listeners"][listener_id] = (ws, new_lang)
