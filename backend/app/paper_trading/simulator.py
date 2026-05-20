"""
Paper Trading Simulator — Stub
==============================
Minimal stub so the app can boot without a full paper trading engine.
Replace with a real implementation when ready.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger('trading_app')


class PaperTradingSimulator:
    """Stub paper trading simulator."""

    def __init__(self, initial_balance: float = 100000.0):
        self.balance = initial_balance
        self.positions = {}
        self.trades = []
        logger.info(f"PaperTradingSimulator initialized with balance: {initial_balance}")

    def execute_order(self, symbol: str, action: str, quantity: int, price: float, **kwargs) -> dict:
        cost = quantity * price
        if action.upper() == 'BUY':
            if cost > self.balance:
                return {'success': False, 'error': 'Insufficient balance'}
            self.balance -= cost
            self.positions[symbol] = self.positions.get(symbol, 0) + quantity
        elif action.upper() == 'SELL':
            held = self.positions.get(symbol, 0)
            if quantity > held:
                return {'success': False, 'error': 'Insufficient position'}
            self.positions[symbol] = held - quantity
            self.balance += quantity * price

        trade = {
            'id': f"PT-{len(self.trades)+1:06d}",
            'symbol': symbol,
            'action': action.upper(),
            'quantity': quantity,
            'price': price,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }
        self.trades.append(trade)
        return {'success': True, 'trade': trade}

    def get_balance(self) -> float:
        return self.balance

    def get_positions(self) -> dict:
        return dict(self.positions)

    def get_trades(self, limit: int = 100) -> list:
        return self.trades[-limit:]


_simulator: PaperTradingSimulator | None = None


def get_paper_simulator() -> PaperTradingSimulator:
    global _simulator
    if _simulator is None:
        import os
        balance = float(os.environ.get('PAPER_BALANCE', '100000'))
        _simulator = PaperTradingSimulator(initial_balance=balance)
    return _simulator
