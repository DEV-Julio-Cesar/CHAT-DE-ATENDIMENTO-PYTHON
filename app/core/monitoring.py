"""
Sistema de monitoramento simplificado
"""
import structlog

logger = structlog.get_logger(__name__)


class MonitoringService:
    """Serviço de monitoramento simplificado"""
    
    def __init__(self):
        self.started = False
    
    async def start(self):
        """Iniciar monitoramento"""
        self.started = True
        logger.info("Monitoring service started")
    
    async def stop(self):
        """Parar monitoramento"""
        self.started = False
        logger.info("Monitoring service stopped")


# Instância global
monitoring = MonitoringService()