"""
Otimizador de Queries - Resolver N+1 e Otimizar Performance
"""
import asyncio
from typing import List, Dict, Any, Optional, Set, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload, contains_eager
from sqlalchemy import select, func, and_, or_
from dataclasses import dataclass
import structlog

from app.models.database import (
    Usuario, ClienteWhatsApp, Conversa, Mensagem, 
    Campanha, EnvioCampanha, ConversationState, UserRole
)
from app.core.database import get_db_session
from app.core.cache_strategy import cache_manager, cached
from app.core.metrics import metrics_collector, measure_time

logger = structlog.get_logger(__name__)


@dataclass
class QueryResult:
    """Resultado de query otimizada"""
    data: Any
    total_count: Optional[int] = None
    execution_time: Optional[float] = None
    cache_hit: bool = False


class QueryOptimizer:
    """Otimizador de queries com cache e preload"""
    
    def __init__(self):
        self.query_cache: Dict[str, Any] = {}
    
    @measure_time("database_query", component="query_optimizer", operation="get_conversations_with_messages")
    async def get_conversations_with_messages(
        self,
        session: AsyncSession,
        user_id: Optional[str] = None,
        state: Optional[ConversationState] = None,
        limit: int = 50,
        offset: int = 0,
        include_messages: bool = True
    ) -> QueryResult:
        """
        Buscar conversas com mensagens (otimizado para evitar N+1)
        """
        try:
            # Query base com joins otimizados
            query = select(Conversa).options(
                # Preload relacionamentos para evitar N+1
                selectinload(Conversa.cliente),
                selectinload(Conversa.atendente),
                selectinload(Conversa.mensagens).options(
                    # Limitar mensagens por conversa para performance
                    selectinload(Mensagem.conversa)
                ) if include_messages else selectinload(Conversa.mensagens).options()
            )
            
            # Filtros
            filters = []
            if user_id:
                filters.append(Conversa.atendente_id == user_id)
            if state:
                filters.append(Conversa.estado == state)
            
            if filters:
                query = query.where(and_(*filters))
            
            # Ordenação e paginação
            query = query.order_by(Conversa.updated_at.desc())
            
            # Count total (query separada otimizada)
            count_query = select(func.count(Conversa.id))
            if filters:
                count_query = count_query.where(and_(*filters))
            
            # Executar queries
            total_result = await session.execute(count_query)
            total_count = total_result.scalar()
            
            # Query principal com paginação
            paginated_query = query.offset(offset).limit(limit)
            result = await session.execute(paginated_query)
            conversations = result.scalars().all()
            
            return QueryResult(
                data=conversations,
                total_count=total_count,
                cache_hit=False
            )
            
        except Exception as e:
            logger.error("Error fetching conversations", error=str(e))
            raise
    
    @cached("user_conversations:{hash}", ttl=1800)  # Cache por 30 min
    async def get_user_conversations_cached(
        self,
        user_id: str,
        state: Optional[ConversationState] = None,
        limit: int = 20
    ) -> List[Dict]:
        """Buscar conversas do usuário com cache"""
        async with get_db_session() as session:
            result = await self.get_conversations_with_messages(
                session, user_id, state, limit, include_messages=False
            )
            
            # Converter para dict para serialização
            conversations_data = []
            for conv in result.data:
                conversations_data.append({
                    "id": str(conv.id),
                    "chat_id": conv.chat_id,
                    "estado": conv.estado.value,
                    "prioridade": conv.prioridade,
                    "cliente_nome": conv.cliente.nome if conv.cliente else None,
                    "created_at": conv.created_at.isoformat(),
                    "updated_at": conv.updated_at.isoformat()
                })
            
            return conversations_data
    
    @measure_time("database_query", component="query_optimizer", operation="get_conversation_messages")
    async def get_conversation_messages_optimized(
        self,
        session: AsyncSession,
        conversation_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> QueryResult:
        """
        Buscar mensagens de uma conversa (otimizado)
        """
        try:
            # Query otimizada com índices
            query = select(Mensagem).where(
                Mensagem.conversa_id == conversation_id
            ).order_by(
                Mensagem.created_at.desc()
            ).offset(offset).limit(limit)
            
            # Count total
            count_query = select(func.count(Mensagem.id)).where(
                Mensagem.conversa_id == conversation_id
            )
            
            # Executar queries
            total_result = await session.execute(count_query)
            total_count = total_result.scalar()
            
            result = await session.execute(query)
            messages = result.scalars().all()
            
            return QueryResult(
                data=messages,
                total_count=total_count
            )
            
        except Exception as e:
            logger.error("Error fetching messages", conversation_id=conversation_id, error=str(e))
            raise
    
    @measure_time("database_query", component="query_optimizer", operation="get_dashboard_stats")
    async def get_dashboard_stats_optimized(self, session: AsyncSession) -> Dict[str, Any]:
        """
        Estatísticas do dashboard (otimizado com uma query)
        """
        try:
            # Query única para múltiplas estatísticas
            stats_query = select(
                func.count(Conversa.id).label('total_conversations'),
                func.count(Conversa.id).filter(
                    Conversa.estado == ConversationState.ATENDIMENTO
                ).label('active_conversations'),
                func.count(Conversa.id).filter(
                    Conversa.estado == ConversationState.ESPERA
                ).label('waiting_conversations'),
                func.count(Conversa.id).filter(
                    Conversa.estado == ConversationState.ENCERRADO
                ).label('closed_conversations'),
                func.count(Usuario.id).filter(
                    Usuario.ativo == True
                ).label('active_users')
            ).select_from(
                Conversa
            ).outerjoin(Usuario)
            
            result = await session.execute(stats_query)
            row = result.first()
            
            # Mensagens de hoje (query separada otimizada)
            from datetime import datetime, timedelta
            today = datetime.utcnow().date()
            messages_today_query = select(func.count(Mensagem.id)).where(
                func.date(Mensagem.created_at) == today
            )
            
            messages_result = await session.execute(messages_today_query)
            messages_today = messages_result.scalar()
            
            return {
                "total_conversations": row.total_conversations or 0,
                "active_conversations": row.active_conversations or 0,
                "waiting_conversations": row.waiting_conversations or 0,
                "closed_conversations": row.closed_conversations or 0,
                "active_users": row.active_users or 0,
                "messages_today": messages_today or 0,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Error fetching dashboard stats", error=str(e))
            raise
    
    @cached("dashboard_stats", ttl=300)  # Cache por 5 min
    async def get_dashboard_stats_cached(self) -> Dict[str, Any]:
        """Estatísticas do dashboard com cache"""
        async with get_db_session() as session:
            return await self.get_dashboard_stats_optimized(session)
    
    @measure_time("database_query", component="query_optimizer", operation="bulk_update_conversation_states")
    async def bulk_update_conversation_states(
        self,
        session: AsyncSession,
        conversation_ids: List[str],
        new_state: ConversationState,
        atendente_id: Optional[str] = None
    ) -> int:
        """
        Atualização em lote de estados de conversa (otimizado)
        """
        try:
            from sqlalchemy import update
            
            # Update em lote
            update_data = {"estado": new_state, "updated_at": func.now()}
            if atendente_id:
                update_data["atendente_id"] = atendente_id
            
            stmt = update(Conversa).where(
                Conversa.id.in_(conversation_ids)
            ).values(**update_data)
            
            result = await session.execute(stmt)
            await session.commit()
            
            updated_count = result.rowcount
            logger.info("Bulk conversation update", 
                       count=updated_count, 
                       new_state=new_state.value)
            
            # Invalidar cache relacionado
            await cache_manager.invalidate_pattern("user_conversations:*")
            await cache_manager.invalidate_pattern("dashboard_stats")
            
            return updated_count
            
        except Exception as e:
            await session.rollback()
            logger.error("Error in bulk update", error=str(e))
            raise
    
    async def get_user_workload_optimized(
        self,
        session: AsyncSession,
        user_role: UserRole = UserRole.ATENDENTE
    ) -> List[Dict[str, Any]]:
        """
        Carga de trabalho dos usuários (otimizado)
        """
        try:
            # Query otimizada com agregação
            workload_query = select(
                Usuario.id,
                Usuario.username,
                Usuario.email,
                func.count(Conversa.id).label('total_conversations'),
                func.count(Conversa.id).filter(
                    Conversa.estado == ConversationState.ATENDIMENTO
                ).label('active_conversations'),
                func.avg(
                    func.extract('epoch', Conversa.updated_at - Conversa.created_at)
                ).label('avg_response_time')
            ).select_from(
                Usuario
            ).outerjoin(
                Conversa, Usuario.id == Conversa.atendente_id
            ).where(
                Usuario.role == user_role,
                Usuario.ativo == True
            ).group_by(
                Usuario.id, Usuario.username, Usuario.email
            ).order_by(
                func.count(Conversa.id).desc()
            )
            
            result = await session.execute(workload_query)
            rows = result.all()
            
            workload_data = []
            for row in rows:
                workload_data.append({
                    "user_id": str(row.id),
                    "username": row.username,
                    "email": row.email,
                    "total_conversations": row.total_conversations or 0,
                    "active_conversations": row.active_conversations or 0,
                    "avg_response_time": float(row.avg_response_time or 0)
                })
            
            return workload_data
            
        except Exception as e:
            logger.error("Error fetching user workload", error=str(e))
            raise
    
    async def optimize_database_indexes(self, session: AsyncSession) -> Dict[str, Any]:
        """
        Analisar e sugerir otimizações de índices
        """
        try:
            # Queries para analisar performance
            analysis_queries = {
                "slow_conversations": """
                    SELECT COUNT(*) as count
                    FROM conversas c
                    LEFT JOIN mensagens m ON c.id = m.conversa_id
                    WHERE c.created_at > NOW() - INTERVAL '7 days'
                    GROUP BY c.id
                    HAVING COUNT(m.id) > 100
                """,
                "unindexed_searches": """
                    SELECT COUNT(*) as count
                    FROM conversas c
                    WHERE c.estado = 'atendimento'
                    AND c.prioridade > 0
                """,
                "large_conversations": """
                    SELECT c.id, COUNT(m.id) as message_count
                    FROM conversas c
                    LEFT JOIN mensagens m ON c.id = m.conversa_id
                    GROUP BY c.id
                    HAVING COUNT(m.id) > 1000
                    ORDER BY COUNT(m.id) DESC
                    LIMIT 10
                """
            }
            
            analysis_results = {}
            for name, query in analysis_queries.items():
                try:
                    result = await session.execute(query)
                    analysis_results[name] = result.fetchall()
                except Exception as e:
                    analysis_results[name] = f"Error: {str(e)}"
            
            # Sugestões de otimização
            suggestions = [
                "Considere particionar tabela de mensagens por data",
                "Adicione índice composto em (estado, prioridade, created_at)",
                "Implemente arquivamento de conversas antigas",
                "Considere índice parcial para conversas ativas"
            ]
            
            return {
                "analysis": analysis_results,
                "suggestions": suggestions,
                "analyzed_at": func.now()
            }
            
        except Exception as e:
            logger.error("Error in database analysis", error=str(e))
            return {"error": str(e)}


# Instância global
query_optimizer = QueryOptimizer()


# Funções utilitárias para uso comum
async def get_active_conversations_count() -> int:
    """Contar conversas ativas (com cache)"""
    stats = await query_optimizer.get_dashboard_stats_cached()
    return stats.get("active_conversations", 0)


async def get_user_active_conversations(user_id: str) -> List[Dict]:
    """Buscar conversas ativas do usuário (com cache)"""
    return await query_optimizer.get_user_conversations_cached(
        user_id, ConversationState.ATENDIMENTO
    )