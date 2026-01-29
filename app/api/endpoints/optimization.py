"""
API Endpoints para Otimização de Performance
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from app.services.performance_optimizer import performance_optimizer
from app.api.endpoints.auth import get_current_user
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/optimization", tags=["optimization"])


@router.get("/analyze")
async def analyze_performance(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Analisa performance atual e gera recomendações
    """
    try:
        result = await performance_optimizer.analyze_and_optimize()
        return result
        
    except Exception as e:
        logger.error("Error analyzing performance", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report")
async def get_optimization_report(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Obtém relatório completo de otimização
    """
    try:
        report = await performance_optimizer.get_optimization_report()
        return report
        
    except Exception as e:
        logger.error("Error getting optimization report", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_performance_metrics(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Obtém métricas de performance em tempo real
    """
    try:
        metrics = await performance_optimizer._collect_metrics()
        return {
            "timestamp": metrics.timestamp.isoformat(),
            "cpu_usage": metrics.cpu_usage,
            "memory_usage": metrics.memory_usage,
            "disk_usage": metrics.disk_usage,
            "database_connections": metrics.database_connections,
            "database_query_time": metrics.database_query_time,
            "redis_memory": metrics.redis_memory,
            "redis_hit_rate": metrics.redis_hit_rate,
            "api_response_time": metrics.api_response_time,
            "performance_score": await performance_optimizer._calculate_performance_score(metrics)
        }
        
    except Exception as e:
        logger.error("Error getting performance metrics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/thresholds")
async def get_performance_thresholds(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Obtém thresholds de performance configurados
    """
    return {
        "thresholds": performance_optimizer.thresholds,
        "description": {
            "cpu_critical": "CPU usage above this triggers critical alerts",
            "memory_critical": "Memory usage above this triggers critical alerts",
            "db_query_time_max": "Maximum acceptable database query time (seconds)",
            "api_response_time_max": "Maximum acceptable API response time (seconds)"
        }
    }


@router.put("/thresholds")
async def update_performance_thresholds(
    thresholds: Dict[str, float],
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Atualiza thresholds de performance
    """
    try:
        if current_user.get('role') != 'admin':
            raise HTTPException(
                status_code=403,
                detail="Only administrators can update performance thresholds"
            )
            
        # Validar thresholds
        valid_keys = set(performance_optimizer.thresholds.keys())
        invalid_keys = set(thresholds.keys()) - valid_keys
        
        if invalid_keys:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid threshold keys: {list(invalid_keys)}"
            )
            
        # Atualizar thresholds
        performance_optimizer.thresholds.update(thresholds)
        
        return {
            "success": True,
            "message": "Performance thresholds updated successfully",
            "updated_thresholds": thresholds
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating performance thresholds", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))