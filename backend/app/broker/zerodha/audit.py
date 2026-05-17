"""
Audit Logging for Zerodha Broker Integration
=============================================
Comprehensive audit trail for all broker operations.
"""

import logging
import json
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import deque
import uuid

logger = logging.getLogger('zerodha.audit')


class AuditEvent(str, Enum):
    ORDER_PLACEMENT_REQUESTED = "ORDER_PLACEMENT_REQUESTED"
    ORDER_PLACED = "ORDER_PLACED"
    ORDER_PLACEMENT_FAILED = "ORDER_PLACEMENT_FAILED"
    ORDER_MODIFICATION_REQUESTED = "ORDER_MODIFICATION_REQUESTED"
    ORDER_MODIFIED = "ORDER_MODIFIED"
    ORDER_MODIFICATION_FAILED = "ORDER_MODIFICATION_FAILED"
    ORDER_CANCELLATION_REQUESTED = "ORDER_CANCELLATION_REQUESTED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ORDER_CANCELLATION_FAILED = "ORDER_CANCELLATION_FAILED"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_PARTIALLY_FILLED = "ORDER_PARTIALLY_FILLED"
    ORDER_COMPLETED = "ORDER_COMPLETED"

    TOKEN_REFRESHED = "TOKEN_REFRESHED"
    TOKEN_INVALIDATED = "TOKEN_INVALIDATED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"

    WEBSOCKET_CONNECTED = "WEBSOCKET_CONNECTED"
    WEBSOCKET_DISCONNECTED = "WEBSOCKET_DISCONNECTED"
    WEBSOCKET_ERROR = "WEBSOCKET_ERROR"
    WEBSOCKET_RECONNECTED = "WEBSOCKET_RECONNECTED"

    POSITION_OPENED = "POSITION_OPENED"
    POSITION_CLOSED = "POSITION_CLOSED"
    POSITION_MODIFIED = "POSITION_MODIFIED"

    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    CIRCUIT_BREAKER_OPENED = "CIRCUIT_BREAKER_OPENED"
    CIRCUIT_BREAKER_CLOSED = "CIRCUIT_BREAKER_CLOSED"

    RECONCILIATION_STARTED = "RECONCILIATION_STARTED"
    RECONCILIATION_COMPLETED = "RECONCILIATION_COMPLETED"
    RECONCILIATION_FAILED = "RECONCILIATION_FAILED"
    RECONCILIATION_MISMATCH = "RECONCILIATION_MISMATCH"

    LOGIN_INITIATED = "LOGIN_INITIATED"
    LOGIN_SUCCESSFUL = "LOGIN_SUCCESSFUL"
    LOGIN_FAILED = "LOGIN_FAILED"

    API_CALL = "API_CALL"
    API_ERROR = "API_ERROR"


@dataclass
class AuditEntry:
    event_id: str
    event: str
    timestamp: datetime
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    severity: str = "INFO"
    source: str = "broker"
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event": self.event,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "session_id": self.session_id,
            "details": self.details,
            "severity": self.severity,
            "source": self.source,
            "correlation_id": self.correlation_id,
        }


class AuditLogger:
    """
    Thread-safe audit logger with in-memory buffering and optional persistence.
    """

    def __init__(
        self,
        max_buffer_size: int = 10000,
        persistence_enabled: bool = False,
        db_collection=None,
    ):
        self._buffer: deque = deque(maxlen=max_buffer_size)
        self._db_collection = db_collection
        self._persistence_enabled = persistence_enabled
        self._lock = threading.RLock()

        self._current_user_id: Optional[str] = None
        self._current_session_id: Optional[str] = None

        self._log_callbacks: List[callable] = []

    def set_user_context(self, user_id: Optional[str] = None, session_id: Optional[str] = None) -> None:
        self._current_user_id = user_id
        self._current_session_id = session_id

    def log(
        self,
        event: AuditEvent,
        details: Dict[str, Any],
        severity: str = "INFO",
        correlation_id: Optional[str] = None,
    ) -> str:
        entry = AuditEntry(
            event_id=str(uuid.uuid4()),
            event=event.value,
            timestamp=datetime.now(timezone.utc),
            user_id=self._current_user_id,
            session_id=self._current_session_id,
            details=details,
            severity=severity,
            correlation_id=correlation_id or self._generate_correlation_id(),
        )

        with self._lock:
            self._buffer.append(entry)

            if self._persistence_enabled and self._db_collection:
                self._persist_entry(entry)

        for callback in self._log_callbacks:
            try:
                callback(entry)
            except Exception as e:
                logger.warning(f"Audit callback error: {e}")

        self._log_to_standard_logger(entry)

        return entry.event_id

    def _log_to_standard_logger(self, entry: AuditEntry) -> None:
        log_message = f"[{entry.event}] {json.dumps(entry.details)}"

        if entry.severity == "ERROR":
            logger.error(log_message)
        elif entry.severity == "WARNING":
            logger.warning(log_message)
        elif entry.severity == "DEBUG":
            logger.debug(log_message)
        else:
            logger.info(log_message)

    def _generate_correlation_id(self) -> str:
        return str(uuid.uuid4())[:12]

    def _persist_entry(self, entry: AuditEntry) -> None:
        try:
            self._db_collection.insert_one(entry.to_dict())
        except Exception as e:
            logger.error(f"Failed to persist audit entry: {e}")

    def register_callback(self, callback: callable) -> None:
        self._log_callbacks.append(callback)

    def get_recent_entries(self, count: int = 100, event_filter: Optional[str] = None) -> List[AuditEntry]:
        with self._lock:
            entries = list(self._buffer)

        if event_filter:
            entries = [e for e in entries if e.event == event_filter]

        return entries[-count:]

    def get_entries_by_correlation(self, correlation_id: str) -> List[AuditEntry]:
        with self._lock:
            return [e for e in self._buffer if e.correlation_id == correlation_id]

    def get_entries_by_user(self, user_id: str, count: int = 100) -> List[AuditEntry]:
        with self._lock:
            user_entries = [e for e in self._buffer if e.user_id == user_id]
            return user_entries[-count:]

    def get_entries_by_event(self, event: AuditEvent, count: int = 100) -> List[AuditEntry]:
        with self._lock:
            event_entries = [e for e in self._buffer if e.event == event.value]
            return event_entries[-count:]

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            events_count: Dict[str, int] = {}
            for entry in self._buffer:
                events_count[entry.event] = events_count.get(entry.event, 0) + 1

            severities = {"ERROR": 0, "WARNING": 0, "INFO": 0, "DEBUG": 0}
            for entry in self._buffer:
                if entry.severity in severities:
                    severities[entry.severity] += 1

            return {
                "total_entries": len(self._buffer),
                "events": events_count,
                "severities": severities,
            }

    def clear_buffer(self) -> None:
        with self._lock:
            self._buffer.clear()


_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def initialize_audit_logger(db_collection=None, max_buffer_size: int = 10000) -> AuditLogger:
    global _audit_logger
    _audit_logger = AuditLogger(
        max_buffer_size=max_buffer_size,
        persistence_enabled=db_collection is not None,
        db_collection=db_collection,
    )
    return _audit_logger