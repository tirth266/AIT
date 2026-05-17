"""
Kill Switch System
==================
Emergency trading controls and account freezing.
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class KillSwitchScope(str, Enum):
    GLOBAL = "global"
    USER = "user"
    STRATEGY = "strategy"


class KillSwitchReason(str, Enum):
    MANUAL = "manual"
    DRAWDOWN = "drawdown"
    MARGIN_CALL = "margin_call"
    CIRCUIT_BREAKER = "circuit_breaker"
    BROKER_REQUEST = "broker_request"
    COMPLIANCE = "compliance"
    SYSTEM_ERROR = "system_error"


@dataclass
class KillSwitchStatus:
    scope: str
    target_id: str
    active: bool
    reason: str
    triggered_at: datetime
    released_at: Optional[datetime]
    triggered_by: str


class KillSwitchManager:
    """
    Manages emergency kill switches for trading.
    """
    
    def __init__(self, risk_engine=None):
        self.logger = logging.getLogger('kill_switch_manager')
        self.risk_engine = risk_engine
        
        self._global_switch: Optional[KillSwitchStatus] = None
        self._user_switches: Dict[str, KillSwitchStatus] = {}
        self._strategy_switches: Dict[str, KillSwitchStatus] = {}
        
        self._switch_history: List[Dict] = []
    
    def trigger_global_kill_switch(self, reason: str, triggered_by: str = "system") -> bool:
        if self._global_switch and self._global_switch.active:
            self.logger.warning("Global kill switch already active")
            return False
        
        self._global_switch = KillSwitchStatus(
            scope=KillSwitchScope.GLOBAL.value,
            target_id="global",
            active=True,
            reason=reason,
            triggered_at=datetime.now(timezone.utc),
            released_at=None,
            triggered_by=triggered_by
        )
        
        if self.risk_engine:
            self.risk_engine.trigger_global_kill_switch(reason)
        
        self._log_switch_event("triggered", reason, triggered_by, "global")
        
        self.logger.critical(f"GLOBAL KILL SWITCH TRIGGERED: {reason} by {triggered_by}")
        
        return True
    
    def release_global_kill_switch(self, released_by: str = "system") -> bool:
        if not self._global_switch or not self._global_switch.active:
            self.logger.warning("Global kill switch not active")
            return False
        
        self._global_switch.released_at = datetime.now(timezone.utc)
        self._global_switch.active = False
        
        if self.risk_engine:
            self.risk_engine.release_global_kill_switch()
        
        self._log_switch_event("released", "manual release", released_by, "global")
        
        self.logger.info(f"Global kill switch released by {released_by}")
        
        return True
    
    def trigger_user_kill_switch(self, user_id: str, reason: str, 
                                  triggered_by: str = "system") -> bool:
        if user_id in self._user_switches and self._user_switches[user_id].active:
            self.logger.warning(f"User kill switch already active for {user_id}")
            return False
        
        self._user_switches[user_id] = KillSwitchStatus(
            scope=KillSwitchScope.USER.value,
            target_id=user_id,
            active=True,
            reason=reason,
            triggered_at=datetime.now(timezone.utc),
            released_at=None,
            triggered_by=triggered_by
        )
        
        if self.risk_engine:
            self.risk_engine.update_state(user_id, risk_level='critical')
        
        self._log_switch_event("triggered", reason, triggered_by, user_id)
        
        self.logger.warning(f"User kill switch triggered for {user_id}: {reason}")
        
        return True
    
    def release_user_kill_switch(self, user_id: str, released_by: str = "system") -> bool:
        if user_id not in self._user_switches:
            return False
        
        switch = self._user_switches[user_id]
        switch.active = False
        switch.released_at = datetime.now(timezone.utc)
        
        if self.risk_engine:
            self.risk_engine.update_state(user_id, risk_level='low')
        
        self._log_switch_event("released", "manual release", released_by, user_id)
        
        self.logger.info(f"User kill switch released for {user_id}")
        
        return True
    
    def trigger_strategy_kill_switch(self, strategy_id: str, reason: str,
                                     triggered_by: str = "system") -> bool:
        if strategy_id in self._strategy_switches and self._strategy_switches[strategy_id].active:
            return False
        
        self._strategy_switches[strategy_id] = KillSwitchStatus(
            scope=KillSwitchScope.STRATEGY.value,
            target_id=strategy_id,
            active=True,
            reason=reason,
            triggered_at=datetime.now(timezone.utc),
            released_at=None,
            triggered_by=triggered_by
        )
        
        self._log_switch_event("triggered", reason, triggered_by, f"strategy:{strategy_id}")
        
        self.logger.warning(f"Strategy kill switch triggered for {strategy_id}: {reason}")
        
        return True
    
    def release_strategy_kill_switch(self, strategy_id: str, released_by: str = "system") -> bool:
        if strategy_id not in self._strategy_switches:
            return False
        
        switch = self._strategy_switches[strategy_id]
        switch.active = False
        switch.released_at = datetime.now(timezone.utc)
        
        self._log_switch_event("released", "manual release", released_by, f"strategy:{strategy_id}")
        
        return True
    
    def is_trading_allowed(self, user_id: str, strategy_id: str = None) -> tuple[bool, str]:
        if self._global_switch and self._global_switch.active:
            return False, f"Global kill switch active: {self._global_switch.reason}"
        
        if user_id in self._user_switches:
            switch = self._user_switches[user_id]
            if switch.active:
                return False, f"User kill switch active: {switch.reason}"
        
        if strategy_id and strategy_id in self._strategy_switches:
            switch = self._strategy_switches[strategy_id]
            if switch.active:
                return False, f"Strategy kill switch active: {switch.reason}"
        
        return True, "Trading allowed"
    
    def _log_switch_event(self, action: str, reason: str, triggered_by: str, target: str) -> None:
        event = {
            'action': action,
            'reason': reason,
            'triggered_by': triggered_by,
            'target': target,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        self._switch_history.append(event)
        
        if len(self._switch_history) > 1000:
            self._switch_history = self._switch_history[-500:]
    
    def get_global_status(self) -> Optional[Dict]:
        if not self._global_switch:
            return None
        
        return {
            'active': self._global_switch.active,
            'reason': self._global_switch.reason,
            'triggered_at': self._global_switch.triggered_at.isoformat(),
            'triggered_by': self._global_switch.triggered_by,
            'released_at': self._global_switch.released_at.isoformat() if self._global_switch.released_at else None
        }
    
    def get_user_status(self, user_id: str) -> Optional[Dict]:
        if user_id not in self._user_switches:
            return None
        
        switch = self._user_switches[user_id]
        return {
            'active': switch.active,
            'reason': switch.reason,
            'triggered_at': switch.triggered_at.isoformat(),
            'triggered_by': switch.triggered_by,
            'released_at': switch.released_at.isoformat() if switch.released_at else None
        }
    
    def get_strategy_status(self, strategy_id: str) -> Optional[Dict]:
        if strategy_id not in self._strategy_switches:
            return None
        
        switch = self._strategy_switches[strategy_id]
        return {
            'active': switch.active,
            'reason': switch.reason,
            'triggered_at': switch.triggered_at.isoformat(),
            'triggered_by': switch.triggered_by,
            'released_at': switch.released_at.isoformat() if switch.released_at else None
        }
    
    def get_all_active_switches(self) -> List[Dict]:
        switches = []
        
        if self._global_switch and self._global_switch.active:
            switches.append({
                'scope': 'global',
                'target': 'global',
                'reason': self._global_switch.reason,
                'triggered_at': self._global_switch.triggered_at.isoformat()
            })
        
        for user_id, switch in self._user_switches.items():
            if switch.active:
                switches.append({
                    'scope': 'user',
                    'target': user_id,
                    'reason': switch.reason,
                    'triggered_at': switch.triggered_at.isoformat()
                })
        
        for strategy_id, switch in self._strategy_switches.items():
            if switch.active:
                switches.append({
                    'scope': 'strategy',
                    'target': strategy_id,
                    'reason': switch.reason,
                    'triggered_at': switch.triggered_at.isoformat()
                })
        
        return switches
    
    def get_switch_history(self, limit: int = 100) -> List[Dict]:
        return self._switch_history[-limit:]


kill_switch_manager = KillSwitchManager()


def get_kill_switch_manager() -> KillSwitchManager:
    return kill_switch_manager