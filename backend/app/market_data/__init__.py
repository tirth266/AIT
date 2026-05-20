"""
Market Data Infrastructure
==========================
Institutional-grade market data system for Indian markets (NSE/BSE).

All sub-module imports are guarded so that missing optional modules
don't crash the application at startup.
"""

# Core models — these must exist
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

# Orderbook — OrderBookBuilder lives inside processor.py
from .orderbook.processor import OrderBookProcessor, OrderBookBuilder

# Optional submodules — guarded so startup is not broken by missing files
def _try_import(module_path, names):
    """Attempt an import; return empty dict on failure."""
    try:
        import importlib
        mod = importlib.import_module(module_path)
        return {n: getattr(mod, n) for n in names if hasattr(mod, n)}
    except (ImportError, ModuleNotFoundError):
        return {}

_pipeline_ingestion    = _try_import('app.market_data.pipeline.ingestion',     ['TickIngestionPipeline'])
_pipeline_norm         = _try_import('app.market_data.pipeline.normalization',  ['TickNormalizer'])
_pipeline_dedup        = _try_import('app.market_data.pipeline.deduplication',  ['TickDeduplicator'])
_candles_agg           = _try_import('app.market_data.candles.aggregator',      ['CandleAggregator'])
_candles_ohlcv         = _try_import('app.market_data.candles.ohlcv',           ['OHLCVCalculator'])
_symbols_master        = _try_import('app.market_data.symbols.master',          ['SymbolMasterManager'])
_symbols_validator     = _try_import('app.market_data.symbols.validator',       ['SymbolValidator'])
_session_engine        = _try_import('app.market_data.session.engine',          ['MarketSessionEngine'])
_session_calendar      = _try_import('app.market_data.session.calendar',        ['TradingCalendar'])
_history_store         = _try_import('app.market_data.history.store',           ['HistoricalDataStore'])
_history_replay        = _try_import('app.market_data.history.replay',          ['TickReplayEngine'])
_history_compress      = _try_import('app.market_data.history.compression',     ['TickCompressor'])
_streaming_redis       = _try_import('app.market_data.streaming.redis_stream',  ['RedisMarketDataStream'])
_streaming_pub         = _try_import('app.market_data.streaming.publisher',     ['DataPublisher'])
_streaming_sub         = _try_import('app.market_data.streaming.subscriber',    ['DataSubscriber'])
_quality_validator     = _try_import('app.market_data.quality.validator',       ['DataQualityValidator'])
_quality_metrics       = _try_import('app.market_data.quality.metrics',         ['QualityMetrics'])
_corporate             = _try_import('app.market_data.corporate.actions',       ['CorporateActionHandler'])
_feeds_zerodha         = _try_import('app.market_data.feeds.zerodha',           ['ZerodhaMarketDataFeed'])

TickIngestionPipeline   = _pipeline_ingestion.get('TickIngestionPipeline')
TickNormalizer          = _pipeline_norm.get('TickNormalizer')
TickDeduplicator        = _pipeline_dedup.get('TickDeduplicator')
CandleAggregator        = _candles_agg.get('CandleAggregator')
OHLCVCalculator         = _candles_ohlcv.get('OHLCVCalculator')
SymbolMasterManager     = _symbols_master.get('SymbolMasterManager')
SymbolValidator         = _symbols_validator.get('SymbolValidator')
MarketSessionEngine     = _session_engine.get('MarketSessionEngine')
TradingCalendar         = _session_calendar.get('TradingCalendar')
HistoricalDataStore     = _history_store.get('HistoricalDataStore')
TickReplayEngine        = _history_replay.get('TickReplayEngine')
TickCompressor          = _history_compress.get('TickCompressor')
RedisMarketDataStream   = _streaming_redis.get('RedisMarketDataStream')
DataPublisher           = _streaming_pub.get('DataPublisher')
DataSubscriber          = _streaming_sub.get('DataSubscriber')
DataQualityValidator    = _quality_validator.get('DataQualityValidator')
QualityMetrics          = _quality_metrics.get('QualityMetrics')
CorporateActionHandler  = _corporate.get('CorporateActionHandler')
ZerodhaMarketDataFeed   = _feeds_zerodha.get('ZerodhaMarketDataFeed')

__all__ = [
    "Tick", "OrderBook", "Candle", "SymbolMaster", "CorporateAction",
    "TradingSession", "MarketStatus", "Exchange", "InstrumentType", "CandleInterval",
    "OrderBookProcessor", "OrderBookBuilder",
    "TickIngestionPipeline", "TickNormalizer", "TickDeduplicator",
    "CandleAggregator", "OHLCVCalculator",
    "SymbolMasterManager", "SymbolValidator",
    "MarketSessionEngine", "TradingCalendar",
    "HistoricalDataStore", "TickReplayEngine", "TickCompressor",
    "RedisMarketDataStream", "DataPublisher", "DataSubscriber",
    "DataQualityValidator", "QualityMetrics",
    "CorporateActionHandler", "ZerodhaMarketDataFeed",
]