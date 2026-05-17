"""
Pre-Trade Risk Checks
====================
Comprehensive validation of every order before execution.
"""

import logging
import asyncio
from datetime import datetime, timezone, time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class CheckResult(str, Enum):
    PASS = "pass"
    WARN = "warn"
    BLOCK = "block"


class CheckType(str, Enum):
    MARGIN = "margin"
    POSITION_SIZE = "position_size"
    ORDER_VALUE = "order_value"
    QUANTITY = "quantity"
    DAILY_TRADES = "daily_trades"
    DUPLICATE = "duplicate"
    TRADING_HOURS = "trading_hours"
    SYMBOL_RESTRICTION = "symbol_restriction"
    STRATEGY_PERMISSION = "strategy_permission"
    BROKER_VALIDATION = "broker_validation"
    CIRCUIT_BREAKER = "circuit_breaker"
    EXPOSURE_LIMIT = "exposure_limit"
    LEVERAGE_LIMIT = "leverage_limit"


@dataclass
class PreTradeCheckResult:
    check_type: str
    result: str
    message: str
    details: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class OrderData:
    user_id: str
    symbol: str
    quantity: int
    price: float
    order_type: str
    transaction_type: str
    product_type: str
    exchange: str
    strategy_id: Optional[str] = None
    trigger_price: Optional[float] = None


class PreTradeChecker:
    """
    Pre-trade risk validation engine.
    Validates every order before execution.
    """
    
    def __init__(self, risk_engine=None):
        self.logger = logging.getLogger('pre_trade_checks')
        self.risk_engine = risk_engine
        
        self._trading_hours = {
            'NSE': {'start': time(9, 15), 'end': time(15, 30)},
            'BSE': {'start': time(9, 15), 'end': time(15, 30)},
            'NFO': {'start': time(9, 15), 'end': time(15, 30)},
            'MCX': {'start': time(9, 0), 'end': time(23, 30)},
        }
        
        self._restricted_symbols: set = set()
        self._user_symbol_restrictions: Dict[str, set] = defaultdict(set)
        
        self._order_history: Dict[str, List[datetime]] = defaultdict(list)
        self._daily_trade_counts: Dict[str, int] = defaultdict(int)
        
        self._check_results_cache: List[PreTradeCheckResult] = []
    
    def add_restricted_symbol(self, symbol: str) -> None:
        self._restricted_symbols.add(symbol.upper())
    
    def remove_restricted_symbol(self, symbol: str) -> None:
        self._restricted_symbols.discard(symbol.upper())
    
    def restrict_symbol_for_user(self, user_id: str, symbol: str) -> None:
        self._user_symbol_restrictions[user_id].add(symbol.upper())
    
    def get_remaining_trades(self, user_id: str, max_trades: int = 50) -> int:
        return max(0, max_trades - self._daily_trade_counts.get(user_id, 0))
    
    def increment_trade_count(self, user_id: str) -> None:
        self._daily_trade_counts[user_id] += 1
    
    def reset_daily_trade_counts(self) -> None:
        self._daily_trade_counts.clear()
    
    async def validate_order(self, order: OrderData, context: Dict) -> tuple[bool, List[PreTradeCheckResult]]:
        results = []
        blocked = False
        
        if not self.risk_engine:
            return True, results
        
        allowed, reason = self.risk_engine.is_trading_allowed(order.user_id)
        if not allowed:
            results.append(PreTradeCheckResult(
                check_type=CheckType.BROKER_VALIDATION.value,
                result=CheckResult.BLOCK.value,
                message=reason,
                details={'reason': reason}
            ))
            blocked = True
            return blocked, results
        
        checks = [
            self._check_margin_availability,
            self._check_position_size,
            self._check_order_value,
            self._check_quantity,
            self._check_daily_trade_limit,
            self._check_trading_hours,
            self._check_symbol_restriction,
            self._check_exposure_limit,
            self._check_leverage_limit,
            self._check_circuit_breaker,
        ]
        
        for check in checks:
            try:
                result = await check(order, context)
                results.append(result)
                
                if result.result == CheckResult.BLOCK.value:
                    blocked = True
                    self.logger.warning(
                        f"BLOCK: {result.check_type} | User: {order.user_id} | "
                        f"Symbol: {order.symbol} | {result.message}"
                    )
                elif result.result == CheckResult.WARN.value:
                    self.logger.info(f"WARN: {result.check_type} | {result.message}")
                    
            except Exception as e:
                self.logger.error(f"Check error {check.__name__}: {e}")
        
        self._cache_result(results)
        
        return not blocked, results
    
    async def _check_margin_availability(self, order: OrderData, context: Dict) -> PreTradeCheckResult:
        margin_info = context.get('margin_info')
        
        if not margin_info:
            return PreTradeCheckResult(
                check_type=CheckType.MARGIN.value,
                result=CheckResult.WARN.value,
                message="Margin information not available"
            )
        
        required_margin = self._calculate_required_margin(order)
        
        if required_margin <= 0:
            return PreTradeCheckResult(
                check_type=CheckType.MARGIN.value,
                result=CheckResult.PASS.value,
                message="No margin required"
            )
        
        available = margin_info.get('available_margin', 0)
        
        if available < required_margin:
            return PreTradeCheckResult(
                check_type=CheckType.MARGIN.value,
                result=CheckResult.BLOCK.value,
                message=f"Insufficient margin: required {required_margin:.2f}, available {available:.2f}",
                details={'required': required_margin, 'available': available}
            )
        
        utilization = ((margin_info.get('used_margin', 0) + required_margin) / 
                      margin_info.get('total_margin', 1)) * 100
        
        if utilization > 90:
            return PreTradeCheckResult(
                check_type=CheckType.MARGIN.value,
                result=CheckResult.WARN.value,
                message=f"Margin utilization will be {utilization:.1f}%",
                details={'utilization': utilization}
            )
        
        return PreTradeCheckResult(
            check_type=CheckType.MARGIN.value,
            result=CheckResult.PASS.value,
            message="Margin check passed"
        )
    
    def _calculate_required_margin(self, order: OrderData) -> float:
        product_margins = {
            'MIS': 0.05,
            'CNC': 1.0,
            'NRML': 0.15,
            'CO': 0.05,
        }
        
        margin_percent = product_margins.get(order.product_type, 0.1)
        order_value = order.quantity * (order.price or order.trigger_price or 0)
        
        leverage = 20 if order.product_type == 'MIS' else 1
        
        return (order_value * margin_percent) / leverage
    
    async def _check_position_size(self, order: OrderData, context: Dict) -> PreTradeCheckResult:
        config = self.risk_engine.get_config(order.user_id)
        
        open_positions = context.get('open_positions', [])
        
        symbol = order.symbol.upper()
        current_position_value = 0
        
        for pos in open_positions:
            if pos.get('symbol', '').upper() == symbol:
                current_position_value += pos.get('quantity', 0) * pos.get('average_price', 0)
        
        order_value = order.quantity * (order.price or 0)
        total_value = current_position_value + order_value
        
        if total_value > config.max_position_value:
            return PreTradeCheckResult(
                check_type=CheckType.POSITION_SIZE.value,
                result=CheckResult.BLOCK.value,
                message=f"Position value {total_value:.2f} exceeds limit {config.max_position_value:.2f}",
                details={'current': current_position_value, 'order': order_value, 'limit': config.max_position_value}
            )
        
        return PreTradeCheckResult(
            check_type=CheckType.POSITION_SIZE.value,
            result=CheckResult.PASS.value,
            message="Position size check passed"
        )
    
    async def _check_order_value(self, order: OrderData, context: Dict) -> PreTradeCheckResult:
        config = self.risk_engine.get_config(order.user_id)
        
        order_value = order.quantity * (order.price or 0)
        
        if order_value > config.max_order_value:
            return PreTradeCheckResult(
                check_type=CheckType.ORDER_VALUE.value,
                result=CheckResult.BLOCK.value,
                message=f"Order value {order_value:.2f} exceeds limit {config.max_order_value:.2f}",
                details={'order_value': order_value, 'limit': config.max_order_value}
            )
        
        return PreTradeCheckResult(
            check_type=CheckType.ORDER_VALUE.value,
            result=CheckResult.PASS.value,
            message="Order value check passed"
        )
    
    async def _check_quantity(self, order: OrderData, context: Dict) -> PreTradeCheckResult:
        min_quantity = 1
        max_quantity = 10000
        
        if order.quantity < min_quantity:
            return PreTradeCheckResult(
                check_type=CheckType.QUANTITY.value,
                result=CheckResult.BLOCK.value,
                message=f"Quantity {order.quantity} below minimum {min_quantity}",
                details={'quantity': order.quantity, 'min': min_quantity}
            )
        
        if order.quantity > max_quantity:
            return PreTradeCheckResult(
                check_type=CheckType.QUANTITY.value,
                result=CheckResult.BLOCK.value,
                message=f"Quantity {order.quantity} exceeds maximum {max_quantity}",
                details={'quantity': order.quantity, 'max': max_quantity}
            )
        
        lot_sizes = {'NSE': 1, 'BSE': 1, 'NFO': 1, 'MCX': 1}
        lot_size = lot_sizes.get(order.exchange, 1)
        
        if order.quantity % lot_size != 0:
            return PreTradeCheckResult(
                check_type=CheckType.QUANTITY.value,
                result=CheckResult.BLOCK.value,
                message=f"Quantity must be in multiples of {lot_size}",
                details={'quantity': order.quantity, 'lot_size': lot_size}
            )
        
        return PreTradeCheckResult(
            check_type=CheckType.QUANTITY.value,
            result=CheckResult.PASS.value,
            message="Quantity check passed"
        )
    
    async def _check_daily_trade_limit(self, order: OrderData, context: Dict) -> PreTradeCheckResult:
        max_daily_trades = context.get('max_daily_trades', 50)
        current_count = self._daily_trade_counts.get(order.user_id, 0)
        
        if current_count >= max_daily_trades:
            return PreTradeCheckResult(
                check_type=CheckType.DAILY_TRADES.value,
                result=CheckResult.BLOCK.value,
                message=f"Daily trade limit ({max_daily_trades}) reached",
                details={'current': current_count, 'limit': max_daily_trades}
            )
        
        remaining = max_daily_trades - current_count
        if remaining <= 5:
            return PreTradeCheckResult(
                check_type=CheckType.DAILY_TRADES.value,
                result=CheckResult.WARN.value,
                message=f"Only {remaining} trades remaining today",
                details={'remaining': remaining}
            )
        
        return PreTradeCheckResult(
            check_type=CheckType.DAILY_TRADES.value,
            result=CheckResult.PASS.value,
            message="Daily trade check passed"
        )
    
    async def _check_trading_hours(self, order: OrderData, context: Dict) -> PreTradeCheckResult:
        exchange = order.exchange
        hours = self._trading_hours.get(exchange)
        
        if not hours:
            return PreTradeCheckResult(
                check_type=CheckType.TRADING_HOURS.value,
                result=CheckResult.PASS.value,
                message="Exchange hours not configured"
            )
        
        now = datetime.now(timezone.utc).astimezone().time()
        
        if now < hours['start'] or now > hours['end']:
            return PreTradeCheckResult(
                check_type=CheckType.TRADING_HOURS.value,
                result=CheckResult.BLOCK.value,
                message=f"Trading hours closed for {exchange} ({hours['start']}-{hours['end']})",
                details={'current_time': now.isoformat(), 'trading_start': hours['start'].isoformat(), 
                         'trading_end': hours['end'].isoformat()}
            )
        
        return PreTradeCheckResult(
            check_type=CheckType.TRADING_HOURS.value,
            result=CheckResult.PASS.value,
            message="Within trading hours"
        )
    
    async def _check_symbol_restriction(self, order: OrderData, context: Dict) -> PreTradeCheckResult:
        symbol = order.symbol.upper()
        
        if symbol in self._restricted_symbols:
            return PreTradeCheckResult(
                check_type=CheckType.SYMBOL_RESTRICTION.value,
                result=CheckResult.BLOCK.value,
                message=f"Symbol {symbol} is restricted globally",
                details={'symbol': symbol}
            )
        
        user_restrictions = self._user_symbol_restrictions.get(order.user_id, set())
        if symbol in user_restrictions:
            return PreTradeCheckResult(
                check_type=CheckType.SYMBOL_RESTRICTION.value,
                result=CheckResult.BLOCK.value,
                message=f"Symbol {symbol} is restricted for this user",
                details={'symbol': symbol}
            )
        
        return PreTradeCheckResult(
            check_type=CheckType.SYMBOL_RESTRICTION.value,
            result=CheckResult.PASS.value,
            message="Symbol allowed"
        )
    
    async def _check_exposure_limit(self, order: OrderData, context: Dict) -> PreTradeCheckResult:
        config = self.risk_engine.get_config(order.user_id)
        
        total_exposure = context.get('total_exposure', 0)
        account_value = context.get('account_value', 100000)
        
        order_value = order.quantity * (order.price or 0)
        new_exposure = total_exposure + order_value
        
        exposure_percent = (new_exposure / account_value * 100) if account_value > 0 else 0
        
        if exposure_percent > config.max_exposure_percent:
            return PreTradeCheckResult(
                check_type=CheckType.EXPOSURE_LIMIT.value,
                result=CheckResult.BLOCK.value,
                message=f"Exposure {exposure_percent:.1f}% exceeds limit {config.max_exposure_percent}%",
                details={'current': total_exposure, 'new': new_exposure, 'percent': exposure_percent}
            )
        
        return PreTradeCheckResult(
            check_type=CheckType.EXPOSURE_LIMIT.value,
            result=CheckResult.PASS.value,
            message="Exposure check passed"
        )
    
    async def _check_leverage_limit(self, order: OrderData, context: Dict) -> PreTradeCheckResult:
        config = self.risk_engine.get_config(order.user_id)
        
        order_value = order.quantity * (order.price or 0)
        margin_required = self._calculate_required_margin(order)
        
        if margin_required > 0:
            leverage = order_value / margin_required
            
            if leverage > config.max_leverage:
                return PreTradeCheckResult(
                    check_type=CheckType.LEVERAGE_LIMIT.value,
                    result=CheckResult.BLOCK.value,
                    message=f"Leverage {leverage:.1f}x exceeds limit {config.max_leverage}x",
                    details={'leverage': leverage, 'limit': config.max_leverage}
                )
        
        return PreTradeCheckResult(
            check_type=CheckType.LEVERAGE_LIMIT.value,
            result=CheckResult.PASS.value,
            message="Leverage check passed"
        )
    
    async def _check_circuit_breaker(self, order: OrderData, context: Dict) -> PreTradeCheckResult:
        if not self.risk_engine:
            return PreTradeCheckResult(
                check_type=CheckType.CIRCUIT_BREAKER.value,
                result=CheckResult.PASS.value,
                message="No risk engine"
            )
        
        circuit_breaker = self.risk_engine.get_component('circuit_breaker')
        if not circuit_breaker:
            return PreTradeCheckResult(
                check_type=CheckType.CIRCUIT_BREAKER.value,
                result=CheckResult.PASS.value,
                message="No circuit breaker configured"
            )
        
        is_triggered, reason = circuit_breaker.is_triggered(order.symbol)
        
        if is_triggered:
            return PreTradeCheckResult(
                check_type=CheckType.CIRCUIT_BREAKER.value,
                result=CheckResult.BLOCK.value,
                message=f"Circuit breaker triggered: {reason}",
                details={'symbol': order.symbol, 'reason': reason}
            )
        
        return PreTradeCheckResult(
            check_type=CheckType.CIRCUIT_BREAKER.value,
            result=CheckResult.PASS.value,
            message="Circuit breaker check passed"
        )
    
    def _cache_result(self, results: List[PreTradeCheckResult]) -> None:
        self._check_results_cache.extend(results)
        
        if len(self._check_results_cache) > 10000:
            self._check_results_cache = self._check_results_cache[-5000:]
    
    def get_recent_checks(self, user_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
        results = self._check_results_cache
        
        if user_id:
            results = [r for r in results if r.details.get('user_id') == user_id]
        
        return [
            {
                'check_type': r.check_type,
                'result': r.result,
                'message': r.message,
                'details': r.details,
                'timestamp': r.timestamp.isoformat()
            }
            for r in results[-limit:]
        ]


pre_trade_checker = PreTradeChecker()


def get_pre_trade_checker() -> PreTradeChecker:
    return pre_trade_checker