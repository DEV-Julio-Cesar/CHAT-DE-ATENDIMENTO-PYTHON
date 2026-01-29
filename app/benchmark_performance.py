#!/usr/bin/env python3
"""
Benchmark de Performance - Semana 3-4
"""
import asyncio
import time
import json
import statistics
from typing import List, Dict, Any
import sys
import os

# Adicionar o diretório app ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.cache_strategy import cache_manager, CacheConfig
from core.redis_client import redis_manager
from core.compression import compression_manager
from core.metrics import metrics_collector


class PerformanceBenchmark:
    """Benchmark de performance das otimizações"""
    
    def __init__(self):
        self.results = {}
    
    async def run_all_benchmarks(self):
        """Executar todos os benchmarks"""
        print("🚀 Iniciando Benchmark de Performance - Semana 3-4")
        print("=" * 60)
        
        # Benchmark de Cache
        await self.benchmark_cache_performance()
        
        # Benchmark de Compressão
        await self.benchmark_compression_performance()
        
        # Benchmark de Redis
        await self.benchmark_redis_performance()
        
        # Benchmark de Métricas
        await self.benchmark_metrics_performance()
        
        # Relatório final
        self.print_final_report()
    
    async def benchmark_cache_performance(self):
        """Benchmark do sistema de cache"""
        print("\n📊 Benchmark: Sistema de Cache Multi-Level")
        print("-" * 40)
        
        # Configurar cache para teste
        cache_manager.config = CacheConfig(
            ttl=300,
            max_size=1000,
            enable_l1=True,
            enable_l2=True
        )
        
        # Dados de teste
        test_data = {
            "user_id": "test_user_123",
            "profile": {"name": "Test User", "email": "test@example.com"},
            "settings": {"theme": "dark", "notifications": True},
            "large_data": ["item_" + str(i) for i in range(1000)]
        }
        
        # Teste 1: Cache Miss (primeira vez)
        cache_miss_times = []
        for i in range(10):
            key = f"cache_test_{i}"
            start_time = time.time()
            
            result = await cache_manager.get_or_set(
                key, 
                lambda: test_data, 
                ttl=300
            )
            
            cache_miss_times.append(time.time() - start_time)
        
        # Teste 2: Cache Hit L1 (memória)
        cache_hit_l1_times = []
        for i in range(10):
            key = f"cache_test_{i}"
            start_time = time.time()
            
            result = await cache_manager.get(key)
            
            cache_hit_l1_times.append(time.time() - start_time)
        
        # Teste 3: Cache Hit L2 (Redis) - limpar L1 primeiro
        cache_manager.l1_cache.clear()
        cache_hit_l2_times = []
        for i in range(10):
            key = f"cache_test_{i}"
            start_time = time.time()
            
            result = await cache_manager.get(key)
            
            cache_hit_l2_times.append(time.time() - start_time)
        
        # Calcular estatísticas
        avg_miss = statistics.mean(cache_miss_times) * 1000
        avg_hit_l1 = statistics.mean(cache_hit_l1_times) * 1000
        avg_hit_l2 = statistics.mean(cache_hit_l2_times) * 1000
        
        print(f"Cache Miss (primeira vez):  {avg_miss:.2f}ms")
        print(f"Cache Hit L1 (memória):     {avg_hit_l1:.2f}ms")
        print(f"Cache Hit L2 (Redis):       {avg_hit_l2:.2f}ms")
        print(f"Speedup L1 vs Miss:         {avg_miss/avg_hit_l1:.1f}x")
        print(f"Speedup L2 vs Miss:         {avg_miss/avg_hit_l2:.1f}x")
        
        # Obter estatísticas do cache
        stats = cache_manager.get_stats()
        print(f"Hit Rate:                   {stats['hit_rate']:.1f}%")
        print(f"L1 Cache Size:              {stats['l1_size']} items")
        
        self.results["cache"] = {
            "cache_miss_avg_ms": avg_miss,
            "cache_hit_l1_avg_ms": avg_hit_l1,
            "cache_hit_l2_avg_ms": avg_hit_l2,
            "speedup_l1": avg_miss/avg_hit_l1,
            "speedup_l2": avg_miss/avg_hit_l2,
            "hit_rate": stats['hit_rate']
        }
    
    async def benchmark_compression_performance(self):
        """Benchmark do sistema de compressão"""
        print("\n🗜️ Benchmark: Sistema de Compressão")
        print("-" * 40)
        
        # Dados de teste (JSON típico de API)
        test_data = {
            "users": [
                {
                    "id": i,
                    "name": f"User {i}",
                    "email": f"user{i}@example.com",
                    "profile": {
                        "bio": "This is a sample bio that repeats often " * 5,
                        "settings": {"theme": "dark", "notifications": True}
                    }
                }
                for i in range(100)
            ],
            "metadata": {
                "total": 100,
                "page": 1,
                "per_page": 100,
                "timestamp": "2024-01-01T10:00:00Z"
            }
        }
        
        json_content = json.dumps(test_data).encode("utf-8")
        original_size = len(json_content)
        
        print(f"Original Size:              {original_size:,} bytes ({original_size/1024:.1f} KB)")
        
        # Teste Gzip
        start_time = time.time()
        gzip_compressed = compression_manager.compress_content(json_content, "gzip")
        gzip_time = (time.time() - start_time) * 1000
        gzip_size = len(gzip_compressed)
        gzip_ratio = (1 - gzip_size / original_size) * 100
        
        # Teste Brotli
        start_time = time.time()
        brotli_compressed = compression_manager.compress_content(json_content, "brotli")
        brotli_time = (time.time() - start_time) * 1000
        brotli_size = len(brotli_compressed)
        brotli_ratio = (1 - brotli_size / original_size) * 100
        
        print(f"Gzip Compressed:            {gzip_size:,} bytes ({gzip_ratio:.1f}% reduction)")
        print(f"Gzip Time:                  {gzip_time:.2f}ms")
        print(f"Brotli Compressed:          {brotli_size:,} bytes ({brotli_ratio:.1f}% reduction)")
        print(f"Brotli Time:                {brotli_time:.2f}ms")
        print(f"Brotli vs Gzip Size:        {((gzip_size - brotli_size) / gzip_size * 100):.1f}% smaller")
        
        self.results["compression"] = {
            "original_size_kb": original_size / 1024,
            "gzip_ratio": gzip_ratio,
            "gzip_time_ms": gzip_time,
            "brotli_ratio": brotli_ratio,
            "brotli_time_ms": brotli_time,
            "brotli_advantage": (gzip_size - brotli_size) / gzip_size * 100
        }
    
    async def benchmark_redis_performance(self):
        """Benchmark do Redis com connection pooling"""
        print("\n🔴 Benchmark: Redis Connection Pooling")
        print("-" * 40)
        
        try:
            # Inicializar Redis
            await redis_manager.initialize()
            
            # Teste 1: Operações individuais
            individual_times = []
            for i in range(50):
                start_time = time.time()
                await redis_manager.set(f"bench_key_{i}", f"value_{i}")
                await redis_manager.get(f"bench_key_{i}")
                individual_times.append(time.time() - start_time)
            
            # Teste 2: Operações em lote (MSET/MGET)
            bulk_data = {f"bulk_key_{i}": f"bulk_value_{i}" for i in range(50)}
            
            start_time = time.time()
            await redis_manager.mset(bulk_data)
            mset_time = time.time() - start_time
            
            start_time = time.time()
            results = await redis_manager.mget(list(bulk_data.keys()))
            mget_time = time.time() - start_time
            
            # Teste 3: Pipeline
            pipeline_ops = [
                {"method": "set", "args": [f"pipe_key_{i}", f"pipe_value_{i}"]}
                for i in range(50)
            ]
            
            start_time = time.time()
            await redis_manager.pipeline_operations(pipeline_ops)
            pipeline_time = time.time() - start_time
            
            # Calcular estatísticas
            avg_individual = statistics.mean(individual_times) * 1000
            bulk_total_time = (mset_time + mget_time) * 1000
            pipeline_time_ms = pipeline_time * 1000
            
            print(f"Individual Ops (avg):       {avg_individual:.2f}ms per op")
            print(f"Bulk Ops (MSET+MGET):       {bulk_total_time:.2f}ms total")
            print(f"Pipeline Ops:               {pipeline_time_ms:.2f}ms total")
            print(f"Bulk vs Individual:         {(avg_individual * 50) / bulk_total_time:.1f}x faster")
            print(f"Pipeline vs Individual:     {(avg_individual * 50) / pipeline_time_ms:.1f}x faster")
            
            # Health check
            health = await redis_manager.health_check()
            print(f"Redis Health:               {health['status']}")
            print(f"Ping Time:                  {health['ping_time_ms']:.2f}ms")
            
            if health.get('pool_info'):
                pool_info = health['pool_info']
                print(f"Pool Connections:           {pool_info.get('created_connections', 'N/A')}")
            
            self.results["redis"] = {
                "individual_avg_ms": avg_individual,
                "bulk_total_ms": bulk_total_time,
                "pipeline_total_ms": pipeline_time_ms,
                "bulk_speedup": (avg_individual * 50) / bulk_total_time,
                "pipeline_speedup": (avg_individual * 50) / pipeline_time_ms,
                "ping_time_ms": health['ping_time_ms']
            }
            
        except Exception as e:
            print(f"Redis benchmark failed: {e}")
            self.results["redis"] = {"error": str(e)}
    
    async def benchmark_metrics_performance(self):
        """Benchmark do sistema de métricas"""
        print("\n📈 Benchmark: Sistema de Métricas")
        print("-" * 40)
        
        # Teste de overhead das métricas
        iterations = 1000
        
        # Sem métricas
        start_time = time.time()
        for i in range(iterations):
            # Simular operação simples
            result = i * 2 + 1
        no_metrics_time = time.time() - start_time
        
        # Com métricas
        start_time = time.time()
        for i in range(iterations):
            # Simular operação com métricas
            timer_id = metrics_collector.start_timer(f"test_op_{i}")
            result = i * 2 + 1
            metrics_collector.end_timer(timer_id)
            metrics_collector.record_cache_operation("test", "success")
        with_metrics_time = time.time() - start_time
        
        overhead = ((with_metrics_time - no_metrics_time) / no_metrics_time) * 100
        
        print(f"Without Metrics:            {no_metrics_time*1000:.2f}ms")
        print(f"With Metrics:               {with_metrics_time*1000:.2f}ms")
        print(f"Metrics Overhead:           {overhead:.1f}%")
        print(f"Per Operation Overhead:     {((with_metrics_time - no_metrics_time) / iterations)*1000000:.1f}μs")
        
        self.results["metrics"] = {
            "without_metrics_ms": no_metrics_time * 1000,
            "with_metrics_ms": with_metrics_time * 1000,
            "overhead_percent": overhead,
            "per_op_overhead_us": ((with_metrics_time - no_metrics_time) / iterations) * 1000000
        }
    
    def print_final_report(self):
        """Imprimir relatório final"""
        print("\n" + "=" * 60)
        print("📊 RELATÓRIO FINAL DE PERFORMANCE")
        print("=" * 60)
        
        if "cache" in self.results:
            cache = self.results["cache"]
            print(f"\n🎯 CACHE PERFORMANCE:")
            print(f"   • L1 Cache Speedup:      {cache['speedup_l1']:.1f}x")
            print(f"   • L2 Cache Speedup:      {cache['speedup_l2']:.1f}x")
            print(f"   • Hit Rate:              {cache['hit_rate']:.1f}%")
        
        if "compression" in self.results:
            comp = self.results["compression"]
            print(f"\n🗜️ COMPRESSION PERFORMANCE:")
            print(f"   • Gzip Reduction:        {comp['gzip_ratio']:.1f}%")
            print(f"   • Brotli Reduction:      {comp['brotli_ratio']:.1f}%")
            print(f"   • Brotli Advantage:      {comp['brotli_advantage']:.1f}%")
        
        if "redis" in self.results and "error" not in self.results["redis"]:
            redis = self.results["redis"]
            print(f"\n🔴 REDIS PERFORMANCE:")
            print(f"   • Bulk Operations:       {redis['bulk_speedup']:.1f}x faster")
            print(f"   • Pipeline Operations:   {redis['pipeline_speedup']:.1f}x faster")
            print(f"   • Connection Ping:       {redis['ping_time_ms']:.2f}ms")
        
        if "metrics" in self.results:
            metrics = self.results["metrics"]
            print(f"\n📈 METRICS OVERHEAD:")
            print(f"   • Total Overhead:        {metrics['overhead_percent']:.1f}%")
            print(f"   • Per Operation:         {metrics['per_op_overhead_us']:.1f}μs")
        
        print(f"\n✅ RESUMO GERAL:")
        print(f"   • Cache implementado com speedup de até {self.results.get('cache', {}).get('speedup_l1', 0):.1f}x")
        print(f"   • Compressão reduz dados em até {self.results.get('compression', {}).get('brotli_ratio', 0):.1f}%")
        print(f"   • Redis otimizado com speedup de até {self.results.get('redis', {}).get('pipeline_speedup', 0):.1f}x")
        print(f"   • Overhead de métricas: apenas {self.results.get('metrics', {}).get('overhead_percent', 0):.1f}%")
        
        print("\n🎉 SEMANA 3-4 CONCLUÍDA COM SUCESSO!")
        print("=" * 60)


async def main():
    """Função principal"""
    benchmark = PerformanceBenchmark()
    await benchmark.run_all_benchmarks()


if __name__ == "__main__":
    asyncio.run(main())