"""
Backtest Metrics
================
Performance metrics calculation for backtests.
"""

from typing import List, Dict
import numpy as np


def calculate_metrics(trades: List[Dict], initial_capital: float) -> Dict:
    """
    Calculate comprehensive performance metrics.

    Args:
        trades: List of trade dicts
        initial_capital: Initial capital

    Returns:
        Dict of performance metrics
    """
    if not trades:
        return {}

    total_trades = len(trades)
    winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
    losing_trades = [t for t in trades if t.get('pnl', 0) <= 0]

    total_pnl = sum(t.get('pnl', 0) for t in trades)

    win_count = len(winning_trades)
    loss_count = len(losing_trades)

    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

    avg_pnl = total_pnl / total_trades if total_trades > 0 else 0

    avg_win = sum(t.get('pnl', 0) for t in winning_trades) / win_count if win_count > 0 else 0
    avg_loss = sum(t.get('pnl', 0) for t in losing_trades) / loss_count if loss_count > 0 else 0

    profit_factor = 0
    if avg_loss != 0:
        profit_factor = abs((avg_win * win_count) / (avg_loss * loss_count))

    expectancy = (win_rate / 100 * avg_win) - ((100 - win_rate) / 100 * abs(avg_loss))

    final_capital = initial_capital + total_pnl
    total_return_percent = (total_pnl / initial_capital * 100) if initial_capital > 0 else 0

    return {
        'total_trades': total_trades,
        'winning_trades': win_count,
        'losing_trades': loss_count,
        'win_rate': round(win_rate, 2),
        'total_pnl': round(total_pnl, 2),
        'avg_pnl': round(avg_pnl, 2),
        'avg_win': round(avg_win, 2),
        'avg_loss': round(avg_loss, 2),
        'profit_factor': round(profit_factor, 2),
        'expectancy': round(expectancy, 2),
        'initial_capital': initial_capital,
        'final_capital': round(final_capital, 2),
        'total_return_percent': round(total_return_percent, 2)
    }


def calculate_drawdown(equity_curve: List[float]) -> Dict:
    """
    Calculate drawdown metrics.

    Args:
        equity_curve: List of equity values

    Returns:
        Dict with drawdown metrics
    """
    if not equity_curve:
        return {}

    equity = np.array(equity_curve)
    running_max = np.maximum.accumulate(equity)
    drawdowns = running_max - equity

    max_drawdown = np.max(drawdowns)
    max_drawdown_percent = (max_drawdown / running_max[np.argmax(drawdowns)] * 100) if running_max[np.argmax(drawdowns)] > 0 else 0

    in_drawdown = drawdowns > 0
    drawdown_periods = []
    start = None

    for i, in_dd in enumerate(in_drawdown):
        if in_dd and start is None:
            start = i
        elif not in_dd and start is not None:
            drawdown_periods.append(i - start)
            start = None

    avg_drawdown_duration = np.mean(drawdown_periods) if drawdown_periods else 0

    return {
        'max_drawdown': round(max_drawdown, 2),
        'max_drawdown_percent': round(max_drawdown_percent, 2),
        'avg_drawdown_duration': round(avg_drawdown_duration, 1)
    }


def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.06) -> float:
    """
    Calculate Sharpe ratio.

    Args:
        returns: List of returns
        risk_free_rate: Risk-free rate (annual)

    Returns:
        Sharpe ratio
    """
    if not returns or len(returns) < 2:
        return 0.0

    returns_arr = np.array(returns)
    avg_return = np.mean(returns_arr)
    std_return = np.std(returns_arr)

    if std_return == 0:
        return 0.0

    sharpe = (avg_return - risk_free_rate / 252) / std_return * np.sqrt(252)

    return round(sharpe, 2)


def calculate_sortino_ratio(returns: List[float], risk_free_rate: float = 0.06) -> float:
    """
    Calculate Sortino ratio.

    Args:
        returns: List of returns
        risk_free_rate: Risk-free rate (annual)

    Returns:
        Sortino ratio
    """
    if not returns or len(returns) < 2:
        return 0.0

    returns_arr = np.array(returns)
    avg_return = np.mean(returns_arr)
    downside_returns = returns_arr[returns_arr < 0]

    if len(downside_returns) == 0:
        return 0.0

    downside_std = np.std(downside_returns)

    if downside_std == 0:
        return 0.0

    sortino = (avg_return - risk_free_rate / 252) / downside_std * np.sqrt(252)

    return round(sortino, 2)


def calculate_calmar_ratio(total_return: float, max_drawdown: float) -> float:
    """
    Calculate Calmar ratio.

    Args:
        total_return: Total return
        max_drawdown: Maximum drawdown

    Returns:
        Calmar ratio
    """
    if max_drawdown == 0:
        return 0.0

    return round(total_return / max_drawdown, 2)


def generate_performance_report(
    trades: List[Dict],
    equity_curve: List[float],
    initial_capital: float
) -> Dict:
    """
    Generate comprehensive performance report.

    Args:
        trades: List of trades
        equity_curve: List of equity values
        initial_capital: Initial capital

    Returns:
        Complete performance report
    """
    metrics = calculate_metrics(trades, initial_capital)

    drawdown_metrics = calculate_drawdown(equity_curve)

    returns = []
    for i in range(1, len(equity_curve)):
        ret = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
        returns.append(ret)

    sharpe = calculate_sharpe_ratio(returns)
    sortino = calculate_sortino_ratio(returns)
    calmar = calculate_calmar_ratio(metrics.get('total_return', 0), drawdown_metrics.get('max_drawdown', 1))

    winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
    losing_trades = [t for t in trades if t.get('pnl', 0) <= 0]

    longest_win_streak = calculate_streak(winning_trades)
    longest_loss_streak = calculate_streak(losing_trades)

    return {
        **metrics,
        **drawdown_metrics,
        'sharpe_ratio': sharpe,
        'sortino_ratio': sortino,
        'calmar_ratio': calmar,
        'longest_win_streak': longest_win_streak,
        'longest_loss_streak': longest_loss_streak
    }


def calculate_streak(trades: List[Dict]) -> int:
    """Calculate longest winning/losing streak."""
    if not trades:
        return 0

    max_streak = 1
    current_streak = 1

    for i in range(1, len(trades)):
        if (trades[i].get('pnl', 0) > 0) == (trades[i-1].get('pnl', 0) > 0):
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 1

    return max_streak