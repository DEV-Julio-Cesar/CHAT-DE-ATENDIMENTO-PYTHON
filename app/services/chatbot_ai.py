"""
Chatbot AI simplificado
"""
import structlog

logger = structlog.get_logger(__name__)


class ChatbotAI:
    """Chatbot AI simplificado"""
    
    def __init__(self):
        self.initialized = False
    
    async def initialize(self):
        """Inicializar chatbot"""
        self.initialized = True
        logger.info("Chatbot AI initialized")


# Instância global
chatbot_ai = ChatbotAI()