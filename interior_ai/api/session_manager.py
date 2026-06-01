"""In-memory session management for design state."""

from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from ..types import SceneGraph, DesignSpec, FloorPlanData


@dataclass
class DesignSession:
    id: str
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    scene: Optional[SceneGraph] = None
    spec: Optional[DesignSpec] = None
    floor_plan: Optional[FloorPlanData] = None
    upload_paths: list[str] = field(default_factory=list)
    render_history: list[str] = field(default_factory=list)  # job IDs
    command_history: list[str] = field(default_factory=list)
    timeout_minutes: int = 60

    def touch(self) -> None:
        self.updated_at = time.time()

    @property
    def is_expired(self) -> bool:
        return time.time() - self.updated_at > self.timeout_minutes * 60


class SessionManager:
    """Simple in-memory store for active design sessions."""

    def __init__(self, timeout_minutes: int = 60):
        self._sessions: dict[str, DesignSession] = {}
        self._timeout = timeout_minutes

    def create(self) -> DesignSession:
        session_id = str(uuid.uuid4())
        session = DesignSession(id=session_id, timeout_minutes=self._timeout)
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Optional[DesignSession]:
        session = self._sessions.get(session_id)
        if session and session.is_expired:
            del self._sessions[session_id]
            return None
        return session

    def get_or_create(self, session_id: Optional[str]) -> DesignSession:
        if session_id:
            session = self.get(session_id)
            if session:
                return session
        return self.create()

    def delete(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def prune_expired(self) -> int:
        expired = [sid for sid, s in self._sessions.items() if s.is_expired]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)

    def count(self) -> int:
        return len(self._sessions)
