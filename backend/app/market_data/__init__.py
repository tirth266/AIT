"""
Market Data Infrastructure
==========================
Institutional-grade market data system for Indian markets (NSE/BSE).

Architecture Overview:
- Tick ingestion pipeline with normalization
- L2 orderbook processing
- Redis streaming for real-time distribution
- Kafka preparation for historical storage
- Symbol master management
- Market session and trading calendar
- Corporate actions handling
- Historical replay engine
"""

from .core.models import (
    Tick,
    OrderBook,
    Candle,
    SymbolMaster,
    CorporateAction,
    TradingSession,
    MarketStatus,
)
from .core.types import Exchange, InstrumentType, CandleInterval
from .pipeline.ingestion import TickIngestionPipeline
from .pipeline.normalization import TickNormalizer
from .pipeline.deduplication import TickDeduplicator
from .orderbook.processor import OrderBookProcessor
from .orderbook.book_builder import OrderBookBuilder
from .candles.aggregator import CandleAggregator
from .candles.ohlcv import OHLCVCalculator
from .symbols.master import SymbolMasterManager
from .symbols.validator import SymbolValidator
from .session.engine import MarketSessionEngine
from .session.calendar import TradingCalendar
from .history.store import HistoricalDataStore
from .history.replay import TickReplayEngine
from .history.compression import TickCompressor
from .streaming.redis_stream import RedisMarketDataStream
from .streaming.publisher import DataPublisher
from .streaming.subscriber import DataSubscriber
from .quality.validator import DataQualityValidator
from .quality.metrics import QualityMetrics
from .corporate.actions import CorporateActionHandler
from .feeds.zerodha import ZerodhaMarketDataFeed

__all__ = [
    "Tick",
    "OrderBook",
    "Candle",
    "SymbolMaster",
    "CorporateAction",
    "TradingSession",
    "MarketStatus",
    "Exchange",
    "InstrumentType",
    "CandleInterval",
    "TickIngestionPipeline",
    "TickNormalizer",
    "TickDeduplicator",
    "OrderBookProcessor",
    "OrderBookBuilder",
    "CandleAggregator",
    "OHLCVCalculator",
    "SymbolMasterManager",
    "SymbolValidator",
    "MarketSessionEngine",
    "TradingCalendar",
    "HistoricalDataStore",
    "TickReplayEngine",
    "TickCompressor",
    "RedisMarketDataStream",
    "DataPublisher",
    "DataSubscriber",
    "DataQualityValidator",
    "QualityMetrics",
    "CorporateActionHandler",
    "ZerodhaMarketDataFeed",
]