"""
Testes de Integração - Performance e Cache
"""
import pytest
import asyncio
import time
import json
from typing import List, Dict
from unittest.mock import AsyncMock, patch

from app.core.cache_strategy import cache_manager, cached, CacheLevel
from app.core.query_optimizer import query_optimizer
from app.core.redis_client import redis_manager
from app.core.compression import compression_manager, CompressedJSONResponse
from app.core.metrics import metrics_collector


class TestCacheStrategy:
    """Testes do sistema de cache avançado"""
    
    @pytest.mark.asyncio
    async def test_multilevel_cache_flow(self):
        """Testar fluxo completo do cache em múltiplas camadas"""
        key = "test_multilevel_key"
        test_data = {"message": "test data", "timestamp": time.time()}
        
        # Limpar cache
        await cache_manager.delete(key)
        
        # 1. Cache miss - deve retornar None
        result = await cache_manager.get(key)
        assert result is None
        
        # 2. Set no cache
        success = await cache_manager.set(key, test_data, ttl=60)
        assert success is True
        
        # 3. Get deve retornar dados (L1 cache)
        result = await cache_manager.get(key)
        assert result == test_data
        
        # 4. Limpar L1, deve buscar do L2 (Redis)
        cache_manager.l1_cache.clear()
        result = await cache_manager.get(key)
        assert result == test_data
        
        # 5. Verificar estatísticas
        stats = cache_manager.get_stats()
        assert stats["hits"] > 0
        assert stats["sets"] > 0
    
    @pytest.mark.asyncio
    async def test_get_or_set_pattern(self):
        """Testar padrão get-or-set"""
        key = "test_get_or_set"
        
        # Mock da função de fetch
        fetch_count = 0
        async def mock_fetch():
            nonlocal fetch_count
            fetch_count += 1
            return {"data": f"fetched_{fetch_count}", "count": fetch_count}
        
        # Limpar cache
        await cache_manager.delete(key)
        
        # 1. Primeira chamada - deve executar fetch
        result1 = await cache_manager.get_or_set(key, mock_fetch, ttl=60)
        assert result1["count"] == 1
        assert fetch_count == 1
        
        # 2. Segunda chamada - deve usar cache
        result2 = await cache_manager.get_or_set(key, mock_fetch, ttl=60)
        assert result2["count"] == 1  # Mesmo resultado
        assert fetch_count == 1  # Fetch não foi chamado novamente
    
    @pytest.mark.asyncio
    async def test_cache_warming(self):
        """Testar cache warming"""
        warming_config = {
            "warm_key_1": {
                "fetch_func": lambda: {"data": "warmed_1"},
                "ttl": 300
            },
            "warm_key_2": {
                "fetch_func": lambda: {"data": "warmed_2"},
                "ttl": 300
            }
        }
        
        # Executar warming
        results = await cache_manager.warm_cache(warming_config)
        
        # Verificar se tasks foram criadas
        assert len(results) == 2
        assert all(results.values())
        
        # Aguardar um pouco para warming completar
        await asyncio.sleep(0.1)
        
        # Verificar se dados foram cacheados
        result1 = await cache_manager.get("warm_key_1")
        result2 = await cache_manager.get("warm_key_2")
        
        assert result1 == {"data": "warmed_1"}
        assert result2 == {"data": "warmed_2"}
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_pattern(self):
        """Testar invalidação por padrão"""
        # Criar várias chaves com padrão
        keys = ["user:123:profile", "user:123:settings", "user:456:profile"]
        
        for key in keys:
            await cache_manager.set(key, {"data": key}, ttl=300)
        
        # Verificar se foram criadas
        for key in keys:
            result = await cache_manager.get(key)
            assert result is not None
        
        # Invalidar padrão user:123:*
        deleted_count = await cache_manager.invalidate_pattern("user:123:*")
        assert deleted_count >= 2  # Pelo menos 2 chaves
        
        # Verificar invalidação
        assert await cache_manager.get("user:123:profile") is None
        assert await cache_manager.get("user:123:settings") is None
        assert await cache_manager.get("user:456:profile") is not None
    
    def test_cached_decorator(self):
        """Testar decorador de cache"""
        call_count = 0
        
        @cached("test_func:{hash}", ttl=60)
        def expensive_function(param1: str, param2: int):
            nonlocal call_count
            call_count += 1
            return f"result_{param1}_{param2}_{call_count}"
        
        # Primeira chamada
        result1 = expensive_function("test", 123)
        assert call_count == 1
        
        # Segunda chamada com mesmos parâmetros - deve usar cache
        result2 = expensive_function("test", 123)
        assert result1 == result2
        assert call_count == 1  # Não deve ter chamado novamente
        
        # Chamada com parâmetros diferentes
        result3 = expensive_function("test", 456)
        assert call_count == 2
        assert result3 != result1


class TestQueryOptimizer:
    """Testes do otimizador de queries"""
    
    @pytest.mark.asyncio
    async def test_dashboard_stats_caching(self):
        """Testar cache das estatísticas do dashboard"""
        # Mock da sessão de banco
        with patch('app.core.query_optimizer.get_db_session') as mock_session:
            mock_session.return_value.__aenter__.return_value.execute = AsyncMock()
            mock_session.return_value.__aenter__.return_value.execute.return_value.first.return_value = type('Row', (), {
                'total_conversations': 100,
                'active_conversations': 25,
                'waiting_conversations': 10,
                'closed_conversations': 65,
                'active_users': 15
            })()
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalar.return_value = 50
            
            # Primeira chamada
            start_time = time.time()
            stats1 = await query_optimizer.get_dashboard_stats_cached()
            first_call_time = time.time() - start_time
            
            # Segunda chamada - deve ser mais rápida (cache)
            start_time = time.time()
            stats2 = await query_optimizer.get_dashboard_stats_cached()
            second_call_time = time.time() - start_time
            
            # Verificar resultados
            assert stats1 == stats2
            assert stats1["total_conversations"] == 100
            assert stats1["active_conversations"] == 25
            
            # Segunda chamada deve ser mais rápida (cache hit)
            assert second_call_time < first_call_time
    
    @pytest.mark.asyncio
    async def test_user_conversations_caching(self):
        """Testar cache de conversas do usuário"""
        user_id = "test_user_123"
        
        # Mock do otimizador
        with patch.object(query_optimizer, 'get_conversations_with_messages') as mock_get_convs:
            mock_conversations = [
                type('Conversation', (), {
                    'id': 'conv_1',
                    'chat_id': 'chat_1',
                    'estado': type('State', (), {'value': 'atendimento'})(),
                    'prioridade': 1,
                    'cliente': type('Client', (), {'nome': 'Cliente 1'})(),
                    'created_at': type('DateTime', (), {'isoformat': lambda: '2024-01-01T10:00:00'})(),
                    'updated_at': type('DateTime', (), {'isoformat': lambda: '2024-01-01T11:00:00'})()
                })()
            ]
            
            mock_get_convs.return_value = type('QueryResult', (), {
                'data': mock_conversations
            })()
            
            # Primeira chamada
            result1 = await query_optimizer.get_user_conversations_cached(user_id)
            
            # Segunda chamada - deve usar cache
            result2 = await query_optimizer.get_user_conversations_cached(user_id)
            
            # Verificar que função foi chamada apenas uma vez
            assert mock_get_convs.call_count == 1
            assert result1 == result2
            assert len(result1) == 1
            assert result1[0]["id"] == "conv_1"


class TestRedisPerformance:
    """Testes de performance do Redis"""
    
    @pytest.mark.asyncio
    async def test_bulk_operations_performance(self):
        """Testar performance de operações em lote"""
        # Preparar dados de teste
        test_data = {f"bulk_key_{i}": f"value_{i}" for i in range(100)}
        
        # Teste MSET vs SET individual
        start_time = time.time()
        success = await redis_manager.mset(test_data)
        mset_time = time.time() - start_time
        
        assert success is True
        
        # Teste MGET vs GET individual
        keys = list(test_data.keys())
        
        start_time = time.time()
        results = await redis_manager.mget(keys)
        mget_time = time.time() - start_time
        
        assert len(results) == 100
        assert all(r is not None for r in results)
        
        # MGET deve ser mais eficiente que GETs individuais
        start_time = time.time()
        individual_results = []
        for key in keys[:10]:  # Testar apenas 10 para não demorar
            result = await redis_manager.get(key)
            individual_results.append(result)
        individual_time = time.time() - start_time
        
        # Calcular tempo por operação
        mget_per_op = mget_time / 100
        individual_per_op = individual_time / 10
        
        # MGET deve ser mais eficiente
        assert mget_per_op < individual_per_op
    
    @pytest.mark.asyncio
    async def test_pipeline_operations(self):
        """Testar operações em pipeline"""
        operations = [
            {"method": "set", "args": ["pipe_key_1", "value_1"]},
            {"method": "set", "args": ["pipe_key_2", "value_2"]},
            {"method": "get", "args": ["pipe_key_1"]},
            {"method": "get", "args": ["pipe_key_2"]},
        ]
        
        results = await redis_manager.pipeline_operations(operations)
        
        assert len(results) == 4
        assert results[0] is True  # SET result
        assert results[1] is True  # SET result
        assert results[2] == "value_1"  # GET result
        assert results[3] == "value_2"  # GET result
    
    @pytest.mark.asyncio
    async def test_connection_pool_stats(self):
        """Testar estatísticas do pool de conexões"""
        health = await redis_manager.health_check()
        
        assert health["status"] == "healthy"
        assert "pool_info" in health
        assert "connection_stats" in health
        assert "ping_time_ms" in health
        
        # Verificar se pool está funcionando
        if health["pool_info"]:
            assert "created_connections" in health["pool_info"]
            assert "available_connections" in health["pool_info"]


class TestCompressionSystem:
    """Testes do sistema de compressão"""
    
    def test_compression_decision(self):
        """Testar decisão de compressão"""
        # Conteúdo pequeno - não deve comprimir
        small_content = b"small"
        assert not compression_manager.should_compress(small_content, "application/json")
        
        # Conteúdo grande - deve comprimir
        large_content = b"x" * 2000
        assert compression_manager.should_compress(large_content, "application/json")
        
        # Tipo não comprimível - não deve comprimir
        assert not compression_manager.should_compress(large_content, "image/jpeg")
    
    def test_encoding_selection(self):
        """Testar seleção de encoding"""
        # Brotli preferido
        assert compression_manager.get_best_encoding("gzip, deflate, br") == "brotli"
        
        # Gzip como fallback
        assert compression_manager.get_best_encoding("gzip, deflate") == "gzip"
        
        # Deflate como último recurso
        assert compression_manager.get_best_encoding("deflate") == "deflate"
        
        # Nenhum suportado
        assert compression_manager.get_best_encoding("identity") is None
    
    def test_compression_effectiveness(self):
        """Testar efetividade da compressão"""
        # Dados JSON repetitivos (comprimem bem)
        test_data = {"message": "test " * 100, "data": [{"id": i, "name": f"item_{i}"} for i in range(50)]}
        json_content = json.dumps(test_data).encode("utf-8")
        
        original_size = len(json_content)
        
        # Testar gzip
        gzip_compressed = compression_manager.compress_content(json_content, "gzip")
        gzip_ratio = (1 - len(gzip_compressed) / original_size) * 100
        
        # Testar brotli
        brotli_compressed = compression_manager.compress_content(json_content, "brotli")
        brotli_ratio = (1 - len(brotli_compressed) / original_size) * 100
        
        # Verificar que houve compressão significativa
        assert gzip_ratio > 50  # Pelo menos 50% de compressão
        assert brotli_ratio > 50
        
        # Brotli geralmente é melhor que gzip
        assert len(brotli_compressed) <= len(gzip_compressed)
    
    def test_compression_stats(self):
        """Testar estatísticas de compressão"""
        # Resetar stats
        compression_manager.compression_stats = {
            "gzip": {"requests": 0, "bytes_saved": 0},
            "brotli": {"requests": 0, "bytes_saved": 0},
            "deflate": {"requests": 0, "bytes_saved": 0},
            "none": {"requests": 0}
        }
        
        # Comprimir alguns dados
        test_content = b"x" * 1000
        compression_manager.compress_content(test_content, "gzip")
        compression_manager.compress_content(test_content, "brotli")
        
        stats = compression_manager.get_stats()
        
        assert stats["total_requests"] == 2
        assert stats["total_bytes_saved"] > 0
        assert stats["by_encoding"]["gzip"]["requests"] == 1
        assert stats["by_encoding"]["brotli"]["requests"] == 1


class TestMetricsCollection:
    """Testes de coleta de métricas"""
    
    def test_metrics_recording(self):
        """Testar gravação de métricas"""
        # Resetar métricas
        initial_stats = metrics_collector.start_timer("test_operation")
        
        # Simular operação
        time.sleep(0.01)
        
        duration = metrics_collector.end_timer(initial_stats)
        
        assert duration > 0
        assert duration < 1  # Deve ser menos de 1 segundo
    
    def test_conversation_metrics(self):
        """Testar métricas de conversa"""
        # Registrar criação de conversa
        metrics_collector.record_conversation_created("whatsapp", "high")
        
        # Registrar duração de conversa
        metrics_collector.record_conversation_duration(300.5, "resolved", False)
        
        # Registrar escalação de bot
        metrics_collector.record_bot_escalation("low_confidence", 0.3)
        
        # Verificar que métricas foram registradas (não há erro)
        assert True  # Se chegou aqui, as métricas foram registradas
    
    def test_cache_metrics(self):
        """Testar métricas de cache"""
        metrics_collector.record_cache_operation("get", "hit")
        metrics_collector.record_cache_operation("set", "success")
        metrics_collector.update_cache_hit_rate("redis", 85.5)
        
        # Verificar que não houve erro
        assert True