"""Celery Tasks — Trading Stub"""
from app.celery_app import celery_app
import logging

logger = logging.getLogger('trading_app')


@celery_app.task(bind=True, name='trading.schedule_strategy')
def schedule_strategy_evaluation(self, strategy_id: str) -> dict:
    """Stub strategy evaluation task."""
    logger.info(f"Strategy evaluation scheduled for {strategy_id}")
    return {'status': 'scheduled', 'strategy_id': strategy_id}
