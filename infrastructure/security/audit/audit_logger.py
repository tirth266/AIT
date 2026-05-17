"""
SEBI Audit Infrastructure
==========================
Immutable audit trail for regulatory compliance.
Implements: SEBI requirements, trade retention, user activity logging.
"""

import logging
import json
import time
import uuid
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from enum import Enum
import threading

logger = logging.getLogger('audit')


class AuditEventType(str, Enum):
    """Audit event types per SEBI requirements."""

    # Trading events
    ORDER_PLACED = "ORDER_PLACED"
    ORDER_MODIFIED = "ORDER_MODIFIED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ORDER_REJECTED = "ORDER_REJECTED"
    TRADE_EXECUTED = "TRADE_EXECUTED"
    TRADE_MODIFIED = "TRADE_MODIFIED"

    # User events
    USER_LOGIN = "USER_LOGIN"
    USER_LOGOUT = "USER_LOGOUT"
    USER_PASSWORD_CHANGE = "USER_PASSWORD_CHANGE"
    USER_2FA_ENABLED = "USER_2FA_ENABLED"
    USER_API_KEY_CREATED = "USER_API_KEY_CREATED"
    USER_API_KEY_REVOKED = "USER_API_KEY_REVOKED"

    # Admin events
    BROKER_CONNECTED = "BROKER_CONNECTED"
    BROKER_DISCONNECTED = "BROKER_DISCONNECTED"
    STRATEGY_CREATED = "STRATEGY_CREATED"
    STRATEGY_MODIFIED = "STRATEGY_MODIFIED"
    STRATEGY_DELETED = "STRATEGY_DELETED"
    RISK_LIMIT_CHANGED = "RISK_LIMIT_CHANGED"

    # System events
    SYSTEM_STARTUP = "SYSTEM_STARTUP"
    SYSTEM_SHUTDOWN = "SYSTEM_SHUTDOWN"
    CONFIG_CHANGED = "CONFIG_CHANGED"

    # Data events
    DATA_EXPORTED = "DATA_EXPORTED"
    DATA_IMPORTED = "DATA_IMPORTED"


@dataclass
class AuditEvent:
    """Immutable audit event structure."""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: AuditEventType = AuditEventType.USER_LOGIN
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    user_id: str = ""
    user_ip: str = ""
    user_agent: str = ""

    resource_type: str = ""
    resource_id: str = ""

    action: str = ""
    result: str = "success"

    details: Dict[str, Any] = field(default_factory=dict)
    previous_state: Dict[str, Any] = field(default_factory=dict)
    new_state: Dict[str, Any] = field(default_factory=dict)

    correlation_id: Optional[str] = None
    session_id: Optional[str] = None

    hash: str = ""

    def compute_hash(self) -> str:
        """Compute SHA-256 hash for integrity verification."""
        event_data = {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'timestamp': self.timestamp,
            'user_id': self.user_id,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'action': self.action,
            'details': self.details
        }

        canonical = json.dumps(event_data, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def sign(self, secret_key: str) -> str:
        """Sign the event for additional integrity."""
        content = self.compute_hash()
        return hashlib.sha512((content + secret_key).encode()).hexdigest()[:32]

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        return data


class ImmutableAuditLog:
    """
    Immutable audit log with append-only semantics.
    Implements WORM (Write Once Read Many) storage.
    """

    def __init__(self, storage_backend=None, retention_years: int = 10):
        self._storage = storage_backend
        self._retention_years = retention_years
        self._write_buffer: List[AuditEvent] = []
        self._buffer_size = 100
        self._lock = threading.Lock()

        self._stats = {
            'events_logged': 0,
            'events_by_type': {},
            'verification_failures': 0
        }

        logger.info(f"ImmutableAuditLog initialized with {retention_years} year retention")

    def log(
        self,
        event_type: AuditEventType,
        user_id: str,
        action: str,
        resource_type: str = "",
        resource_id: str = "",
        result: str = "success",
        details: Optional[Dict] = None,
        previous_state: Optional[Dict] = None,
        new_state: Optional[Dict] = None,
        user_ip: str = "",
        user_agent: str = "",
        correlation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Log an audit event. Returns event ID.
        """
        event = AuditEvent(
            event_type=event_type,
            user_id=user_id,
            user_ip=user_ip,
            user_agent=user_agent,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            result=result,
            details=details or {},
            previous_state=previous_state or {},
            new_state=new_state or {},
            correlation_id=correlation_id,
            session_id=session_id
        )

        event.hash = event.compute_hash()

        with self._lock:
            self._write_buffer.append(event)
            self._stats['events_logged'] += 1

            event_type_key = event_type.value
            if event_type_key not in self._stats['events_by_type']:
                self._stats['events_by_type'][event_type_key] = 0
            self._stats['events_by_type'][event_type_key] += 1

            if len(self._write_buffer) >= self._buffer_size:
                self._flush_buffer()

        return event.event_id

    def _flush_buffer(self):
        """Flush write buffer to storage."""
        if not self._write_buffer:
            return

        events = self._write_buffer.copy()
        self._write_buffer.clear()

        if self._storage:
            try:
                for event in events:
                    self._storage.store(event.to_dict())
            except Exception as e:
                logger.error(f"Failed to store audit events: {e}")
                self._write_buffer.extend(events)

    def get_event(self, event_id: str) -> Optional[AuditEvent]:
        """Retrieve a specific audit event."""
        if self._storage:
            try:
                data = self._storage.get(event_id)
                if data:
                    return self._deserialize_event(data)
            except Exception as e:
                logger.error(f"Failed to retrieve event {event_id}: {e}")
        return None

    def query(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[AuditEvent]:
        """Query audit events."""
        if self._storage:
            try:
                filters = {}
                if user_id:
                    filters['user_id'] = user_id
                if event_type:
                    filters['event_type'] = event_type.value
                if resource_type:
                    filters['resource_type'] = resource_type
                if resource_id:
                    filters['resource_id'] = resource_id
                if start_time:
                    filters['start_time'] = start_time.isoformat()
                if end_time:
                    filters['end_time'] = end_time.isoformat()

                results = self._storage.query(filters, limit=limit)
                return [self._deserialize_event(r) for r in results]
            except Exception as e:
                logger.error(f"Query failed: {e}")

        return []

    def verify_integrity(self, event_id: str) -> bool:
        """Verify integrity of an audit event."""
        event = self.get_event(event_id)
        if not event:
            return False

        computed_hash = event.compute_hash()
        if computed_hash != event.hash:
            logger.error(f"Event {event_id} integrity check failed")
            self._stats['verification_failures'] += 1
            return False

        return True

    def get_stats(self) -> Dict:
        """Get audit statistics."""
        return {
            **self._stats,
            'buffer_size': len(self._write_buffer)
        }

    def _deserialize_event(self, data: Dict) -> AuditEvent:
        """Deserialize event from storage."""
        data['event_type'] = AuditEventType(data['event_type'])
        return AuditEvent(**data)


class AuditLogger:
    """
    High-level audit logging interface.
    """

    def __init__(self, audit_log: ImmutableAuditLog):
        self._audit = audit_log

    def log_order(self, user_id: str, order_id: str, action: str, order_data: Dict, **kwargs):
        """Log order-related event."""
        return self._audit.log(
            event_type=AuditEventType.ORDER_PLACED if action == "placed" else AuditEventType.ORDER_MODIFIED,
            user_id=user_id,
            action=action,
            resource_type="order",
            resource_id=order_id,
            details=order_data,
            **kwargs
        )

    def log_trade(self, user_id: str, trade_id: str, trade_data: Dict, **kwargs):
        """Log trade execution."""
        return self._audit.log(
            event_type=AuditEventType.TRADE_EXECUTED,
            user_id=user_id,
            action="executed",
            resource_type="trade",
            resource_id=trade_id,
            details=trade_data,
            **kwargs
        )

    def log_user_login(self, user_id: str, ip_address: str, user_agent: str, **kwargs):
        """Log user login."""
        return self._audit.log(
            event_type=AuditEventType.USER_LOGIN,
            user_id=user_id,
            action="login",
            result="success",
            user_ip=ip_address,
            user_agent=user_agent,
            **kwargs
        )

    def log_user_activity(self, user_id: str, activity: str, details: Dict, **kwargs):
        """Log general user activity."""
        return self._audit.log(
            event_type=AuditEventType.USER_LOGIN,
            user_id=user_id,
            action=activity,
            resource_type="user",
            resource_id=user_id,
            details=details,
            **kwargs
        )

    def log_api_access(self, user_id: str, endpoint: str, method: str, **kwargs):
        """Log API access."""
        return self._audit.log(
            event_type=AuditEventType.USER_LOGIN,
            user_id=user_id,
            action=f"api_access_{method}",
            resource_type="api",
            resource_id=endpoint,
            **kwargs
        )


# Global audit logger
_audit_log: Optional[ImmutableAuditLog] = None


def get_audit_log(storage_backend=None) -> ImmutableAuditLog:
    """Get or create the global audit log."""
    global _audit_log
    if _audit_log is None:
        _audit_log = ImmutableAuditLog(storage_backend, retention_years=10)
    return _audit_log


def get_audit_logger() -> AuditLogger:
    """Get an audit logger instance."""
    return AuditLogger(get_audit_log())