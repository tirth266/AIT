"""
Celery Application Configuration
=================================
Celery setup with Redis broker, task routes, and beat schedule.
"""

import os
from celery import Celery
from celery.schedules import crontab

celery_app = Celery(
    'trading_app',
    broker=os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/1'),
    backend=os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2'),
    include=[
        'app.celery_tasks.trading_tasks',
        'app.celery_tasks.backtest_tasks',
        'app.celery_tasks.market_tasks',
        'app.celery_tasks.maintenance_tasks'
    ]
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,

    task_routes={
        'app.celery_tasks.trading_tasks.*': {'queue': 'trading'},
        'app.celery_tasks.backtest_tasks.*': {'queue': 'backtest'},
        'app.celery_tasks.market_tasks.*': {'queue': 'market'},
        'app.celery_tasks.maintenance_tasks.*': {'queue': 'maintenance'},
    },

    task_annotations={
        'app.celery_tasks.backtest_tasks.run_backtest': {
            'rate_limit': '1/m',
            'soft_time_limit': 3600,
            'time_limit': 3900
        },
        'app.celery_tasks.trading_tasks.*': {
            'rate_limit': '10/m'
        }
    },

    beat_schedule={
        'evaluate-strategies-every-5min': {
            'task': 'app.celery_tasks.trading_tasks.evaluate_all_strategies',
            'schedule': 300.0,
            'options': {'queue': 'trading'}
        },
        'check-positions-every-1min': {
            'task': 'app.celery_tasks.trading_tasks.check_all_positions',
            'schedule': 60.0,
            'options': {'queue': 'trading'}
        },
        'fetch-candles-every-1min': {
            'task': 'app.celery_tasks.market_tasks.fetch_live_candles',
            'schedule': 60.0,
            'options': {'queue': 'market'}
        },
        'cleanup-old-data-daily': {
            'task': 'app.celery_tasks.maintenance_tasks.cleanup_old_candles',
            'schedule': crontab(hour=2, minute=0),
            'options': {'queue': 'maintenance'}
        },
        'daily-summary-evening': {
            'task': 'app.celery_tasks.maintenance_tasks.send_daily_summary',
            'schedule': crontab(hour=18, minute=0),
            'options': {'queue': 'maintenance'}
        },
        'health-check-every-5min': {
            'task': 'app.celery_tasks.maintenance_tasks.health_check',
            'schedule': 300.0,
            'options': {'queue': 'maintenance'}
        }
    },

    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    result_expires=3600,
    result_persistent=True,

    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10
)


class CeleryTask:
    """Base Celery task with error handling and logging."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        from app.logs.setup import get_logger
        logger = get_logger('celery')
        logger.error(f"Task {task_id} failed: {exc}", exc_info=einfo)

        from app.database.connection import get_db
        db = get_db()
        if db:
            db.logs.insert_one({
                'level': 'ERROR',
                'category': 'CELERY',
                'message': f"Task {task_id} failed: {exc}",
                'task_id': task_id,
                'args': str(args),
                'kwargs': str(kwargs),
                'created_at': __import__('datetime').datetime.utcnow()
            })

    def on_success(self, retval, task_id, args, kwargs):
        from app.logs.setup import get_logger
        logger = get_logger('celery')
        logger.info(f"Task {task_id} completed successfully")


if __name__ == '__main__':
    celery_app.start()