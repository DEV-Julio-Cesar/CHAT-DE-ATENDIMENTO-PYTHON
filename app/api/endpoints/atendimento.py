"""
Endpoints de atendimento profissional com estados (Automação, Espera, Ativo)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update
from typing import List, Optional
from datetime import datetime, timedelta
import structlog

from app.core.dependencies import get_current_user, get_db
from app.models.database import (
    Conversa, ConversationState, ClienteWhatsApp, 
    Mensagem, Usuario, SenderType
)
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/atendimento", tags=["atendimento"])


# ============================================================================
# SCHEMAS
# ============================================================================

class ConversaResponse(BaseModel):
    id: str
    cliente_nome: str
    cliente_telefone: str
    estado: str
    prioridade: int
    tentativas_bot: int
    atendente_nome: Optional[str]
    ultima_mensagem: Optional[str]
    ultima_mensagem_em: Optional[datetime]
    tempo_espera_minutos: Optional[int]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AtribuirAtendimentoRequest(BaseModel):
    conversa_id: str


class TransferirAtendimentoRequest(BaseModel):
    conversa_id: str
    atendente_destino_id: str
    motivo: Optional[str] = None


class FinalizarAtendimentoRequest(BaseModel):
    conversa_id: str
    observacoes: Optional[str] = None


# ============================================================================
# ENDPOINTS - LISTAR CONVERSAS POR ESTADO
# ============================================================================

@router.get("/automacao", response_model=List[ConversaResponse])
async def listar_automacao(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    limit: int = Query(50, le=100)
):
    """
    Listar conversas em AUTOMAÇÃO (sendo atendidas pela IA)
    
    - Apenas conversas novas que entraram em contato
    - Ordenadas por prioridade e data de criação
    """
    try:
        # Buscar conversas em automação (últimas 24h)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        query = (
            select(Conversa, ClienteWhatsApp, Mensagem)
            .join(ClienteWhatsApp, Conversa.cliente_id == ClienteWhatsApp.id)
            .outerjoin(
                Mensagem,
                and_(
                    Mensagem.conversa_id == Conversa.id,
                    Mensagem.id == select(Mensagem.id)
                    .where(Mensagem.conversa_id == Conversa.id)
                    .order_by(Mensagem.created_at.desc())
                    .limit(1)
                    .scalar_subquery()
                )
            )
            .where(
                and_(
                    Conversa.estado == ConversationState.AUTOMACAO,
                    Conversa.created_at >= cutoff_time
                )
            )
            .order_by(Conversa.prioridade.desc(), Conversa.created_at.desc())
            .limit(limit)
        )
        
        result = await db.execute(query)
        rows = result.all()
        
        conversas = []
        for conversa, cliente, ultima_msg in rows:
            tempo_espera = None
            if conversa.created_at:
                tempo_espera = int((datetime.utcnow() - conversa.created_at).total_seconds() / 60)
            
            conversas.append(ConversaResponse(
                id=str(conversa.id),
                cliente_nome=cliente.nome,
                cliente_telefone=cliente.telefone,
                estado=conversa.estado.value,
                prioridade=conversa.prioridade,
                tentativas_bot=conversa.tentativas_bot,
                atendente_nome=None,
                ultima_mensagem=ultima_msg.conteudo_decriptografado if ultima_msg else None,
                ultima_mensagem_em=ultima_msg.created_at if ultima_msg else None,
                tempo_espera_minutos=tempo_espera,
                created_at=conversa.created_at,
                updated_at=conversa.updated_at
            ))
        
        return conversas
        
    except Exception as e:
        logger.error("Erro ao listar conversas em automação", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/espera", response_model=List[ConversaResponse])
async def listar_espera(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    limit: int = Query(50, le=100)
):
    """
    Listar conversas em ESPERA (aguardando atendente puxar)
    
    - Conversas que a IA não conseguiu resolver
    - Ordenadas por prioridade e tempo de espera
    """
    try:
        query = (
            select(Conversa, ClienteWhatsApp, Mensagem)
            .join(ClienteWhatsApp, Conversa.cliente_id == ClienteWhatsApp.id)
            .outerjoin(
                Mensagem,
                and_(
                    Mensagem.conversa_id == Conversa.id,
                    Mensagem.id == select(Mensagem.id)
                    .where(Mensagem.conversa_id == Conversa.id)
                    .order_by(Mensagem.created_at.desc())
                    .limit(1)
                    .scalar_subquery()
                )
            )
            .where(Conversa.estado == ConversationState.ESPERA)
            .order_by(Conversa.prioridade.desc(), Conversa.created_at.asc())
            .limit(limit)
        )
        
        result = await db.execute(query)
        rows = result.all()
        
        conversas = []
        for conversa, cliente, ultima_msg in rows:
            tempo_espera = None
            if conversa.updated_at:
                tempo_espera = int((datetime.utcnow() - conversa.updated_at).total_seconds() / 60)
            
            conversas.append(ConversaResponse(
                id=str(conversa.id),
                cliente_nome=cliente.nome,
                cliente_telefone=cliente.telefone,
                estado=conversa.estado.value,
                prioridade=conversa.prioridade,
                tentativas_bot=conversa.tentativas_bot,
                atendente_nome=None,
                ultima_mensagem=ultima_msg.conteudo_decriptografado if ultima_msg else None,
                ultima_mensagem_em=ultima_msg.created_at if ultima_msg else None,
                tempo_espera_minutos=tempo_espera,
                created_at=conversa.created_at,
                updated_at=conversa.updated_at
            ))
        
        return conversas
        
    except Exception as e:
        logger.error("Erro ao listar conversas em espera", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ativo", response_model=List[ConversaResponse])
async def listar_ativo(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    limit: int = Query(50, le=100)
):
    """
    Listar conversas ATIVAS (em atendimento humano)
    
    - Conversas que estão sendo atendidas
    - Pode filtrar por atendente
    """
    try:
        query = (
            select(Conversa, ClienteWhatsApp, Usuario, Mensagem)
            .join(ClienteWhatsApp, Conversa.cliente_id == ClienteWhatsApp.id)
            .outerjoin(Usuario, Conversa.atendente_id == Usuario.id)
            .outerjoin(
                Mensagem,
                and_(
                    Mensagem.conversa_id == Conversa.id,
                    Mensagem.id == select(Mensagem.id)
                    .where(Mensagem.conversa_id == Conversa.id)
                    .order_by(Mensagem.created_at.desc())
                    .limit(1)
                    .scalar_subquery()
                )
            )
            .where(Conversa.estado == ConversationState.ATENDIMENTO)
            .order_by(Conversa.updated_at.desc())
            .limit(limit)
        )
        
        result = await db.execute(query)
        rows = result.all()
        
        conversas = []
        for conversa, cliente, atendente, ultima_msg in rows:
            tempo_espera = None
            if conversa.updated_at:
                tempo_espera = int((datetime.utcnow() - conversa.updated_at).total_seconds() / 60)
            
            conversas.append(ConversaResponse(
                id=str(conversa.id),
                cliente_nome=cliente.nome,
                cliente_telefone=cliente.telefone,
                estado=conversa.estado.value,
                prioridade=conversa.prioridade,
                tentativas_bot=conversa.tentativas_bot,
                atendente_nome=atendente.username if atendente else None,
                ultima_mensagem=ultima_msg.conteudo_decriptografado if ultima_msg else None,
                ultima_mensagem_em=ultima_msg.created_at if ultima_msg else None,
                tempo_espera_minutos=tempo_espera,
                created_at=conversa.created_at,
                updated_at=conversa.updated_at
            ))
        
        return conversas
        
    except Exception as e:
        logger.error("Erro ao listar conversas ativas", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS - AÇÕES DE ATENDIMENTO
# ============================================================================

@router.post("/atribuir")
async def atribuir_atendimento(
    request: AtribuirAtendimentoRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Atendente PUXA uma conversa da fila de ESPERA para ATIVO
    
    - Move conversa de ESPERA → ATENDIMENTO
    - Atribui atendente atual
    """
    try:
        # Buscar conversa
        query = select(Conversa).where(Conversa.id == request.conversa_id)
        result = await db.execute(query)
        conversa = result.scalar_one_or_none()
        
        if not conversa:
            raise HTTPException(status_code=404, detail="Conversa não encontrada")
        
        # Verificar se está em ESPERA
        if conversa.estado != ConversationState.ESPERA:
            raise HTTPException(
                status_code=400, 
                detail=f"Conversa não está em ESPERA (estado atual: {conversa.estado.value})"
            )
        
        # Atribuir atendente e mudar estado
        conversa.estado = ConversationState.ATENDIMENTO
        conversa.atendente_id = current_user["user_id"]
        conversa.updated_at = datetime.utcnow()
        
        await db.commit()
        
        logger.info(
            "Atendimento atribuído",
            conversa_id=str(conversa.id),
            atendente_id=current_user["user_id"],
            atendente_username=current_user["username"]
        )
        
        return {
            "success": True,
            "message": "Atendimento atribuído com sucesso",
            "conversa_id": str(conversa.id),
            "estado": conversa.estado.value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Erro ao atribuir atendimento", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transferir")
async def transferir_atendimento(
    request: TransferirAtendimentoRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Transferir atendimento para outro atendente
    
    - Apenas atendente atual ou admin pode transferir
    - Mantém estado ATENDIMENTO
    """
    try:
        # Buscar conversa
        query = select(Conversa).where(Conversa.id == request.conversa_id)
        result = await db.execute(query)
        conversa = result.scalar_one_or_none()
        
        if not conversa:
            raise HTTPException(status_code=404, detail="Conversa não encontrada")
        
        # Verificar permissão (apenas atendente atual ou admin)
        if (str(conversa.atendente_id) != current_user["user_id"] and 
            current_user["role"] != "admin"):
            raise HTTPException(
                status_code=403, 
                detail="Apenas o atendente atual ou admin pode transferir"
            )
        
        # Verificar se atendente destino existe
        query_destino = select(Usuario).where(Usuario.id == request.atendente_destino_id)
        result_destino = await db.execute(query_destino)
        atendente_destino = result_destino.scalar_one_or_none()
        
        if not atendente_destino:
            raise HTTPException(status_code=404, detail="Atendente destino não encontrado")
        
        # Transferir
        atendente_anterior_id = conversa.atendente_id
        conversa.atendente_id = request.atendente_destino_id
        conversa.updated_at = datetime.utcnow()
        
        # Adicionar mensagem de sistema sobre transferência
        mensagem_sistema = Mensagem(
            conversa_id=conversa.id,
            remetente_tipo=SenderType.SISTEMA,
            remetente_id="system",
            tipo_criptografia=None
        )
        mensagem_sistema.set_conteudo(
            f"Atendimento transferido de {current_user['username']} para {atendente_destino.username}. "
            f"Motivo: {request.motivo or 'Não informado'}"
        )
        db.add(mensagem_sistema)
        
        await db.commit()
        
        logger.info(
            "Atendimento transferido",
            conversa_id=str(conversa.id),
            de_atendente=current_user["user_id"],
            para_atendente=request.atendente_destino_id,
            motivo=request.motivo
        )
        
        return {
            "success": True,
            "message": f"Atendimento transferido para {atendente_destino.username}",
            "conversa_id": str(conversa.id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Erro ao transferir atendimento", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/finalizar")
async def finalizar_atendimento(
    request: FinalizarAtendimentoRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Finalizar atendimento
    
    - Move conversa de ATENDIMENTO → ENCERRADO
    - Registra data de encerramento
    """
    try:
        # Buscar conversa
        query = select(Conversa).where(Conversa.id == request.conversa_id)
        result = await db.execute(query)
        conversa = result.scalar_one_or_none()
        
        if not conversa:
            raise HTTPException(status_code=404, detail="Conversa não encontrada")
        
        # Verificar permissão
        if (str(conversa.atendente_id) != current_user["user_id"] and 
            current_user["role"] != "admin"):
            raise HTTPException(
                status_code=403, 
                detail="Apenas o atendente atual ou admin pode finalizar"
            )
        
        # Finalizar
        conversa.estado = ConversationState.ENCERRADO
        conversa.encerrada_em = datetime.utcnow()
        conversa.updated_at = datetime.utcnow()
        
        # Adicionar mensagem de sistema
        mensagem_sistema = Mensagem(
            conversa_id=conversa.id,
            remetente_tipo=SenderType.SISTEMA,
            remetente_id="system",
            tipo_criptografia=None
        )
        mensagem_sistema.set_conteudo(
            f"Atendimento finalizado por {current_user['username']}. "
            f"Observações: {request.observacoes or 'Nenhuma'}"
        )
        db.add(mensagem_sistema)
        
        await db.commit()
        
        logger.info(
            "Atendimento finalizado",
            conversa_id=str(conversa.id),
            atendente_id=current_user["user_id"],
            observacoes=request.observacoes
        )
        
        return {
            "success": True,
            "message": "Atendimento finalizado com sucesso",
            "conversa_id": str(conversa.id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Erro ao finalizar atendimento", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/estatisticas")
async def estatisticas_atendimento(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Estatísticas de atendimento em tempo real
    """
    try:
        # Contar por estado
        query_automacao = select(func.count(Conversa.id)).where(
            Conversa.estado == ConversationState.AUTOMACAO
        )
        query_espera = select(func.count(Conversa.id)).where(
            Conversa.estado == ConversationState.ESPERA
        )
        query_ativo = select(func.count(Conversa.id)).where(
            Conversa.estado == ConversationState.ATENDIMENTO
        )
        
        result_automacao = await db.execute(query_automacao)
        result_espera = await db.execute(query_espera)
        result_ativo = await db.execute(query_ativo)
        
        total_automacao = result_automacao.scalar()
        total_espera = result_espera.scalar()
        total_ativo = result_ativo.scalar()
        
        return {
            "automacao": total_automacao,
            "espera": total_espera,
            "ativo": total_ativo,
            "total": total_automacao + total_espera + total_ativo
        }
        
    except Exception as e:
        logger.error("Erro ao buscar estatísticas", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
