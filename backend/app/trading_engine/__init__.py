"""
Trading Engine
==============
Institutional-grade trading engine for Indian stock markets.
"""

from .engine import (
    TradingEngine,
    Order,
    Position,
    Trade,
    OrderStatus,
    OrderType,
    TransactionType,
    ProductType,
    Exchange,
    TradingMode,
    get_trading_engine
)

from .order_manager import (
    OrderManager,
    OrderValidator,
    get_order_manager
)

from .execution_engine import (
    ExecutionEngine,
    ExecutionQueue,
    SlippageModel,
    FillEngine,
    RetryManager,
    get_execution_engine
)

from .position_manager import (
    PositionManager,
    get_position_manager
)

from .pnl_engine import (
    PnLEngine,
    get_pnl_engine
)

from .margin_engine import (
    MarginEngine,
    MarginInfo,
    get_margin_engine
)

from .portfolio_manager import (
    PortfolioManager,
    get_portfolio_manager
)

from .risk.pre_trade_risk import (
    PreTradeRiskEngine,
    RiskCheckResult,
    RiskProfile,
    RiskAction,
    RiskCheckType,
    get_pre_trade_risk_engine
)

from .paper.paper_exchange import (
    PaperExchange,
    MarketDepth,
    ExchangeStatus,
    get_paper_exchange
)

from .reconciliation.trade_reconciliation import (
    TradeReconciliation,
    ReconciliationResult,
    ExecutionLog,
    get_trade_reconciliation,
    get_execution_log
)


__all__ = [
    'TradingEngine',
    'Order',
    'Position',
    'Trade',
    'OrderStatus',
    'OrderType',
    'TransactionType',
    'ProductType',
    'Exchange',
    'TradingMode',
    'get_trading_engine',
    
    'OrderManager',
    'OrderValidator',
    'get_order_manager',
    
    'ExecutionEngine',
    'ExecutionQueue',
    'SlippageModel',
    'FillEngine',
    'RetryManager',
    'get_execution_engine',
    
    'PositionManager',
    'get_position_manager',
    
    'PnLEngine',
    'get_pnl_engine',
    
    'MarginEngine',
    'MarginInfo',
    'get_margin_engine',
    
    'PortfolioManager',
    'get_portfolio_manager',
    
    'PreTradeRiskEngine',
    'RiskCheckResult',
    'RiskProfile',
    'RiskAction',
    'RiskCheckType',
    'get_pre_trade_risk_engine',
    
    'PaperExchange',
    'MarketDepth',
    'ExchangeStatus',
    'get_paper_exchange',
    
    'TradeReconciliation',
    'ReconciliationResult',
    'ExecutionLog',
    'get_trade_reconciliation',
    'get_execution_log',
]


def init_trading_engine():
    """Initialize the trading engine with all components."""
    engine = get_trading_engine()
    engine.start()
    
    get_order_manager()
    get_execution_engine()
    get_position_manager()
    get_pnl_engine()
    get_margin_engine()
    get_portfolio_manager()
    get_pre_trade_risk_engine()
    get_paper_exchange()
    
    return engine


def get_trading_engine_status() -> dict:
    """Get status of all trading engine components."""
    engine = get_trading_engine()
    return {
        'orders_count': len(engine.orders),
        'positions_count': len(engine.positions),
        'trades_count': len(engine.trades),
        'market_prices_count': len(engine._market_prices),
        'running': engine._running
    }