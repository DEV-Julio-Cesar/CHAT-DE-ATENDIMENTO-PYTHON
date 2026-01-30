"""
Celery worker principal para processamento assíncrono
"""
from celery import Celery
from celery.schedules import crontab
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Configurar Celery
celery_app = Celery(
    "isp_support",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.whatsapp_tasks",
        "app.workers.campaign_tasks", 
        "app.workers.ai_tasks",
        "app.workers.maintenance_tasks"
    ]
)

# Configurações do Celery
celery_app.conf.update(
    # Timezone
    timezone='America/Sao_Paulo',
    enable_utc=True,
    
    # Task routing
    task_routes={
        'app.workers.whatsapp_tasks.*': {'queue': 'whatsapp'},
        'app.workers.campaign_tasks.*': {'queue': 'campaigns'},
        'app.workers.ai_tasks.*': {'queue': 'ai'},
        'app.workers.maintenance_tasks.*': {'queue': 'maintenance'},
    },
    
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    result_expires=3600,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    
    # Retry settings
    task_default_retry_delay=60,
    task_max_retries=3,
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Beat schedule
    beat_schedule={
        # Health check dos clientes WhatsApp a cada 30 segundos
        'whatsapp-health-check': {
            'task': 'app.workers.whatsapp_tasks.health_check_clients',
            'schedule': 30.0,
        },
        
        # Processar fila de mensagens a cada 10 segundos
        'process-message-queue': {
            'task': 'app.workers.whatsapp_tasks.process_message_queue',
            'schedule': 10.0,
        },
        
        # Limpeza de dados antigos - diariamente às 2h
        'cleanup-old-data': {
            'task': 'app.workers.maintenance_tasks.cleanup_old_data',
            'schedule': crontab(hour=2, minute=0),
        },
        
        # Backup automático - diariamente às 3h
        'daily-backup': {
            'task': 'app.workers.maintenance_tasks.create_backup',
            'schedule': crontab(hour=3, minute=0),
        },
        
        # Relatório de métricas - a cada hora
        'hourly-metrics': {
            'task': 'app.workers.maintenance_tasks.calculate_hourly_metrics',
            'schedule': crontab(minute=0),
        },
        
        # Verificar campanhas agendadas - a cada 5 minutos
        'check-scheduled-campaigns': {
            'task': 'app.workers.campaign_tasks.check_scheduled_campaigns',
            'schedule': 300.0,
        },
    },
)

# Event handlers
@celery_app.task(bind=True)
def debug_task(self):
    """Task de debug"""
    print(f'Request: {self.request!r}')


# Configurar logging estruturado para Celery
import logging
from celery.signals import setup_logging

@setup_logging.connect
def config_loggers(*args, **kwargs):
    """Configurar logging estruturado para Celery"""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


# Task error handler
@celery_app.task(bind=True)
def error_handler(self, uuid, err, traceback):
    """Handler para erros em tasks"""
    logger.error(
        "Task failed",
        task_id=uuid,
        error=str(err),
        traceback=traceback
    )


# Startup event
@celery_app.task(bind=True)
def startup_task(self):
    """Task executada no startup do worker"""
    logger.info("Celery worker started", worker_id=self.request.id)


if __name__ == '__main__':
    celery_app.start()