"""
Backtest Engine
===============
Historical strategy testing engine.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from app.database.connection import get_db
from ..indicators.registry import IndicatorRegistry
from ..strategies.registry import StrategyRegistry

logger = logging.getLogger('backtest_engine')


@dataclass
class BacktestTrade:
    entry_date: datetime
    exit_date: datetime
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    quantity: int
    pnl: float
    pnl_percent: float
    holding_period: int


@dataclass
class BacktestResult:
    strategy_id: str
    symbol: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_return: float
    total_return_percent: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    max_drawdown: float
    max_drawdown_percent: float
    sharpe_ratio: float
    trades: List[BacktestTrade] = field(default_factory=list)
    daily_equity: List[Dict] = field(default_factory=list)


class BacktestEngine:
    """
    Backtesting engine for strategies.
    """

    def __init__(self):
        self.indicators = IndicatorRegistry()
        self.strategies = StrategyRegistry()

    async def run_backtest(
        self,
        strategy_config: Dict,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 100000,
        timeframe: str = '1d'
    ) -> Optional[BacktestResult]:
        """
        Run a backtest.

        Args:
            strategy_config: Strategy configuration
            symbol: Trading symbol
            start_date: Backtest start date
            end_date: Backtest end date
            initial_capital: Initial capital
            timeframe: Timeframe for candles

        Returns:
            BacktestResult object
        """
        logger.info(f"Starting backtest: {symbol} from {start_date} to {end_date}")

        candles = await self._get_historical_data(symbol, start_date, end_date, timeframe)

        if not candles or len(candles) < 100:
            logger.error("Insufficient historical data")
            return None

        strategy_type = strategy_config.get('strategy_type', 'ema_crossover')
        strategy_params = strategy_config.get('parameters', {})

        strategy = self.strategies.get(strategy_type)
        if not strategy:
            logger.error(f"Unknown strategy: {strategy_type}")
            return None

        trades = []
        capital = initial_capital
        position = None
        equity_curve = [{'date': start_date, 'equity': initial_capital}]

        for i in range(50, len(candles)):
            current_candles = candles[:i+1]
            current_bar = current_candles[-1]
            current_date = current_bar.get('timestamp')

            signal = await strategy.generate(current_candles, strategy_params, symbol)

            if signal and signal.get('action') != 'HOLD' and not position:
                position = {
                    'side': signal['action'],
                    'entry_price': signal['entry_price'],
                    'entry_date': current_date,
                    'quantity': self._calculate_quantity(signal['entry_price'], capital, strategy_config.get('risk_settings', {}))
                }

                logger.info(f"Entry: {signal['action']} @ {signal['entry_price']} on {current_date}")

            if position:
                current_price = current_bar.get('close', 0)
                sl = strategy_config.get('risk_settings', {}).get('stop_loss_percent', 2) / 100
                tp = strategy_config.get('risk_settings', {}).get('target_percent', 4) / 100

                pnl_pct = 0
                if position['side'] == 'BUY':
                    pnl_pct = (current_price - position['entry_price']) / position['entry_price']
                else:
                    pnl_pct = (position['entry_price'] - current_price) / position['entry_price']

                exited = False

                if (position['side'] == 'BUY' and current_price <= position['entry_price'] * (1 - sl)) or \
                   (position['side'] == 'SELL' and current_price >= position['entry_price'] * (1 + sl)):
                    exit_reason = 'SL'
                    exited = True
                elif (position['side'] == 'BUY' and current_price >= position['entry_price'] * (1 + tp)) or \
                     (position['side'] == 'SELL' and current_price <= position['entry_price'] * (1 - tp)):
                    exit_reason = 'TP'
                    exited = True
                elif i - candles.index(position['entry_date']) > 50:
                    exit_reason = 'TIME'
                    exited = True

                if exited:
                    exit_price = current_price
                    if position['side'] == 'BUY':
                        pnl = (exit_price - position['entry_price']) * position['quantity']
                    else:
                        pnl = (position['entry_price'] - exit_price) * position['quantity']

                    pnl_percent = pnl / (position['entry_price'] * position['quantity']) * 100

                    trade = BacktestTrade(
                        entry_date=position['entry_date'],
                        exit_date=current_date,
                        symbol=symbol,
                        side=position['side'],
                        entry_price=position['entry_price'],
                        exit_price=exit_price,
                        quantity=position['quantity'],
                        pnl=pnl,
                        pnl_percent=pnl_percent,
                        holding_period=i - candles.index(position['entry_date'])
                    )

                    trades.append(trade)
                    capital += pnl

                    logger.info(f"Exit: {exit_reason} @ {exit_price}, P&L: {pnl:.2f}")

                    position = None

            equity_curve.append({'date': current_date, 'equity': capital})

        final_capital = capital

        result = self._calculate_results(
            strategy_config.get('_id', 'unknown'),
            symbol,
            start_date,
            end_date,
            initial_capital,
            final_capital,
            trades,
            equity_curve
        )

        logger.info(f"Backtest complete: {result.total_trades} trades, Return: {result.total_return_percent:.2f}%")

        return result

    def _calculate_quantity(
        self,
        price: float,
        capital: float,
        risk_settings: Dict
    ) -> int:
        """Calculate position quantity."""
        position_pct = risk_settings.get('position_size_percent', 10) / 100
        return int((capital * position_pct) / price)

    async def _get_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str
    ) -> List[Dict]:
        """Get historical candle data."""
        db = get_db()
        if not db:
            return self._generate_sample_data(symbol, start_date, end_date)

        try:
            candles = list(db.candles.find({
                'symbol': symbol,
                'timestamp': {'$gte': start_date, '$lte': end_date}
            }).sort('timestamp', 1))

            if candles:
                return candles

        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")

        return self._generate_sample_data(symbol, start_date, end_date)

    def _generate_sample_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """Generate sample data for backtesting."""
        import random
        import numpy as np

        days = (end_date - start_date).days
        num_candles = days * 78

        base_price = {
            'RELIANCE': 2500, 'TCS': 3500, 'INFY': 1500,
            'HDFCBANK': 1600, 'SBIN': 600, 'BHARTIARTL': 800
        }.get(symbol, 1000)

        prices = [base_price]
        for _ in range(num_candles):
            change = random.uniform(-2, 2)
            new_price = prices[-1] * (1 + change / 100)
            prices.append(new_price)

        candles = []
        current_date = start_date

        for price in prices:
            high = price * (1 + random.uniform(0, 1) / 100)
            low = price * (1 - random.uniform(0, 1) / 100)
            volume = random.randint(100000, 1000000)

            candles.append({
                'symbol': symbol,
                'timestamp': current_date.isoformat(),
                'open': round(price * (1 + random.uniform(-0.2, 0.2) / 100), 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(price, 2),
                'volume': volume
            })

            current_date += timedelta(minutes=5)

        return candles

    def _calculate_results(
        self,
        strategy_id: str,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float,
        final_capital: float,
        trades: List[BacktestTrade],
        equity_curve: List[Dict]
    ) -> BacktestResult:
        """Calculate backtest metrics."""
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.pnl > 0)
        losing_trades = total_trades - winning_trades

        total_return = final_capital - initial_capital
        total_return_percent = (total_return / initial_capital) * 100

        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        wins = [t.pnl for t in trades if t.pnl > 0]
        losses = [abs(t.pnl) for t in trades if t.pnl < 0]

        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0

        profit_factor = (avg_win * winning_trades) / (avg_loss * losing_trades) if (avg_loss * losing_trades) > 0 else 0

        equity_values = [e['equity'] for e in equity_curve]
        peak = equity_values[0]
        max_drawdown = 0

        for value in equity_values:
            if value > peak:
                peak = value
            drawdown = peak - value
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        max_drawdown_percent = (max_drawdown / peak * 100) if peak > 0 else 0

        returns = []
        for i in range(1, len(equity_curve)):
            ret = (equity_curve[i]['equity'] - equity_curve[i-1]['equity']) / equity_curve[i-1]['equity']
            returns.append(ret)

        sharpe_ratio = 0
        if returns:
            avg_return = sum(returns) / len(returns)
            std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
            if std_return > 0:
                sharpe_ratio = (avg_return * 252) / std_return

        return BacktestResult(
            strategy_id=strategy_id,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            total_return_percent=total_return_percent,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            max_drawdown_percent=max_drawdown_percent,
            sharpe_ratio=sharpe_ratio,
            trades=trades,
            daily_equity=equity_curve
        )


_backtest_engine: Optional[BacktestEngine] = None


def get_backtest_engine() -> BacktestEngine:
    """Get the global backtest engine instance."""
    global _backtest_engine
    if _backtest_engine is None:
        _backtest_engine = BacktestEngine()
    return _backtest_engine