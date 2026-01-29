"""
Sistema de métricas customizadas
"""
import time
import asyncio
from typing import Dict, Any, Optional
from prometheus_client import Counter, Histogram, Gauge, Info
import structlog

logger = structlog.get_logger(__name__)

# Métricas de Conversas
CONVERSATION_DURATION = Histogram(
    'conversation_duration_seconds',
    'Duração das conversas em segundos',
    ['resolution_type', 'escalated']
)

CONVERSATION_STATES = Gauge(
    'conversations_by_state',
    'Número de conversas por estado',
    ['state']
)

CONVERSATION_CREATED = Counter(
    'conversations_created_total',
    'Total de conversas criadas',
    ['source', 'priority']
)

# Métricas de Mensagens
MESSAGE_PROCESSING_TIME = Histogram(
    'message_processing_seconds',
    'Tempo para processar mensagem',
    ['message_type', 'ai_used', 'sender_type']
)

MESSAGES_SENT = Counter(
    'messages_sent_total',
    'Total de mensagens enviadas',
    ['type', 'direction', 'status']
)

MESSAGE_QUEUE_SIZE = Gauge(
    'message_queue_size',
    'Tamanho da fila de mensagens',
    ['queue_type']
)

# Métricas de WhatsApp
WHATSAPP_CONNECTIONS = Gauge(
    'whatsapp_connections_active',
    'Conexões WhatsApp ativas',
    ['status']
)

WHATSAPP_API_CALLS = Counter(
    'whatsapp_api_calls_total',
    'Chamadas para API do WhatsApp',
    ['endpoint', 'status_code']
)

WHATSAPP_RATE_LIMITS = Counter(
    'whatsapp_rate_limits_total',
    'Rate limits atingidos',
    ['client_id']
)

# Métricas de AI/Chatbot
AI_REQUESTS = Counter(
    'ai_requests_total',
    'Requisições para AI',
    ['model', 'intent', 'confidence_level']
)

AI_RESPONSE_TIME = Histogram(
    'ai_response_time_seconds',
    'Tempo de resposta da AI',
    ['model', 'intent']
)

BOT_ESCALATIONS = Counter(
    'bot_escalations_total',
    'Escalações do bot para humano',
    ['reason', 'confidence_score']
)

# Métricas de Usuários
USER_SESSIONS = Gauge(
    'user_sessions_active',
    'Sessões de usuário ativas',
    ['role']
)

USER_ACTIONS = Counter(
    'user_actions_total',
    'Ações de usuário',
    ['action', 'role', 'resource']
)

LOGIN_ATTEMPTS = Counter(
    'login_attempts_total',
    'Tentativas de login',
    ['status', 'method']
)

# Métricas de Performance
DATABASE_QUERY_TIME = Histogram(
    'database_query_duration_seconds',
    'Tempo de execução de queries',
    ['operation', 'table']
)

CACHE_OPERATIONS = Counter(
    'cache_operations_total',
    'Operações de cache',
    ['operation', 'status']
)

CACHE_HIT_RATE = Gauge(
    'cache_hit_rate',
    'Taxa de acerto do cache',
    ['cache_type']
)

# Métricas de Negócio
CUSTOMER_SATISFACTION = Histogram(
    'customer_satisfaction_score',
    'Score de satisfação do cliente',
    ['resolution_type']
)

FIRST_RESPONSE_TIME = Histogram(
    'first_response_time_seconds',
    'Tempo para primeira resposta',
    ['channel', 'priority']
)

RESOLUTION_TIME = Histogram(
    'issue_resolution_time_seconds',
    'Tempo para resolução de problemas',
    ['category', 'complexity']
)

# Métricas de Sistema
SYSTEM_HEALTH = Info(
    'system_health_info',
    'Informações de saúde do sistema'
)

ERROR_RATE = Counter(
    'errors_total',
    'Total de erros',
    ['component', 'error_type', 'severity']
)


class MetricsCollector:
    """Coletor de métricas customizadas"""
    
    def __init__(self):
        self.start_times: Dict[str, float] = {}
    
    def start_timer(self, operation_id: str) -> str:
        """Iniciar timer para operação"""
        self.start_times[operation_id] = time.time()
        return operation_id
    
    def end_timer(self, operation_id: str) -> float:
        """Finalizar timer e retornar duração"""
        if operation_id in self.start_times:
            duration = time.time() - self.start_times[operation_id]
            del self.start_times[operation_id]
            return duration
        return 0.0
    
    def record_conversation_created(self, source: str = "whatsapp", priority: str = "normal"):
        """Registrar criação de conversa"""
        CONVERSATION_CREATED.labels(source=source, priority=priority).inc()
    
    def record_conversation_duration(self, duration: float, resolution_type: str, escalated: bool = False):
        """Registrar duração de conversa"""
        CONVERSATION_DURATION.labels(
            resolution_type=resolution_type,
            escalated=str(escalated).lower()
        ).observe(duration)
    
    def record_message_processing(self, duration: float, message_type: str, ai_used: bool, sender_type: str):
        """Registrar processamento de mensagem"""
        MESSAGE_PROCESSING_TIME.labels(
            message_type=message_type,
            ai_used=str(ai_used).lower(),
            sender_type=sender_type
        ).observe(duration)
    
    def record_message_sent(self, msg_type: str, direction: str, status: str):
        """Registrar envio de mensagem"""
        MESSAGES_SENT.labels(type=msg_type, direction=direction, status=status).inc()
    
    def record_ai_request(self, model: str, intent: str, confidence: float, response_time: float):
        """Registrar requisição para AI"""
        confidence_level = "high" if confidence > 0.8 else "medium" if confidence > 0.5 else "low"
        
        AI_REQUESTS.labels(
            model=model,
            intent=intent,
            confidence_level=confidence_level
        ).inc()
        
        AI_RESPONSE_TIME.labels(model=model, intent=intent).observe(response_time)
    
    def record_bot_escalation(self, reason: str, confidence_score: float):
        """Registrar escalação do bot"""
        BOT_ESCALATIONS.labels(
            reason=reason,
            confidence_score=f"{confidence_score:.1f}"
        ).inc()
    
    def record_user_action(self, action: str, role: str, resource: str):
        """Registrar ação de usuário"""
        USER_ACTIONS.labels(action=action, role=role, resource=resource).inc()
    
    def record_login_attempt(self, status: str, method: str = "password"):
        """Registrar tentativa de login"""
        LOGIN_ATTEMPTS.labels(status=status, method=method).inc()
    
    def record_database_query(self, duration: float, operation: str, table: str):
        """Registrar query de banco"""
        DATABASE_QUERY_TIME.labels(operation=operation, table=table).observe(duration)
    
    def record_cache_operation(self, operation: str, status: str):
        """Registrar operação de cache"""
        CACHE_OPERATIONS.labels(operation=operation, status=status).inc()
    
    def update_cache_hit_rate(self, cache_type: str, hit_rate: float):
        """Atualizar taxa de acerto do cache"""
        CACHE_HIT_RATE.labels(cache_type=cache_type).set(hit_rate)
    
    def record_whatsapp_api_call(self, endpoint: str, status_code: int):
        """Registrar chamada para API WhatsApp"""
        WHATSAPP_API_CALLS.labels(endpoint=endpoint, status_code=str(status_code)).inc()
    
    def record_error(self, component: str, error_type: str, severity: str = "error"):
        """Registrar erro"""
        ERROR_RATE.labels(component=component, error_type=error_type, severity=severity).inc()
    
    def update_conversation_states(self, state_counts: Dict[str, int]):
        """Atualizar contadores de estado de conversa"""
        for state, count in state_counts.items():
            CONVERSATION_STATES.labels(state=state).set(count)
    
    def update_whatsapp_connections(self, status_counts: Dict[str, int]):
        """Atualizar contadores de conexões WhatsApp"""
        for status, count in status_counts.items():
            WHATSAPP_CONNECTIONS.labels(status=status).set(count)
    
    def update_user_sessions(self, role_counts: Dict[str, int]):
        """Atualizar contadores de sessões de usuário"""
        for role, count in role_counts.items():
            USER_SESSIONS.labels(role=role).set(count)


# Instância global
metrics_collector = MetricsCollector()


# Decorador para medir tempo de execução
def measure_time(metric_name: str, **labels):
    """Decorador para medir tempo de execução"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Registrar métrica baseada no nome
                if metric_name == "message_processing":
                    MESSAGE_PROCESSING_TIME.labels(**labels).observe(duration)
                elif metric_name == "ai_response":
                    AI_RESPONSE_TIME.labels(**labels).observe(duration)
                elif metric_name == "database_query":
                    DATABASE_QUERY_TIME.labels(**labels).observe(duration)
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                metrics_collector.record_error(
                    component=labels.get("component", "unknown"),
                    error_type=type(e).__name__
                )
                raise
        
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                if metric_name == "database_query":
                    DATABASE_QUERY_TIME.labels(**labels).observe(duration)
                
                return result
            except Exception as e:
                metrics_collector.record_error(
                    component=labels.get("component", "unknown"),
                    error_type=type(e).__name__
                )
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator