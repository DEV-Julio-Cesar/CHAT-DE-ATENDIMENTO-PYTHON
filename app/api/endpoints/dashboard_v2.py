"""
Dashboard V2 - Métricas Reais do SQL Server
CIANET PROVEDOR - v3.0

Dashboard completo com:
- Métricas em tempo real
- Gráficos de performance
- KPIs de atendimento
- Ranking de atendentes
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, status, Request, Depends, Query
from pydantic import BaseModel, Field

from app.core.auth_manager import get_current_user, require_permissions
from app.core.sqlserver_db import sqlserver_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["Dashboard V2"])


# ============================================================================
# SCHEMAS
# ============================================================================

class TodayMetrics(BaseModel):
    """Métricas do dia"""
    total_conversations: int
    waiting_in_queue: int
    in_progress: int
    resolved_today: int
    avg_response_time_minutes: Optional[float]
    avg_resolution_time_minutes: Optional[float]
    avg_rating: Optional[float]
    agents_online: int


class ConversationTrend(BaseModel):
    """Tendência de conversas"""
    hour: str
    total: int
    resolved: int


class AgentPerformance(BaseModel):
    """Performance do atendente"""
    id: int
    name: str
    conversations_today: int
    resolved_today: int
    avg_resolution_minutes: Optional[float]
    avg_rating: Optional[float]
    status: str


class QueueStatus(BaseModel):
    """Status da fila"""
    waiting: int
    avg_wait_time_minutes: Optional[float]
    longest_wait_minutes: Optional[int]
    by_priority: Dict[str, int]


class CategoryDistribution(BaseModel):
    """Distribuição por categoria"""
    category: str
    total: int
    percentage: float


class SatisfactionMetrics(BaseModel):
    """Métricas de satisfação"""
    total_rated: int
    avg_rating: float
    distribution: Dict[str, int]  # 1-5 stars


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get(
    "/metrics/today",
    response_model=TodayMetrics,
    summary="Métricas do dia"
)
async def get_today_metrics(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Obter métricas consolidadas do dia atual.
    """
    try:
        stats = sqlserver_manager.get_conversation_stats()
        
        # Obter agentes online
        agents = sqlserver_manager.get_online_agents()
        
        return TodayMetrics(
            total_conversations=stats.get("total_today", 0),
            waiting_in_queue=stats.get("waiting", 0),
            in_progress=stats.get("in_progress", 0),
            resolved_today=stats.get("resolved_today", 0),
            avg_response_time_minutes=stats.get("avg_response_time_minutes"),
            avg_resolution_time_minutes=stats.get("avg_resolution_time_minutes"),
            avg_rating=None,  # TODO: Implementar
            agents_online=len(agents)
        )
    except Exception as e:
        logger.error(f"Error getting today metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter métricas"
        )


@router.get(
    "/metrics/trends",
    response_model=List[ConversationTrend],
    summary="Tendência de conversas por hora"
)
async def get_conversation_trends(
    request: Request,
    date: Optional[str] = Query(None, description="Data (YYYY-MM-DD), default=hoje"),
    current_user: dict = Depends(get_current_user)
):
    """
    Obter tendência de conversas por hora.
    """
    try:
        target_date = date or datetime.now().strftime("%Y-%m-%d")
        
        with sqlserver_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    DATEPART(HOUR, started_at) as hour,
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) as resolved
                FROM conversas
                WHERE CAST(started_at AS DATE) = ?
                GROUP BY DATEPART(HOUR, started_at)
                ORDER BY hour
            """, (target_date,))
            
            trends = []
            for row in cursor.fetchall():
                trends.append(ConversationTrend(
                    hour=f"{row.hour:02d}:00",
                    total=row.total,
                    resolved=row.resolved
                ))
            
            return trends
    except Exception as e:
        logger.error(f"Error getting trends: {e}")
        return []


@router.get(
    "/agents/performance",
    response_model=List[AgentPerformance],
    summary="Performance dos atendentes"
)
async def get_agents_performance(
    request: Request,
    date: Optional[str] = Query(None, description="Data (YYYY-MM-DD), default=hoje"),
    current_user: dict = Depends(require_permissions(["dashboard:read", "users:read"]))
):
    """
    Obter ranking de performance dos atendentes.
    Requer permissão de supervisor ou admin.
    """
    try:
        target_date = date or datetime.now().strftime("%Y-%m-%d")
        
        with sqlserver_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    u.id,
                    u.nome,
                    COUNT(c.id) as conversations_today,
                    SUM(CASE WHEN c.status = 'resolved' THEN 1 ELSE 0 END) as resolved_today,
                    AVG(
                        CASE WHEN c.resolved_at IS NOT NULL 
                        THEN DATEDIFF(MINUTE, c.started_at, c.resolved_at) 
                        ELSE NULL END
                    ) as avg_resolution_minutes,
                    AVG(CAST(c.rating AS FLOAT)) as avg_rating,
                    CASE 
                        WHEN u.last_activity_at > DATEADD(MINUTE, -5, GETDATE()) THEN 'online'
                        ELSE 'offline'
                    END as status
                FROM usuarios u
                LEFT JOIN conversas c ON u.id = c.attendant_id 
                    AND CAST(c.started_at AS DATE) = ?
                WHERE u.role IN ('atendente', 'supervisor') AND u.is_active = 1
                GROUP BY u.id, u.nome, u.last_activity_at
                ORDER BY resolved_today DESC, conversations_today DESC
            """, (target_date,))
            
            agents = []
            for row in cursor.fetchall():
                agents.append(AgentPerformance(
                    id=row.id,
                    name=row.nome,
                    conversations_today=row.conversations_today or 0,
                    resolved_today=row.resolved_today or 0,
                    avg_resolution_minutes=float(row.avg_resolution_minutes) if row.avg_resolution_minutes else None,
                    avg_rating=float(row.avg_rating) if row.avg_rating else None,
                    status=row.status
                ))
            
            return agents
    except Exception as e:
        logger.error(f"Error getting agents performance: {e}")
        return []


@router.get(
    "/queue/status",
    response_model=QueueStatus,
    summary="Status da fila"
)
async def get_queue_status(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Obter status atual da fila de espera.
    """
    try:
        with sqlserver_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Contagem e tempos de espera
            cursor.execute("""
                SELECT 
                    COUNT(*) as waiting,
                    AVG(DATEDIFF(MINUTE, started_at, GETDATE())) as avg_wait,
                    MAX(DATEDIFF(MINUTE, started_at, GETDATE())) as max_wait
                FROM conversas
                WHERE status = 'waiting'
            """)
            
            row = cursor.fetchone()
            waiting = row.waiting or 0
            avg_wait = row.avg_wait
            max_wait = row.max_wait
            
            # Por prioridade
            cursor.execute("""
                SELECT priority, COUNT(*) as total
                FROM conversas
                WHERE status = 'waiting'
                GROUP BY priority
            """)
            
            by_priority = {"urgent": 0, "high": 0, "normal": 0, "low": 0}
            for row in cursor.fetchall():
                by_priority[row.priority] = row.total
            
            return QueueStatus(
                waiting=waiting,
                avg_wait_time_minutes=float(avg_wait) if avg_wait else None,
                longest_wait_minutes=max_wait,
                by_priority=by_priority
            )
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        return QueueStatus(
            waiting=0,
            avg_wait_time_minutes=None,
            longest_wait_minutes=None,
            by_priority={"urgent": 0, "high": 0, "normal": 0, "low": 0}
        )


@router.get(
    "/categories/distribution",
    response_model=List[CategoryDistribution],
    summary="Distribuição por categoria"
)
async def get_category_distribution(
    request: Request,
    days: int = Query(7, ge=1, le=30, description="Últimos N dias"),
    current_user: dict = Depends(get_current_user)
):
    """
    Obter distribuição de conversas por categoria.
    """
    try:
        with sqlserver_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    ISNULL(category, 'Não categorizado') as category,
                    COUNT(*) as total
                FROM conversas
                WHERE started_at >= DATEADD(DAY, -?, GETDATE())
                GROUP BY category
                ORDER BY total DESC
            """, (days,))
            
            rows = cursor.fetchall()
            total_all = sum(row.total for row in rows) if rows else 1
            
            distribution = []
            for row in rows:
                distribution.append(CategoryDistribution(
                    category=row.category,
                    total=row.total,
                    percentage=round((row.total / total_all) * 100, 1)
                ))
            
            return distribution
    except Exception as e:
        logger.error(f"Error getting category distribution: {e}")
        return []


@router.get(
    "/satisfaction",
    response_model=SatisfactionMetrics,
    summary="Métricas de satisfação"
)
async def get_satisfaction_metrics(
    request: Request,
    days: int = Query(30, ge=1, le=90, description="Últimos N dias"),
    current_user: dict = Depends(get_current_user)
):
    """
    Obter métricas de satisfação do cliente.
    """
    try:
        with sqlserver_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_rated,
                    AVG(CAST(rating AS FLOAT)) as avg_rating,
                    SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) as star_1,
                    SUM(CASE WHEN rating = 2 THEN 1 ELSE 0 END) as star_2,
                    SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END) as star_3,
                    SUM(CASE WHEN rating = 4 THEN 1 ELSE 0 END) as star_4,
                    SUM(CASE WHEN rating = 5 THEN 1 ELSE 0 END) as star_5
                FROM conversas
                WHERE rating IS NOT NULL 
                AND resolved_at >= DATEADD(DAY, -?, GETDATE())
            """, (days,))
            
            row = cursor.fetchone()
            
            return SatisfactionMetrics(
                total_rated=row.total_rated or 0,
                avg_rating=float(row.avg_rating) if row.avg_rating else 0,
                distribution={
                    "1": row.star_1 or 0,
                    "2": row.star_2 or 0,
                    "3": row.star_3 or 0,
                    "4": row.star_4 or 0,
                    "5": row.star_5 or 0
                }
            )
    except Exception as e:
        logger.error(f"Error getting satisfaction metrics: {e}")
        return SatisfactionMetrics(
            total_rated=0,
            avg_rating=0,
            distribution={"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
        )


@router.get(
    "/realtime",
    summary="Dados em tempo real"
)
async def get_realtime_data(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Obter dados consolidados para dashboard em tempo real.
    """
    try:
        # Métricas do dia
        stats = sqlserver_manager.get_conversation_stats()
        
        # Agentes online
        agents = sqlserver_manager.get_online_agents()
        
        # Fila de espera
        queue = sqlserver_manager.get_waiting_conversations()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "conversations_today": stats.get("total_today", 0),
                "resolved_today": stats.get("resolved_today", 0),
                "in_queue": stats.get("waiting", 0),
                "in_progress": stats.get("in_progress", 0),
                "avg_response_time": stats.get("avg_response_time_minutes"),
                "avg_resolution_time": stats.get("avg_resolution_time_minutes")
            },
            "agents": [
                {
                    "id": a["id"],
                    "name": a["nome"],
                    "status": a.get("status", "online"),
                    "current_conversations": a.get("current_conversations", 0),
                    "available_slots": a.get("available_slots", 0)
                }
                for a in agents
            ],
            "queue": {
                "total": len(queue),
                "urgent": len([q for q in queue if q.get("priority") == "urgent"]),
                "high": len([q for q in queue if q.get("priority") == "high"]),
                "oldest_wait_minutes": queue[0].get("waiting_minutes", 0) if queue else 0
            }
        }
    except Exception as e:
        logger.error(f"Error getting realtime data: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": {},
            "agents": [],
            "queue": {"total": 0}
        }


@router.get(
    "/my-stats",
    summary="Minhas estatísticas (atendente)"
)
async def get_my_stats(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Obter estatísticas do próprio atendente.
    """
    try:
        user_id = current_user["id"]
        
        with sqlserver_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Estatísticas de hoje
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_today,
                    SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) as resolved_today,
                    SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
                    AVG(CAST(rating AS FLOAT)) as avg_rating,
                    AVG(
                        CASE WHEN resolved_at IS NOT NULL 
                        THEN DATEDIFF(MINUTE, started_at, resolved_at) 
                        ELSE NULL END
                    ) as avg_resolution_minutes
                FROM conversas
                WHERE attendant_id = ? 
                AND CAST(started_at AS DATE) = CAST(GETDATE() AS DATE)
            """, (user_id,))
            
            row = cursor.fetchone()
            
            # Estatísticas do mês
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_month,
                    SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) as resolved_month,
                    AVG(CAST(rating AS FLOAT)) as avg_rating_month
                FROM conversas
                WHERE attendant_id = ? 
                AND started_at >= DATEADD(DAY, -30, GETDATE())
            """, (user_id,))
            
            month_row = cursor.fetchone()
            
            return {
                "today": {
                    "total": row.total_today or 0,
                    "resolved": row.resolved_today or 0,
                    "in_progress": row.in_progress or 0,
                    "avg_rating": float(row.avg_rating) if row.avg_rating else None,
                    "avg_resolution_minutes": float(row.avg_resolution_minutes) if row.avg_resolution_minutes else None
                },
                "month": {
                    "total": month_row.total_month or 0,
                    "resolved": month_row.resolved_month or 0,
                    "avg_rating": float(month_row.avg_rating_month) if month_row.avg_rating_month else None
                }
            }
    except Exception as e:
        logger.error(f"Error getting my stats: {e}")
        return {"today": {}, "month": {}}
