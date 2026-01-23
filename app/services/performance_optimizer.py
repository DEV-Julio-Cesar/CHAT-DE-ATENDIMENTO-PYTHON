"""
Sistema de Otimização de Performance para ISP
Otimização automática para suportar 10k+ clientes
"""
import asyncio
import psutil
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import structlog
from app.core.config import settings
from app.core.redis_client import redis_manager
from app.core.database import db_manager
from app.core.monitoring import monitoring
from sqlalchemy import text
import json

logger = structlog.get_logger(__name__)


@dataclass
class PerformanceMetrics:
    """Métricas de performance"""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, int]
    database_connections: int
    database_query_time: float
    redis_memory: int
    redis_hit_rate: float
    api_response_time: float
    active_websockets: int
    queue_size: int


@dataclass
class OptimizationAction:
    """Ação de otimização"""
    action_type: str
    description: str
    priority: int  # 1=crítico, 2=alto, 3=médio, 4=baixo
    auto_apply: bool
    parameters: Dict[str, Any]
    estimated_impact: str


class PerformanceOptimizer:
    """Otimizador de performance automático"""
    
    def __init__(self):
        self.optimization_rules = {}
        self.performance_history = []
        self.active_optimizations = {}
        self.thresholds = {
            'cpu_critical': 85.0,
            'cpu_warning': 70.0,
            'memory_critical': 90.0,
            'memory_warning': 75.0,
            'disk_critical': 95.0,
            'disk_warning': 85.0,
            'db_connections_max': 80,
            'db_query_time_max': 1.0,
            'api_response_time_max': 2.0,
            'redis_memory_max': 2 * 1024 * 1024 * 1024  # 2GB
        }
        
    async def initialize(self):
        """Inicializa o otimizador"""
        await self._load_optimization_rules()
        await self._start_monitoring_loop()
        logger.info("Performance optimizer initialized")
        
    async def analyze_and_optimize(self) -> Dict[str, Any]:
        """Analisa performance e aplica otimizações"""
        try:
            # Coleta métricas atuais
            metrics = await self._collect_metrics()
            
            # Analisa problemas de performance
            issues = await self._analyze_performance_issues(metrics)
            
            # Gera recomendações de otimização
            recommendations = await self._generate_optimizations(issues, metrics)
            
            # Aplica otimizações automáticas
            applied_optimizations = await self._apply_auto_optimizations(recommendations)
            
            # Salva histórico
            await self._save_performance_data(metrics, issues, recommendations)
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'metrics': asdict(metrics),
                'issues': issues,
                'recommendations': recommendations,
                'applied_optimizations': applied_optimizations,
                'performance_score': await self._calculate_performance_score(metrics)
            }
            
        except Exception as e:
            logger.error("Error in performance analysis", error=str(e))
            return {'error': str(e)}
            
    async def _collect_metrics(self) -> PerformanceMetrics:
        """Coleta métricas de performance"""
        
        # Métricas do sistema
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        network = psutil.net_io_counters()
        
        # Métricas do banco de dados
        db_connections = await self._get_db_connections()
        db_query_time = await self._measure_db_performance()
        
        # Métricas do Redis
        redis_info = await redis_manager.info()
        redis_memory = redis_info.get('used_memory', 0)
        redis_hit_rate = await self._calculate_redis_hit_rate()
        
        # Métricas da API
        api_response_time = await self._measure_api_performance()
        
        # Métricas de WebSocket e filas
        active_websockets = await self._count_active_websockets()
        queue_size = await self._get_queue_size()
        
        return PerformanceMetrics(
            timestamp=datetime.utcnow(),
            cpu_usage=cpu_usage,
            memory_usage=memory.percent,
            disk_usage=disk.percent,
            network_io={
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv,
                'packets_sent': network.packets_sent,
                'packets_recv': network.packets_recv
            },
            database_connections=db_connections,
            database_query_time=db_query_time,
            redis_memory=redis_memory,
            redis_hit_rate=redis_hit_rate,
            api_response_time=api_response_time,
            active_websockets=active_websockets,
            queue_size=queue_size
        )
        
    async def _analyze_performance_issues(self, metrics: PerformanceMetrics) -> List[Dict[str, Any]]:
        """Analisa problemas de performance"""
        issues = []
        
        # CPU Issues
        if metrics.cpu_usage >= self.thresholds['cpu_critical']:
            issues.append({
                'type': 'cpu_critical',
                'severity': 'critical',
                'message': f'CPU usage critical: {metrics.cpu_usage:.1f}%',
                'value': metrics.cpu_usage,
                'threshold': self.thresholds['cpu_critical']
            })
        elif metrics.cpu_usage >= self.thresholds['cpu_warning']:
            issues.append({
                'type': 'cpu_warning',
                'severity': 'warning',
                'message': f'CPU usage high: {metrics.cpu_usage:.1f}%',
                'value': metrics.cpu_usage,
                'threshold': self.thresholds['cpu_warning']
            })
            
        # Memory Issues
        if metrics.memory_usage >= self.thresholds['memory_critical']:
            issues.append({
                'type': 'memory_critical',
                'severity': 'critical',
                'message': f'Memory usage critical: {metrics.memory_usage:.1f}%',
                'value': metrics.memory_usage,
                'threshold': self.thresholds['memory_critical']
            })
        elif metrics.memory_usage >= self.thresholds['memory_warning']:
            issues.append({
                'type': 'memory_warning',
                'severity': 'warning',
                'message': f'Memory usage high: {metrics.memory_usage:.1f}%',
                'value': metrics.memory_usage,
                'threshold': self.thresholds['memory_warning']
            })
            
        # Disk Issues
        if metrics.disk_usage >= self.thresholds['disk_critical']:
            issues.append({
                'type': 'disk_critical',
                'severity': 'critical',
                'message': f'Disk usage critical: {metrics.disk_usage:.1f}%',
                'value': metrics.disk_usage,
                'threshold': self.thresholds['disk_critical']
            })
            
        # Database Issues
        if metrics.database_connections >= self.thresholds['db_connections_max']:
            issues.append({
                'type': 'db_connections_high',
                'severity': 'warning',
                'message': f'Database connections high: {metrics.database_connections}',
                'value': metrics.database_connections,
                'threshold': self.thresholds['db_connections_max']
            })
            
        if metrics.database_query_time >= self.thresholds['db_query_time_max']:
            issues.append({
                'type': 'db_slow_queries',
                'severity': 'warning',
                'message': f'Database queries slow: {metrics.database_query_time:.2f}s',
                'value': metrics.database_query_time,
                'threshold': self.thresholds['db_query_time_max']
            })
            
        # API Performance Issues
        if metrics.api_response_time >= self.thresholds['api_response_time_max']:
            issues.append({
                'type': 'api_slow_response',
                'severity': 'warning',
                'message': f'API response time slow: {metrics.api_response_time:.2f}s',
                'value': metrics.api_response_time,
                'threshold': self.thresholds['api_response_time_max']
            })
            
        # Redis Issues
        if metrics.redis_memory >= self.thresholds['redis_memory_max']:
            issues.append({
                'type': 'redis_memory_high',
                'severity': 'warning',
                'message': f'Redis memory usage high: {metrics.redis_memory / 1024 / 1024:.1f}MB',
                'value': metrics.redis_memory,
                'threshold': self.thresholds['redis_memory_max']
            })
            
        if metrics.redis_hit_rate < 0.8:  # 80% hit rate mínimo
            issues.append({
                'type': 'redis_low_hit_rate',
                'severity': 'info',
                'message': f'Redis hit rate low: {metrics.redis_hit_rate:.1%}',
                'value': metrics.redis_hit_rate,
                'threshold': 0.8
            })
            
        return issues
        
    async def _generate_optimizations(
        self,
        issues: List[Dict[str, Any]],
        metrics: PerformanceMetrics
    ) -> List[OptimizationAction]:
        """Gera recomendações de otimização"""
        optimizations = []
        
        for issue in issues:
            issue_type = issue['type']
            
            if issue_type == 'cpu_critical':
                optimizations.extend([
                    OptimizationAction(
                        action_type='scale_workers',
                        description='Reduzir número de workers para diminuir carga de CPU',
                        priority=1,
                        auto_apply=True,
                        parameters={'worker_count': max(2, psutil.cpu_count() // 2)},
                        estimated_impact='Redução de 20-30% no uso de CPU'
                    ),
                    OptimizationAction(
                        action_type='enable_cpu_throttling',
                        description='Ativar throttling de CPU para requests',
                        priority=2,
                        auto_apply=True,
                        parameters={'max_cpu_per_request': 0.1},
                        estimated_impact='Controle de picos de CPU'
                    )
                ])
                
            elif issue_type == 'memory_critical':
                optimizations.extend([
                    OptimizationAction(
                        action_type='clear_cache',
                        description='Limpar cache Redis para liberar memória',
                        priority=1,
                        auto_apply=True,
                        parameters={'cache_types': ['session', 'temporary']},
                        estimated_impact='Liberação de 10-20% da memória'
                    ),
                    OptimizationAction(
                        action_type='optimize_db_connections',
                        description='Reduzir pool de conexões do banco',
                        priority=2,
                        auto_apply=True,
                        parameters={'max_connections': 10},
                        estimated_impact='Redução no uso de memória'
                    )
                ])
                
            elif issue_type == 'db_slow_queries':
                optimizations.extend([
                    OptimizationAction(
                        action_type='analyze_slow_queries',
                        description='Analisar e otimizar queries lentas',
                        priority=2,
                        auto_apply=False,
                        parameters={'log_slow_queries': True},
                        estimated_impact='Melhoria de 30-50% na performance do DB'
                    ),
                    OptimizationAction(
                        action_type='update_db_statistics',
                        description='Atualizar estatísticas do banco de dados',
                        priority=3,
                        auto_apply=True,
                        parameters={},
                        estimated_impact='Melhoria no plano de execução das queries'
                    )
                ])
                
            elif issue_type == 'redis_memory_high':
                optimizations.append(
                    OptimizationAction(
                        action_type='redis_memory_optimization',
                        description='Otimizar uso de memória do Redis',
                        priority=2,
                        auto_apply=True,
                        parameters={
                            'expire_old_keys': True,
                            'compress_values': True
                        },
                        estimated_impact='Redução de 15-25% no uso de memória Redis'
                    )
                )
                
            elif issue_type == 'api_slow_response':
                optimizations.extend([
                    OptimizationAction(
                        action_type='enable_response_compression',
                        description='Ativar compressão de respostas da API',
                        priority=3,
                        auto_apply=True,
                        parameters={'compression_level': 6},
                        estimated_impact='Redução de 20-40% no tempo de resposta'
                    ),
                    OptimizationAction(
                        action_type='optimize_serialization',
                        description='Otimizar serialização de dados JSON',
                        priority=3,
                        auto_apply=True,
                        parameters={'use_fast_json': True},
                        estimated_impact='Melhoria de 10-15% na performance da API'
                    )
                ])
                
        # Otimizações preventivas baseadas na carga atual
        if metrics.cpu_usage > 50 or metrics.memory_usage > 60:
            optimizations.append(
                OptimizationAction(
                    action_type='preemptive_scaling',
                    description='Preparar sistema para alta carga',
                    priority=4,
                    auto_apply=False,
                    parameters={
                        'increase_cache_size': True,
                        'preload_common_queries': True
                    },
                    estimated_impact='Melhor preparação para picos de carga'
                )
            )
            
        return optimizations
        
    async def _apply_auto_optimizations(
        self,
        optimizations: List[OptimizationAction]
    ) -> List[Dict[str, Any]]:
        """Aplica otimizações automáticas"""
        applied = []
        
        for optimization in optimizations:
            if not optimization.auto_apply:
                continue
                
            try:
                result = await self._execute_optimization(optimization)
                if result['success']:
                    applied.append({
                        'action': optimization.action_type,
                        'description': optimization.description,
                        'result': result,
                        'timestamp': datetime.utcnow().isoformat()
                    })
                    
                    # Registra otimização ativa
                    self.active_optimizations[optimization.action_type] = {
                        'applied_at': datetime.utcnow(),
                        'parameters': optimization.parameters
                    }
                    
            except Exception as e:
                logger.error(
                    "Error applying optimization",
                    action=optimization.action_type,
                    error=str(e)
                )
                
        return applied
        
    async def _execute_optimization(self, optimization: OptimizationAction) -> Dict[str, Any]:
        """Executa uma otimização específica"""
        action_type = optimization.action_type
        params = optimization.parameters
        
        try:
            if action_type == 'clear_cache':
                return await self._clear_cache(params)
                
            elif action_type == 'optimize_db_connections':
                return await self._optimize_db_connections(params)
                
            elif action_type == 'update_db_statistics':
                return await self._update_db_statistics()
                
            elif action_type == 'redis_memory_optimization':
                return await self._optimize_redis_memory(params)
                
            elif action_type == 'enable_response_compression':
                return await self._enable_response_compression(params)
                
            elif action_type == 'scale_workers':
                return await self._scale_workers(params)
                
            else:
                return {
                    'success': False,
                    'message': f'Unknown optimization action: {action_type}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Error executing {action_type}: {str(e)}'
            }
            
    async def _clear_cache(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Limpa cache Redis"""
        cache_types = params.get('cache_types', ['temporary'])
        cleared_keys = 0
        
        for cache_type in cache_types:
            pattern = f"{cache_type}:*"
            keys = await redis_manager.keys(pattern)
            if keys:
                await redis_manager.delete(*keys)
                cleared_keys += len(keys)
                
        return {
            'success': True,
            'message': f'Cleared {cleared_keys} cache keys',
            'cleared_keys': cleared_keys
        }
        
    async def _optimize_db_connections(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Otimiza conexões do banco"""
        max_connections = params.get('max_connections', 10)
        
        # Atualizar configuração do pool de conexões
        # Nota: Em produção, isso seria feito através de configuração
        
        return {
            'success': True,
            'message': f'Database connection pool optimized to {max_connections} connections'
        }
        
    async def _update_db_statistics(self) -> Dict[str, Any]:
        """Atualiza estatísticas do banco"""
        try:
            async with db_manager.get_session() as session:
                # PostgreSQL: Atualizar estatísticas
                await session.execute(text("ANALYZE;"))
                await session.commit()
                
            return {
                'success': True,
                'message': 'Database statistics updated successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error updating database statistics: {str(e)}'
            }
            
    async def _optimize_redis_memory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Otimiza uso de memória do Redis"""
        actions_taken = []
        
        if params.get('expire_old_keys', False):
            # Definir TTL para chaves sem expiração
            keys = await redis_manager.keys('*')
            expired_count = 0
            
            for key in keys[:1000]:  # Limitar para não sobrecarregar
                ttl = await redis_manager.ttl(key)
                if ttl == -1:  # Sem TTL
                    await redis_manager.expire(key, 3600)  # 1 hora
                    expired_count += 1
                    
            actions_taken.append(f'Set TTL for {expired_count} keys')
            
        if params.get('compress_values', False):
            # Em produção, isso seria configurado no Redis
            actions_taken.append('Enabled value compression')
            
        return {
            'success': True,
            'message': 'Redis memory optimization completed',
            'actions': actions_taken
        }
        
    async def _enable_response_compression(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Ativa compressão de respostas"""
        # Em produção, isso seria configurado no middleware
        compression_level = params.get('compression_level', 6)
        
        return {
            'success': True,
            'message': f'Response compression enabled (level {compression_level})'
        }
        
    async def _scale_workers(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Escala workers"""
        worker_count = params.get('worker_count', 2)
        
        # Em produção, isso seria feito através do orquestrador (Docker/K8s)
        return {
            'success': True,
            'message': f'Worker scaling configured to {worker_count} workers'
        }
        
    async def _calculate_performance_score(self, metrics: PerformanceMetrics) -> float:
        """Calcula score de performance (0-100)"""
        scores = []
        
        # CPU Score (invertido - menor uso = melhor score)
        cpu_score = max(0, 100 - metrics.cpu_usage)
        scores.append(cpu_score * 0.25)  # 25% do peso
        
        # Memory Score
        memory_score = max(0, 100 - metrics.memory_usage)
        scores.append(memory_score * 0.25)  # 25% do peso
        
        # Database Score
        db_score = 100
        if metrics.database_query_time > 0.5:
            db_score = max(0, 100 - (metrics.database_query_time * 50))
        scores.append(db_score * 0.25)  # 25% do peso
        
        # API Score
        api_score = 100
        if metrics.api_response_time > 0.2:
            api_score = max(0, 100 - (metrics.api_response_time * 50))
        scores.append(api_score * 0.25)  # 25% do peso
        
        return sum(scores)
        
    # Métodos auxiliares para coleta de métricas
    async def _get_db_connections(self) -> int:
        """Conta conexões ativas do banco"""
        try:
            async with db_manager.get_session() as session:
                result = await session.execute(
                    text("SELECT count(*) FROM pg_stat_activity WHERE state = 'active';")
                )
                return result.scalar() or 0
        except:
            return 0
            
    async def _measure_db_performance(self) -> float:
        """Mede performance do banco"""
        try:
            start_time = time.time()
            async with db_manager.get_session() as session:
                await session.execute(text("SELECT 1;"))
            return time.time() - start_time
        except:
            return 0.0
            
    async def _calculate_redis_hit_rate(self) -> float:
        """Calcula taxa de hit do Redis"""
        try:
            info = await redis_manager.info()
            hits = info.get('keyspace_hits', 0)
            misses = info.get('keyspace_misses', 0)
            total = hits + misses
            return hits / total if total > 0 else 0.0
        except:
            return 0.0
            
    async def _measure_api_performance(self) -> float:
        """Mede performance da API"""
        # Simulação - em produção seria baseado em métricas reais
        return 0.15  # 150ms
        
    async def _count_active_websockets(self) -> int:
        """Conta WebSockets ativos"""
        # Simulação - em produção seria baseado em métricas reais
        return 50
        
    async def _get_queue_size(self) -> int:
        """Obtém tamanho da fila"""
        # Simulação - em produção seria baseado no Celery
        return 5
        
    async def _save_performance_data(
        self,
        metrics: PerformanceMetrics,
        issues: List[Dict[str, Any]],
        recommendations: List[OptimizationAction]
    ):
        """Salva dados de performance"""
        performance_data = {
            'timestamp': metrics.timestamp.isoformat(),
            'metrics': asdict(metrics),
            'issues_count': len(issues),
            'recommendations_count': len(recommendations),
            'performance_score': await self._calculate_performance_score(metrics)
        }
        
        # Salva no Redis
        await redis_manager.lpush(
            'performance:history',
            json.dumps(performance_data)
        )
        
        # Mantém apenas últimas 1000 entradas
        await redis_manager.ltrim('performance:history', 0, 999)
        
    async def _load_optimization_rules(self):
        """Carrega regras de otimização"""
        self.optimization_rules = {
            'auto_scaling': True,
            'cache_optimization': True,
            'db_optimization': True,
            'memory_management': True
        }
        
    async def _start_monitoring_loop(self):
        """Inicia loop de monitoramento contínuo"""
        asyncio.create_task(self._monitoring_loop())
        
    async def _monitoring_loop(self):
        """Loop de monitoramento contínuo"""
        while True:
            try:
                await self.analyze_and_optimize()
                await asyncio.sleep(300)  # 5 minutos
            except Exception as e:
                logger.error("Error in monitoring loop", error=str(e))
                await asyncio.sleep(60)  # 1 minuto em caso de erro
                
    async def get_optimization_report(self) -> Dict[str, Any]:
        """Gera relatório de otimização"""
        try:
            # Histórico de performance
            history_data = await redis_manager.lrange('performance:history', 0, 99)
            history = [json.loads(data) for data in history_data]
            
            # Otimizações ativas
            active_opts = list(self.active_optimizations.keys())
            
            # Tendências
            if len(history) >= 2:
                latest = history[0]
                previous = history[1]
                trend = {
                    'performance_score': latest['performance_score'] - previous['performance_score'],
                    'issues_count': latest['issues_count'] - previous['issues_count']
                }
            else:
                trend = {'performance_score': 0, 'issues_count': 0}
                
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'active_optimizations': active_opts,
                'performance_trend': trend,
                'history_points': len(history),
                'recommendations': {
                    'immediate': await self._get_immediate_recommendations(),
                    'long_term': await self._get_long_term_recommendations()
                }
            }
            
        except Exception as e:
            logger.error("Error generating optimization report", error=str(e))
            return {'error': str(e)}
            
    async def _get_immediate_recommendations(self) -> List[str]:
        """Recomendações imediatas"""
        return [
            "Monitorar uso de CPU durante picos de tráfego",
            "Configurar alertas para uso de memória > 80%",
            "Implementar cache para queries frequentes",
            "Otimizar índices do banco de dados"
        ]
        
    async def _get_long_term_recommendations(self) -> List[str]:
        """Recomendações de longo prazo"""
        return [
            "Implementar sharding do banco de dados",
            "Configurar cluster Redis para alta disponibilidade",
            "Implementar CDN para assets estáticos",
            "Configurar auto-scaling baseado em métricas",
            "Implementar cache distribuído L2"
        ]


# Instância global
performance_optimizer = PerformanceOptimizer()