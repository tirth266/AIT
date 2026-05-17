"""
Order State Machine
====================
Defines valid state transitions for order lifecycle.
"""

from enum import Enum
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json


class OrderState(str, Enum):
    """Complete order states for institutional trading."""
    DRAFT = "DRAFT"
    PENDING_SUBMISSION = "PENDING_SUBMISSION"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    SUBMITTED = "SUBMITTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PENDING_CANCEL = "PENDING_CANCEL"
    PENDING_MODIFY = "PENDING_MODIFY"
    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    REPLACED = "REPLACED"


class OrderEvent(str, Enum):
    """Order lifecycle events."""
    CREATE = "CREATE"
    VALIDATE = "VALIDATE"
    SUBMIT = "SUBMIT"
    ACKNOWLEDGE = "ACKNOWLEDGE"
    FILL = "FILL"
    PARTIAL_FILL = "PARTIAL_FILL"
    CANCEL = "CANCEL"
    MODIFY = "MODIFY"
    EXPIRE = "EXPIRE"
    REJECT = "REJECT"
    REPLACE = "REPLACE"
    CANCEL_ACK = "CANCEL_ACK"
    MODIFY_ACK = "MODIFY_ACK"


class OrderStateMachine:
    """
    Validates and executes state transitions for orders.
    Implements finite state machine with audit logging.
    """
    
    VALID_TRANSITIONS: Dict[OrderState, Set[OrderState]] = {
        OrderState.DRAFT: {OrderState.VALIDATED, OrderState.REJECTED},
        OrderState.PENDING_SUBMISSION: {OrderState.SUBMITTED, OrderState.REJECTED},
        OrderState.VALIDATED: {OrderState.SUBMITTED, OrderState.REJECTED, OrderState.CANCELLED},
        OrderState.SUBMITTED: {OrderState.ACKNOWLEDGED, OrderState.REJECTED, OrderState.CANCELLED},
        OrderState.ACKNOWLEDGED: {OrderState.OPEN, OrderState.CANCELLED, OrderState.REJECTED, OrderState.EXPIRED},
        OrderState.OPEN: {
            OrderState.PARTIALLY_FILLED, OrderState.FILLED, OrderState.CANCELLED, 
            OrderState.EXPIRED, OrderState.PENDING_CANCEL, OrderState.PENDING_MODIFY
        },
        OrderState.PARTIALLY_FILLED: {
            OrderState.PARTIALLY_FILLED, OrderState.FILLED, OrderState.CANCELLED,
            OrderState.EXPIRED, OrderState.PENDING_CANCEL, OrderState.PENDING_MODIFY
        },
        OrderState.PENDING_CANCEL: {OrderState.CANCELLED, OrderState.OPEN, OrderState.PARTIALLY_FILLED},
        OrderState.PENDING_MODIFY: {OrderState.OPEN, OrderState.REJECTED},
        OrderState.FILLED: set(),
        OrderState.CANCELLED: set(),
        OrderState.REJECTED: set(),
        OrderState.EXPIRED: set(),
    }
    
    @classmethod
    def can_transition(cls, from_state: OrderState, to_state: OrderState) -> bool:
        """Check if transition is valid."""
        return to_state in cls.VALID_TRANSITIONS.get(from_state, set())
    
    @classmethod
    def get_valid_transitions(cls, from_state: OrderState) -> Set[OrderState]:
        """Get all valid target states from current state."""
        return cls.VALID_TRANSITIONS.get(from_state, set())


@dataclass
class StateTransition:
    """Immutable state transition record."""
    order_id: str
    from_state: OrderState
    to_state: OrderState
    event: OrderEvent
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str = ""
    metadata: Dict = field(default_factory=dict)
    transition_id: str = ""
    
    def __post_init__(self):
        if not self.transition_id:
            self.transition_id = self._generate_transition_id()
    
    def _generate_transition_id(self) -> str:
        data = f"{self.order_id}:{self.from_state.value}:{self.to_state.value}:{self.event.value}:{self.timestamp.isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16].upper()
    
    def to_dict(self) -> Dict:
        return {
            'transition_id': self.transition_id,
            'order_id': self.order_id,
            'from_state': self.from_state.value,
            'to_state': self.to_state.value,
            'event': self.event.value,
            'timestamp': self.timestamp.isoformat(),
            'reason': self.reason,
            'metadata': self.metadata,
        }


class StateTransitionLog:
    """In-memory and persistent state transition logging."""
    
    def __init__(self, max_memory: int = 10000):
        self._transitions: Dict[str, List[StateTransition]] = {}
        self._max_memory = max_memory
    
    def add_transition(self, transition: StateTransition) -> None:
        order_id = transition.order_id
        if order_id not in self._transitions:
            self._transitions[order_id] = []
        
        self._transitions[order_id].append(transition)
        
        if len(self._transitions[order_id]) > self._max_memory:
            self._transitions[order_id] = self._transitions[order_id][-self._max_memory:]
    
    def get_transitions(self, order_id: str) -> List[StateTransition]:
        return self._transitions.get(order_id, [])
    
    def get_latest_state(self, order_id: str) -> Optional[OrderState]:
        transitions = self.get_transitions(order_id)
        if transitions:
            return transitions[-1].to_state
        return None
    
    def get_transition_count(self, order_id: str) -> int:
        return len(self._transitions.get(order_id, []))


transition_log = StateTransitionLog()


def get_transition_log() -> StateTransitionLog:
    return transition_log