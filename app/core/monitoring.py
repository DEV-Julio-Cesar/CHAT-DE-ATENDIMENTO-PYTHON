"""
Sistema de Monitoramento Avançado para ISP
Monitoramento em tempo real para 10k+ clientes
"""
import asyncio
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import psutil
import structlog
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
from app.core.redis_client import redis_manager
from app.core.database import db_manager

logger = structlog.get_logger(__name__)

# Métricas Prometheus customizadas
CUSTOM_REGISTRY = CollectorRegistry()

# Métricas de negócio
TICKETS_CREATED = Counter(
    'isp_tickets_created_total',
    'Total de tickets criados',
    ['priority', 'channel', 'category'],
    registry=CUSTOM_REGISTRY
)

TICKETS_RESOLVED = Counter(
    'isp_tickets_resolved_total', 
    'Total de tickets resolvidos',
    ['resolution_type', 'agent'],
    registry=CUSTOM_REGISTRY
)

RESPONSE_TIME = Histogram(
    'isp_response_time_seconds',
    'Tempo de primeira resposta',
    ['channel', 'priority'],
    registry=CUSTOM_REGISTRY
)

RESOLUTION_TIME = Histogram(
    'isp_resolution_time_seconds',
    'Tempo total de resolução',
    ['category', 'complexity'],
    registry=CUSTOM_REGISTRY
)

ACTIVE_CONVERSATIONS = Gauge(
    'isp_active_conversations',
    'Conversas ativas por canal',
    ['channel', 'status'],
    registry=CUSTOM_REGISTRY
)

CUSTOMER_SATISFACTION = Histogram(
    'isp_customer_satisfaction_score',
    'Score de satisfação do cliente',
    ['channel', 'agent'],
    registry=CUSTOM_REGISTRY
)

WHATSAPP_MESSAGES = Counter(
    'isp_whatsapp_messages_total',
    'Total de mensagens WhatsApp',
    ['direction', 'type', 'status'],
    registry=CUSTOM_REGISTRY
)

SYSTEM_HEALTH = Gauge(
    'isp_system_health_score',
    'Score de saúde do sistema (0-100)',
    ['component'],
    registry=CUSTOM_REGISTRY
)


@dataclass
class SystemMetrics:
    """Métricas do sistema"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_io: Dict[str, int]
    active_connections: int
    database_connections: int
    redis_memory: int
    queue_size: int
    error_rate: float
    response_time_p95: float


@dataclass
class BusinessMetrics:
    """Métricas de negócio"""
    timestamp: datetime
    active_tickets: int
    tickets_created_today: int
    tickets_resolved_today: int
    avg_response_time: float
    avg_resolution_time: float
    customer_satisfaction: float
    agent_productivity: float
    automation_rate: float
    whatsapp_messages_today: int
    revenue_impact: float


class AdvancedMonitoring:
    """Sistema de monitoramento avançado"""
    
    def __init__(self):
        self.is_running = False
        self.metrics_history: List[SystemMetrics] = []
        self.business_history: List[BusinessMetrics] = []
        self.alerts_sent = set()
        
    async def start(self):
        """Inicia o monitoramento"""
        if self.is_running:
            return
            
        self.is_running = True
        logger.info("Starting advanced monitoring system")
        
        # Inicia tasks de monitoramento
        asyncio.create_task(self._collect_system_metrics())
        asyncio.create_task(self._collect_business_metrics())
        asyncio.create_task(self._health_check_loop())
        asyncio.create_task(self._alert_manager())
        
    async def stop(self):
        """Para o monitoramento"""
        self.is_running = False
        logger.info("Stopping advanced monitoring system")
        
    async def _collect_system_metrics(self):
        """Coleta métricas do sistema a cada 30 segundos"""
        while self.is_running:
            try:
                # CPU e Memória
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                # Rede
                network = psutil.net_io_counters()
                network_io = {
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv,
                    'packets_sent': network.packets_sent,
                    'packets_recv': network.packets_recv
                }
                
                # Conexões
                active_connections = len(psutil.net_connections())
                
                # Database
                db_connections = await self._get_db_connections()
                
                # Redis
                redis_info = await redis_manager.info()
                redis_memory = redis_info.get('used_memory', 0)
                
                # Queue (simulado - implementar com Celery)
                queue_size = await self._get_queue_size()
                
                # Taxa de erro (últimos 5 minutos)
                error_rate = await self._calculate_error_rate()
                
                # Tempo de resposta P95
                response_time_p95 = await self._get_response_time_p95()
                
                metrics = SystemMetrics(
                    timestamp=datetime.utcnow(),
                    cpu_percent=cpu_percent,
                    memory_percent=memory.percent,
                    disk_percent=disk.percent,
                    network_io=network_io,
                    active_connections=active_connections,
                    database_connections=db_connections,
                    redis_memory=redis_memory,
                    queue_size=queue_size,
                    error_rate=error_rate,
                    response_time_p95=response_time_p95
                )
                
                # Armazena histórico (últimas 24h)
                self.metrics_history.append(metrics)
                if len(self.metrics_history) > 2880:  # 24h * 60min * 2 (30s interval)
                    self.metrics_history.pop(0)
                
                # Atualiza métricas Prometheus
                SYSTEM_HEALTH.labels(component='cpu').set(100 - cpu_percent)
                SYSTEM_HEALTH.labels(component='memory').set(100 - memory.percent)
                SYSTEM_HEALTH.labels(component='disk').set(100 - disk.percent)
                
                # Cache no Redis
                await redis_manager.setex(
                    'system_metrics:latest',
                    300,  # 5 minutos
                    asdict(metrics)
                )
                
            except Exception as e:
                logger.error("Error collecting system metrics", error=str(e))
                
            await asyncio.sleep(30)
            
    async def _collect_business_metrics(self):
        """Coleta métricas de negócio a cada 5 minutos"""
        while self.is_running:
            try:
                # Tickets ativos
                active_tickets = await self._count_active_tickets()
                
                # Tickets criados hoje
                tickets_created_today = await self._count_tickets_created_today()
                
                # Tickets resolvidos hoje
                tickets_resolved_today = await self._count_tickets_resolved_today()
                
                # Tempo médio de resposta
                avg_response_time = await self._calculate_avg_response_time()
                
                # Tempo médio de resolução
                avg_resolution_time = await self._calculate_avg_resolution_time()
                
                # Satisfação do cliente
                customer_satisfaction = await self._calculate_customer_satisfaction()
                
                # Produtividade dos agentes
                agent_productivity = await self._calculate_agent_productivity()
                
                # Taxa de automação
                automation_rate = await self._calculate_automation_rate()
                
                # Mensagens WhatsApp hoje
                whatsapp_messages_today = await self._count_whatsapp_messages_today()
                
                # Impacto na receita (simulado)
                revenue_impact = await self._calculate_revenue_impact()
                
                metrics = BusinessMetrics(
                    timestamp=datetime.utcnow(),
                    active_tickets=active_tickets,
                    tickets_created_today=tickets_created_today,
                    tickets_resolved_today=tickets_resolved_today,
                    avg_response_time=avg_response_time,
                    avg_resolution_time=avg_resolution_time,
                    customer_satisfaction=customer_satisfaction,
                    agent_productivity=agent_productivity,
                    automation_rate=automation_rate,
                    whatsapp_messages_today=whatsapp_messages_today,
                    revenue_impact=revenue_impact
                )
                
                # Armazena histórico
                self.business_history.append(metrics)
                if len(self.business_history) > 288:  # 24h (5min interval)
                    self.business_history.pop(0)
                
                # Cache no Redis
                await redis_manager.setex(
                    'business_metrics:latest',
                    300,
                    asdict(metrics)
                )
                
            except Exception as e:
                logger.error("Error collecting business metrics", error=str(e))
                
            await asyncio.sleep(300)  # 5 minutos
            
    async def _health_check_loop(self):
        """Loop de verificação de saúde dos componentes"""
        while self.is_running:
            try:
                health_status = await self.comprehensive_health_check()
                
                # Atualiza métricas de saúde
                for component, status in health_status.items():
                    score = 100 if status['healthy'] else 0
                    SYSTEM_HEALTH.labels(component=component).set(score)
                
                # Cache status
                await redis_manager.setex(
                    'health_status:latest',
                    60,
                    health_status
                )
                
            except Exception as e:
                logger.error("Error in health check loop", error=str(e))
                
            await asyncio.sleep(60)  # 1 minuto
            
    async def _alert_manager(self):
        """Gerenciador de alertas inteligentes"""
        while self.is_running:
            try:
                await self._check_system_alerts()
                await self._check_business_alerts()
                await self._check_sla_alerts()
                
            except Exception as e:
                logger.error("Error in alert manager", error=str(e))
                
            await asyncio.sleep(120)  # 2 minutos
            
    async def comprehensive_health_check(self) -> Dict[str, Any]:
        """Verificação completa de saúde do sistema"""
        health_status = {}
        
        # Database
        try:
            db_healthy = await db_manager.health_check()
            health_status['database'] = {
                'healthy': db_healthy,
                'response_time': await self._measure_db_response_time(),
                'connections': await self._get_db_connections()
            }
        except Exception as e:
            health_status['database'] = {
                'healthy': False,
                'error': str(e)
            }
            
        # Redis
        try:
            redis_healthy = await redis_manager.health_check()
            redis_info = await redis_manager.info()
            health_status['redis'] = {
                'healthy': redis_healthy,
                'memory_usage': redis_info.get('used_memory_human', 'unknown'),
                'connected_clients': redis_info.get('connected_clients', 0)
            }
        except Exception as e:
            health_status['redis'] = {
                'healthy': False,
                'error': str(e)
            }
            
        # WhatsApp API
        health_status['whatsapp'] = await self._check_whatsapp_health()
        
        # Gemini AI
        health_status['gemini'] = await self._check_gemini_health()
        
        # Sistema
        health_status['system'] = {
            'healthy': True,
            'cpu_usage': psutil.cpu_percent(),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent
        }
        
        return health_status
        
    async def get_real_time_dashboard(self) -> Dict[str, Any]:
        """Dados para dashboard em tempo real"""
        try:
            # Métricas mais recentes
            latest_system = self.metrics_history[-1] if self.metrics_history else None
            latest_business = self.business_history[-1] if self.business_history else None
            
            # Status de saúde
            health_status = await redis_manager.get('health_status:latest') or {}
            
            # Alertas ativos
            active_alerts = await self._get_active_alerts()
            
            # Tendências (últimas 4 horas)
            trends = await self._calculate_trends()
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'system_metrics': asdict(latest_system) if latest_system else None,
                'business_metrics': asdict(latest_business) if latest_business else None,
                'health_status': health_status,
                'active_alerts': active_alerts,
                'trends': trends,
                'summary': {
                    'total_customers': 10000,  # Configurável
                    'active_conversations': len(await self._get_active_conversations()),
                    'agents_online': await self._count_online_agents(),
                    'system_uptime': self._get_system_uptime(),
                    'overall_health': self._calculate_overall_health(health_status)
                }
            }
            
        except Exception as e:
            logger.error("Error generating dashboard data", error=str(e))
            return {'error': str(e)}
            
    # Métodos auxiliares (implementação simplificada)
    async def _get_db_connections(self) -> int:
        """Conta conexões ativas do banco"""
        # Implementar query específica do PostgreSQL
        return 10  # Placeholder
        
    async def _get_queue_size(self) -> int:
        """Tamanho da fila de mensagens"""
        # Implementar com Celery/RabbitMQ
        return 0  # Placeholder
        
    async def _calculate_error_rate(self) -> float:
        """Taxa de erro dos últimos 5 minutos"""
        # Implementar baseado em logs/métricas
        return 0.1  # Placeholder
        
    async def _get_response_time_p95(self) -> float:
        """Tempo de resposta percentil 95"""
        # Implementar baseado em métricas HTTP
        return 0.2  # Placeholder
        
    async def _count_active_tickets(self) -> int:
        """Conta tickets ativos"""
        # Query no banco de dados
        return 150  # Placeholder
        
    async def _count_tickets_created_today(self) -> int:
        """Tickets criados hoje"""
        return 45  # Placeholder
        
    async def _count_tickets_resolved_today(self) -> int:
        """Tickets resolvidos hoje"""
        return 38  # Placeholder
        
    async def _calculate_avg_response_time(self) -> float:
        """Tempo médio de primeira resposta (segundos)"""
        return 120.5  # Placeholder
        
    async def _calculate_avg_resolution_time(self) -> float:
        """Tempo médio de resolução (segundos)"""
        return 3600.0  # Placeholder
        
    async def _calculate_customer_satisfaction(self) -> float:
        """Score médio de satisfação (1-5)"""
        return 4.2  # Placeholder
        
    async def _calculate_agent_productivity(self) -> float:
        """Tickets por agente por dia"""
        return 25.5  # Placeholder
        
    async def _calculate_automation_rate(self) -> float:
        """Taxa de automação (0-1)"""
        return 0.65  # Placeholder
        
    async def _count_whatsapp_messages_today(self) -> int:
        """Mensagens WhatsApp hoje"""
        return 1250  # Placeholder
        
    async def _calculate_revenue_impact(self) -> float:
        """Impacto na receita (R$)"""
        return 15000.0  # Placeholder
        
    async def _measure_db_response_time(self) -> float:
        """Mede tempo de resposta do banco"""
        start = time.time()
        await db_manager.health_check()
        return time.time() - start
        
    async def _check_whatsapp_health(self) -> Dict[str, Any]:
        """Verifica saúde da API WhatsApp"""
        return {'healthy': True, 'active_sessions': 3}
        
    async def _check_gemini_health(self) -> Dict[str, Any]:
        """Verifica saúde da API Gemini"""
        return {'healthy': True, 'quota_remaining': 95}
        
    async def _check_system_alerts(self):
        """Verifica alertas de sistema"""
        pass  # Implementar lógica de alertas
        
    async def _check_business_alerts(self):
        """Verifica alertas de negócio"""
        pass  # Implementar lógica de alertas
        
    async def _check_sla_alerts(self):
        """Verifica alertas de SLA"""
        pass  # Implementar lógica de alertas
        
    async def _get_active_alerts(self) -> List[Dict]:
        """Retorna alertas ativos"""
        return []  # Placeholder
        
    async def _calculate_trends(self) -> Dict[str, Any]:
        """Calcula tendências das métricas"""
        return {}  # Placeholder
        
    async def _get_active_conversations(self) -> List[str]:
        """Retorna conversas ativas"""
        return []  # Placeholder
        
    async def _count_online_agents(self) -> int:
        """Conta agentes online"""
        return 8  # Placeholder
        
    def _get_system_uptime(self) -> str:
        """Uptime do sistema"""
        return "99.9%"  # Placeholder
        
    def _calculate_overall_health(self, health_status: Dict) -> float:
        """Calcula saúde geral do sistema (0-100)"""
        if not health_status:
            return 0.0
            
        healthy_components = sum(1 for status in health_status.values() 
                               if isinstance(status, dict) and status.get('healthy', False))
        total_components = len(health_status)
        
        return (healthy_components / total_components * 100) if total_components > 0 else 0.0


# Instância global
monitoring = AdvancedMonitoring()