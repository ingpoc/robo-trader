# Celery configuration for Robo Trader Job Queue
# Distributed task processing with Redis as broker and result backend

import os

# Broker settings (Redis)
broker_url = os.getenv('CELERY_BROKER_URL', 'redis://redis-cache:6379/1')

# Result backend
result_backend = os.getenv('CELERY_RESULT_BACKEND', 'redis://redis-cache:6379/2')

# Task settings
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
timezone = 'UTC'
enable_utc = True

# Worker settings
worker_prefetch_multiplier = 1
worker_max_tasks_per_child = 1000
worker_disable_rate_limits = False

# Task routing
task_routes = {
    'tasks.portfolio_tasks.*': {'queue': 'portfolio'},
    'tasks.risk_tasks.*': {'queue': 'risk'},
    'tasks.analytics_tasks.*': {'queue': 'analytics'},
    'tasks.market_data_tasks.*': {'queue': 'market_data'},
}

# Queue definitions
task_queues = {
    'celery',      # Default queue
    'portfolio',   # Portfolio-related tasks
    'risk',        # Risk management tasks
    'analytics',   # Analytics and screening
    'market_data', # Market data processing
    'critical',    # High-priority tasks
}

# Task time limits
task_time_limit = 300  # 5 minutes
task_soft_time_limit = 240  # 4 minutes

# Result expiration
result_expires = 3600  # 1 hour

# Beat scheduler settings (for periodic tasks)
beat_schedule = {
    'market-data-sync': {
        'task': 'tasks.market_data_tasks.sync_market_data',
        'schedule': 60.0,  # Every minute
        'options': {'queue': 'market_data'}
    },
    'portfolio-rebalancing-check': {
        'task': 'tasks.portfolio_tasks.check_rebalancing',
        'schedule': 300.0,  # Every 5 minutes
        'options': {'queue': 'portfolio'}
    },
    'risk-limits-monitoring': {
        'task': 'tasks.risk_tasks.monitor_limits',
        'schedule': 120.0,  # Every 2 minutes
        'options': {'queue': 'risk'}
    },
}

# Error handling
task_reject_on_worker_lost = True
task_acks_late = True

# Logging
worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
worker_task_log_format = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'