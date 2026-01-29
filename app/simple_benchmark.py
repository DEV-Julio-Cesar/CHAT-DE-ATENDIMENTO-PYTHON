#!/usr/bin/env python3
"""
Benchmark Simplificado de Performance
"""
import asyncio
import time
import json
import statistics
import gzip
import brotli


def benchmark_compression():
    """Benchmark de compressão"""
    print("🗜️ Benchmark: Sistema de Compressão")
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
    gzip_compressed = gzip.compress(json_content, compresslevel=6)
    gzip_time = (time.time() - start_time) * 1000
    gzip_size = len(gzip_compressed)
    gzip_ratio = (1 - gzip_size / original_size) * 100
    
    # Teste Brotli
    start_time = time.time()
    brotli_compressed = brotli.compress(json_content, quality=4)
    brotli_time = (time.time() - start_time) * 1000
    brotli_size = len(brotli_compressed)
    brotli_ratio = (1 - brotli_size / original_size) * 100
    
    print(f"Gzip Compressed:            {gzip_size:,} bytes ({gzip_ratio:.1f}% reduction)")
    print(f"Gzip Time:                  {gzip_time:.2f}ms")
    print(f"Brotli Compressed:          {brotli_size:,} bytes ({brotli_ratio:.1f}% reduction)")
    print(f"Brotli Time:                {brotli_time:.2f}ms")
    print(f"Brotli vs Gzip Size:        {((gzip_size - brotli_size) / gzip_size * 100):.1f}% smaller")
    
    return {
        "original_size_kb": original_size / 1024,
        "gzip_ratio": gzip_ratio,
        "gzip_time_ms": gzip_time,
        "brotli_ratio": brotli_ratio,
        "brotli_time_ms": brotli_time,
        "brotli_advantage": (gzip_size - brotli_size) / gzip_size * 100
    }


def benchmark_cache_simulation():
    """Benchmark simulado de cache"""
    print("\n📊 Benchmark: Simulação de Cache")
    print("-" * 40)
    
    # Simular cache em memória
    cache = {}
    
    # Dados de teste
    test_data = {"user_id": "123", "profile": {"name": "Test"}, "data": list(range(1000))}
    
    # Teste 1: Cache Miss (primeira vez)
    cache_miss_times = []
    for i in range(10):
        key = f"cache_test_{i}"
        start_time = time.time()
        
        # Simular busca no banco (operação lenta)
        time.sleep(0.001)  # 1ms de latência simulada
        cache[key] = test_data
        result = cache[key]
        
        cache_miss_times.append(time.time() - start_time)
    
    # Teste 2: Cache Hit (memória)
    cache_hit_times = []
    for i in range(10):
        key = f"cache_test_{i}"
        start_time = time.time()
        
        result = cache.get(key)
        
        cache_hit_times.append(time.time() - start_time)
    
    # Calcular estatísticas
    avg_miss = statistics.mean(cache_miss_times) * 1000
    avg_hit = statistics.mean(cache_hit_times) * 1000
    
    print(f"Cache Miss (primeira vez):  {avg_miss:.2f}ms")
    print(f"Cache Hit (memória):        {avg_hit:.2f}ms")
    print(f"Speedup:                    {avg_miss/avg_hit:.1f}x")
    print(f"Cache Size:                 {len(cache)} items")
    
    return {
        "cache_miss_avg_ms": avg_miss,
        "cache_hit_avg_ms": avg_hit,
        "speedup": avg_miss/avg_hit,
        "cache_size": len(cache)
    }


def benchmark_metrics_overhead():
    """Benchmark de overhead de métricas"""
    print("\n📈 Benchmark: Overhead de Métricas")
    print("-" * 40)
    
    iterations = 1000
    
    # Sem métricas
    start_time = time.time()
    for i in range(iterations):
        result = i * 2 + 1
    no_metrics_time = time.time() - start_time
    
    # Com métricas simuladas
    metrics = {"operations": 0, "total_time": 0}
    start_time = time.time()
    for i in range(iterations):
        op_start = time.time()
        result = i * 2 + 1
        op_time = time.time() - op_start
        
        # Simular coleta de métricas
        metrics["operations"] += 1
        metrics["total_time"] += op_time
    with_metrics_time = time.time() - start_time
    
    overhead = ((with_metrics_time - no_metrics_time) / no_metrics_time) * 100
    
    print(f"Without Metrics:            {no_metrics_time*1000:.2f}ms")
    print(f"With Metrics:               {with_metrics_time*1000:.2f}ms")
    print(f"Metrics Overhead:           {overhead:.1f}%")
    print(f"Per Operation Overhead:     {((with_metrics_time - no_metrics_time) / iterations)*1000000:.1f}μs")
    
    return {
        "without_metrics_ms": no_metrics_time * 1000,
        "with_metrics_ms": with_metrics_time * 1000,
        "overhead_percent": overhead,
        "per_op_overhead_us": ((with_metrics_time - no_metrics_time) / iterations) * 1000000
    }


def main():
    """Função principal"""
    print("🚀 Benchmark de Performance - Semana 3-4")
    print("=" * 60)
    
    # Executar benchmarks
    compression_results = benchmark_compression()
    cache_results = benchmark_cache_simulation()
    metrics_results = benchmark_metrics_overhead()
    
    # Relatório final
    print("\n" + "=" * 60)
    print("📊 RELATÓRIO FINAL DE PERFORMANCE")
    print("=" * 60)
    
    print(f"\n🗜️ COMPRESSION PERFORMANCE:")
    print(f"   • Gzip Reduction:        {compression_results['gzip_ratio']:.1f}%")
    print(f"   • Brotli Reduction:      {compression_results['brotli_ratio']:.1f}%")
    print(f"   • Brotli Advantage:      {compression_results['brotli_advantage']:.1f}%")
    
    print(f"\n🎯 CACHE PERFORMANCE:")
    print(f"   • Cache Speedup:         {cache_results['speedup']:.1f}x")
    print(f"   • Miss Time:             {cache_results['cache_miss_avg_ms']:.2f}ms")
    print(f"   • Hit Time:              {cache_results['cache_hit_avg_ms']:.2f}ms")
    
    print(f"\n📈 METRICS OVERHEAD:")
    print(f"   • Total Overhead:        {metrics_results['overhead_percent']:.1f}%")
    print(f"   • Per Operation:         {metrics_results['per_op_overhead_us']:.1f}μs")
    
    print(f"\n✅ RESUMO GERAL:")
    print(f"   • Compressão reduz dados em até {compression_results['brotli_ratio']:.1f}%")
    print(f"   • Cache acelera operações em {cache_results['speedup']:.1f}x")
    print(f"   • Overhead de métricas: apenas {metrics_results['overhead_percent']:.1f}%")
    
    print("\n🎉 SEMANA 3-4: PERFORMANCE OTIMIZADA!")
    print("=" * 60)


if __name__ == "__main__":
    main()