"""
Serviço de migração de dados simplificado
"""
import structlog

logger = structlog.get_logger(__name__)


class DataMigrationService:
    """Serviço de migração de dados"""
    
    def __init__(self):
        self.initialized = False


# Instância global
migration_service = DataMigrationService()