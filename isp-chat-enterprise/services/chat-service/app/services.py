#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Serviços de negócio do Chat Service
Implementa lógica de conversas, mensagens, filas e atendimento
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload

from shared.utils.memory_cache import memory_cache
from shared.schemas.chat import (
    ConversationCreate, ConversationUpdate, ConversationResponse,
    MessageCreate, MessageResponse, ConversationListResponse, MessageListResponse
)
from .models import (
    Conversation, Message, Queue, QueueAgent,
    ConversationStatus, MessageType, QueuePriority
)

logger = logging.getLogger(__name__)

class ChatServiceError(Exception):
    """Erro base do Chat Service"""
    pass

class ConversationNotFoundError(ChatServiceError):
    """Conversa não encontrada"""
    pass

class QueueNotFoundError(ChatServiceError):
    """Fila não encontrada"""
    pass

class AgentNotAvailableError(ChatServiceError):
    """Agente não disponível"""
    pass

class ChatService:
    """
    Serviço principal de chat
    Gerencia conversas, mensagens e atendimento
    """
    
    def __init__(self):
        self.cache_ttl = 300  # 5 minutos
    
    # === CONVERSAS ===
    
    async def create_conversation(
        self, 
        db: AsyncSession, 
        conversation_data: ConversationCreate,
        user_id: Optional[str] = None
    ) -> ConversationResponse:
        """
        Criar nova conversa
        
        Args:
            db: Sessão do banco
            conversation_data: Dados da conversa
            user_id: ID do usuário que criou (opcional)
            
        Returns:
            Conversa criada
        """
        try:
            # Verificar se já existe conversa ativa para este cliente
            existing = await self._get_active_conversation_by_phone(
                db, conversation_data.customer_phone
            )
            
            if existing:
                logger.info(f"Conversa ativa encontrada para {conversation_data.customer_phone}")
                return self._conversation_to_response(existing)
            
            # Criar nova conversa
            conversation = Conversation(
                customer_phone=conversation_data.customer_phone,
                customer_name=conversation_data.customer_name,
                priority=conversation_data.priority.value if hasattr(conversation_data.priority, 'value') else conversation_data.priority,
                whatsapp_client_id=getattr(conversation_data, 'whatsapp_client_id', None),
                metadata_json=json.dumps(conversation_data.metadata or {}, ensure_ascii=False)
            )
            
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)
            
            # Adicionar à fila se especificada
            # if conversation_data.queue_id:
            #     await self._add_to_queue(db, str(conversation.id), conversation_data.queue_id)
            
            # Criar mensagem inicial se fornecida
            if hasattr(conversation_data, 'initial_message') and conversation_data.initial_message:
                await self.create_message(db, MessageCreate(
                    conversation_id=str(conversation.id),
                    content=conversation_data.initial_message,
                    message_type='text',
                    sender_type='customer'
                ))
            
            logger.info(f"Conversa criada: {conversation.id} para {conversation_data.customer_phone}")
            
            return self._conversation_to_response(conversation)
            
        except Exception as e:
            logger.error(f"Erro ao criar conversa: {e}")
            await db.rollback()
            raise ChatServiceError(f"Erro ao criar conversa: {e}")
    
    async def get_conversation(self, db: AsyncSession, conversation_id: str) -> Optional[ConversationResponse]:
        """Obter conversa por ID"""
        try:
            # Tentar cache primeiro
            cache_key = f"conversation:{conversation_id}"
            cached = await memory_cache.get(cache_key)
            if cached:
                return ConversationResponse.model_validate(cached)
            
            # Buscar no banco
            result = await db.execute(
                select(Conversation)
                .options(selectinload(Conversation.messages))
                .where(Conversation.id == conversation_id)
            )
            conversation = result.scalar_one_or_none()
            
            if not conversation:
                return None
            
            response = self._conversation_to_response(conversation)
            
            # Cachear resultado
            await memory_cache.set(
                cache_key, 
                response.model_dump(), 
                ttl=self.cache_ttl
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Erro ao obter conversa {conversation_id}: {e}")
            raise ChatServiceError(f"Erro ao obter conversa: {e}")
    
    async def update_conversation(
        self, 
        db: AsyncSession, 
        conversation_id: str, 
        update_data: ConversationUpdate,
        user_id: Optional[str] = None
    ) -> ConversationResponse:
        """Atualizar conversa"""
        try:
            # Buscar conversa
            result = await db.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            conversation = result.scalar_one_or_none()
            
            if not conversation:
                raise ConversationNotFoundError(f"Conversa {conversation_id} não encontrada")
            
            # Atualizar campos
            if update_data.status is not None:
                old_status = conversation.status
                conversation.status = update_data.status.value
                
                # Atualizar timestamps baseado no status
                now = datetime.utcnow()
                if update_data.status == ConversationStatus.IN_SERVICE and old_status == ConversationStatus.WAITING.value:
                    conversation.started_at = now
                elif update_data.status == ConversationStatus.RESOLVED:
                    conversation.resolved_at = now
                    if conversation.started_at:
                        conversation.resolution_time = int((now - conversation.started_at).total_seconds())
                elif update_data.status == ConversationStatus.CLOSED:
                    conversation.closed_at = now
            
            if update_data.agent_id is not None:
                conversation.agent_id = update_data.agent_id
            
            if update_data.priority is not None:
                conversation.priority = update_data.priority.value
            
            if update_data.tags is not None:
                conversation.tags = update_data.tags
            
            if update_data.metadata is not None:
                conversation.extra_data = {**(conversation.extra_data or {}), **update_data.metadata}
            
            conversation.updated_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(conversation)
            
            # Limpar cache
            await memory_cache.delete(f"conversation:{conversation_id}")
            
            logger.info(f"Conversa atualizada: {conversation_id}")
            
            return self._conversation_to_response(conversation)
            
        except ConversationNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Erro ao atualizar conversa {conversation_id}: {e}")
            await db.rollback()
            raise ChatServiceError(f"Erro ao atualizar conversa: {e}")
    
    async def list_conversations(
        self,
        db: AsyncSession,
        page: int = 1,
        per_page: int = 50,
        status: Optional[ConversationStatus] = None,
        agent_id: Optional[str] = None,
        queue_id: Optional[str] = None,
        customer_phone: Optional[str] = None,
        priority: Optional[QueuePriority] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Listar conversas com filtros e paginação"""
        try:
            # Construir query base
            query = select(Conversation)
            count_query = select(func.count(Conversation.id))
            
            # Aplicar filtros
            filters = []
            
            if status:
                filters.append(Conversation.status == status.value)
            
            if agent_id:
                filters.append(Conversation.agent_id == agent_id)
            
            if queue_id:
                filters.append(Conversation.queue_id == queue_id)
            
            if customer_phone:
                filters.append(Conversation.customer_phone.like(f"%{customer_phone}%"))
            
            if priority:
                filters.append(Conversation.priority == priority.value)
            
            if date_from:
                filters.append(Conversation.created_at >= date_from)
            
            if date_to:
                filters.append(Conversation.created_at <= date_to)
            
            if filters:
                query = query.where(and_(*filters))
                count_query = count_query.where(and_(*filters))
            
            # Contar total
            total_result = await db.execute(count_query)
            total = total_result.scalar()
            
            # Aplicar paginação e ordenação
            offset = (page - 1) * per_page
            query = query.order_by(desc(Conversation.updated_at)).offset(offset).limit(per_page)
            
            # Executar query
            result = await db.execute(query)
            conversations = result.scalars().all()
            
            # Converter para response
            conversation_responses = [
                self._conversation_to_response(conv) for conv in conversations
            ]
            
            pages = (total + per_page - 1) // per_page
            
            return {
                "conversations": conversation_responses,
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": pages
            }
            
        except Exception as e:
            logger.error(f"Erro ao listar conversas: {e}")
            raise ChatServiceError(f"Erro ao listar conversas: {e}")
    
    # === MENSAGENS ===
    
    async def create_message(
        self, 
        db: AsyncSession, 
        message_data: MessageCreate,
        user_id: Optional[str] = None
    ) -> MessageResponse:
        """Criar nova mensagem"""
        try:
            # Verificar se conversa existe
            conversation = await self._get_conversation_by_id(db, message_data.conversation_id)
            if not conversation:
                raise ConversationNotFoundError(f"Conversa {message_data.conversation_id} não encontrada")
            
            # Criar mensagem
            message = Message(
                conversation_id=message_data.conversation_id,
                content=message_data.content,
                message_type=message_data.message_type.value if hasattr(message_data.message_type, 'value') else message_data.message_type,
                sender_type=message_data.sender_type if hasattr(message_data, 'sender_type') else 'agent',
                sender_id=user_id,
                metadata_json=json.dumps(message_data.metadata or {}, ensure_ascii=False) if hasattr(message_data, 'metadata') else '{}'
            )
            
            db.add(message)
            
            # Atualizar contador de mensagens na conversa
            conversation.message_count += 1
            conversation.updated_at = datetime.utcnow()
            
            # Calcular tempo de primeira resposta se for outbound
            if (hasattr(message_data, 'sender_type') and message_data.sender_type == 'agent' and 
                not conversation.first_response_time and 
                conversation.created_at):
                
                first_response_time = int((datetime.utcnow() - conversation.created_at).total_seconds())
                conversation.first_response_time = first_response_time
            
            await db.commit()
            await db.refresh(message)
            
            # Limpar cache da conversa
            await memory_cache.delete(f"conversation:{message_data.conversation_id}")
            
            logger.info(f"Mensagem criada: {message.id} na conversa {message_data.conversation_id}")
            
            return self._message_to_response(message)
            
        except ConversationNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Erro ao criar mensagem: {e}")
            await db.rollback()
            raise ChatServiceError(f"Erro ao criar mensagem: {e}")
    
    async def get_conversation_messages(
        self,
        db: AsyncSession,
        conversation_id: str,
        page: int = 1,
        per_page: int = 100,
        message_type: Optional[MessageType] = None
    ) -> Dict[str, Any]:
        """Obter mensagens de uma conversa"""
        try:
            # Verificar se conversa existe
            conversation = await self._get_conversation_by_id(db, conversation_id)
            if not conversation:
                raise ConversationNotFoundError(f"Conversa {conversation_id} não encontrada")
            
            # Construir query
            query = select(Message).where(Message.conversation_id == conversation_id)
            count_query = select(func.count(Message.id)).where(Message.conversation_id == conversation_id)
            
            # Filtrar por tipo se especificado
            if message_type:
                query = query.where(Message.message_type == message_type.value)
                count_query = count_query.where(Message.message_type == message_type.value)
            
            # Contar total
            total_result = await db.execute(count_query)
            total = total_result.scalar()
            
            # Aplicar paginação e ordenação
            offset = (page - 1) * per_page
            query = query.order_by(asc(Message.created_at)).offset(offset).limit(per_page)
            
            # Executar query
            result = await db.execute(query)
            messages = result.scalars().all()
            
            # Converter para response
            message_responses = [
                self._message_to_response(msg) for msg in messages
            ]
            
            pages = (total + per_page - 1) // per_page
            
            return {
                "messages": message_responses,
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": pages
            }
            
        except ConversationNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Erro ao obter mensagens da conversa {conversation_id}: {e}")
            raise ChatServiceError(f"Erro ao obter mensagens: {e}")
    
    # === FILAS ===
    
    async def create_queue(self, db: AsyncSession, queue_data: Dict[str, Any]) -> Dict[str, Any]:
        """Criar nova fila"""
        try:
            queue = Queue(**queue_data)
            db.add(queue)
            await db.commit()
            await db.refresh(queue)
            
            logger.info(f"Fila criada: {queue.id} - {queue.name}")
            
            return self._queue_to_response(queue)
            
        except Exception as e:
            logger.error(f"Erro ao criar fila: {e}")
            await db.rollback()
            raise ChatServiceError(f"Erro ao criar fila: {e}")
    
    async def assign_conversation_to_agent(
        self,
        db: AsyncSession,
        conversation_id: str,
        agent_id: str
    ) -> ConversationResponse:
        """Atribuir conversa a um agente"""
        try:
            # Verificar se agente está disponível
            if not await self._is_agent_available(db, agent_id):
                raise AgentNotAvailableError(f"Agente {agent_id} não está disponível")
            
            # Atualizar conversa
            update_data = ConversationUpdate(
                agent_id=agent_id,
                status=ConversationStatus.IN_SERVICE
            )
            
            return await self.update_conversation(db, conversation_id, update_data)
            
        except (ConversationNotFoundError, AgentNotAvailableError):
            raise
        except Exception as e:
            logger.error(f"Erro ao atribuir conversa {conversation_id} ao agente {agent_id}: {e}")
            raise ChatServiceError(f"Erro ao atribuir conversa: {e}")
    
    # === ESTATÍSTICAS ===
    
    async def get_chat_stats(self, db: AsyncSession, date_from: Optional[datetime] = None) -> Dict[str, Any]:
        """Obter estatísticas do chat"""
        try:
            if not date_from:
                date_from = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Total de conversas
            total_result = await db.execute(select(func.count(Conversation.id)))
            total_conversations = total_result.scalar()
            
            # Conversas ativas
            active_result = await db.execute(
                select(func.count(Conversation.id))
                .where(Conversation.status.in_([
                    ConversationStatus.WAITING.value,
                    ConversationStatus.IN_SERVICE.value
                ]))
            )
            active_conversations = active_result.scalar()
            
            # Conversas aguardando
            waiting_result = await db.execute(
                select(func.count(Conversation.id))
                .where(Conversation.status == ConversationStatus.WAITING.value)
            )
            waiting_conversations = waiting_result.scalar()
            
            # Resolvidas hoje
            resolved_today_result = await db.execute(
                select(func.count(Conversation.id))
                .where(and_(
                    Conversation.status == ConversationStatus.RESOLVED.value,
                    Conversation.resolved_at >= date_from
                ))
            )
            resolved_today = resolved_today_result.scalar()
            
            # Tempo médio de resposta
            avg_response_result = await db.execute(
                select(func.avg(Conversation.first_response_time))
                .where(Conversation.first_response_time.is_not(None))
            )
            avg_response_time = avg_response_result.scalar() or 0
            
            # Tempo médio de resolução
            avg_resolution_result = await db.execute(
                select(func.avg(Conversation.resolution_time))
                .where(Conversation.resolution_time.is_not(None))
            )
            avg_resolution_time = avg_resolution_result.scalar() or 0
            
            return {
                "total_conversations": total_conversations,
                "active_conversations": active_conversations,
                "waiting_conversations": waiting_conversations,
                "resolved_today": resolved_today,
                "avg_response_time": float(avg_response_time),
                "avg_resolution_time": float(avg_resolution_time),
                "agent_utilization": {},  # TODO: Implementar
                "queue_stats": {}  # TODO: Implementar
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            raise ChatServiceError(f"Erro ao obter estatísticas: {e}")
    
    # === MÉTODOS AUXILIARES ===
    
    async def _get_active_conversation_by_phone(
        self, 
        db: AsyncSession, 
        phone: str
    ) -> Optional[Conversation]:
        """Buscar conversa ativa por telefone"""
        result = await db.execute(
            select(Conversation)
            .where(and_(
                Conversation.customer_phone == phone,
                Conversation.status.in_([
                    ConversationStatus.WAITING.value,
                    ConversationStatus.IN_SERVICE.value
                ])
            ))
            .order_by(desc(Conversation.created_at))
        )
        return result.scalar_one_or_none()
    
    async def _get_conversation_by_id(self, db: AsyncSession, conversation_id: str) -> Optional[Conversation]:
        """Buscar conversa por ID"""
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()
    
    async def _add_to_queue(self, db: AsyncSession, conversation_id: str, queue_id: str):
        """Adicionar conversa à fila"""
        # TODO: Implementar lógica de fila
        pass
    
    async def _is_agent_available(self, db: AsyncSession, agent_id: str) -> bool:
        """Verificar se agente está disponível"""
        # TODO: Implementar verificação de disponibilidade
        return True
    
    def _conversation_to_response(self, conversation: Conversation) -> ConversationResponse:
        """Converter modelo para response"""
        import json
        
        # Parse metadata JSON
        try:
            metadata = json.loads(conversation.metadata_json) if conversation.metadata_json else {}
        except (json.JSONDecodeError, TypeError):
            metadata = {}
        
        return ConversationResponse(
            id=str(conversation.id),
            customer_phone=conversation.customer_phone,
            customer_name=conversation.customer_name,
            status=conversation.status,
            priority=conversation.priority,
            agent_id=str(conversation.agent_id) if conversation.agent_id else None,
            whatsapp_client_id=conversation.whatsapp_client_id,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            assigned_at=conversation.assigned_at,
            closed_at=conversation.closed_at,
            last_message=conversation.last_message,
            last_message_at=conversation.last_message_at,
            bot_attempts=conversation.bot_attempts,
            bot_escalated=conversation.bot_escalated,
            message_count=conversation.message_count,
            metadata=metadata
        )
    
    def _message_to_response(self, message: Message) -> MessageResponse:
        """Converter modelo para response"""
        import json
        
        # Parse metadata JSON
        try:
            metadata = json.loads(message.metadata_json) if message.metadata_json else {}
        except (json.JSONDecodeError, TypeError):
            metadata = {}
        
        return MessageResponse(
            id=str(message.id),
            conversation_id=str(message.conversation_id),
            content=message.content,
            message_type=message.message_type,
            sender_type=message.sender_type,
            sender_id=str(message.sender_id) if message.sender_id else None,
            is_read=message.is_read,
            created_at=message.created_at,
            delivered_at=message.delivered_at,
            read_at=message.read_at,
            metadata=metadata
        )
    
    def _queue_to_response(self, queue: Queue):
        """Converter modelo para response"""
        # TODO: Implementar quando Queue for necessário
        return {
            "id": str(queue.id),
            "name": getattr(queue, 'name', ''),
            "description": getattr(queue, 'description', ''),
            "is_active": getattr(queue, 'is_active', True)
        }

# Instância global do serviço
chat_service = ChatService()