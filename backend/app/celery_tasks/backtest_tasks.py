"""Celery Tasks — Backtest Stub"""
from app.celery_app import celery_app
import logging

logger = logging.getLogger('trading_app')


@celery_app.task(bind=True, name='backtest.run')
def run_backtest(self, strategy_id: str, config: dict) -> dict:
    """Stub backtest task."""
    logger.info(f"Backtest task invoked for strategy {strategy_id}")
    return {'status': 'completed', 'strategy_id': strategy_id, 'results': {}}
